#!/usr/bin/env python3
"""進捗つきステータスライン。

タスク進行中（.claude/progress.json あり）: 進捗（タスク名・ステップ・経過/見積・残り）を
従来表示（~/.claude/statusline.sh）の前に連結して出す。従来表示は常に消さない。
待機中: 従来表示のみ。
常時: セッションの累計消費を差分読みで出す（⚠ Σ268.4M 出力1,341/t 660t ｜ API換算 $12.30（¥1,968）[S $0.86（¥138）F $4.33（¥693）sub $0.30（¥48）] 直近+$0.04（¥7））。
  料金は transcript の usage を model 別に単価表 _PRICES で自前計算し、[S $0.86 F $4.33 sub $0.30] の内訳を添える（sub はサブエージェント分。Σ と $ に合算）。（入力・5m/1h キャッシュ書込・キャッシュ読出・出力の 5 区分）。
  円は _JPY_PER_USD の固定レート。単価表に無い model があれば末尾に ※。消費を尋ねるターン自体が文脈全量を読み直すため、表示で済ませる。
末尾（B76）: 入力 JSON に Claude Code が渡す `context_window`・`rate_limits` が**あれば**、今の文脈の使用率と
  5 時間枠・週次枠の使用率と戻る時刻を足す（ctx 38% 5h 72%（14:20） 7d 40%（9/28 09:00））。5h が 80% 以上なら ⚠ を付ける
  （表示だけ。止めない）。ctx は `used_percentage`、無ければ `used_tokens`（または `current_usage` の input＋cache の合計）÷
  `max_tokens`（または `context_window_size`）。版やサブスクによって来ないフィールドは出さない（推測で合成しない）。
  inf・nan・負値・100 超の使用率も出さない（変換の失敗で Traceback を出さず、従来表示を消さない）。
  時刻は AIDD_TZ（既定 Asia/Tokyo。subagent-context.py と同じ保守者の時計）。
"""
import datetime
import json
import math
import os
import pathlib
import subprocess
import sys
import time

_FILE = pathlib.Path(__file__).resolve().parent.parent / "progress.json"
# 従来表示の本体。install.sh が hooks/ ごと配るので同じディレクトリを先に見る（無ければ旧配置 ~/.claude/statusline.sh）
_FALLBACK = next((p for p in (pathlib.Path(__file__).resolve().parent / "statusline.sh",
                              pathlib.Path.home() / ".claude" / "statusline.sh") if p.exists()),
                 pathlib.Path.home() / ".claude" / "statusline.sh")
_TOKEN_CACHE = pathlib.Path.home() / ".claude" / ".statusline-tokens.json"
_USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
_OUT_WARN = 1000  # 1 応答あたり出力がこれを超えたら ⚠（H-0 の目安）
_RATE_WARN = 80   # 5 時間枠の使用率がこれ以上なら ⚠（model-routing の「残り 20% 未満」）
_WINDOWS = (("5h", ("five_hour", "5h", "fiveHour")), ("7d", ("seven_day", "7d", "sevenDay")))
_JPY_PER_USD = 160  # API 換算料金の円表示に使う固定レート（保守者が変える）
# $/MTok: (入力, 5m キャッシュ書込, 1h キャッシュ書込, キャッシュ読出, 出力)。出典: platform.claude.com/docs/en/about-claude/pricing（2026-09-25 取得）
# model ID の部分一致で先頭から探す（"opus-5-5" を "opus-5" より先に置く）。一致しない model は集計から外し、表示に ※ を付ける
_PRICES = (
    ("fable-5-1", (10, 12.5, 20, 0.25, 50)), ("mythos-5-1", (10, 12.5, 20, 0.25, 50)),
    ("fable-5", (10, 12.5, 20, 1, 50)), ("mythos-5", (10, 12.5, 20, 1, 50)),
    ("opus-5-5", (4, 5, 8, 0.20, 20)),
    ("opus-5", (5, 6.25, 10, 0.5, 25)), ("opus-4", (5, 6.25, 10, 0.5, 25)),
    ("sonnet-5", (2, 2.5, 4, 0.2, 10)), ("sonnet-4", (3, 3.75, 6, 0.3, 15)),
    ("haiku-4-5", (1, 1.25, 2, 0.1, 5)),
)


def _usd(model: str, u: dict) -> float | None:
    """1 応答の API 換算料金（USD）。単価表に無い model は None。cache_creation の 5m/1h 内訳が無ければ 1h として扱う（Claude Code の既定）。"""
    price = next((p for key, p in _PRICES if key in (model or "")), None)
    if price is None:
        return None
    g = lambda k: int(u.get(k) or 0)
    cc = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else {}
    w5 = int(cc.get("ephemeral_5m_input_tokens") or 0)
    w1 = int(cc.get("ephemeral_1h_input_tokens") or 0)
    if not cc:
        w1 = g("cache_creation_input_tokens")
    toks = (g("input_tokens"), w5, w1, g("cache_read_input_tokens"), g("output_tokens"))
    return sum(n * p for n, p in zip(toks, price)) / 1e6


def _fmt(sec: float) -> str:
    sec = max(0, int(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def _progress_part() -> str:
    """進行中タスクの進捗文字列。無ければ空文字。"""
    if not _FILE.exists():
        return ""
    try:
        d = json.loads(_FILE.read_text(encoding="utf-8"))
        elapsed = time.time() - d["started"]
        est = d["estimate_sec"]
        remain = est - elapsed
        tail = (f"残り {_fmt(remain)}" if remain >= 0
                else f"残り 0:00（超過 +{_fmt(-remain)}）")
        return f"⏱ {d['task']} [{d['step']}] {_fmt(elapsed)}/{_fmt(est)} {tail}"
    except (json.JSONDecodeError, KeyError, OSError):
        return ""  # 壊れた進捗ファイルは無視して従来表示のみ


def _fallback_part(stdin_raw: str) -> str:
    """従来のステータスライン出力。常に表示し続ける。"""
    if _FALLBACK.exists():
        try:
            out = subprocess.run(
                ["bash", str(_FALLBACK)], input=stdin_raw, capture_output=True,
                text=True, timeout=5,
            )
            return out.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            pass
    return os.path.basename(os.getcwd())


def _human(n: int) -> str:
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k"


def _abbr(model: str) -> str:
    """内訳表示用の頭文字（S/O/F/H/M）。単価表に無い model は ?。"""
    for key, ch in (("sonnet", "S"), ("opus", "O"), ("fable", "F"), ("haiku", "H"), ("mythos", "M")):
        if key in (model or ""):
            return ch
    return "?"


def _scan(path: pathlib.Path, st: dict, c: dict, sub: bool) -> None:
    """transcript を前回の位置から差分で読み、c（合計）と c["by"]（model 別）に足す。sub=True はサブエージェント分。"""
    if st.get("offset", 0) > path.stat().st_size:
        st.update(offset=0, last="")
    with path.open("rb") as f:
        f.seek(st.get("offset", 0))
        for raw in f:
            if not raw.endswith(b"\n"):
                break  # 書きかけの行は次回
            st["offset"] = st.get("offset", 0) + len(raw)
            try:
                e = json.loads(raw)
            except ValueError:
                continue
            m = e.get("message") if e.get("type") == "assistant" else None
            if not isinstance(m, dict) or not m.get("usage") or m.get("id") == st.get("last"):
                continue
            st["last"] = m.get("id") or ""
            u = m["usage"]
            tok = sum(int(u.get(k) or 0) for k in _USAGE_KEYS)
            cc = u.get("cache_creation")
            if not u.get("cache_creation_input_tokens") and isinstance(cc, dict):  # 内訳だけ来る形にも備える
                tok += sum(int(v or 0) for v in cc.values() if isinstance(v, (int, float)))
            c["total"] += tok
            usd = _usd(m.get("model") or "", u)
            if sub:
                c["sub_n"] += 1
                if usd is not None:
                    c["usd"] += usd
                    c["sub_usd"] += usd
                continue
            c["out"] += int(u.get("output_tokens") or 0)
            c["n"] += 1
            if usd is None:
                c["unpriced"] += 1
            else:
                c["usd"] += usd
                c["last_usd"] = usd
                k = _abbr(m.get("model") or "")
                c["by"][k] = c["by"].get(k, 0.0) + usd


def _token_part(stdin_raw: str) -> str:
    """セッションの累計消費（Σ）・1 応答あたり出力・応答数・API 換算料金（model 別内訳＋サブエージェント分）。差分読み。"""
    try:
        path = pathlib.Path(json.loads(stdin_raw or "{}").get("transcript_path") or "")
        if not path.is_file():
            return ""
        try:
            c = json.loads(_TOKEN_CACHE.read_text(encoding="utf-8")) if _TOKEN_CACHE.exists() else {}
        except (ValueError, OSError):
            c = {}  # 壊れたキャッシュは捨てて transcript から再集計する（表示を消さない）
        if not isinstance(c, dict) or c.get("path") != str(path) or "by" not in c:
            c = {"path": str(path), "main": {"offset": 0, "last": ""}, "subs": {}, "total": 0, "out": 0, "n": 0,
                 "usd": 0.0, "last_usd": 0.0, "unpriced": 0, "by": {}, "sub_usd": 0.0, "sub_n": 0}
        _scan(path, c["main"], c, sub=False)
        # サブエージェント: <dir>/<session>/subagents/agent-*.jsonl（同じ usage 形式。Σ と $ に合算し、内訳に sub で出す）
        for sp in sorted((path.parent / path.stem / "subagents").glob("*.jsonl")):
            _scan(sp, c["subs"].setdefault(str(sp), {"offset": 0, "last": ""}), c, sub=True)
        _TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        # 5 秒ごとの起動が重なると同じファイルへの同時書き込みで JSON の後ろにゴミが残る（2026-09-25 に発生）。
        # 一時ファイルに書いて os.replace で原子的に置き換える
        tmp = _TOKEN_CACHE.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(c), encoding="utf-8")
        os.replace(tmp, _TOKEN_CACHE)
        if not c["n"]:
            return ""
        per = c["out"] // c["n"]
        warn = "⚠ " if per > _OUT_WARN else ""
        mark = "※" if c.get("unpriced") else ""
        money = lambda v: f"${v:,.2f}（¥{round(v * _JPY_PER_USD):,}）"  # $ は常に小数 2 桁で、必ず円とセット
        parts = [f"{k} {money(v)}" for k, v in sorted(c["by"].items(), key=lambda kv: -kv[1])]
        if c["sub_n"]:
            parts.append(f"sub {money(c['sub_usd'])}")
        detail = f"[{' '.join(parts)}] " if len(parts) > 1 else ""
        cost = f"API換算 {money(c['usd'])}{detail}直近+{money(c['last_usd'])}{mark}"
        return f"{warn}Σ{_human(c['total'])} 出力{per:,}/t {c['n']}t ｜ {cost}"
    except (OSError, ValueError, TypeError, AttributeError):
        return ""  # 表示の失敗で従来表示を消さない


def _num(v) -> float | None:
    """有限で 0 以上の数だけを返す（inf・nan・負値・数でないものは None。変換の失敗も None）。"""
    try:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        f = float(v)
        return f if math.isfinite(f) and f >= 0 else None
    except (ValueError, OverflowError, TypeError):
        return None


def _pct(v) -> float | None:
    """使用率として表示できる値（0〜100）。100 超・inf・nan・負値は None（何も足さない）。"""
    f = _num(v)
    return f if f is not None and f <= 100 else None


def _ctx_pct(cw) -> float | None:
    if not isinstance(cw, dict):
        return None
    if "used_percentage" in cw:
        return _pct(cw.get("used_percentage"))
    used = _num(cw.get("used_tokens"))
    cu = cw.get("current_usage")
    if used is None and isinstance(cu, dict):
        vals = [_num(cu.get(k)) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")]
        used = sum(v for v in vals if v is not None) if any(v is not None for v in vals) else None
    size = _num(cw.get("max_tokens")) or _num(cw.get("context_window_size"))
    if used is None or not size:
        return None
    try:
        return _pct(used * 100 / size)
    except (ValueError, OverflowError, TypeError, ZeroDivisionError):
        return None


def _reset_at(v) -> datetime.datetime | None:
    try:
        if _num(v) is not None:
            sec = v / 1000 if v > 1e12 else v      # ミリ秒で来ても秒に直す（inf・nan・負値は _num が落とす）
            return datetime.datetime.fromtimestamp(sec, datetime.timezone.utc)
        if isinstance(v, str) and v.strip():
            d = datetime.datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
    except (ValueError, OverflowError, OSError, TypeError):
        pass
    return None


def _local(d: datetime.datetime) -> datetime.datetime:
    try:
        import zoneinfo
        return d.astimezone(zoneinfo.ZoneInfo(os.environ.get("AIDD_TZ", "Asia/Tokyo")))
    except Exception:   # tzdata が無い環境は OS の時計で出す
        return d.astimezone()


def _limits_part(stdin_raw: str) -> str:
    """文脈の使用率と 5h・7d の使用枠。フィールドが無ければ空文字（推測で合成しない）。"""
    try:
        d = json.loads(stdin_raw or "{}")
        if not isinstance(d, dict):
            return ""
        out = []
        ctx = _ctx_pct(d.get("context_window"))
        if ctx is not None:
            out.append(f"ctx {round(ctx)}%")
        rl = d.get("rate_limits")
        for label, keys in _WINDOWS if isinstance(rl, dict) else ():
            w = next((rl[k] for k in keys if isinstance(rl.get(k), dict)), None)
            pct = _pct(w.get("used_percentage")) if w else None
            if pct is None:
                continue
            txt = f"{label} {round(pct)}%"
            at = _reset_at(w.get("resets_at"))
            if at is not None:
                loc = _local(at)
                far = at - datetime.datetime.now(datetime.timezone.utc) > datetime.timedelta(hours=24)
                txt += f"（{loc.month}/{loc.day} {loc:%H:%M}）" if far else f"（{loc:%H:%M}）"
            if label == "5h" and pct >= _RATE_WARN:
                txt = "⚠ " + txt
            out.append(txt)
        return " ".join(out)
    except (ValueError, OverflowError, TypeError, AttributeError):
        return ""  # 表示の失敗で従来表示を消さない


def main() -> int:
    stdin_raw = sys.stdin.read()
    lines = _fallback_part(stdin_raw).splitlines() or [""]
    # 1 行目: 進捗 ｜ model effort | dir ｜ トークン合計 ｜ API 換算料金 $（¥）直近（2 行目以降の従来表示はそのまま）
    head = [p for p in (_progress_part(), lines[0], _token_part(stdin_raw)) if p]
    print("\n".join([" ｜ ".join(head)] + lines[1:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

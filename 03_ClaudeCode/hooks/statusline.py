#!/usr/bin/env python3
"""進捗つきステータスライン。

タスク進行中（.claude/progress.json あり）: 進捗（タスク名・ステップ・経過/見積・残り）を
従来表示（~/.claude/statusline.sh）の前に連結して出す。従来表示は常に消さない。
待機中: 従来表示のみ。
常時: セッションの累計消費を差分読みで集計し、`今日 ¥x｜本件 ¥y` を出す（2026-11-14 利用者指定。$・Σ・応答数・直近は出さない）。
  料金は transcript の usage を model 別に単価表 _PRICES で自前計算する（サブエージェント分を含む。入力・5m/1h キャッシュ書込・キャッシュ読出・出力の 5 区分）。
  円は _JPY_PER_USD の固定レート。単価表に無い model があれば末尾に ※。本件＝このセッションの合計。
  今日＝_TOKEN_CACHE_DIR のセッション別記録のうち最終更新が今日（AIDD_TZ）のものの合計。
  限界: 日をまたぐセッションは全額が今日に入る（日別の内訳を持たない近似）。
1 行目の並び（2026-11-14 利用者指定で固定）: モデル effort ｜ 作業フォルダ名 ｜ 〜HH:MM ｜ 文脈 12万 ｜ 今日 ¥x｜本件 ¥y ｜ guard×n
  作業フォルダ名は入力の workspace.current_dir（無ければ cwd）の basename。文脈は常時（25 万以上は `☆文脈 26万 → /clear`）。
  cache の項目は出さない（旧 statusline.sh が出しても外す）。条件を満たさない項目は区切りごと出さない。会話記録は末尾 256KB だけ読む。
  〜HH:MM（最後の利用者発言より後の見積の完了予定。過ぎたら 超過+N分。終了の計測行があれば出さない）／
  guard×n（同じ hook の停止が 2 回以上）／文脈 N万（最後の本線応答の入力側。25 万以上は ☆ と → /clear を付ける）。
5 行目以降（2026-11-14 利用者指定）: 稼働中の担当（最終更新 120 秒以内、または最後が未完了の tool_use で最終更新 30 分以内）を 1 本 1 行・起動の早い順に
  `担当 opus·medium 回帰全体 19:09〜 見積6分 経過2分 2/5`。effort・名前・見積は最初の user 本文の担当票
  `[担当票 name=.. effort=.. 見積=N分]`、進捗は assistant 本文の最後の `【担当進捗 k/n`。欠けた項目は出さない。
  記録の先頭は 64KB だけ読む。読めない担当の行だけ出さない（起動時刻が取れない記録も出さない）。
  現在時刻は環境変数 AIDD_STATUSLINE_NOW（epoch 秒）で差し替えられる（回帰テスト用）。
末尾（B76。2026-10-06 保守者指定で現在は表示しない。_limits_part は残すが main から呼ばない）: 入力 JSON に Claude Code が渡す `context_window`・`rate_limits` が**あれば**、今の文脈の使用率と
  5 時間枠・週次枠の使用率と戻る時刻を足す（ctx 38% 5h 72%（14:20） 7d 40%（9/28 09:00））。5h が 80% 以上なら ⚠ を付ける
  （表示だけ。止めない）。ctx は `used_percentage`、無ければ `used_tokens`（または `current_usage` の input＋cache の合計）÷
  `max_tokens`（または `context_window_size`）。版やサブスクによって来ないフィールドは出さない（推測で合成しない）。
  inf・nan・負値・100 超の使用率も出さない（変換の失敗で Traceback を出さず、従来表示を消さない）。
  時刻は AIDD_TZ（既定 Asia/Tokyo。subagent-context.py と同じ保守者の時計）。
"""
import datetime
import json
import math
import re
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
# 差分読みキャッシュはセッション（transcript）ごとに分ける。1 ファイル共有だと複数セッションが 5 秒ごとに上書きし合い、
# 毎回リセット→全量読み直しになる（2026-09-25 に発生）
_TOKEN_CACHE_DIR = pathlib.Path.home() / ".claude" / ".statusline-tokens"
_USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
_RATE_WARN = 80   # 5 時間枠の使用率がこれ以上なら ⚠（model-routing の「残り 20% 未満」）
_WINDOWS = (("5h", ("five_hour", "5h", "fiveHour")), ("7d", ("seven_day", "7d", "sevenDay")))
_TAIL_BYTES = 256 * 1024   # 会話記録は末尾だけ読む（5 秒ごとに呼ばれるため全量を読まない）
_CTX_WARN = 250_000        # 本線の入力側トークンがこれ以上なら /clear を促す
_HEAD_BYTES = 64 * 1024    # 担当の記録は先頭（最初の user 本文・起動時刻）をこれだけ読む
_TICKET_RE = re.compile(r"\[担当票([^\]\n]*)\]")
_PROG_RE = re.compile(r"【担当進捗\s*(\d+)\s*/\s*(\d+)")
_PENDING_SEC = 30 * 60     # 最後が未完了の tool_use なら、この秒数まで稼働中とみなす（長いコマンドの担当を落とさない）
_ACTIVE_SEC = 120          # サブエージェントを「稼働中」とみなす最終更新からの秒数
_MODEL_NAMES = {"O": "opus", "S": "sonnet", "F": "fable", "H": "haiku", "M": "mythos", "?": "other"}
_ETA_RES = (re.compile(r"見積[：:]\s*\d+\s*分\s*[（(]\s*(?:完了予定\s*)?(\d{1,2})[:：](\d{2})(?:\s*完了予定)?\s*[）)]"),
            re.compile(r"【見積[：:]\s*\d+\s*分\s*\|\s*開始:\s*\d{1,2}:\d{2}\s*\|\s*終了:\s*(\d{1,2}):(\d{2})"))
_END_RE = re.compile(r"【見積[:：][^】\n]*実測[:：]")
_HOOK_RE = re.compile(r"hook error:\s*\[([^\]]*)\]")
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


def _progress_part(session_id: str = "") -> str:
    """進行中タスクの進捗文字列。無ければ空文字。他セッションの進捗は出さない（2026-11-07 残骸の混入）。"""
    if not _FILE.exists() or not session_id:
        return ""
    try:
        d = json.loads(_FILE.read_text(encoding="utf-8"))
        if d.get("session") != session_id:
            return ""
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
    return ""  # 作業フォルダ名は出さない（2026-11-14 利用者の指定）


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


def _session_cost(path: pathlib.Path) -> dict | None:
    """このセッションの累計（差分読み）を更新して返す。キャッシュは _TOKEN_CACHE_DIR/<session>.json。"""
    cache = _TOKEN_CACHE_DIR / f"{path.stem}.json"
    try:
        c = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    except (ValueError, OSError):
        c = {}  # 壊れたキャッシュは捨てて transcript から再集計する（表示を消さない）
    if not isinstance(c, dict) or c.get("path") != str(path) or "by" not in c:
        c = {"path": str(path), "main": {"offset": 0, "last": ""}, "subs": {}, "total": 0, "out": 0, "n": 0,
             "usd": 0.0, "last_usd": 0.0, "unpriced": 0, "by": {}, "sub_usd": 0.0, "sub_n": 0}
    _scan(path, c["main"], c, sub=False)
    # サブエージェント: <dir>/<session>/subagents/agent-*.jsonl（同じ usage 形式。合計に足す）
    for sp in sorted(_sub_dir(path).glob("*.jsonl")):
        _scan(sp, c["subs"].setdefault(str(sp), {"offset": 0, "last": ""}), c, sub=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    # 5 秒ごとの起動が重なると同じファイルへの同時書き込みで JSON の後ろにゴミが残る（2026-09-25 に発生）。
    # 一時ファイルに書いて os.replace で原子的に置き換える
    tmp = cache.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(c), encoding="utf-8")
    os.replace(tmp, cache)
    return c


def _today_usd() -> float:
    """最終更新が今日（AIDD_TZ）のセッション別記録の合計 USD。日をまたぐセッションは全額が今日に入る（近似）。"""
    today, total = _local(_now()).date(), 0.0
    for f in _TOKEN_CACHE_DIR.glob("*.json"):
        try:
            mt = datetime.datetime.fromtimestamp(f.stat().st_mtime, datetime.timezone.utc)
            if _local(mt).date() == today:
                total += float(json.loads(f.read_text(encoding="utf-8")).get("usd") or 0)
        except (OSError, ValueError, TypeError, AttributeError):
            continue  # 壊れた記録はその 1 件だけ外す
    return total


def _token_part(stdin_raw: str) -> str:
    """`今日 ¥x｜本件 ¥y`（API 換算の円。$・Σ・応答数は出さない）。差分読み。"""
    try:
        path = _transcript(stdin_raw)
        c = _session_cost(path) if path else None
        if not c or not c["n"]:
            return ""
        mark = "※" if c.get("unpriced") else ""
        yen = lambda v: f"¥{round(v * _JPY_PER_USD):,}"
        return f"今日 {yen(_today_usd())}｜本件 {yen(c['usd'])}{mark}"
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
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


def _now() -> datetime.datetime:
    """現在時刻（UTC）。AIDD_STATUSLINE_NOW（epoch 秒）があればそれを使う（回帰テストの差し替え口）。"""
    try:
        return datetime.datetime.fromtimestamp(float(os.environ["AIDD_STATUSLINE_NOW"]), datetime.timezone.utc)
    except (KeyError, ValueError, OverflowError, OSError):
        return datetime.datetime.now(datetime.timezone.utc)


def _transcript(stdin_raw: str) -> pathlib.Path | None:
    d = json.loads(stdin_raw or "{}")
    p = pathlib.Path(d.get("transcript_path") or "") if isinstance(d, dict) else None
    return p if p and d.get("transcript_path") and p.is_file() else None


def _sub_dir(path: pathlib.Path) -> pathlib.Path:
    return path.parent / path.stem / "subagents"


def _tail(path: pathlib.Path, limit: int = _TAIL_BYTES) -> list:
    """末尾 limit バイトの JSONL を dict の列で返す。途中から読んだ先頭行と壊れた行は捨てる。"""
    size = path.stat().st_size
    with path.open("rb") as f:
        f.seek(max(0, size - limit))
        raw = f.read().split(b"\n")
    if size > limit:
        raw = raw[1:]
    return _rows(raw)


def _head(path: pathlib.Path, limit: int = _HEAD_BYTES) -> list:
    """先頭 limit バイトの JSONL を dict の列で返す。途中で切れた末尾行と壊れた行は捨てる。"""
    with path.open("rb") as f:
        data = f.read(limit)
    raw = data.split(b"\n")
    return _rows(raw[:-1] if len(data) >= limit else raw)


def _rows(raw: list) -> list:
    out = []
    for line in raw:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict):
            out.append(e)
    return out


def _texts(content, kind: str) -> list:
    """message.content から kind（text / tool_result）の本文を取り出す。"""
    if isinstance(content, str):
        return [content] if kind == "text" else []
    out = []
    for b in content if isinstance(content, list) else ():
        if not isinstance(b, dict) or b.get("type") != kind:
            continue
        v = b.get("text") if kind == "text" else b.get("content")
        if isinstance(v, list):
            v = "\n".join(x.get("text", "") for x in v if isinstance(x, dict))
        if isinstance(v, str):
            out.append(v)
    return out


def _since_user(entries: list) -> list:
    """最後の利用者発言（tool_result でない user の本文）より後の記録。"""
    idx = 0
    for i, e in enumerate(entries):
        m = e.get("message")
        if e.get("type") == "user" and not e.get("isMeta") and isinstance(m, dict) and _texts(m.get("content"), "text"):
            idx = i + 1
    return entries[idx:]


def _eta_part(after: list) -> str:
    """最後の見積の完了予定 `〜HH:MM`（過ぎたら `超過+N分`）。後に終了の計測行があれば空。"""
    body = "\n".join(t for e in after if e.get("type") == "assistant" and isinstance(e.get("message"), dict)
                     for t in _texts(e["message"].get("content"), "text"))
    hits = [(m.start(), m) for r in _ETA_RES for m in r.finditer(body)]
    if not hits:
        return ""
    pos, m = max(hits, key=lambda h: h[0])
    if _END_RE.search(body, pos + 1):
        return ""
    now = _local(_now())
    due = now.replace(hour=int(m.group(1)) % 24, minute=int(m.group(2)) % 60, second=0, microsecond=0)
    if due - now > datetime.timedelta(hours=12):
        due -= datetime.timedelta(days=1)   # 日をまたいだ見積（23:50 に出した 00:10 等）
    elif now - due > datetime.timedelta(hours=12):
        due += datetime.timedelta(days=1)
    over = (now - due).total_seconds()
    return f"超過+{int(over // 60)}分" if over > 0 else f"〜{due:%H:%M}"


def _ticket(head: list) -> dict:
    """最初の user 本文の先頭付近（1000 字）にある担当票の name・effort・見積（分の数字）。無ければ空。"""
    first = next((e for e in head if e.get("type") == "user" and isinstance(e.get("message"), dict)), None)
    text = "\n".join(_texts(first["message"].get("content"), "text"))[:1000] if first else ""
    hit = _TICKET_RE.search(text)
    kv = dict(t.split("=", 1) for t in (hit.group(1).split() if hit else ()) if "=" in t)
    est = re.match(r"(\d+)", kv.get("見積", ""))
    return {"name": kv.get("name", ""), "effort": kv.get("effort", ""), "est": int(est.group(1)) if est else None}


def _agent_type(sp: pathlib.Path, head: list) -> str:
    """エージェント種別。記録の agentType か隣の <名前>.meta.json の agentType（どちらも無ければ空）。"""
    for e in head:
        if isinstance(e.get("agentType"), str) and e["agentType"]:
            return e["agentType"]
    meta = sp.with_suffix(".meta.json")
    try:
        v = json.loads(meta.read_text(encoding="utf-8")).get("agentType") if meta.is_file() else ""
    except (OSError, ValueError, AttributeError):
        v = ""
    return v if isinstance(v, str) else ""


def _agent_line(sp: pathlib.Path, now: datetime.datetime) -> tuple:
    """担当 1 本の (起動時刻, 行)。起動時刻が取れなければ ValueError（その担当の行は出さない）。"""
    head, tail = _head(sp), _tail(sp, 64 * 1024)
    start = _reset_at(head[0].get("timestamp")) if head else None
    if start is None:
        raise ValueError("no start")
    said = [e["message"] for e in tail if e.get("type") == "assistant" and isinstance(e.get("message"), dict)]
    model = _MODEL_NAMES[_abbr(next((m.get("model") for m in reversed(said) if m.get("model")), ""))]
    t = _ticket(head)
    words = ["担当", f"{model}·{t['effort']}" if t["effort"] else model]
    name = t["name"] or _agent_type(sp, head)
    words += ([name] if name else []) + [f"{_local(start):%H:%M}〜"]
    el = int(max(0.0, (now - start).total_seconds()) // 60)
    words += ([f"見積{t['est']}分"] if t["est"] is not None else []) + [f"経過{el}分"]
    if t["est"] is not None and el > t["est"]:
        words.append(f"超過+{el - t['est']}分")
    prog = [m for x in said for b in _texts(x.get("content"), "text") for m in _PROG_RE.finditer(b)]
    if prog:
        words.append(f"{prog[-1].group(1)}/{prog[-1].group(2)}")
    return start, " ".join(words)


def _running(sp: pathlib.Path, now_ts: float) -> bool:
    """最終更新 _ACTIVE_SEC 秒以内、または最後のエントリが tool_use の assistant で最終更新 _PENDING_SEC 秒以内。"""
    age = now_ts - sp.stat().st_mtime
    if age <= _ACTIVE_SEC:
        return True
    if age > _PENDING_SEC:
        return False
    try:
        rows = _tail(sp)
        m = rows[-1].get("message") if rows and rows[-1].get("type") == "assistant" else None
        blocks = m.get("content") if isinstance(m, dict) else None
        return any(isinstance(b, dict) and b.get("type") == "tool_use" for b in blocks or ())
    except Exception:   # 判定できなければ 120 秒の条件だけで判断する
        return False


def _folder_part(stdin_raw: str) -> str:
    """入力の workspace.current_dir（無ければ cwd）の basename。取れなければ空。"""
    try:
        d = json.loads(stdin_raw or "{}")
        ws = d.get("workspace") if isinstance(d, dict) else None
        cur = (ws.get("current_dir") if isinstance(ws, dict) else None) or (d.get("cwd") if isinstance(d, dict) else None)
        return os.path.basename(cur.rstrip("/")) if isinstance(cur, str) else ""
    except (ValueError, AttributeError):
        return ""


def _agent_lines(stdin_raw: str) -> list:
    """稼働中（最終更新 _ACTIVE_SEC 秒以内）の担当を 1 本 1 行、起動の早い順に。読めない担当は外す。"""
    try:
        path = _transcript(stdin_raw)
        subs = sorted(_sub_dir(path).glob("*.jsonl")) if path else []
    except (OSError, ValueError, TypeError, AttributeError):
        return []
    now, rows = _now(), []
    for sp in subs:
        try:
            if _running(sp, now.timestamp()):
                rows.append(_agent_line(sp, now))
        except Exception:   # 1 本の失敗で他の担当・ステータスラインを消さない
            continue
    return [line for _, line in sorted(rows, key=lambda r: r[0])]


def _hook_name(inner: str) -> str:
    toks = [t for t in re.findall(r"[\w.\-]+", inner) if not t.startswith("-")]
    if not toks:
        return "hook"
    return toks[-1].rsplit(".", 1)[0].split("-")[-1] or "hook"


def _guard_part(after: list) -> str:
    """最後の利用者発言より後で、同じ hook の停止（`hook error:`）が 2 回以上なら `名前×n`。"""
    n = {}
    for e in after:
        m = e.get("message")
        for t in _texts(m.get("content"), "tool_result") if e.get("type") == "user" and isinstance(m, dict) else ():
            if "hook error:" not in t:
                continue
            hit = _HOOK_RE.search(t)
            k = _hook_name(hit.group(1)) if hit else "hook"
            n[k] = n.get(k, 0) + 1
    k, v = max(n.items(), key=lambda kv: kv[1], default=("", 0))
    return f"{k}×{v}" if v >= 2 else ""


def _ctx_part(entries: list) -> str:
    """最後の本線応答の入力側（input＋cache_creation＋cache_read）を `文脈 12万`。_CTX_WARN 以上は `☆文脈 26万 → /clear`。"""
    for e in reversed(entries):
        m = e.get("message")
        if e.get("type") == "assistant" and not e.get("isSidechain") and isinstance(m, dict) and isinstance(m.get("usage"), dict):
            u = m["usage"]
            tok = sum(int(u.get(k) or 0) for k in _USAGE_KEYS[:3])
            return f"☆文脈 {tok // 10000}万 → /clear" if tok >= _CTX_WARN else f"文脈 {tok // 10000}万"
    return ""


def _signals(stdin_raw: str) -> list:
    """1 行目の信号を仕様の順（完了予定・hook 停止・文脈）で返す。項目ごとに失敗を閉じ込める。"""
    try:
        path = _transcript(stdin_raw)
        entries = _tail(path) if path else []
    except (OSError, ValueError, TypeError, AttributeError):
        return []
    after = _since_user(entries)
    out = []
    for fn, arg in ((_eta_part, after), (_guard_part, after), (_ctx_part, entries)):
        try:
            out.append(fn(arg) if arg is not None else "")
        except Exception:   # 1 項目の失敗で他の表示を消さない
            out.append("")
    return out


def main() -> int:
    stdin_raw = sys.stdin.read()
    lines = _fallback_part(stdin_raw).splitlines() or [""]
    # 1 行目: 進捗 ｜ model effort ｜ API 換算料金（作業フォルダ名は出さない。2026-11-14 利用者の指定） $（¥）直近（2 行目以降の従来表示はそのまま）
    # 区切りは「｜」に統一する（従来表示は半角「|」で出すため置き換える）。末尾に文脈・5h・7d の使用率（B76）
    # 1 行目は改行せず 1 行で出す（保守者の指定）。区切りは「｜」に統一、末尾に文脈・5h・7d の使用率（B76）
    # ctx・5h・7d は出さない（2026-10-06 保守者の指定）
    try:
        sid = str(json.loads(stdin_raw or "{}").get("session_id") or "")
    except (ValueError, AttributeError):
        sid = ""
    model = " ｜ ".join(p for p in lines[0].split(" | ") if p and not re.match(r"cache\b", p))
    eta, guard, ctx = (_signals(stdin_raw) + ["", "", ""])[:3]
    parts = (_progress_part(sid), model, _folder_part(stdin_raw), eta, ctx, _token_part(stdin_raw), guard)
    head = [p for p in parts if p]
    print("\n".join([" ｜ ".join(head)] + lines[1:] + _agent_lines(stdin_raw)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""evidence.py — キットの効果を数字で示す「証拠レポート」を Markdown で出す（ハッカソン審査・README 用）。

入力（すべて任意。無いものは「未記録」と出して続ける）:
  ~/.claude/tool-time.json の history（[見積分, 実測分]。tool-timer.py の record/factor と同じ形）
  02_共通/ツール/estimate/log.csv（est.py の COLS。判定は est.py weekly と同じ）
  .claude/hook-decisions.log（secret_patterns.log_decision の JSONL）
  .claude/e2e-history.jsonl（e2e_history.py の JSONL）

使い方:
  python3 02_共通/ツール/evidence.py [--since 30] [--out evidence.md]
      [--tool-time PATH] [--est-log PATH] [--hook-log PATH] [--e2e PATH]
  python3 02_共通/ツール/evidence.py --acceptance [--root .] [--base main] [--gate-log P] [--sbom P]
      [--approval-log P] [--config-log P]   # 検収用の証跡3点（ゲート結果・構成の記録・実行の証跡）
注: tool-time.json の history には日時が無いため --since は効かない（全件）。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics as stt
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
NA = "未記録"


def pct(n: float, d: float) -> str:
    return f"{n / d * 100:.1f}%" if d else "—"


def to_epoch(v: str) -> float | None:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        pass
    for fmt in (None, "%Y-%m-%dT%H:%M:%S%z"):
        try:
            d = datetime.fromisoformat(v.replace("Z", "+00:00")) if fmt is None else datetime.strptime(v, fmt)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.timestamp()
        except ValueError:
            continue
    return None


def read_jsonl(p: Path) -> list[dict] | None:
    if not p.is_file():
        return None
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def in_window(rec_time, since: float) -> bool:
    t = to_epoch(str(rec_time or ""))
    return t is None or t >= since   # 日時の無い行は落とさない


def sec_tool_time(p: Path) -> tuple[list[str], int]:
    L = ["## 見積校正（tool-timer）", ""]
    try:
        h = json.loads(p.read_text(encoding="utf-8")).get("history", [])
    except Exception:
        h = None
    if h is None:
        return L + ["| 項目 | 値 |", "|---|---|", f"| 件数 | {NA} |", ""], 0
    h = [x for x in h if isinstance(x, list) and len(x) == 2 and isinstance(x[0], (int, float)) and x[0] > 0
         and isinstance(x[1], (int, float))]
    rs = [a / e for e, a in h]
    inr = sum(1 for r in rs if 0.67 <= r <= 1.5)
    L += ["| 項目 | 値 |", "|---|---|", f"| 件数 | {len(h)} |",
          f"| 校正係数（実測/見積の中央値） | {stt.median(rs):.2f} |" if rs else "| 校正係数（実測/見積の中央値） | — |",
          f"| 0.67〜1.5 に収まった割合 | {pct(inr, len(rs))} |", ""]
    return L, len(h)


def sec_est(p: Path, since: float) -> tuple[list[str], int]:
    L = ["## 見積精度（est.py 種別別）", ""]
    if not p.is_file():
        return L + ["| 種別 | 件数 | 比の中央値 | 範囲外割合 |", "|---|---|---|---|", f"| {NA} | 0 | — | — |", ""], 0
    fin = []
    with p.open(encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            try:
                e, a = int(float(r.get("est_s") or 0)), int(float(r.get("actual_s") or 0))
            except ValueError:
                continue
            t = to_epoch(r.get("t0", ""))
            if (r.get("unfinished") or "0") != "0" or e <= 0 or (t is not None and t < since):
                continue
            fin.append((r.get("kind") or "（なし）", e, a))
    ok = lambda e, a: abs(a - e) <= 60 if a < 300 else 0.67 <= a / e <= 1.5   # est.py weekly と同じ判定
    L += ["| 種別 | 件数 | 比の中央値 | 範囲外割合 |", "|---|---|---|---|"]
    for k in sorted({x[0] for x in fin}):
        ks = [x for x in fin if x[0] == k]
        L.append(f"| {k} | {len(ks)} | {stt.median(a / e for _, e, a in ks):.2f} | {pct(sum(not ok(e, a) for _, e, a in ks), len(ks))} |")
    if fin:
        L.append(f"| 合計 | {len(fin)} | {stt.median(a / e for _, e, a in fin):.2f} | {pct(sum(not ok(e, a) for _, e, a in fin), len(fin))} |")
    else:
        L.append(f"| {NA} | 0 | — | — |")
    return L + [""], len(fin)


def sec_hooks(p: Path, since: float) -> tuple[list[str], int]:
    L = ["## hook 判定（誤検知率の目安 = override ÷ (deny+warn)）", ""]
    hdr = ["| hook | deny | warn | override | 誤検知率の目安 |", "|---|---|---|---|---|"]
    recs = read_jsonl(p)
    if recs is None:
        return L + hdr + [f"| {NA} | 0 | 0 | 0 | — |", ""], 0
    recs = [r for r in recs if in_window(r.get("time"), since)]
    agg: dict[str, dict[str, int]] = {}
    for r in recs:
        d = str(r.get("decision", ""))
        d = "deny" if d == "block" else d   # block は deny と同じ扱い
        if d in ("deny", "warn", "override"):
            agg.setdefault(str(r.get("hook", "?")), {"deny": 0, "warn": 0, "override": 0})[d] += 1
    L += hdr
    tot = {"deny": 0, "warn": 0, "override": 0}
    for h in sorted(agg):
        c = agg[h]
        for k in tot:
            tot[k] += c[k]
        L.append(f"| {h} | {c['deny']} | {c['warn']} | {c['override']} | {pct(c['override'], c['deny'] + c['warn'])} |")
    if agg:
        L.append(f"| 合計 | {tot['deny']} | {tot['warn']} | {tot['override']} | {pct(tot['override'], tot['deny'] + tot['warn'])} |")
    else:
        L.append(f"| {NA} | 0 | 0 | 0 | — |")
    return L + [""], sum(tot.values())


def sec_e2e(p: Path, since: float) -> tuple[list[str], int]:
    L = ["## E2E（e2e_history）", "", "| 項目 | 値 |", "|---|---|"]
    recs = read_jsonl(p)
    if recs is None:
        return L + [f"| 実行数 | {NA} |", ""], 0
    recs = [r for r in recs if in_window(r.get("time"), since)]
    eff = [r.get("outcome") for r in recs if r.get("outcome") in ("pass", "fail", "flaky")]
    runs = len({r.get("run") for r in recs})
    tests = len({(r.get("file"), r.get("title"), r.get("project")) for r in recs})
    n = len(eff)
    L += [f"| 実行数（run） | {runs} |", f"| テスト数 | {tests} |", f"| 判定対象の結果数 | {n} |",
          f"| 通過率（pass ÷ 判定対象） | {pct(eff.count('pass'), n)} |",
          f"| flaky 率（flaky ÷ 判定対象） | {pct(eff.count('flaky'), n)} |", ""]
    return L, n


# ---- --acceptance（検収用の証跡3点） ----
def esc(v) -> str:
    return str(v).replace("|", "\\|").replace("\n", " ")


def git(root: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def read_gate_log(p: Path) -> list[tuple[str, str]] | None:
    if not p.is_file():
        return None
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("{"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if isinstance(d, dict):
                out.append((str(d.get("gate") or d.get("name") or "?"), str(d.get("result") or d.get("status") or "?")))
        elif "\t" in line:
            n, r = line.split("\t", 1)
            out.append((n.strip(), r.strip()))
    return out


def judge(r: str) -> str:
    x = r.lower()
    if x in ("pass", "passed", "ok", "success", "合格", "0"):
        return "合格"
    if x in ("fail", "failed", "ng", "error", "不合格"):
        return "不合格"
    if x in ("skip", "skipped", "not run", "未実行", ""):
        return "未実行"
    return esc(r)


def acc_gates(a, root: Path, since: float) -> list[str]:
    L = ["## 1. ゲート結果", "", "| ゲート | 結果 |", "|---|---|"]
    g = read_gate_log(Path(a.gate_log).expanduser()) if a.gate_log else None
    if g:
        L += [f"| {esc(n)} | {judge(r)} |" for n, r in g]
    else:
        L.append(f"| {NA} | 未実行 |")
    L.append("")
    hs, _ = sec_hooks(Path(a.hook_log).expanduser(), since)
    L += ["### hook 判定"] + hs[1:]
    L += ["### テストの削除・スキップ・期待値変更（test-weaken-check）", ""]
    if not a.base:
        return L + ["| 項目 | 値 |", "|---|---|", "| 実行 | 未実行（--base 無し） |", ""]
    try:
        r = subprocess.run([sys.executable, str(KIT / "02_共通" / "ツール" / "test-weaken-check.py"),
                            "--base", a.base, "--root", str(root)], capture_output=True, text=True, timeout=120)
        rc, body = r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        rc, body = 2, str(e)
    res = {0: "合格（NG なし）", 1: "不合格（NG あり）"}.get(rc, "判定不能")
    L += ["| 項目 | 値 |", "|---|---|", f"| 基準 | {esc(a.base)} |", f"| 結果 | {res}（exit={rc}） |", ""]
    if body:
        L += ["```", body, "```", ""]
    return L


def deps(root: Path) -> list[tuple[str, str, str]]:
    out = []
    for f in sorted(root.glob("requirements*.txt")):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            m = re.match(r"([A-Za-z0-9_.\-\[\]]+)\s*(.*)", line)
            if m:
                out.append((f.name, m.group(1), m.group(2).strip() or "—"))
    pj = root / "package.json"
    if pj.is_file():
        try:
            d = json.loads(pj.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        for k in ("dependencies", "devDependencies"):
            v = d.get(k) if isinstance(d, dict) else None
            if isinstance(v, dict):
                out += [(f"package.json {k}", n, str(ver)) for n, ver in sorted(v.items())]
    return out


def sbom_count(p: Path) -> str:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return "読めない"
    if isinstance(d, dict):
        for k in ("components", "packages"):   # CycloneDX / SPDX
            if isinstance(d.get(k), list):
                return str(len(d[k]))
    return "件数不明"


def acc_config(a, root: Path, since: float) -> list[str]:
    L = ["## 2. 構成の記録", "", "### AI 設定の変更（ai-config-log）", ""]
    recs = read_jsonl(Path(a.config_log).expanduser())
    if not recs:
        L += ["| 項目 | 値 |", "|---|---|", f"| 変更記録 | {NA} |", ""]
    else:
        recs = [r for r in recs if in_window(r.get("time"), since)]
        keys: list[str] = []
        for r in recs:
            keys += [k for k in r if k not in keys]
        L += ["| " + " | ".join(esc(k) for k in keys) + " |", "|" + "---|" * len(keys)]
        for r in recs:
            L.append("| " + " | ".join(esc(", ".join(map(str, r[k])) if isinstance(r.get(k), list)
                                           else r.get(k, "")) for k in keys) + " |")
        L.append("")
    kv = root / "KIT_VERSION"
    if not kv.is_file():
        kv = KIT / "KIT_VERSION"
    ver = kv.read_text(encoding="utf-8").strip() if kv.is_file() else NA
    L += ["### 版と依存", "", "| 項目 | 値 |", "|---|---|", f"| KIT_VERSION | {esc(ver)} |"]
    L.append(f"| SBOM の件数 | {sbom_count(Path(a.sbom).expanduser()) if a.sbom else NA} |")
    ds = deps(root)
    L += [f"| 依存の件数 | {len(ds) if ds else NA} |", ""]
    if ds:
        L += ["| 出所 | 名前 | 版 |", "|---|---|---|"] + [f"| {esc(s)} | {esc(n)} | {esc(v)} |" for s, n, v in ds] + [""]
    return L


def acc_run(a, since: float) -> list[str]:
    L = ["## 3. 実行の証跡", ""]
    s1, _ = sec_tool_time(Path(a.tool_time).expanduser())
    s4, _ = sec_e2e(Path(a.e2e).expanduser(), since)
    recs = read_jsonl(Path(a.hook_log).expanduser())
    stop = NA if recs is None else str(sum(1 for r in recs if in_window(r.get("time"), since)
                                          and str(r.get("decision")) in ("deny", "block")))
    L += ["#" + x if x.startswith("## ") else x for x in s1 + s4]
    L += ["### hook に止められた記録", "", "| 項目 | 値 |", "|---|---|", f"| 件数（deny・block） | {stop} |", ""]
    L += ["### 人の承認記録", ""]
    ap = Path(a.approval_log).expanduser() if a.approval_log else None
    rows = read_jsonl(ap) if ap and ap.suffix == ".jsonl" else None
    if ap is None or not ap.is_file():
        return L + ["| 項目 | 値 |", "|---|---|", f"| 承認記録 | {NA} |", ""]
    if rows:
        keys: list[str] = []
        for r in rows:
            keys += [k for k in r if k not in keys]
        return L + ["| " + " | ".join(esc(k) for k in keys) + " |", "|" + "---|" * len(keys)] + \
            ["| " + " | ".join(esc(r.get(k, "")) for k in keys) + " |" for r in rows] + [""]
    lines = [x for x in ap.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]
    return L + ["| # | 記録 |", "|---|---|"] + [f"| {i} | {esc(x)} |" for i, x in enumerate(lines, 1)] + [""]


def acceptance(a, now: float, since: float) -> str:
    root = Path(a.root).expanduser().resolve()
    rev = git(root, "rev-parse", "--short", "HEAD") or NA
    fmt = lambda t: datetime.fromtimestamp(t).strftime("%Y-%m-%d")
    head = ["# 検収用の証跡", "", "| 項目 | 値 |", "|---|---|", f"| 対象の版 | {esc(rev)} |",
            f"| 作成日時 | {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M')} |",
            f"| 集計期間 | {fmt(since)} 〜 {fmt(now)}（{a.since}日） |", ""]
    tail = ["| 注意 |", "|---|", "| 秘密情報・個人情報を含めない。影響の大きい変更から求める（記事の注意） |", ""]
    return "\n".join(head + acc_gates(a, root, since) + acc_config(a, root, since) + acc_run(a, since) + tail)


def main() -> int:
    ap = argparse.ArgumentParser(description="キットの効果の証拠レポート（Markdown）")
    ap.add_argument("--since", type=int, default=30, help="集計期間の日数（既定 30）")
    ap.add_argument("--out", help="出力ファイル（既定 標準出力）")
    ap.add_argument("--tool-time", default=str(Path.home() / ".claude" / "tool-time.json"))
    ap.add_argument("--est-log", default=str(KIT / "02_共通" / "ツール" / "estimate" / "log.csv"))
    ap.add_argument("--hook-log", default=".claude/hook-decisions.log")
    ap.add_argument("--e2e", default=".claude/e2e-history.jsonl")
    ap.add_argument("--acceptance", action="store_true", help="検収用の証跡3点を出す")
    ap.add_argument("--root", default=".", help="--acceptance: 対象リポジトリ（既定 カレント）")
    ap.add_argument("--base", help="--acceptance: test-weaken-check に渡す基準 rev（無ければ未実行）")
    ap.add_argument("--gate-log", help="--acceptance: ゲート結果（1行1ゲート 名前<TAB>結果 か JSONL）")
    ap.add_argument("--config-log", default=".claude/ai-config-log.jsonl", help="--acceptance: config-snapshot の JSONL")
    ap.add_argument("--sbom", help="--acceptance: SBOM ファイル（CycloneDX / SPDX JSON）")
    ap.add_argument("--approval-log", help="--acceptance: 人の承認記録")
    ap.add_argument("--now", type=float, help=argparse.SUPPRESS)   # 回帰テスト用の現在時刻（epoch）
    a = ap.parse_args()
    now = a.now if a.now is not None else time.time()
    since = now - a.since * 86400
    if a.acceptance:
        text = acceptance(a, now, since)
        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    s1, n1 = sec_tool_time(Path(a.tool_time).expanduser())
    s2, n2 = sec_est(Path(a.est_log).expanduser(), since)
    s3, n3 = sec_hooks(Path(a.hook_log).expanduser(), since)
    s4, n4 = sec_e2e(Path(a.e2e).expanduser(), since)
    fmt = lambda t: datetime.fromtimestamp(t).strftime("%Y-%m-%d")
    head = ["# yuki-aidd-kit 効果の証拠レポート", "", "| 項目 | 値 |", "|---|---|",
            f"| 集計期間 | {fmt(since)} 〜 {fmt(now)}（{a.since}日） |",
            f"| 見積校正の件数 | {n1} |", f"| 見積ログの件数 | {n2} |", f"| hook 判定の件数 | {n3} |", f"| E2E 結果の件数 | {n4} |", ""]
    text = "\n".join(head + s1 + s2 + s3 + s4)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

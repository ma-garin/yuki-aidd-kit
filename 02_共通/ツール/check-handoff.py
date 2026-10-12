#!/usr/bin/env python3
"""check-handoff.py — Codex（別モデル）から返ってきた REPORT.md の先頭 4 行（返却時の状態）を検査する。

`02_共通/ひな形/work-order.md`「返却時の状態」が定める 4 行が揃っていないと、誰も次を持たない状態になる。
受け取る側（Claude・保守者）が目で見て差し戻すのではなく、機械で差し戻せるようにする。
標準ライブラリのみ・Python 3.9 互換・ネット不使用・読むだけ（ファイルを書かない）。Windows でも動く。

検査（どれか 1 つでも当たれば NG・exit 1）:
  H1 先頭 4 行     空行と ``` の行を除いた先頭 4 行が、順に `状態:` `閉じる条件:` `次の担当:` `証跡:` で始まる
                   （区切りは半角 `:`・全角 `：` のどちらでもよい）
  H2 空欄          値が空・`<…>` のまま（ひな形の置き場所が埋まっていない）は NG。分からなければ `unknown` と書く
  H3 状態          `完了` `停止` `ブロック` `unknown` のどれか（`完了 | 停止 | ブロック` をそのまま写したものは NG）
  H4 次の担当      `Claude` `保守者` `Codex` `Codex（再依頼）` `unknown` のどれか
  H5 証跡          `unknown` 以外は --root からの相対パスで、実在するファイル（絶対パス・root の外・存在しないものは NG）。
                   Windows の `\\` 区切りと、バッククォートで囲んだ書き方も受け付ける
  W1 未達・要判断  状態が `停止`／`ブロック` なのに「未達」「要判断」の語が本文に無い（WARN。止めない）

使い方:
  python3 02_共通/ツール/check-handoff.py <REPORT.md> [--root DIR] [--json]
    --root  証跡のパスの起点（既定: REPORT.md のあるディレクトリ。zip を展開した場所）
終了コード: 0=4 行が揃っている / 1=NG あり / 2=REPORT.md が読めない・引数誤り
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

KEYS = ("状態", "閉じる条件", "次の担当", "証跡")
STATES = ("完了", "停止", "ブロック")
OWNERS = ("Claude", "保守者", "Codex", "Codex（再依頼）", "Codex(再依頼)")
UNKNOWN = "unknown"
LINE_RE = re.compile(r"^\s*(?P<key>[^:：]+?)\s*[:：]\s*(?P<val>.*?)\s*$")
PLACEHOLDER_RE = re.compile(r"^<.*>$")


def header_lines(text: str) -> list[tuple[int, str]]:
    """空行とフェンス（``` / ~~~）の行を飛ばした先頭 4 行を (行番号, 本文) で返す。"""
    out: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        s = line.strip().lstrip("﻿")
        if not s or s.startswith("```") or s.startswith("~~~"):
            continue
        out.append((i, s))
        if len(out) == len(KEYS):
            break
    return out


def check_evidence(val: str, root: Path) -> str | None:
    """証跡のパスを検査する。問題があれば理由、無ければ None。"""
    p = val.strip().strip("`").strip().replace("\\", "/")
    if not p:
        return "証跡が空"
    if p.startswith("/") or re.match(r"^[A-Za-z]:/", p):
        return f"証跡は root からの相対パスで書く（絶対パス: {val}）"
    parts = PurePosixPath(p).parts
    if ".." in parts:
        return f"証跡が root の外を指す: {val}"
    f = root.joinpath(*parts)
    if not f.is_file():
        return f"証跡のファイルが無い: {p}（root: {root}）"
    return None


def check(text: str, root: Path) -> tuple[list[str], list[str], dict[str, str]]:
    ng: list[str] = []
    warn: list[str] = []
    values: dict[str, str] = {}
    lines = header_lines(text)
    for idx, key in enumerate(KEYS):
        if idx >= len(lines):
            ng.append(f"H1 先頭 {idx + 1} 行目に `{key}:` が無い（4 行が揃っていない）")
            continue
        lineno, s = lines[idx]
        m = LINE_RE.match(s)
        if not m or m.group("key") != key:
            ng.append(f"H1 {lineno} 行目は `{key}:` で始まるはず（実際: {s[:60]}）")
            continue
        val = m.group("val")
        values[key] = val
        if not val or PLACEHOLDER_RE.match(val):
            ng.append(f"H2 `{key}` が空・置き場所のまま（分からなければ `{UNKNOWN}` と書く）: {lineno} 行目")
            continue
        if val == UNKNOWN:
            continue
        if key == "状態" and val not in STATES:
            ng.append(f"H3 状態は {' / '.join(STATES)} / {UNKNOWN} のどれか（実際: {val}）")
        elif key == "次の担当" and val not in OWNERS:
            ng.append(f"H4 次の担当は Claude / 保守者 / Codex（再依頼） / {UNKNOWN} のどれか（実際: {val}）")
        elif key == "証跡":
            why = check_evidence(val, root)
            if why:
                ng.append(f"H5 {why}")
    if values.get("状態") in ("停止", "ブロック") and not re.search(r"未達|要判断", text):
        warn.append("W1 状態が停止／ブロックなのに「未達・要判断」の記載が無い（理由を書く）")
    return ng, warn, values


def main() -> int:
    ap = argparse.ArgumentParser(description="REPORT.md の返却時の状態 4 行を検査する")
    ap.add_argument("report")
    ap.add_argument("--root", default=None, help="証跡のパスの起点（既定: REPORT.md のディレクトリ）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rp = Path(a.report)
    try:
        text = rp.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as e:
        print(f"判定不能: REPORT.md を読めない（{e}）", file=sys.stderr)
        return 2
    root = Path(a.root) if a.root else rp.resolve().parent
    if not root.is_dir():
        print(f"判定不能: --root がディレクトリではない: {root}", file=sys.stderr)
        return 2
    ng, warn, values = check(text, root)
    if a.json:
        print(json.dumps({"report": str(rp), "ok": not ng, "ng": ng, "warn": warn, "values": values},
                         ensure_ascii=False, indent=2))
    else:
        for r in ng:
            print(f"NG  {r}")
        for r in warn:
            print(f"WARN {r}")
        if ng:
            print(f"差し戻し: {rp}（NG={len(ng)} WARN={len(warn)}）。work-order.md「返却時の状態」の 4 行を先頭に書き直す")
        else:
            print(f"OK: 返却時の状態 4 行が揃っている（NG=0 WARN={len(warn)}）")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())

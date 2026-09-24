#!/usr/bin/env python3
"""baseline.py — 既知の指摘の基準線（baseline）を読み書きする共通部品（B-24 B15。A19 の部品の切り出し）。

check_design.py（デザイン検査）と security-scan.sh（セキュリティ走査）が同じ書式・同じ規律で使う。

書式（1 行 1 件・タブ区切り）:
  規則ID <TAB> 相対パス <TAB> 正規化した行 <TAB> #n [<TAB> 理由 <TAB> 期限(YYYY-MM-DD)]
  - 先頭 4 列が指紋（照合のキー）。#n は同じ「規則・パス・行」の n 番目の出現（number()）。同じ文面の行を
    足したら #2 として新規に数える（「件数は減る方向だけ」を同じ文面の複製ですり抜けさせない）。
  - 5・6 列目（理由・期限）は任意。理由も期限も無い行は 4 列で書く（check_design は 4 列）。
  - 旧形式（#n の列が無い `規則ID 相対パス 正規化した行 [理由 期限]`）は #1 として読む。
  - UTF-8 として読めない・列が足りない・#n が壊れている基準線は BaselineError（判定不能。呼び出し側は exit 2）。
  - security-scan は 3 列目に行そのものではなく `sha256:<先頭16桁>`（正規化した行の指紋）を書く。
    秘密値の指摘で値を基準線に残さないため。
  - 空行と `#` で始まる行は読み飛ばす。
規律（skills/done-gate/SKILL.md）:
  - 件数は減る方向だけ。前回より増える更新は拒否する（update_allowed）。
  - 除外には理由と期限（既定 90 日）。理由なし・期限なし・期限切れの既知は「既知」に数えない（audit_entry）。

部品:
  normalize_line(text) / fingerprint(text) / number(keys) / load(path) / load_keys(path) / save(path, keys, previous, reason, expires)
  update_allowed(existed, prev_total, current_total) / audit_entry(entry, today) / default_expiry(today)
CLI（security-scan.sh から呼ぶ）:
  python3 baseline.py classify --baseline FILE --rows ROWS.tsv --root DIR --out OUT.tsv
         [--write [--reason 理由] [--expires YYYY-MM-DD]]
  ROWS.tsv は security-scan の行（ツール/規則/file:line/重大度/要旨）。重大度が中以上の行だけを基準線で扱う。
  OUT.tsv は入力の各行の末尾に区分（new / known / noreason / expired / low）を足したもの。
  標準出力に `key=value` の集計（known new noreason expired resolved prev current）を出す。
  終了コード: 0 = 分類した／書いた、1 = 増える更新を拒否（書かない）、2 = 使い方の誤り・理由なしで新規を書こうとした
  （標準出力 `write=noreason`）・基準線を読めない（標準出力 `error=基準線を読めない（<path>）`。Traceback は出さない）。
  テスト用に環境変数 AIDD_TODAY=YYYY-MM-DD で「今日」を差し替えられる。

標準ライブラリのみ。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import os
import re
import sys
from pathlib import Path

DEFAULT_EXPIRY_DAYS = 90
Key = tuple[str, str, str, str]   # (規則ID, 相対パス, 正規化した行 or 指紋, "#n")
OCC_RE = re.compile(r"#[1-9][0-9]*")


class BaselineError(Exception):
    """基準線を読めない（UTF-8 でない・形式が壊れている）。判定不能として扱う。"""


class Entry:
    __slots__ = ("key", "reason", "expires")

    def __init__(self, key: Key, reason: str = "", expires: str = "") -> None:
        self.key = key
        self.reason = reason
        self.expires = expires

    def to_line(self) -> str:
        cols = list(self.key)
        if self.reason or self.expires:
            cols += [self.reason, self.expires]
        return "\t".join(cols)


def normalize_line(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(normalize_line(text).encode("utf-8")).hexdigest()[:16]


def _clean(s: str) -> str:
    return re.sub(r"[\t\r\n]+", " ", s).strip()


def number(keys3: list[tuple[str, str, str]]) -> list[Key]:
    """(規則, パス, 行) の並びに出現順の #n を付ける（同じ 3 つ組の 2 つ目は #2）。"""
    seen: dict[tuple[str, str, str], int] = {}
    out: list[Key] = []
    for k in keys3:
        seen[k] = seen.get(k, 0) + 1
        out.append((k[0], k[1], k[2], f"#{seen[k]}"))
    return out


def load(path: Path | None) -> dict[Key, Entry]:
    out: dict[Key, Entry] = {}
    if path is None or not path.is_file():
        return out
    try:
        body = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise BaselineError(f"基準線を読めない（{path}）") from e
    for no, line in enumerate(body.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3 or not all(x.strip() for x in parts[:3]):
            raise BaselineError(f"基準線を読めない（{path}）")
        if len(parts) >= 4 and parts[3].startswith("#"):   # 新形式: 4 列目が #n
            if not OCC_RE.fullmatch(parts[3]) or len(parts) > 6:
                raise BaselineError(f"基準線を読めない（{path}）")
            occ, rest = parts[3], parts[4:]
        else:                                               # 旧形式（#n 無し）は #1
            if len(parts) > 5:
                raise BaselineError(f"基準線を読めない（{path}）")
            occ, rest = "#1", parts[3:]
        key = (parts[0], parts[1], parts[2], occ)
        out[key] = Entry(key, rest[0].strip() if rest else "", rest[1].strip() if len(rest) > 1 else "")
    return out


def load_keys(path: Path | None) -> set[Key]:
    return set(load(path))


def save(path: Path, keys: set[Key], previous: dict[Key, Entry] | None = None,
         reason: str = "", expires: str = "") -> None:
    """keys を書く。previous にある行は理由・期限を引き継ぐ。無い行には reason / expires を付ける。"""
    previous = previous or {}
    entries = [previous[k] if k in previous else Entry(k, _clean(reason), expires if reason else "")
               for k in sorted(keys, key=lambda k: (k[0], k[1], k[2], int(k[3][1:])))]
    body = "\n".join(e.to_line() for e in entries)
    path.write_text(body + ("\n" if body else ""), encoding="utf-8")


def update_allowed(existed: bool, prev_total: int, current_total: int) -> bool:
    """件数が増える更新は拒否（基準線が既にある場合）。初回（ファイルが無い）は常に許可。"""
    return not (existed and current_total > prev_total)


def today() -> _dt.date:
    v = os.environ.get("AIDD_TODAY", "")
    try:
        return _dt.date.fromisoformat(v) if v else _dt.date.today()
    except ValueError:
        return _dt.date.today()


def default_expiry(base: _dt.date | None = None) -> str:
    return ((base or today()) + _dt.timedelta(days=DEFAULT_EXPIRY_DAYS)).isoformat()


def audit_entry(entry: Entry, on: _dt.date | None = None) -> str:
    """"ok" / "noreason"（理由が無い）/ "expired"（期限が無い・読めない・過ぎた）。"""
    if not entry.reason.strip():
        return "noreason"
    try:
        exp = _dt.date.fromisoformat(entry.expires.strip())
    except ValueError:
        return "expired"
    return "expired" if exp < (on or today()) else "ok"


# ---------------------------------------------------------------- security-scan 用
SEV_RANK = {"critical": 4, "high": 3, "medium": 2, "中": 2, "low": 1, "低": 1}


def _row_key(root: Path, tool: str, rule: str, loc: str, summary: str) -> Key:
    m = re.match(r"^(.*):(\d+)$", loc)
    file_s, line_no = (m.group(1), int(m.group(2))) if m else (loc, 0)
    cand = Path(file_s)
    resolved = None
    for c in ([cand] if cand.is_absolute() else [Path.cwd() / cand, root / cand]):
        if c.is_file():
            resolved = c.resolve()
            break
    rel = file_s
    if resolved is not None:
        try:
            rel = resolved.relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = resolved.as_posix()
    text = summary
    if resolved is not None and line_no > 0:
        try:
            lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
            if line_no <= len(lines):
                text = lines[line_no - 1]
        except OSError:
            pass
    return (_clean(f"{tool}:{rule}"), _clean(rel), fingerprint(text))


def classify(a: argparse.Namespace) -> int:
    root = Path(a.root)
    bl = Path(a.baseline)
    existed = bl.is_file()
    try:
        prev = load(bl)
    except BaselineError as e:
        print(f"error={e}")
        return 2
    rows = []
    for line in Path(a.rows).read_text(encoding="utf-8").splitlines():
        cols = line.split("\t")
        if len(cols) < 5 or not cols[0]:
            continue
        tool, rule, loc, sev, summary = cols[:5]
        high = SEV_RANK.get(sev.strip().lower(), SEV_RANK.get(sev.strip(), 0)) >= 2
        rows.append((cols[:5], _row_key(root, tool, rule, loc, summary) if high else None))
    # 同じ「規則・パス・行」の n 番目を区別する（同じ文面の行を足したら新規）
    numbered = iter(number([k for _c, k in rows if k is not None]))
    rows = [(c, next(numbered) if k is not None else None) for c, k in rows]
    current = {k for _c, k in rows if k is not None}

    if a.write:
        if not update_allowed(existed, len(prev), len(current)):
            print(f"write=refused prev={len(prev)} current={len(current)}")
            return 1
        added = current - set(prev)
        if added and not a.reason.strip():
            print(f"write=noreason added={len(added)}")
            return 2
        save(bl, current, prev, a.reason, a.expires or default_expiry())
        print(f"write=ok prev={len(prev)} current={len(current)} added={len(added)}")
        return 0

    on = today()
    counts = {"known": 0, "new": 0, "noreason": 0, "expired": 0}
    out_lines = []
    for cols, k in rows:
        if k is None:
            status = "low"
        elif k not in prev:
            status = "new"
        else:
            st = audit_entry(prev[k], on)
            status = "known" if st == "ok" else st
        if status in counts:
            counts[status] += 1
        out_lines.append("\t".join(cols + [status]))
    Path(a.out).write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    resolved = len(set(prev) - current)
    print(" ".join(f"{k}={v}" for k, v in counts.items()) + f" resolved={resolved} prev={len(prev)} current={len(current)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="基準線（baseline）の共通部品")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("classify", help="security-scan の行を基準線で分類する（--write で書く）")
    c.add_argument("--baseline", required=True)
    c.add_argument("--rows", required=True)
    c.add_argument("--root", default=".")
    c.add_argument("--out", default=os.devnull)
    c.add_argument("--write", action="store_true")
    c.add_argument("--reason", default="")
    c.add_argument("--expires", default="")
    a = ap.parse_args(argv)
    if a.cmd != "classify":
        ap.print_help()
        return 2
    if a.expires:
        try:
            _dt.date.fromisoformat(a.expires)
        except ValueError:
            print(f"❌ --expires は YYYY-MM-DD: {a.expires}", file=sys.stderr)
            return 2
    try:
        return classify(a)
    except BaselineError as e:
        print(f"error={e}")
        return 2
    except Exception as e:   # 判定不能を Traceback で落とさない（呼び出し側は exit 2 を判定不能として扱う）
        print(f"error=基準線を扱えない（{a.baseline}: {e.__class__.__name__}）")
        return 2


if __name__ == "__main__":
    sys.exit(main())

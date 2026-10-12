#!/usr/bin/env python3
"""ツール呼び出しごとに 1 行の観測を `.claude/observations.jsonl` に積む PostToolUse フック（G2）。

圧縮・再開の後に「どのファイルを触ったか」が要約から落ちる。中身は残さず、何をしたかの見出しだけを機械で残し、
session-context.py が再注入に使う（直近の変更 ≦ 8 件）。

  - 1 行の形（JSONL）: {"time", "sid"（session_id の先頭 12 字）, "tool", "op", "path", "summary"}
      op      = read / write / edit / search / run / fetch / その他はツール名の小文字
      path    = file_path・notebook_path・path・pattern・url（プロジェクト内ならプロジェクトからの相対）。
                Bash はコマンドの 1 行目の先頭だけ（ヒアドキュメント `<<` 以降は捨てる）
      summary = 結果の要約 60 字以内（「120行（1〜／全120行）」「新規作成」「編集 2 箇所」「3 件」「出力 4 行」など）
  - 残さないもの: ファイルの中身・Write/Edit の本文・コマンドの出力そのもの（件数と種類だけ）
  - 伏字: 残す文字列はすべて `secret_patterns.mask_secrets` を通す。部品が無ければ何も書かない（伏せずに残さない）
  - `<private>…</private>`: 中を捨ててから残す（閉じ忘れは以降すべて捨てる）。捨てた結果 path が空なら 1 行も残さない
  - 重複の抑止: 直近 20 行に同じ tool＋path＋summary があれば積まない
  - 上限: ファイルが OBS_MAX_BYTES（既定 256KB）を超えたら直近 OBS_KEEP（既定 1000）行に切り詰める
  - 置き場: 環境変数 AIDD_OBSERVATIONS（テスト用）> `$CLAUDE_PROJECT_DIR/.claude/` > 入力の cwd の `.claude/`
  - 失敗しても作業を止めない（fail-open。常に exit 0・無出力）

限界: 失敗したツール（PostToolUseFailure）は記録しない。中身を残さないので「何を決めたか」までは残らない
（決定は CURRENT_STATE.md と ADR に書く）。Codex には PostToolUse の配線が無いので効かない。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

try:
    from secret_patterns import mask_secrets
except ImportError:          # 伏字にできないなら残さない
    mask_secrets = None

FILE_NAME = "observations.jsonl"
SUMMARY_MAX = 60
PATH_MAX = 120
DEDUP_WINDOW = 20
MAX_BYTES = int(os.environ.get("OBS_MAX_BYTES", str(256 * 1024)))
KEEP = int(os.environ.get("OBS_KEEP", "1000"))
SKIP_TOOLS = frozenset({"TodoWrite", "TodoRead", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "ToolSearch"})
OPS = {"Read": "read", "Write": "write", "Edit": "edit", "MultiEdit": "edit", "NotebookEdit": "edit",
       "Grep": "search", "Glob": "search", "Bash": "run", "WebFetch": "fetch", "WebSearch": "fetch"}
_PRIVATE = re.compile(r"<private>.*?(?:</private>|\Z)", re.S | re.I)


def obs_path(data: dict) -> Path | None:
    explicit = os.environ.get("AIDD_OBSERVATIONS")
    if explicit:
        return Path(explicit)
    for base in (os.environ.get("CLAUDE_PROJECT_DIR"), data.get("cwd")):
        if isinstance(base, str) and base and Path(base).is_dir():
            return Path(base) / ".claude" / FILE_NAME
    return None


def clean(text, n: int) -> str:
    """<private> を捨て、伏字にし、1 行にまとめて n 字に切る。"""
    if not isinstance(text, str):
        return ""
    t = " ".join(mask_secrets(_PRIVATE.sub("", text)).split())
    return t if len(t) <= n else t[:n - 1] + "…"


def target(tool: str, ti: dict, project: str | None) -> tuple[str, bool]:
    """(残す対象, <private> を含んでいたか)。"""
    if tool == "Bash":
        raw = ti.get("command") if isinstance(ti.get("command"), str) else ""
        rest = _PRIVATE.sub("", raw).strip()
        first = rest.splitlines()[0] if rest else ""
        return clean(first.split("<<", 1)[0], 60), bool(_PRIVATE.search(raw))
    for k in ("file_path", "notebook_path", "path", "pattern", "url", "query"):
        v = ti.get(k)
        if isinstance(v, str) and v:
            private = bool(_PRIVATE.search(v))
            if project and v.startswith(project.rstrip("/") + "/"):
                v = v[len(project.rstrip("/")) + 1:]
            return clean(v, PATH_MAX), private
    return "", False


def summarize(tool: str, ti: dict, resp) -> str:
    """結果の要約。中身は見ず、件数と種類だけを取る。"""
    if isinstance(resp, dict):
        if resp.get("is_error") or resp.get("error"):
            return "エラー: " + clean(str(resp.get("error") or "あり"), 40)
        f = resp.get("file")
        if tool == "Read" and isinstance(f, dict):
            n, start, total = f.get("numLines"), f.get("startLine"), f.get("totalLines")
            if isinstance(n, int):
                rng = f"（{start}〜／全{total}行）" if isinstance(start, int) and isinstance(total, int) else ""
                return f"{n}行{rng}"
        if tool == "Write":
            return {"create": "新規作成", "update": "上書き"}.get(resp.get("type"), "書き込み")
        if tool in ("Edit", "MultiEdit"):
            patch = resp.get("structuredPatch")
            return f"編集 {len(patch)} 箇所" if isinstance(patch, list) else "編集"
        if tool in ("Grep", "Glob"):
            for k in ("numFiles", "numMatches", "numLines"):
                if isinstance(resp.get(k), int):
                    return f"{resp[k]} 件" + ("（打ち切り）" if resp.get("truncated") else "")
        if tool == "Bash":
            out = resp.get("stdout") if isinstance(resp.get("stdout"), str) else ""
            err = resp.get("stderr") if isinstance(resp.get("stderr"), str) else ""
            s = f"出力 {len(out.splitlines())} 行"
            if err.strip():
                s += "・stderr あり"
            if resp.get("interrupted"):
                s += "・中断"
            return s
        if isinstance(resp.get("code"), int):
            return f"HTTP {resp['code']}"
        return "完了"
    if isinstance(resp, str):
        return f"応答 {len(resp)} 字"
    if isinstance(resp, list):
        return f"応答 {len(resp)} 件"
    return "完了"


def recent(path: Path, n: int) -> list[dict]:
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 64 * 1024))
            lines = f.read().decode("utf-8", "replace").splitlines()[-n:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def trim(path: Path) -> None:
    try:
        if path.stat().st_size <= MAX_BYTES:
            return
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-KEEP:]
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def main() -> int:
    try:
        if mask_secrets is None:
            return 0
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            return 0
        tool = data.get("tool_name")
        if not isinstance(tool, str) or not tool or tool in SKIP_TOOLS:
            return 0
        ti = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
        project = os.environ.get("CLAUDE_PROJECT_DIR") or (data.get("cwd") if isinstance(data.get("cwd"), str) else None)
        tgt, private = target(tool, ti, project)
        if private and not tgt:
            return 0                       # 対象そのものが <private> の中。1 行も残さない
        rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "sid": str(data.get("session_id") or "")[:12],
               "tool": clean(tool, 40), "op": OPS.get(tool, clean(tool, 40).lower()),
               "path": tgt, "summary": clean(summarize(tool, ti, data.get("tool_response")), SUMMARY_MAX)}
        path = obs_path(data)
        if path is None:
            return 0
        key = (rec["tool"], rec["path"], rec["summary"])
        if any((d.get("tool"), d.get("path"), d.get("summary")) == key for d in recent(path, DEDUP_WINDOW)):
            return 0
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        trim(path)
    except Exception:   # 観測は付け足し。壊れた入力・書けない置き場でも作業を止めない
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

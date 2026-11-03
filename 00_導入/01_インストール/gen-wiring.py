#!/usr/bin/env python3
"""gen-wiring.py — hook 配線の真実源 `.claude-plugin/hooks.json`（W3）から、他の経路の配線を生成・照合する。

経路:
  W1 global   03_ClaudeCode/hooks/settings.json（`python3 ~/.claude/hooks/X`）。hooks 以外のキーは保持する
  W2 project  00_導入/02_プロジェクト配布/export-project.sh のヒアドキュメント（`python3 .claude/hooks/X`）
  W4 local    .claude/settings.json（`sh -c 'f="$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/X"; …'`）。
              **ファイルには書かない**（AI は .claude/settings*.json を当てない）。標準出力にだけ出す

使い方:
  python3 gen-wiring.py --target global            W1 を書き換える（--stdout で書かずに出す）
  python3 gen-wiring.py --target project           W2 のヒアドキュメントを書き換える（--stdout で書かずに出す）
  python3 gen-wiring.py --target local             W4 の形を標準出力に出す
  python3 gen-wiring.py --check                    W1・W2・W4 の hook 集合（イベント・matcher・スクリプト名・引数）を
                                                   hooks.json と比べ、差を表で出す。W1・W2 の不一致は NG（exit 1）、
                                                   W4 の不一致は WARN（件数表示のみ・exit 0）
  python3 gen-wiring.py --check --strict           W4 の不一致も NG にする
  --root DIR                                       キットのルート（既定はこのファイルから 2 階層上）
標準ライブラリのみ・Python 3.9 互換。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
SRC = ".claude-plugin/hooks.json"
W1 = "03_ClaudeCode/hooks/settings.json"
W2 = "00_導入/02_プロジェクト配布/export-project.sh"
W4 = ".claude/settings.json"
HEREDOC_START = "cat > \"$TARGET/.claude/settings.json\" << 'JSON'"
HEREDOC_END = "JSON"
# 各経路の command からスクリプト名と引数を取り出す（インタプリタ・スクリプト・引数）
PLUGIN_RE = re.compile(r'^(python3|bash) "\$\{CLAUDE_PLUGIN_ROOT\}"/03_ClaudeCode/hooks/([\w.-]+)(?: (.*))?$')
SCRIPT_RE = re.compile(r'hooks/([\w.-]+\.(?:py|sh))"?')


def parse_plugin_cmd(cmd: str) -> tuple[str, str, str]:
    m = PLUGIN_RE.match(cmd)
    if not m:
        raise ValueError(f"hooks.json の command を解釈できない: {cmd}")
    return m.group(1), m.group(2), (m.group(3) or "").strip()


def render(interp: str, script: str, args: str, target: str) -> str:
    tail = f" {args}" if args else ""
    if target == "global":
        return f"{interp} ~/.claude/hooks/{script}{tail}"
    if target == "project":
        return f"{interp} .claude/hooks/{script}{tail}"
    if target == "local":
        return (f"sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/{script}\"; "
                f"[ -f \"$f\" ] && exec {interp} \"$f\"{tail} || exit 0'")
    raise ValueError(target)


def gen_hooks(src: dict, target: str) -> dict:
    out: dict = {}
    for event, groups in src["hooks"].items():
        out[event] = []
        for g in groups:
            ng = {k: v for k, v in g.items() if k != "hooks"}
            ng["hooks"] = []
            for h in g["hooks"]:
                nh = dict(h)
                nh["command"] = render(*parse_plugin_cmd(h["command"]), target)
                ng["hooks"].append(nh)
            out[event].append(ng)
    return out


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def split_heredoc(text: str) -> tuple[str, str, str]:
    lines = text.split("\n")
    s = lines.index(HEREDOC_START)
    e = next(i for i in range(s + 1, len(lines)) if lines[i] == HEREDOC_END)
    return "\n".join(lines[:s + 1]), "\n".join(lines[s + 1:e]), "\n".join(lines[e:])


def merged(base: dict, hooks: dict) -> dict:
    d = {k: v for k, v in base.items() if k != "hooks"}
    d["hooks"] = hooks
    return d


def dump(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, indent=2)


def hook_set(settings: dict) -> list[tuple[str, str, str, str]]:
    """(イベント, matcher, スクリプト名, 引数) の並び（順序は登録順）。"""
    out = []
    for event, groups in (settings.get("hooks") or {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                cmd = h.get("command", "")
                m = SCRIPT_RE.search(cmd)
                if not m:
                    out.append((event, g.get("matcher", ""), f"?{cmd}", ""))
                    continue
                # W4 形は `exec python3 "$f" <引数> || exit 0'`、他は `<スクリプト> <引数>`
                rest = cmd.rsplit('"$f"', 1)[1] if 'exec ' in cmd else cmd[m.end():]
                args = rest.split("||", 1)[0].strip().strip("'\"").strip()
                out.append((event, g.get("matcher", ""), m.group(1), args))
    return out


def read_routes(root: Path) -> dict[str, dict]:
    routes = {}
    routes["W1 global"] = load_json(root / W1)
    routes["W2 project"] = json.loads(split_heredoc((root / W2).read_text(encoding="utf-8"))[1])
    routes["W4 local"] = load_json(root / W4)
    return routes


def check(root: Path, strict: bool = False) -> int:
    """W1・W2 の不一致は NG。W4 は書けない（保守者が当てる）ので既定は WARN、--strict のときだけ NG。"""
    truth = hook_set(load_json(root / SRC))
    tset = sorted(set(truth))
    rows, ng, warn = [], 0, 0
    for name, s in read_routes(root).items():
        soft = name.startswith("W4") and not strict
        got = set(hook_set(s))
        diffs = [("欠落", t) for t in tset if t not in got] + [("余分", g) for g in sorted(got - set(tset))]
        for kind, t in diffs:
            rows.append((name, ("WARN " if soft else "NG ") + kind, *t))
        if soft:
            warn += len(diffs)
        else:
            ng += len(diffs)
    print(f"gen-wiring --check{' --strict' if strict else ''}: 真実源 {SRC}（{len(tset)} 件）")
    print("| 経路 | 差 | イベント | matcher | スクリプト | 引数 |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(x or "-" for x in r) + " |")
    if not rows:
        print("| W1・W2・W4 | 一致 | - | - | - | - |")
    tail = "（W4 は 06_保守者向け/01_内部仕様/settings-patch-portable.md を保守者が当てる）" if warn else ""
    print(f"{'NG' if ng else 'OK'}: NG {ng} 件・WARN {warn} 件{tail}")
    return 1 if ng else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="hooks.json（真実源）から hook 配線を生成・照合する")
    ap.add_argument("--target", choices=("global", "project", "local"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--strict", action="store_true", help="--check で W4 の不一致も NG にする")
    ap.add_argument("--stdout", action="store_true", help="global・project でもファイルに書かず標準出力に出す")
    ap.add_argument("--root", default=str(KIT))
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if a.check:
        return check(root, a.strict)
    if not a.target:
        ap.error("--target か --check を指定する")
    src = load_json(root / SRC)
    hooks = gen_hooks(src, a.target)
    if a.target == "global":
        text = dump(merged(load_json(root / W1), hooks)) + "\n"
        if a.stdout:
            sys.stdout.write(text)
        else:
            (root / W1).write_text(text, encoding="utf-8")
            print(f"書いた: {W1}")
    elif a.target == "project":
        p = root / W2
        head, body, tail = split_heredoc(p.read_text(encoding="utf-8"))
        text = dump(merged(json.loads(body), hooks))
        if a.stdout:
            sys.stdout.write(text + "\n")
        else:
            p.write_text(head + "\n" + text + "\n" + tail, encoding="utf-8")
            print(f"書いた: {W2}（ヒアドキュメント）")
    else:
        base = load_json(root / W4) if (root / W4).is_file() else {}
        sys.stdout.write(dump(merged(base, hooks)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""取り返しのつかない操作を止める PreToolUse フック（Bash 対象）。

根拠: `rules/speed-harness.md` H-2 の禁止操作（`git add -A` / `stash` / `checkout` / `reset` / `clean`）と
`06_保守者向け/保守者の傾向.md` #12。散文で禁じても守られなかったので機械で止める
（2026-09-22。外部事例: Claude Code Safety Net・Dippy。`06_保守者向け/04_監査記録/EXTERNAL-REF-awesome-2026-09.md` §1-3）。

**止めるのは「やり直しが効かない」操作だけ**にする。止めすぎると回避策を覚えさせるだけで逆効果。
- 未コミットの変更を消す git 操作（reset --hard / checkout -- / restore / clean / stash drop|clear）
- 履歴を壊す push（--force。`--force-with-lease` は他人の作業を消さないので許可）
- 再帰削除（`rm -rf`）でホーム・ルート・`.git` を指すもの
- `git add -A` / `git add .`（意図しないファイルの混入。H-2 はパス明示を要求する）

解除は環境変数ではなく、**人間が同じコマンドを自分で叩く**。安全装置に抜け道を作らない
（`rules/speed-harness.md`「安全フックに止められたら、安全装置が正しく働いた結果として受け入れる」）。
ヒアドキュメント本文と引用文字列は照合前に除去する（文書やコミットメッセージの中の語で止めない）。
"""
import json
import re
import sys

_HEREDOC = re.compile(r"<<-?\s*'?\"?(\w+)'?\"?.*?\n.*?\n\1\s*$", re.DOTALL | re.MULTILINE)
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
_START = r"(?:^|&&|\|\||;|\||\n)\s*"

# (正規表現, 理由, 代替手段)
_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(_START + r"git\s+(?:-C\s+\S+\s+)?reset\s+(?:\S+\s+)*--hard\b"),
     "未コミットの変更が消える", "変更を残すなら `git stash push -m <名前>` ではなく、まず `git status --short` で対象を確認して個別に戻す"),
    (re.compile(_START + r"git\s+(?:-C\s+\S+\s+)?clean\s+-\S*[fd]"),
     "追跡外のファイルが消える（空ディレクトリ込み。過去にテストを壊した）", "`git clean -n` で対象を出してから、必要なものだけ手で消す"),
    (re.compile(_START + r"git\s+(?:-C\s+\S+\s+)?stash\s+(?:drop|clear)\b"),
     "退避した変更が消える", "`git stash list` で中身を確かめ、必要なら `git stash show -p` で内容を残す"),
    (re.compile(_START + r"git\s+(?:-C\s+\S+\s+)?(?:checkout|restore)\s+(?:\S+\s+)*--\s+\S"),
     "作業ツリーの変更が消える", "戻す前に `git diff -- <path>` を残す。部分的に戻すなら `git restore -p`"),
    (re.compile(_START + r"git\s+(?:-C\s+\S+\s+)?push\s+(?:\S+\s+)*(?:--force|-f)(?:\s|$)"),
     "他人の作業を消す可能性がある", "`--force-with-lease` を使う（リモートが進んでいたら失敗して気づける）"),
    (re.compile(_START + r"git\s+(?:-C\s+\S+\s+)?add\s+(?:-A|--all|\.)(?:\s|$)"),
     "意図しないファイルが混入する（H-2 はパス明示を要求している）", "`git status --short` で確認し `git add <path>...` とパスを並べる"),
    (re.compile(_START + r"rm\s+(?:-\S*\s+)*-\S*[rR]\S*f|rm\s+(?:-\S*\s+)*-\S*f\S*[rR]"),
     "再帰削除は取り消せない", "`mv <対象> <scratchpad>/` で退避する（H-2 の標準。削除でなく退避）"),
)


def strip_noise(cmd: str) -> str:
    return _QUOTED.sub("''", _HEREDOC.sub("", cmd))


def check(cmd: str) -> tuple[str, str] | None:
    s = strip_noise(cmd)
    for pat, why, alt in _RULES:
        if pat.search(s):
            return why, alt
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        return 0
    hit = check(cmd)
    if hit is None:
        return 0
    why, alt = hit
    reason = (f"[block-destructive] 取り返しのつかない操作を止めた: {why}。"
              f"代わりに: {alt}。どうしても必要なら保守者に依頼して実行してもらう（H-2）")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

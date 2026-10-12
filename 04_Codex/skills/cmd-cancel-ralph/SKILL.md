---
name: cmd-cancel-ralph
description: "/cancel-ralph — 完了ループ（/ralph）を止める"
---
<!-- 生成物: 04_Codex/build_codex_skills.py が 03_ClaudeCode/ から生成する。直接編集しない -->
コマンド `/cancel-ralph` の Codex 版。引数は、呼び出し時にユーザーが続けて書いた文を `$ARGUMENTS` として読む。

# /cancel-ralph — 完了ループ（/ralph）を止める

引数: なし

## 実行内容

1. `.claude/ralph.json` があるか確かめる。無ければ「ループは動いていない」と 1 行で返して終わる
2. 中身の iteration・max を読み、`rm .claude/ralph.json` で消す（壊れていても消す）
3. 「完了ループを止めた（N/max 回目）」と 1 行で返す。続きの作業は勝手に始めない

## 注意

- 消した後の Stop では `ralph-stop.py` は何もしない
- **Codex では使えない**（`/ralph` 自体が Claude Code 専用）

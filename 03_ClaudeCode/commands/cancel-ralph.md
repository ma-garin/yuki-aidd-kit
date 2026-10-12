# /cancel-ralph — 完了ループ（/ralph）を止める

引数: なし

## 実行内容

1. `.claude/ralph.json` があるか確かめる。無ければ「ループは動いていない」と 1 行で返して終わる
2. 中身の iteration・max を読み、`rm .claude/ralph.json` で消す（壊れていても消す）
3. 「完了ループを止めた（N/max 回目）」と 1 行で返す。続きの作業は勝手に始めない

## 注意

- 消した後の Stop では `ralph-stop.py` は何もしない
- **Codex では使えない**（`/ralph` 自体が Claude Code 専用）

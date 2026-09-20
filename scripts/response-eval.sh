#!/bin/bash
# response-eval.sh — 応答の盲検対比評価（薄いラッパ。本体は response_eval.py）
# 使い方: ./scripts/response-eval.sh validate
#         ./scripts/response-eval.sh run --a <基準の system prompt> --b <候補の system prompt> [--runner claude|"cmd:<コマンド> {system}"] [--json]
#         ./scripts/response-eval.sh score [--out DIR]
# exit 0 B は A より悪くない / 1 B が悪い（平均が下回る・blocker あり）/ 2 判定不能
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/response_eval.py" "$@"

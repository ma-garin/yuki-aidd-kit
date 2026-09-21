#!/bin/bash
# check-docs.sh — キット文書の整合をリポジトリ実体と突合する（薄いラッパ。本体は check_docs.py）
# 使い方: ./06_保守者向け/回帰テスト/check-docs.sh [--root DIR] [-o REPORT] [--strict] [--skip-tests]
# NG>0 で exit 1。詳細は check-docs-report.md（3層要約: 結論 → 種別ごと → 全件はファイル）
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check_docs.py" "$@"

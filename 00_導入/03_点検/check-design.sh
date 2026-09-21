#!/bin/bash
# check-design.sh — デザイン出荷物と画面ファイルの直値・未定義トークン・外部 CDN・alert() を機械判定する
# （薄いラッパ。本体は check_design.py）
# 使い方: ./00_導入/03_点検/check-design.sh [--root DIR] [--tokens 02_共通/ひな形/tokens.css] [-o REPORT] [PATH ...]
#   PATH 省略時は 02_共通/ひな形/ui templates/components。配布先では ./00_導入/03_点検/check-design.sh static src 等を指定する。
# NG>0 で exit 1。詳細は check-design-report.md（3層要約: 結論 → 種別ごと → 全件はファイル）
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check_design.py" "$@"

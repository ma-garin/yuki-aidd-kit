#!/bin/bash
# check-screens.sh — 画面を実ブラウザで開き、ページ全体のスクロール・タブの隠れた状態・コンソールエラーを機械判定する
# （薄いラッパ。本体は check_screens.py。静的検査 check-design.sh と対になる）
# 使い方: ./00_導入/03_点検/check-screens.sh [--url URL ...] [--viewports 1366x768,1920x1080] [--out DIR] [PATH ...]
# NG>0 で exit 1、判定不能（playwright 無し・ページが開けない）で exit 2。詳細は <out>/check-screens-report.md
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check_screens.py" "$@"

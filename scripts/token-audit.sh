#!/bin/bash
# token-audit.sh — トークン節約の仕組みが効いているかを点検する（薄いラッパ。本体は token_audit.py）
#
# 使い方: ./scripts/token-audit.sh [--root DIR] [-o REPORT]
#   床（常時読み込みの推定 tok）・実測ログの集計・hook と設定の配線・MCP 数・スキルの肥大を出す。
#   NG>0（配線漏れ）で exit 1。詳細は token-audit-report.md。実測は Claude Code の /context /usage で。
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/token_audit.py" "$@"

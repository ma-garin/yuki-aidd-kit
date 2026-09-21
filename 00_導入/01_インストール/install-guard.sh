#!/bin/bash
# install-guard.sh — 指示優先の 3 hook を ~/.claude に導入（既存 settings.json に merge。冪等）
# Claude Code 全体（全プロジェクト）に効かせる最小導入。本体は 00_導入/01_インストール/install_guard.py
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec python3 "$KIT_DIR/00_導入/01_インストール/install_guard.py" --hooks-dir "$KIT_DIR/03_ClaudeCode/hooks" "$@"

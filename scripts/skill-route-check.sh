#!/bin/bash
# skill-route-check.sh — スキル発火の機械判定（薄いラッパ。本体は skill_route_check.py）
# 使い方: ./scripts/skill-route-check.sh [--root DIR] [--min-rank1 N] [--json] [--explain "<依頼文>"]
# exit 0 合格 / 1 NG / 2 判定不能。ケースは evals/routing/<skill>.json（positive ≧ 3・negative ≧ 2）
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skill_route_check.py" "$@"

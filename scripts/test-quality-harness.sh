#!/bin/bash
# test-quality-harness.sh — quality_harness.py の回帰テスト
# 一時ディレクトリに最小プロジェクトを組み立て、検出 9 種と「雛形が NG=0 で始まること」を確認する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
H="$KIT_DIR/scripts/quality_harness.py"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

expect() { # 名前, 期待exit, 期待部分文字列, 実出力, 実exit
  if [ "$5" -eq "$2" ] && printf '%s' "$4" | grep -qF "$3"; then
    echo "  ✅ $1"; PASS=$((PASS+1))
  else
    echo "  ❌ $1（exit=$5 期待=$2 / 出力: $(printf '%s' "$4" | head -2 | tr '\n' ' ')）"; FAIL=$((FAIL+1))
  fi
}

# 基本プロジェクト（PASS するもの）
base() { # dir
  mkdir -p "$1/.claude/rules" "$1/quality" "$1/web/services" "$1/web/routes" "$1/static/js"
  touch "$1/.claude/rules/functional-integrity.md"
  printf 'def append_feedback():\n    pass\nclass FeedbackError(Exception):\n    pass\n' > "$1/web/services/feedback_store.py"
  printf 'def route():\n    pass\n' > "$1/web/routes/feedback.py"
  printf 'console.log("ok")\n' > "$1/static/js/feedback.js"
  cat > "$1/quality/feature_contracts.yml" <<'JSON'
{"version":1,
 "harness":{"required_docs":[".claude/rules/functional-integrity.md","quality/feature_contracts.yml"],
            "source_roots":["web/routes","web/services"],"scan_roots":["web/routes","static/js"],
            "unregistered_allowlist":{}},
 "features":[{"feature_id":"feedback","name":"f","risk_level":"high","status":"implemented",
  "ui_files":["static/js/feedback.js"],"route_files":["web/routes/feedback.py"],
  "core_files":["web/services/feedback_store.py"],"symbols":["append_feedback","FeedbackError"],
  "outputs":["x"],"persistence":["y"],
  "failure_modes":["empty_rejected"],"required_tests":["happy_path","error_path"]}]}
JSON
}
mutate() { python3 - "$1" "$2" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); exec(sys.argv[2]); json.dump(d,open(p,'w'))
PY
}

echo "=== quality_harness.py 回帰テスト ==="
P="$TMP/ok"; base "$P"; OUT=$(python3 "$H" --root "$P"); RC=$?
expect "正常な契約は PASS" 0 "Functional Integrity Harness: PASS" "$OUT" "$RC"

P="$TMP/nofail"; base "$P"; mutate "$P/quality/feature_contracts.yml" 'd["features"][0]["failure_modes"]=[]'
OUT=$(python3 "$H" --root "$P"); RC=$?
expect "high に failure_modes が無いと FAIL" 1 "lacks failure_modes" "$OUT" "$RC"

P="$TMP/uionly"; base "$P"; mutate "$P/quality/feature_contracts.yml" 'd["features"][0]["status"]="ui-only"'
OUT=$(python3 "$H" --root "$P"); RC=$?
expect "status=ui-only は禁止" 1 "ui-only features are forbidden" "$OUT" "$RC"

P="$TMP/noroute"; base "$P"; mutate "$P/quality/feature_contracts.yml" 'd["features"][0]["route_files"]=[];d["features"][0]["core_files"]=[];d["features"][0]["symbols"]=[];d["harness"]["source_roots"]=[]'
OUT=$(python3 "$H" --root "$P"); RC=$?
expect "implemented に実行経路が無いと FAIL" 1 "lacks route_files/core_files" "$OUT" "$RC"

P="$TMP/unreg"; base "$P"; printf 'def x():\n    pass\n' > "$P/web/services/new_module.py"
OUT=$(python3 "$H" --root "$P"); RC=$?
expect "契約未登録モジュールを検出" 1 "unregistered feature module: web/services/new_module.py" "$OUT" "$RC"

P="$TMP/allow"; base "$P"; printf 'X=1\n' > "$P/web/services/config.py"; mutate "$P/quality/feature_contracts.yml" 'd["harness"]["unregistered_allowlist"]={"web/services/config.py":"設定"}'
OUT=$(python3 "$H" --root "$P"); RC=$?
expect "allowlist（理由付き）に登録したモジュールは PASS" 0 "PASS" "$OUT" "$RC"

P="$TMP/symbol"; base "$P"; mutate "$P/quality/feature_contracts.yml" 'd["features"][0]["symbols"].append("missing_symbol")'
OUT=$(python3 "$H" --root "$P"); RC=$?
expect "存在しない symbol を検出" 1 "symbol 'missing_symbol' not found" "$OUT" "$RC"

P="$TMP/stub"; base "$P"; printf '// TODO not implemented\n' >> "$P/static/js/feedback.js"
OUT=$(python3 "$H" --root "$P"); RC=$?
expect "未実装マーカーを検出" 1 "suspicious incomplete user path" "$OUT" "$RC"

P="$TMP/nodoc"; base "$P"; mv "$P/.claude/rules/functional-integrity.md" "$P/.claude/rules/_moved.md"
OUT=$(python3 "$H" --root "$P"); RC=$?
expect "統制文書の欠落を検出" 1 "missing required governance file" "$OUT" "$RC"

P="$TMP/missingpath"; base "$P"; mv "$P/static/js/feedback.js" "$P/static/js/_moved.js"
OUT=$(python3 "$H" --root "$P"); RC=$?
expect "参照パスの欠落を検出" 1 "missing referenced path" "$OUT" "$RC"

# 配布する雛形が NG=0 で始まること（雛形が NG を出すと利用者が結果を無視するようになる）
P="$TMP/template"; mkdir -p "$P/.claude/rules" "$P/quality"; touch "$P/.claude/rules/functional-integrity.md"
cp "$KIT_DIR/templates/test/feature_contracts.yml" "$P/quality/"
OUT=$(python3 "$H" --root "$P"); RC=$?
expect "templates/test/feature_contracts.yml は新規プロジェクトで PASS" 0 "validated_features=1" "$OUT" "$RC"

echo ""; echo "結果: PASS=$PASS / FAIL=$FAIL"
if [ "$FAIL" -eq 0 ]; then echo "✅ 全て正常"; exit 0; else echo "⚠ 失敗あり"; exit 1; fi

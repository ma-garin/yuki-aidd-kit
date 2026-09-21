#!/bin/bash
# test-install.sh — 導入・配布・初期化スクリプトの回帰テスト
# 対象: install.sh / verify.sh / export-project.sh / init-project.sh / init-test-docs.sh
# キットの「入口」がテストされていなかった（06_保守者向け/01_内部仕様/09_指摘事項.md F-11）ことへの対処。
#
# 実 ~/.claude には一切触らない: HOME を一時ディレクトリに差し替えて実行し、冒頭のガードで保証する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit()  { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_file()  { [ -e "$2" ] && ok "$1" || ng "$1" "無い: $2"; }
expect_nofile(){ [ ! -e "$2" ] && ok "$1" || ng "$1" "在ってはいけない: $2"; }
expect_grep()  { grep -qF -- "$2" "$3" 2>/dev/null && ok "$1" || ng "$1" "'$2' が $3 に無い"; }
expect_out()   { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い"; }
expect_count() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 $2 / 実際 $3"; }

echo "=== AIDD Kit 入口スクリプト 回帰テスト ==="

# ---------------------------------------------------------------- install.sh / verify.sh
echo "[install.sh / verify.sh]"
FAKE_HOME="$TMP/home"; mkdir -p "$FAKE_HOME"
# ガード: 以降のコマンドは必ず HOME=$FAKE_HOME で実行する。実 HOME を使ったら即失敗させる
run_home() { [ "$HOME_OVERRIDE" = "$FAKE_HOME" ] || { echo "ガード違反: HOME が差し替えられていない" >&2; exit 99; }; HOME="$HOME_OVERRIDE" "$@"; }
HOME_OVERRIDE="$FAKE_HOME"

# 既存ファイルを置いてから install（退避・非上書き・スキップの3経路を同時に検証）
mkdir -p "$FAKE_HOME/.claude/rules/other"
echo "my old claude md" > "$FAKE_HOME/.claude/CLAUDE.md"
echo '{"hooks":{},"theme":"dark"}' > "$FAKE_HOME/.claude/settings.json"
echo "user's own rule" > "$FAKE_HOME/.claude/rules/other/absolute-rules.md"

OUT=$(run_home bash "$KIT_DIR/00_導入/01_インストール/install.sh" 2>&1); RC=$?
expect_exit "install.sh が exit 0" 0 "$RC"
expect_grep "既存 CLAUDE.md を .bak に退避（内容保持）" "my old claude md" "$FAKE_HOME/.claude/CLAUDE.md.bak"
expect_file "AGENTS.md（共通規約の本体）を ~/.claude に配置" "$FAKE_HOME/.claude/AGENTS.md"
expect_grep "CLAUDE.md が @AGENTS.md を import する形" "@AGENTS.md" "$FAKE_HOME/.claude/CLAUDE.md"
expect_grep "functional-integrity の paths frontmatter が保たれる" "paths:" "$FAKE_HOME/.claude/rules/aidd-kit/functional-integrity.md"
expect_grep "既存 settings.json は上書きしない（他のキーが残る）" '"theme": "dark"' "$FAKE_HOME/.claude/settings.json"
expect_grep "既存 settings.json にも指示優先 hook（instruction-guard）を merge する" 'instruction-guard.py' "$FAKE_HOME/.claude/settings.json"
[ -f "$FAKE_HOME/.claude/settings.json.bak" ] && ok "merge 前の settings.json を .bak に退避" || ng "merge 前の settings.json を .bak に退避" "無い"
expect_out  "settings.json 既存時に手動マージの警告" "手動でマージ" "$OUT"
expect_out  "同名 rules が別ディレクトリにあればスキップ表示" "absolute-rules.md は ~/.claude/rules 配下に既存のためスキップ" "$OUT"
expect_nofile "スキップした rule は aidd-kit/ に置かれない" "$FAKE_HOME/.claude/rules/aidd-kit/absolute-rules.md"
expect_file "スキップしなかった rule は aidd-kit/ に置かれる" "$FAKE_HOME/.claude/rules/aidd-kit/speed-harness.md"
SKILL_N=$(ls -d "$KIT_DIR"/03_ClaudeCode/skills/*/ | wc -l | tr -d " "); CMD_N=$(ls "$KIT_DIR"/03_ClaudeCode/commands/*.md | wc -l | tr -d " ")
expect_count "スキルが全部配置される（リポジトリ実体から導出: $SKILL_N 個）" "$SKILL_N" "$(ls -d "$FAKE_HOME"/.claude/skills/*/ | wc -l)"
expect_count "コマンドが全部配置される（$CMD_N 個）" "$CMD_N" "$(ls "$FAKE_HOME"/.claude/commands/*.md | wc -l)"
HOOK_N=$(ls "$KIT_DIR"/03_ClaudeCode/hooks/*.sh "$KIT_DIR"/03_ClaudeCode/hooks/*.py | wc -l | tr -d " ")
expect_count "hooks が全部配置される（リポジトリ実体から導出: $HOOK_N 個）" "$HOOK_N" "$(ls "$FAKE_HOME"/.claude/hooks/*.sh "$FAKE_HOME"/.claude/hooks/*.py | wc -l)"
expect_file "工程承認の判定スクリプトが ~/.claude/scripts/ に置かれる（block-phase.py の探索先）" "$FAKE_HOME/.claude/scripts/check_approval.py"
expect_file "phase-hash.py も同じ場所に置かれる（check_approval.py が隣を参照する）" "$FAKE_HOME/.claude/scripts/phase-hash.py"
V=$(cat "$FAKE_HOME/.claude/KIT_VERSION" 2>/dev/null)
expect_count "KIT_VERSION が <版> <commit> <日付> の3フィールド" 3 "$(printf '%s' "$V" | wc -w)"
expect_out  "KIT_VERSION の版が VERSION ファイルと一致" "$(cat "$KIT_DIR/VERSION")" "$V"
DOCS_N=$(find "$KIT_DIR/01_利用者向け資料" -maxdepth 1 -type f ! -name '.*' | wc -l | tr -d " ")
expect_count "利用者向け資料 $DOCS_N 個を ~/.claude/docs/aidd-kit/ へ（01_利用者向け資料/ 直下と同数）" "$DOCS_N" "$(find "$FAKE_HOME/.claude/docs/aidd-kit" -maxdepth 1 -type f | wc -l)"
expect_file "01_利用ガイド.html を配置（グローバル）" "$FAKE_HOME/.claude/docs/aidd-kit/01_利用ガイド.html"
expect_file "02_操作マニュアル.html を配置（グローバル）" "$FAKE_HOME/.claude/docs/aidd-kit/02_操作マニュアル.html"

OUT=$(run_home bash "$KIT_DIR/00_導入/01_インストール/verify.sh" 2>&1); RC=$?
expect_exit "install 直後の verify.sh が exit 0（NG=0）" 0 "$RC"
expect_out  "verify.sh が導入済みの版を表示" "導入済みの版:" "$OUT"
rm "$FAKE_HOME/.claude/skills/retro/SKILL.md"
OUT=$(run_home bash "$KIT_DIR/00_導入/01_インストール/verify.sh" 2>&1); RC=$?
expect_exit "スキルを1つ消すと verify.sh が exit 1" 1 "$RC"
expect_out  "欠落したスキル名が出力に出る" "retro" "$OUT"

# ---------------------------------------------------------------- install-guard.sh（指示優先 3 hook の最小導入・merge・冪等）
echo "[install-guard.sh]"
GH="$TMP/guard-home"; mkdir -p "$GH/.claude"
echo '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"echo mine"}]}]},"effortLevel":"high"}' > "$GH/.claude/settings.json"
OUT=$(HOME="$GH" bash "$KIT_DIR/00_導入/01_インストール/install-guard.sh" 2>&1); RC=$?
expect_exit "install-guard.sh が exit 0" 0 "$RC"
for f in instruction-guard.py prompt-priority.py reply-language.py; do
  [ -x "$GH/.claude/hooks/$f" ] && ok "hooks/$f を配置（実行可）" || ng "hooks/$f を配置" "無い"
done
expect_grep "既存の他の hook（echo mine）を残す" 'echo mine' "$GH/.claude/settings.json"
expect_grep "既存の他のキー（effortLevel）を残す" '"effortLevel": "high"' "$GH/.claude/settings.json"
expect_grep "PreToolUse に instruction-guard を配線" 'instruction-guard.py' "$GH/.claude/settings.json"
expect_grep "Stop に reply-language を配線" 'reply-language.py' "$GH/.claude/settings.json"
expect_grep "UserPromptSubmit に prompt-priority を配線" 'prompt-priority.py' "$GH/.claude/settings.json"
python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$GH/.claude/settings.json" 2>/dev/null && ok "merge 後の settings.json が JSON として妥当" || ng "merge 後の settings.json が JSON として妥当" "パース失敗"
OUT=$(HOME="$GH" bash "$KIT_DIR/00_導入/01_インストール/install-guard.sh" 2>&1)
expect_out "2 回目は「変更なし」（冪等）" "変更なし" "$OUT"
N=$(grep -c 'instruction-guard.py' "$GH/.claude/settings.json"); [ "$N" -eq 1 ] && ok "2 回実行しても配線が重複しない（1 箇所）" || ng "2 回実行しても配線が重複しない" "$N 箇所"
GH2="$TMP/guard-home2"; mkdir -p "$GH2"
OUT=$(HOME="$GH2" bash "$KIT_DIR/00_導入/01_インストール/install-guard.sh" 2>&1); RC=$?
expect_exit "settings.json が無くても exit 0（新規作成）" 0 "$RC"
expect_grep "新規作成した settings.json に配線" 'instruction-guard.py' "$GH2/.claude/settings.json"
echo '{broken' > "$GH2/.claude/settings.json"
OUT=$(HOME="$GH2" bash "$KIT_DIR/00_導入/01_インストール/install-guard.sh" 2>&1); RC=$?
expect_exit "壊れた settings.json は触らず exit 1" 1 "$RC"
expect_grep "壊れた settings.json を上書きしない" '{broken' "$GH2/.claude/settings.json"

# ---------------------------------------------------------------- export-project.sh
echo "[export-project.sh]"
P="$TMP/proj"; mkdir -p "$P/scripts"
echo "# my own trace-check" > "$P/scripts/trace-check.sh"
OUT=$(bash "$KIT_DIR/00_導入/02_プロジェクト配布/export-project.sh" "$P" 2>&1); RC=$?
expect_exit "export-project.sh が exit 0" 0 "$RC"
expect_count "skills $SKILL_N 個（リポジトリ実体と同数）" "$SKILL_N" "$(ls -d "$P"/.claude/skills/*/ | wc -l)"
expect_count "commands $CMD_N 個（リポジトリ実体と同数）" "$CMD_N" "$(ls "$P"/.claude/commands/*.md | wc -l)"
expect_count "hooks $HOOK_N 個（リポジトリ実体と同数）" "$HOOK_N" "$(ls "$P"/.claude/hooks/*.sh "$P"/.claude/hooks/*.py | wc -l)"
expect_count "rules 4 個（absolute / speed / model-routing / functional-integrity）" 4 "$(ls "$P"/.claude/rules/*.md | wc -l)"
for f in .claude/INDEX.md .claude/settings.json .claude/templates/tokens.css .claude/templates/lifecycle/00-rfd.md AGENTS.md CLAUDE.md scripts/quality_harness.py scripts/ui-hash.py scripts/pre-commit-ui-gate.sh scripts/check_approval.py scripts/check-approval.sh scripts/phase-hash.py scripts/test_metrics.py scripts/test-metrics.sh; do
  expect_file "生成物: $f" "$P/$f"
done
expect_grep "既存 scripts/trace-check.sh はスキップ（内容保持）" "# my own trace-check" "$P/scripts/trace-check.sh"
expect_out  "スキップした旨を表示" "scripts/trace-check.sh は既存のためスキップ" "$OUT"
expect_grep "AGENTS.md の INDEX 参照が .claude/INDEX.md に相対化" ".claude/INDEX.md" "$P/AGENTS.md"
expect_grep "配布先の CLAUDE.md も @AGENTS.md 形式" "@AGENTS.md" "$P/CLAUDE.md"
expect_grep "配布先の rules に paths frontmatter が保たれる" "paths:" "$P/.claude/rules/functional-integrity.md"
if grep -q "<YOUR_WORKSPACE>/yuki-aidd-kit/INDEX.md" "$P/CLAUDE.md" "$P/AGENTS.md"; then ng "INDEX の絶対参照が残っていない" "残っている"; else ok "INDEX の絶対参照が残っていない"; fi
expect_grep "hooks の settings.json が相対パス参照" ".claude/hooks/block-gates.py" "$P/.claude/settings.json"
expect_grep "block-explore.sh が Read|Grep|Glob に配線される（グローバル導入と同じ振る舞い）" ".claude/hooks/block-explore.sh" "$P/.claude/settings.json"
expect_grep "block-phase.py が Write|Edit|MultiEdit に配線される（.claude/phase-gate が無ければ何もしない）" ".claude/hooks/block-phase.py" "$P/.claude/settings.json"
python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$P/.claude/settings.json" 2>/dev/null && ok "生成した settings.json が JSON として妥当" || ng "生成した settings.json が JSON として妥当" "パース失敗"
SJ=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('effortLevel'), d.get('autoCompactWindow'), d.get('bashOutputMaxChars'))" "$P/.claude/settings.json" 2>/dev/null)
expect_out "effortLevel=high（xhigh から 1 段下げ。設計判断のときだけ上げる）" "high" "$SJ"
expect_out "autoCompactWindow=200k（Sonnet 5 の 1M を放置しない）" "200k" "$SJ"
expect_out "bashOutputMaxChars=12000（超過分はファイルへ退避）" "12000" "$SJ"
expect_count ".claude/KIT_VERSION が3フィールド" 3 "$(wc -w < "$P/.claude/KIT_VERSION")"
expect_count "利用者向け資料 $DOCS_N 個を .claude/docs/ へ（01_利用者向け資料/ 直下と同数）" "$DOCS_N" "$(find "$P/.claude/docs" -maxdepth 1 -type f | wc -l)"
expect_file "01_利用ガイド.html を配置（プロジェクト）" "$P/.claude/docs/01_利用ガイド.html"
expect_file "02_操作マニュアル.html を配置（プロジェクト）" "$P/.claude/docs/02_操作マニュアル.html"
# 再実行で退避
OUT=$(bash "$KIT_DIR/00_導入/02_プロジェクト配布/export-project.sh" "$P" 2>&1)
expect_file "再実行で CLAUDE.md.bak" "$P/CLAUDE.md.bak"
expect_file "再実行で AGENTS.md.bak" "$P/AGENTS.md.bak"
expect_file "再実行で .claude/settings.json.bak" "$P/.claude/settings.json.bak"
OUT=$(bash "$KIT_DIR/00_導入/02_プロジェクト配布/export-project.sh" "$TMP/does-not-exist" 2>&1); RC=$?
expect_exit "対象ディレクトリ不在なら exit 1" 1 "$RC"

# ---------------------------------------------------------------- init-project.sh
echo "[init-project.sh]"
W="$TMP/work"; mkdir -p "$W"
(cd "$W" && bash "$KIT_DIR/00_導入/02_プロジェクト配布/init-project.sh" app-pwa pwa >/dev/null 2>&1); RC=$?
expect_exit "pwa: exit 0" 0 "$RC"
for f in .gitignore CLAUDE.md CURRENT_STATE.md spec.md plan.md tasks.md docs/manifest.json docs/index.html; do
  expect_file "pwa: $f" "$W/app-pwa/$f"
done
expect_grep "pwa: manifest に theme_color #1976D2" '"theme_color": "#1976D2"' "$W/app-pwa/docs/manifest.json"
(cd "$W" && bash "$KIT_DIR/00_導入/02_プロジェクト配布/init-project.sh" app-html html >/dev/null 2>&1)
expect_file "html: app-html.html" "$W/app-html/app-html.html"
(cd "$W" && bash "$KIT_DIR/00_導入/02_プロジェクト配布/init-project.sh" app-st streamlit >/dev/null 2>&1)
expect_file "streamlit: requirements.txt" "$W/app-st/requirements.txt"
expect_file "streamlit: app.py" "$W/app-st/app.py"
(cd "$W" && bash "$KIT_DIR/00_導入/02_プロジェクト配布/init-project.sh" >/dev/null 2>&1); RC=$?
expect_exit "引数なしは exit 1" 1 "$RC"

# ---------------------------------------------------------------- init-test-docs.sh
echo "[init-test-docs.sh]"
Q="$TMP/qproj"; mkdir -p "$Q"
OUT=$(bash "$KIT_DIR/00_導入/02_プロジェクト配布/init-test-docs.sh" "$Q" --ci 2>&1); RC=$?
expect_exit "--ci: exit 0" 0 "$RC"
expect_count "--ci: 14 ファイル配置（✅ の数）" 14 "$(printf '%s\n' "$OUT" | grep -c '^✅')"
for f in docs/test/TESTING_STRATEGY.md docs/test/iso29119-test-plan.md docs/system_test_cases.csv quality/feature_contracts.yml scripts/quality_harness.py .github/workflows/test-gates.yml; do
  expect_file "配置物: $f" "$Q/$f"
done
expect_file "docs/quality/evidence/ を作る" "$Q/docs/quality/evidence"
[ -x "$Q/scripts/pre-commit-ui-gate.sh" ] && ok "ゲートスクリプトに実行権限" || ng "ゲートスクリプトに実行権限" "chmod +x されていない"
OUT=$(bash "$KIT_DIR/00_導入/02_プロジェクト配布/init-test-docs.sh" "$Q" --ci 2>&1)
expect_count "再実行は全件スキップ（↷ が 14）" 14 "$(printf '%s\n' "$OUT" | grep -c '^↷')"
# 配置直後に機能契約ハーネスが PASS すること（雛形が NG を出すと利用者が検査を無視するため）
mkdir -p "$Q/.claude/rules" && touch "$Q/.claude/rules/functional-integrity.md"
OUT=$(python3 "$Q/scripts/quality_harness.py" --root "$Q" 2>&1); RC=$?
expect_exit "配置直後の quality_harness.py が PASS" 0 "$RC"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }

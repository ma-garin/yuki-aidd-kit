#!/bin/bash
# test-kit-checks.sh — キット自身の検査 4 本の回帰テスト（G3）
#   check-version.py（版の表記 ↔ VERSION）・check-layers.py（02_共通/ → 専用層の逆向き参照）・
#   llms-txt.py（INDEX.md → llms.txt）・00_導入/03_点検/doctor.py（実行して診る・読むだけ）
#
# 一時ディレクトリに小さなキットの形を作り、正例（一致・違反なし・最新）と負例（食い違い・新しい違反・古い）を確かめる。
# 実物のキットでも check-version・check-layers・llms-txt --check・doctor が exit 0 であることを確かめる。
# doctor はキットの写しに対して走らせ、ファイルを 1 つも書かない（__pycache__ も作らない）ことを確かめる。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
T="$KIT_DIR/02_共通/ツール"
DOCTOR="$KIT_DIR/00_導入/03_点検/doctor.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-240)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }
export PYTHONDONTWRITEBYTECODE=1

echo "=== check-version / check-layers / llms-txt / doctor 回帰テスト ==="

echo "[check-version]"
V="$TMP/v"
vfresh() {
  rm -rf "$V"; mkdir -p "$V/01_利用者向け資料" "$V/02_共通/ひな形" "$V/06_保守者向け"
  echo "2.1.0" > "$V/VERSION"
  printf '# CHANGELOG\n\n## 未リリース\n\n- x\n\n## Ver.2.1.0（2026-10-01）— 新\n\n## Ver.2.0.0（2026-09-01）— 旧\n' > "$V/CHANGELOG.md"
  printf '<title>ガイド（Ver.2.1.0）</title>\n<p>この機能（2.0.0〜）</p>\n' > "$V/01_利用者向け資料/guide.html"
  printf '# 雛形\n\n```\nVer.0.0.1 はフェンス内なので見ない\n```\n' > "$V/02_共通/ひな形/a.md"
  printf 'Ver.1.0.0 の見積（履歴）\n' > "$V/06_保守者向け/backlog.md"
}
cv() { python3 "$T/check-version.py" --root "$V" "$@" 2>&1; }
vfresh
OUT=$(cv); RC=$?
expect_exit "一致していれば exit 0" 0 "$RC"
expect_out  "VERSION を出す" "VERSION=2.1.0 NG=0" "$OUT"
expect_noout "導入版の注記（2.0.0〜）・フェンス内・06 の履歴は拾わない" "NG  " "$OUT"
OUT=$(cv --json); RC=$?
expect_out  "--json に changelog_top" '"changelog_top": "2.1.0"' "$OUT"
echo "2.2.0" > "$V/VERSION"
OUT=$(cv); RC=$?
expect_exit "VERSION を上げて CHANGELOG を忘れると exit 1" 1 "$RC"
expect_out  "V2 を出す" "V2 CHANGELOG.md:7 最新のリリース見出しは Ver.2.1.0、VERSION は 2.2.0" "$OUT"
expect_out  "表紙の版の食い違いを V4 で出す（ファイル:行）" "V4 01_利用者向け資料/guide.html:1 Ver.2.1.0" "$OUT"
vfresh; printf '{\n  "name": "aidd-kit",\n  "version": "2.0.9"\n}\n' > "$V/02_共通/ひな形/plugin.json"
OUT=$(cv); RC=$?
expect_exit "JSON の version の食い違いも exit 1" 1 "$RC"
expect_out  "JSON の行を出す" "plugin.json:3" "$OUT"
vfresh; echo "v2.1" > "$V/VERSION"
OUT=$(cv); RC=$?
expect_exit "VERSION が X.Y.Z でなければ exit 1" 1 "$RC"
expect_out  "V1 を出す" "V1 VERSION は X.Y.Z" "$OUT"
vfresh; printf '# CHANGELOG\n\n## Ver.2.0.0（2026-09-01）\n\n## Ver.2.1.0（2026-10-01）\n' > "$V/CHANGELOG.md"
OUT=$(cv); RC=$?
expect_out  "見出しの順の逆転を V3（WARN）で出す" "V3 CHANGELOG.md:3" "$OUT"
vfresh; rm "$V/CHANGELOG.md"
OUT=$(cv); RC=$?
expect_exit "CHANGELOG が無ければ exit 2" 2 "$RC"
OUT=$(python3 "$T/check-version.py" 2>&1); RC=$?
expect_exit "実物のキットは exit 0" 0 "$RC"

echo "[check-layers]"
L="$TMP/l"
lfresh() {
  rm -rf "$L"; mkdir -p "$L/02_共通/rules" "$L/02_共通/ツール" "$L/02_共通/ひな形"
  printf '# 規則\n`skills/dev-lifecycle/SKILL.md` を読む。AGENTS.md と CLAUDE.md の両方。\n' > "$L/02_共通/rules/a.md"
  printf 'print("ok")\n' > "$L/02_共通/ツール/x.py"
}
cl() { python3 "$T/check-layers.py" --root "$L" "$@" 2>&1; }
lfresh
OUT=$(cl); RC=$?
expect_exit "skills/ と AGENTS.md＋CLAUDE.md の併記は違反でない" 0 "$RC"
expect_out  "新しい違反 0 件" "新しい違反 0 件" "$OUT"
printf 'p = KIT / "03_ClaudeCode" / "skills"\n' > "$L/02_共通/ツール/y.py"
OUT=$(cl); RC=$?
expect_exit "L1: 03_ClaudeCode の名指しは exit 1" 1 "$RC"
expect_out  "ファイル:行を出す" "NG  L1 02_共通/ツール/y.py:1 03_ClaudeCode" "$OUT"
lfresh; printf 'hook は `.claude/hooks/block-ci.py` を見る\n' > "$L/02_共通/ひな形/b.md"
OUT=$(cl); RC=$?
expect_exit "L2: .claude/hooks/ の参照は exit 1" 1 "$RC"
expect_out  "L2 を出す" "L2 02_共通/ひな形/b.md:1 .claude/hooks/block-ci.py" "$OUT"
lfresh; printf '実測は hooks/tool-timer.py で\n' > "$L/02_共通/ひな形/c.md"
OUT=$(cl); RC=$?
expect_exit "L2: hooks/<名前>.py の参照も exit 1" 1 "$RC"
lfresh; printf '設定は .codex/config.toml と agents/openai.yaml\n' > "$L/02_共通/ひな形/d.md"
OUT=$(cl); RC=$?
expect_exit "L3: Codex 専用の実体の参照は exit 1" 1 "$RC"
expect_out  "agents/openai.yaml を出す" "agents/openai.yaml" "$OUT"
lfresh; printf '詳しくは CLAUDE.md へ\n' > "$L/02_共通/ひな形/e.md"
OUT=$(cl); RC=$?
expect_exit "L4: CLAUDE.md だけは WARN（exit 0）" 0 "$RC"
expect_out  "L4 を出す" "WARN L4 02_共通/ひな形/e.md" "$OUT"
lfresh; mkdir -p "$L/02_共通/rules"; printf '実測は `hooks/tool-timer.py report`\n' > "$L/02_共通/rules/absolute-rules.md"
OUT=$(cl); RC=$?
expect_exit "基準線にある既存の参照は NG に数えない" 0 "$RC"
expect_out  "基準線の件数に数える" "基準線 1 件" "$OUT"
expect_out  "今は無い基準線を「外せる」と出す" "INFO 基準線から外せる" "$OUT"
OUT=$(cl --no-baseline); RC=$?
expect_exit "--no-baseline なら既存の参照も exit 1" 1 "$RC"
lfresh; printf 'x = "03_ClaudeCode"\n' > "$L/02_共通/ツール/check-version.py"
OUT=$(cl); RC=$?
expect_exit "キット自身用の道具（KIT_SELF）は対象外" 0 "$RC"
OUT=$(python3 "$T/check-layers.py" --root "$TMP/none" 2>&1); RC=$?
expect_exit "02_共通/ が無ければ exit 2" 2 "$RC"
OUT=$(python3 "$T/check-layers.py" 2>&1); RC=$?
expect_exit "実物のキットは新しい違反なし（exit 0）" 0 "$RC"
OUT=$(python3 "$T/check-layers.py" --json 2>&1); RC=$?
expect_out  "--json に baseline を出す" '"baseline": [' "$OUT"

echo "[llms-txt]"
X="$TMP/x"
xfresh() {
  rm -rf "$X"; mkdir -p "$X/03_ClaudeCode/skills/alpha" "$X/03_ClaudeCode/skills/beta" "$X/03_ClaudeCode/commands" "$X/02_共通/rules" "$X/01_利用者向け資料"
  for f in README.md CHANGELOG.md 03_ClaudeCode/skills/alpha/SKILL.md 03_ClaudeCode/skills/beta/SKILL.md 03_ClaudeCode/commands/alpha.md 02_共通/rules/r1.md 01_利用者向け資料/guide.md; do echo x > "$X/$f"; done
  cat > "$X/INDEX.md" <<'EOF'
# Demo Kit — INDEX

デモ用の **キット**。

## DAILY スキル（制御）

| スキル | 1行要約 | タグ | コスト |
|---|---|---|---|
| `alpha` | アルファの要約 | #a | 1行 |
| `ghost` | 実在しない | #a | 1行 |

## LIBRARY スキル（場面）

| スキル | 1行要約 |
|---|---|
| `beta` | ベータ |

## 02_共通/rules/（規律）

| ルール | 1行要約 |
|---|---|
| `r1` | 規則 1 |

## 03_ClaudeCode/hooks/（配線）

| hook | 発火 |
|---|---|
| `r1` | 載せない節 |

## スラッシュコマンド

| コマンド | 1行要約 |
|---|---|
| `/alpha` | コマンド版のアルファ |

## docs/（利用者向け文書）

| ファイル | 1行要約 |
|---|---|
| `01_利用者向け資料/guide.md` | ガイド |
EOF
}
lt() { python3 "$T/llms-txt.py" --root "$X" "$@" 2>&1; }
xfresh
OUT=$(lt); RC=$?
expect_exit "生成は exit 0" 0 "$RC"
expect_out  "解決できない名前は飛ばして知らせる" "飛ばした（実在するパスに解決できない）: DAILY スキル: ghost" "$OUT"
G=$(cat "$X/llms.txt")
expect_out  "H1 から — INDEX を除く" "# Demo Kit" "$G"
expect_noout "H1 に INDEX を残さない" "— INDEX" "$G"
expect_out  "要約を引用で置く（強調記号は除かない原文）" "> デモ用の **キット**。" "$G"
expect_out  "DAILY のスキルを SKILL.md に解決" "- [03_ClaudeCode/skills/alpha/SKILL.md](03_ClaudeCode/skills/alpha/SKILL.md): アルファの要約" "$G"
expect_out  "/alpha はスキルでなくコマンドに解決" "- [03_ClaudeCode/commands/alpha.md](03_ClaudeCode/commands/alpha.md): コマンド版のアルファ" "$G"
expect_out  "rules を解決" "02_共通/rules/r1.md" "$G"
expect_out  "文書の表はパスのまま" "- [01_利用者向け資料/guide.md](01_利用者向け資料/guide.md): ガイド" "$G"
expect_noout "hooks の節は載せない" "載せない節" "$G"
LAST=$(grep -n "^## " "$X/llms.txt" | tail -1)
expect_out  "Optional は最後の節" "## Optional" "$LAST"
OPT=$(sed -n '/^## Optional/,$p' "$X/llms.txt")
expect_out  "LIBRARY は Optional に入る" "skills/beta/SKILL.md" "$OPT"
OUT=$(lt --check); RC=$?
expect_exit "生成直後の --check は exit 0" 0 "$RC"
sed -i 's/アルファの要約/アルファの新しい要約/' "$X/INDEX.md"
OUT=$(lt --check); RC=$?
expect_exit "INDEX を変えて再生成し忘れると --check は exit 1" 1 "$RC"
expect_noout "--check は書き込まない" "新しい要約" "$(cat "$X/llms.txt")"
rm "$X/llms.txt"
OUT=$(lt --check); RC=$?
expect_exit "llms.txt が無ければ --check は exit 1" 1 "$RC"
OUT=$(python3 "$T/llms-txt.py" --root "$TMP/none" 2>&1); RC=$?
expect_exit "INDEX.md が無ければ exit 2" 2 "$RC"
OUT=$(python3 "$T/llms-txt.py" --check 2>&1); RC=$?
expect_exit "実物のキットの llms.txt は最新（--check exit 0）" 0 "$RC"

echo "[doctor]"
K="$TMP/kit"; mkdir -p "$K"
cp -R "$KIT_DIR/00_導入" "$KIT_DIR/02_共通" "$KIT_DIR/03_ClaudeCode" "$KIT_DIR/04_Codex" "$KIT_DIR/VERSION" "$K/"
find "$K" -name __pycache__ -type d -prune -exec rm -rf {} +
# 写しの全パス・サイズ・mtime を前後で比べる（sleep で時刻を待たない）
snap() { python3 -c 'import os,sys
for d,ds,fs in os.walk(sys.argv[1]):
    for n in sorted(ds+fs):
        p=os.path.join(d,n); st=os.stat(p); print(p, st.st_size, st.st_mtime_ns)' "$K" | sort; }
S1=$(snap)
OUT=$(python3 "$DOCTOR" --root "$K" 2>&1); RC=$?
expect_exit "揃った写しは exit 0" 0 "$RC"
expect_out  "スナップショットと明記する" "時点のスナップショット" "$OUT"
expect_out  "集計を出す" "NG=0" "$OUT"
NEW=$(diff <(echo "$S1") <(snap) | head -5)
[ -z "$NEW" ] && ok "doctor はファイルを書かない（__pycache__ も作らない）" || ng "doctor はファイルを書かない" "$NEW"
J=$(python3 "$DOCTOR" --root "$K" --json 2>/dev/null); RC=$?
expect_exit "--json も exit 0" 0 "$RC"
printf '%s' "$J" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["snapshot"] is True and d["summary"]["NG"]==0 and any(i["check"].startswith("D1") for i in d["items"])' \
  && ok "--json は snapshot=true・summary・items を持つ" || ng "--json の形" "$(printf '%s' "$J" | head -c 200)"
expect_out  "D6 で secret_patterns の自己検査を実行した" "D6 部品の自己検査" "$J"
expect_out  "D7 で Codex 生成物の --check を実行した" "D7 Codex 生成物" "$J"
printf 'def broken(:\n' > "$K/03_ClaudeCode/hooks/broken.py"
OUT=$(python3 "$DOCTOR" --root "$K" 2>&1); RC=$?
expect_exit "構文の壊れた hook があると exit 1" 1 "$RC"
expect_out  "D4 で壊れた hook を出す" "NG   D4 hook の構文  03_ClaudeCode/hooks/broken.py" "$OUT"
rm "$K/03_ClaudeCode/hooks/broken.py"
rm "$K/02_共通/ツール/pack-context.py"
OUT=$(python3 "$DOCTOR" --root "$K" 2>&1); RC=$?
expect_exit "必要な道具が欠けると exit 1" 1 "$RC"
expect_out  "D5 で欠けた道具を出す" "D5 道具  02_共通/ツール/pack-context.py  無い" "$OUT"
rm "$K/03_ClaudeCode/hooks/block-ci.py"
OUT=$(python3 "$DOCTOR" --root "$K" 2>&1); RC=$?
expect_out  "D3 で配線先の hook の欠落を出す" "無い: block-ci.py" "$OUT"
echo "8.x" > "$K/VERSION"
OUT=$(python3 "$DOCTOR" --root "$K" 2>&1); RC=$?
expect_out  "D2 で VERSION の形の誤りを出す" "NG   D2 VERSION" "$OUT"
OUT=$(PATH=/nonexistent "$(command -v python3)" "$DOCTOR" --root "$KIT_DIR" 2>&1); RC=$?
expect_out  "git・bash が無い環境（Codex 相当）は D8 WARN" "WARN D8 外部コマンド  git" "$OUT"
expect_out  "bash が無ければ .sh は SKIP（止めない）" "SKIP D4 hook の構文" "$OUT"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }

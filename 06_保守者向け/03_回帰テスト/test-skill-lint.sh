#!/bin/bash
# test-skill-lint.sh — skill-lint.py（SKILL.md の frontmatter と Codex 版の対応）と
#                      build_codex_skills.py のマニフェスト（skills-manifest.json・--check）の回帰テスト（G3）
#
# skill-lint: 正しい形は exit 0、frontmatter 無し・name 不一致・description 無し/1024 字超・真偽値以外・
#   disable-model-invocation: true なのに Codex で暗黙発火、は exit 1。500 字超・未知のキー・Codex 版の欠落・逆向きの不一致は WARN。
# マニフェスト: キットの写しで生成→--check exit 0、生成物の改変・マニフェストの改変・欠落で exit 1、
#   disable-model-invocation: true のスキルは allow_implicit_invocation: false で生成され skill-lint も通ること、
#   生成元の無い配布先ではマニフェストとの照合だけを行うことを確かめる。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LINT="$KIT_DIR/02_共通/ツール/skill-lint.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-240)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }
export PYTHONDONTWRITEBYTECODE=1

echo "=== skill-lint.py / build_codex_skills.py マニフェスト 回帰テスト ==="

S="$TMP/skills"; C="$TMP/codex"
skill() {  # skill <dir> <frontmatter 本文（\n 区切り）>
  mkdir -p "$S/$1"; printf -- '---\n%b\n---\n# 本文\n' "$2" > "$S/$1/SKILL.md"
}
codex() {  # codex <dir> <true|false|none>
  mkdir -p "$C/$1/agents"
  if [ "$2" = none ]; then printf 'display_name: "x"\n' > "$C/$1/agents/openai.yaml"
  else printf 'display_name: "x"\nallow_implicit_invocation: %s\n' "$2" > "$C/$1/agents/openai.yaml"; fi
}
sl() { python3 "$LINT" --skills "$S" --codex "$C" "$@" 2>&1; }
fresh() { rm -rf "$S" "$C"; mkdir -p "$S" "$C"
  skill good 'name: good\ndescription: 「良い」と言われたら使う。'; codex good true
  skill manual 'name: manual\ndescription: 明示の依頼だけ。\ndisable-model-invocation: true'; codex manual false
}

echo "[skill-lint: 正しい形]"
fresh
OUT=$(sl); RC=$?
expect_exit "正しい形は exit 0" 0 "$RC"
expect_out  "スキル 2 件・NG=0" "スキル 2 件・NG=0 WARN=0" "$OUT"
OUT=$(sl --json); RC=$?
expect_out  "--json に codex_checked" '"codex_checked": true' "$OUT"
OUT=$(python3 "$LINT" --skills "$S" --codex "" 2>&1); RC=$?
expect_exit "--codex '' で Codex 照合を飛ばせる" 0 "$RC"
expect_out  "照合なしと出す" "Codex 照合: なし" "$OUT"

echo "[skill-lint: NG]"
fresh; mkdir -p "$S/nofm"; echo "# 本文だけ" > "$S/nofm/SKILL.md"; codex nofm true
OUT=$(sl); RC=$?
expect_exit "frontmatter が無いと exit 1" 1 "$RC"
expect_out  "S1 を出す" "S1 nofm/SKILL.md" "$OUT"
fresh; skill wrong 'name: other\ndescription: x'; codex wrong true
OUT=$(sl); RC=$?
expect_exit "name がディレクトリ名と違うと exit 1" 1 "$RC"
expect_out  "S2 を出す" "S2 wrong/SKILL.md: name「other」" "$OUT"
fresh; skill noname 'description: x'; codex noname true
OUT=$(sl); RC=$?
expect_exit "name が無いと exit 1" 1 "$RC"
fresh; skill nodesc 'name: nodesc\ndescription:'; codex nodesc true
OUT=$(sl); RC=$?
expect_exit "description が空だと exit 1" 1 "$RC"
expect_out  "S3 を出す" "S3 nodesc/SKILL.md" "$OUT"
fresh; skill long "name: long\ndescription: $(printf 'あ%.0s' $(seq 1 1025))"; codex long true
OUT=$(sl); RC=$?
expect_exit "description が 1024 字超で exit 1" 1 "$RC"
expect_out  "S4 で字数を出す" "S4 long/SKILL.md: description が 1025 字 > 1024" "$OUT"
fresh; skill badbool 'name: badbool\ndescription: x\ndisable-model-invocation: yes'; codex badbool true
OUT=$(sl); RC=$?
expect_exit "真偽値以外は exit 1" 1 "$RC"
expect_out  "S5 を出す" "S5 badbool/SKILL.md: disable-model-invocation は true/false" "$OUT"
fresh; codex manual true
OUT=$(sl); RC=$?
expect_exit "disable-model-invocation: true なのに Codex で暗黙発火すると exit 1" 1 "$RC"
expect_out  "S7 を出す" "S7 manual: disable-model-invocation: true なのに" "$OUT"

echo "[skill-lint: WARN（exit 0）]"
fresh; skill mid "name: mid\ndescription: $(printf 'い%.0s' $(seq 1 501))"; codex mid true
OUT=$(sl); RC=$?
expect_exit "500 字超は WARN だけ" 0 "$RC"
expect_out  "S4 の WARN を出す" "WARN S4 mid/SKILL.md: description が 501 字 > 500" "$OUT"
fresh; skill typo 'name: typo\ndescription: x\ndisable-model-invokation: true'; codex typo true
OUT=$(sl); RC=$?
expect_exit "未知のキーは WARN だけ" 0 "$RC"
expect_out  "綴り違いを S6 で出す" "S6 typo/SKILL.md: 未知のキー \`disable-model-invokation\`" "$OUT"
fresh; codex good false
OUT=$(sl); RC=$?
expect_exit "自動発火するスキルが Codex で false は WARN だけ" 0 "$RC"
expect_out  "逆向きの不一致を出す" "WARN S7 good" "$OUT"
fresh; rm -rf "$C/good"
OUT=$(sl); RC=$?
expect_exit "Codex 版が無いのは WARN だけ" 0 "$RC"
expect_out  "再生成を促す" "build_codex_skills.py で再生成" "$OUT"
fresh; codex manual none
OUT=$(sl); RC=$?
expect_exit "openai.yaml に項目が無ければ S7 の照合をしない" 0 "$RC"
OUT=$(python3 "$LINT" --skills "$TMP/none" 2>&1); RC=$?
expect_exit "スキルのディレクトリが無ければ exit 2" 2 "$RC"
OUT=$(python3 "$LINT" 2>&1); RC=$?
expect_exit "実物のキットは NG なし（exit 0）" 0 "$RC"

echo "[マニフェスト]"
K="$TMP/kit"; mkdir -p "$K"
cp -R "$KIT_DIR/03_ClaudeCode" "$KIT_DIR/04_Codex" "$K/"
B="$K/04_Codex/build_codex_skills.py"; M="$K/04_Codex/skills-manifest.json"
OUT=$(python3 "$B" --check 2>&1); RC=$?
expect_exit "コミット済みの生成物とマニフェストは最新（--check exit 0）" 0 "$RC"
expect_out  "マニフェスト一致と出す" "マニフェスト一致" "$OUT"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8")); s=d["skills"]; assert d["count"]==len(s)>0; assert all(len(v["sha256"])==64 and v["files"]>=2 for v in s.values())' "$M" \
  && ok "スキルごとに files と 64 桁の sha256" || ng "マニフェストの形" "$(head -c 200 "$M")"
python3 -c 'import hashlib,json,os,sys
root=sys.argv[1]; d=os.path.join(root,"skills","done-gate"); h=hashlib.sha256(); n=0
fs=sorted(os.path.relpath(os.path.join(a,f),d).replace(os.sep,"/") for a,_,ff in os.walk(d) for f in ff)
for r in fs: h.update(r.encode()+b"\0"+open(os.path.join(d,r),"rb").read()+b"\0"); n+=1
m=json.load(open(os.path.join(root,"skills-manifest.json"),encoding="utf-8"))["skills"]["done-gate"]
assert m=={"files":n,"sha256":h.hexdigest()}, (m,n)' "$K/04_Codex" \
  && ok "sha256 は「相対パス＋NUL＋中身＋NUL」をパス順に連結したもの" || ng "sha256 の定義" "done-gate が一致しない"
echo "改変" >> "$K/04_Codex/skills/done-gate/SKILL.md"
OUT=$(python3 "$B" --check 2>&1); RC=$?
expect_exit "生成物を手で直すと --check は exit 1" 1 "$RC"
python3 "$B" >/dev/null
cp "$M" "$TMP/manifest.bak"
python3 -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p,encoding="utf-8")); d["skills"]["retro"]["sha256"]="0"*64; json.dump(d,open(p,"w",encoding="utf-8"))' "$M"
OUT=$(python3 "$B" --check 2>&1); RC=$?
expect_exit "マニフェストを改変すると --check は exit 1" 1 "$RC"
expect_out  "食い違うスキル名を出す" "skills-manifest.json が生成物と食い違う（1 件）" "$OUT"
expect_out  "スキル名 retro を出す" "retro" "$OUT"
rm "$M"
OUT=$(python3 "$B" --check 2>&1); RC=$?
expect_exit "マニフェストが無いと --check は exit 1" 1 "$RC"
python3 "$B" >/dev/null
OUT=$(python3 "$B" --check 2>&1); RC=$?
expect_exit "再生成すれば --check は exit 0" 0 "$RC"
cmp -s "$M" "$TMP/manifest.bak" && ok "再生成は同じマニフェストを書く（決定的）" || ng "決定的" "再生成で内容が変わった"
cmp -s "$M" "$KIT_DIR/04_Codex/skills-manifest.json" && ok "写しの生成結果がコミット済みと同じ" || ng "コミット済みと同じ" "差分あり"
python3 - "$K/03_ClaudeCode/skills/retro/SKILL.md" <<'EOF'
import sys
p = sys.argv[1]; s = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(s.replace("\n---\n", "\ndisable-model-invocation: true\n---\n", 1))
EOF
python3 "$B" >/dev/null
OUT=$(cat "$K/04_Codex/skills/retro/agents/openai.yaml")
expect_out  "disable-model-invocation: true は allow_implicit_invocation: false で生成" "allow_implicit_invocation: false" "$OUT"
OUT=$(python3 "$LINT" --skills "$K/03_ClaudeCode/skills" --codex "$K/04_Codex/skills" 2>&1); RC=$?
expect_exit "生成し直した写しは skill-lint も通る" 0 "$RC"
mv "$K/03_ClaudeCode" "$K/03_moved"
OUT=$(python3 "$B" --check 2>&1); RC=$?
expect_exit "生成元の無い配布先: マニフェスト一致で exit 0" 0 "$RC"
expect_out  "照合だけと出す" "マニフェストと一致" "$OUT"
echo "改変" >> "$K/04_Codex/skills/retro/SKILL.md"
OUT=$(python3 "$B" --check 2>&1); RC=$?
expect_exit "生成元の無い配布先: 改変を exit 1 で検出" 1 "$RC"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }

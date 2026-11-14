#!/bin/bash
# test-external-skills.sh — doctor.py D9「外部スキルの一致」の回帰テスト
# 一時ディレクトリに小さなキットの形とホーム（.agents/.claude/.codex の skills）を作り、--home で差し替えて確かめる。
# 一致で OK／未登録で WARN／欠落で WARN／sha256 不一致で WARN／retired の残存で WARN／リンク切れで WARN／
# マニフェスト破損・欠如で NG／置き場なしで SKIP／kit 配布名は外部に数えない。実物のキットのマニフェストが JSON として読めること。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DOCTOR="$KIT_DIR/00_導入/03_点検/doctor.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
export PYTHONDONTWRITEBYTECODE=1

echo "=== doctor D9 外部スキル 回帰テスト ==="
K="$TMP/kit"; H="$TMP/home"
M="$K/00_導入/01_インストール/external-skills.json"

# 小さなキット（D9 以外の項目は NG になるが、D9 の行だけを見る）とホームを作り、現物からマニフェストを書く
fresh() {
  rm -rf "$K" "$H"
  mkdir -p "$K/00_導入/01_インストール" "$K/03_ClaudeCode/skills/kit-skill" "$K/04_Codex/skills/cmd-x" \
           "$K/04_Codex/native-skills/aidd-kit"
  mkdir -p "$H/.agents/skills/ext-a/refs" "$H/.agents/skills/kit-skill" "$H/.agents/skills/cmd-x" \
           "$H/.claude/skills/kit-skill" "$H/.claude/skills/synced" "$H/.codex/skills/ext-c" "$H/.codex/skills/.system"
  printf -- '---\nname: ext-a\n---\nA\n' > "$H/.agents/skills/ext-a/SKILL.md"
  printf 'ref\n' > "$H/.agents/skills/ext-a/refs/r.md"
  printf -- '---\nname: ext-c\ndisable-model-invocation: true\n---\nC\n' > "$H/.codex/skills/ext-c/SKILL.md"
  printf 'K\n' > "$H/.agents/skills/kit-skill/SKILL.md"
  ln -s ../../.agents/skills/ext-a "$H/.claude/skills/ext-a"
  python3 - "$DOCTOR" "$H" "$M" <<'PY'
import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("doctor", sys.argv[1]); d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
h = Path(sys.argv[2])
doc = {"generated": "2026-11-14", "note": "test", "ignored": [".system", "synced"], "retired": ["old-one"],
       "skills": {"ext-a": {"tracked": False, "locations": ["agents", "claude"],
                            "sha256": d.tree_sha256(h / ".agents/skills/ext-a")},
                  "ext-c": {"tracked": False, "locations": ["codex"],
                            "sha256": d.tree_sha256(h / ".codex/skills/ext-c")}}}
Path(sys.argv[3]).write_text(json.dumps(doc), encoding="utf-8")
PY
}
# D9 の行（状態 TAB 対象 TAB 詳細）だけを取り出す
d9() { python3 "$DOCTOR" --root "$K" --home "$H" --json 2>/dev/null | python3 -c '
import json,sys
for i in json.load(sys.stdin)["items"]:
    if i["check"].startswith("D9"): print(i["status"]+"\t"+i["target"]+"\t"+i["detail"])'; }
has() { printf '%s\n' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "D9 に '$2' が無い: $(printf '%s' "$3" | tr '\n' '|' | cut -c1-300)"; }
hasnot() { printf '%s\n' "$3" | grep -qF -- "$2" && ng "$1" "D9 に '$2' が出た" || ok "$1"; }

echo "[一致]"
fresh; OUT=$(d9)
has    "一致なら集計行が OK" "OK	00_導入/01_インストール/external-skills.json	検査 2 件／マニフェスト 2 件・差分 0 件" "$OUT"
hasnot "一致なら WARN を出さない" "WARN" "$OUT"
hasnot "kit 配布名（kit-skill・cmd-x）は外部に数えない" "kit-skill" "$OUT"
hasnot "ignored（.system・synced）は外部に数えない" "synced" "$OUT"
TXT=$(python3 "$DOCTOR" --root "$K" --home "$H" 2>&1)
has    "テキスト出力でも D9 の検査件数を出す" "検査 2 件／マニフェスト 2 件" "$TXT"

echo "[未登録]"
fresh; mkdir -p "$H/.claude/skills/new-ext"; printf 'n\n' > "$H/.claude/skills/new-ext/SKILL.md"; OUT=$(d9)
has "環境にあるがマニフェストに無い外部スキルは WARN" "WARN	new-ext	環境にあるがマニフェストに無い外部スキル" "$OUT"
has "集計行も WARN で検査件数が増える" "WARN	00_導入/01_インストール/external-skills.json	検査 3 件／マニフェスト 2 件・差分 1 件" "$OUT"

echo "[欠落]"
fresh; rm "$H/.claude/skills/ext-a"; OUT=$(d9)
has "マニフェストの置き場に無ければ WARN（置き場名を出す）" "WARN	ext-a	マニフェストの置き場に無い: claude" "$OUT"
fresh; mv "$H/.codex/skills/ext-c" "$TMP/ext-c.bak"; OUT=$(d9)
has "全置き場から消えても WARN" "WARN	ext-c	マニフェストの置き場に無い: codex" "$OUT"
hasnot "消えたスキルは NG にしない" "NG	" "$OUT"

echo "[sha256 不一致]"
fresh; printf 'changed\n' >> "$H/.agents/skills/ext-a/refs/r.md"; OUT=$(d9)
has "中身が変われば WARN" "WARN	ext-a	sha256 が一致しない" "$OUT"
fresh; printf 'x\n' > "$H/.agents/skills/ext-a/added.md"; OUT=$(d9)
has "ファイルが増えても WARN" "WARN	ext-a	sha256 が一致しない" "$OUT"

echo "[retired]"
fresh; mkdir -p "$H/.agents/skills/old-one"; printf 'o\n' > "$H/.agents/skills/old-one/SKILL.md"; OUT=$(d9)
has "退役済みの名前が戻っていれば WARN" "WARN	old-one	退役済み（retired）の名前が環境に戻っている" "$OUT"

echo "[リンク切れ]"
fresh; ln -s ../../.agents/skills/gone "$H/.claude/skills/gone"; OUT=$(d9)
has "リンク切れは WARN（置き場/名前）" "WARN	claude/gone	リンク切れ" "$OUT"

echo "[kit に残っていてもマニフェストにあれば外部として検査]"
fresh; mkdir -p "$K/03_ClaudeCode/skills/ext-a"; printf 'changed\n' >> "$H/.agents/skills/ext-a/SKILL.md"; OUT=$(d9)
has "kit 側に同名があってもマニフェストの名前は検査する" "WARN	ext-a	sha256 が一致しない" "$OUT"

echo "[マニフェスト破損・欠如]"
fresh; printf '{broken' > "$M"; OUT=$(d9)
has "JSON として読めなければ NG" "NG	00_導入/01_インストール/external-skills.json	マニフェストが読めない" "$OUT"
python3 "$DOCTOR" --root "$K" --home "$H" >/dev/null 2>&1; RC=$?
[ "$RC" -eq 1 ] && ok "マニフェスト破損で exit 1" || ng "マニフェスト破損で exit 1" "exit=$RC"
fresh; rm "$M"; OUT=$(d9)
has "マニフェストが無ければ NG" "NG	00_導入/01_インストール/external-skills.json	マニフェストが読めない（FileNotFoundError" "$OUT"
fresh; printf '{"skills": []}' > "$M"; OUT=$(d9)
has "skills がオブジェクトでなければ NG" "skills がオブジェクトでない" "$OUT"

echo "[置き場なし]"
fresh; EMPTY="$TMP/empty-home"; mkdir -p "$EMPTY"
OUT=$(python3 "$DOCTOR" --root "$K" --home "$EMPTY" --json 2>/dev/null | python3 -c '
import json,sys
for i in json.load(sys.stdin)["items"]:
    if i["check"].startswith("D9"): print(i["status"]+"\t"+i["detail"])')
has    "置き場が 3 つとも無ければ SKIP（マニフェスト件数を出す）" "SKIP	置き場が無い" "$OUT"
has    "SKIP でもマニフェスト件数を出す" "マニフェスト 2 件" "$OUT"
hasnot "置き場なしは WARN を出さない" "WARN" "$OUT"

echo "[実物のマニフェスト]"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8")); s=d["skills"]
assert s and all(isinstance(v.get("sha256"),str) and len(v["sha256"])==64 for v in s.values())
assert all((v["source"] is None)==(not v["tracked"]) for v in s.values())
assert isinstance(d["retired"],list) and isinstance(d["ignored"],list)' "$KIT_DIR/00_導入/01_インストール/external-skills.json" \
  && ok "実物の external-skills.json は形が正しい（sha256 64桁・tracked と source の整合）" \
  || ng "実物の external-skills.json の形" "読めないか形が違う"

echo ""
echo "PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ]

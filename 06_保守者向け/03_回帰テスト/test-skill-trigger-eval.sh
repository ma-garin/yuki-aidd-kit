#!/bin/bash
# test-skill-trigger-eval.sh — skill_trigger_eval.py（A13）の回帰テスト
# 実 claude は一切呼ばない。PATH に置いた stub の claude（fixtures/stub-bin/claude）だけを使う。
# stub は発話文中の MARK_* トークンに応じて固定の stream-json 1 行を返す
# （fixtures/skill-trigger-stream.jsonl の対応表。MARK_TIMEOUT はスリープ、MARK_CRASH は非 0 終了）。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-200)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }

SCRIPT="$KIT_DIR/06_保守者向け/03_回帰テスト/skill_trigger_eval.py"
export SKILL_TRIGGER_FIXTURES="$KIT_DIR/06_保守者向け/03_回帰テスト/fixtures/skill-trigger-stream.jsonl"
export PATH="$KIT_DIR/06_保守者向け/03_回帰テスト/fixtures/stub-bin:$PATH"
run() { python3 "$SCRIPT" "$@" 2>&1; }

echo "=== skill_trigger_eval.py 回帰テスト ==="

# ---------------------------------------------------------------- 実物の skill-triggers/（20 本）
echo "[実物の skill-triggers/]"
[ "$(command -v claude)" = "$KIT_DIR/06_保守者向け/03_回帰テスト/fixtures/stub-bin/claude" ] && ok "PATH の先頭が stub の claude" || ng "PATH の先頭が stub の claude" "$(command -v claude)"

N_JSONL=$(ls "$KIT_DIR/06_保守者向け/03_回帰テスト/skill-triggers"/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
[ "$N_JSONL" -eq 20 ] && ok "skill-triggers/ に 20 本の jsonl がある" || ng "skill-triggers/ に 20 本の jsonl がある" "$N_JSONL 本"

python3 - "$KIT_DIR/06_保守者向け/03_回帰テスト/skill-triggers" <<'PY'
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
names = {f.stem for f in d.glob("*.jsonl")}
bad = []
for f in sorted(d.glob("*.jsonl")):
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            bad.append(f"{f.name}:{i} JSON不正 {e}"); continue
        if "utterance" not in row or "expect" not in row:
            bad.append(f"{f.name}:{i} utterance/expect 欠落"); continue
        if row["expect"] != "none" and row["expect"] not in names:
            bad.append(f"{f.name}:{i} expect不正 {row['expect']}")
if bad:
    print("\n".join(bad))
    sys.exit(1)
sys.exit(0)
PY
[ $? -eq 0 ] && ok "20 本すべて JSON として読め、expect が実在スキル名か none" || ng "20 本すべて JSON として読め、expect が実在スキル名か none" "壊れている行がある"

OUT=$(run --dry-run); RC=$?
expect_exit "実物 --dry-run は exit 0" 0 "$RC"
expect_out  "実物 --dry-run が 120 件（20×6）を数える" "件数: 120（20 スキル × 6 発話 × --runs 1）" "$OUT"

LOG="$TMP/called.log"
SKILL_TRIGGER_CALLED_LOG="$LOG" run --dry-run >/dev/null
[ -f "$LOG" ] && ng "--dry-run は claude を呼ばない" "呼び出しログが在る" || ok "--dry-run は claude を呼ばない"

# ---------------------------------------------------------------- 合成の発話ケース（判定の分岐を作り込む）
echo "[合成ケース: 正例発火率・誤発火率・取り違え]"
SYN="$TMP/triggers"; mkdir -p "$SYN"
cat > "$SYN/skill-a.jsonl" << 'EOF'
{"utterance": "正例1 MARK_FIRE_SKILL_A", "expect": "skill-a"}
{"utterance": "正例2 MARK_FIRE_SKILL_A", "expect": "skill-a"}
{"utterance": "正例3(取り違え) MARK_FIRE_SKILL_B", "expect": "skill-a"}
{"utterance": "負例1(誤発火) MARK_FIRE_SKILL_A", "expect": "skill-b"}
{"utterance": "負例2 MARK_NOFIRE", "expect": "skill-b"}
{"utterance": "負例3 MARK_NOFIRE", "expect": "none"}
EOF
cat > "$SYN/skill-b.jsonl" << 'EOF'
{"utterance": "b正例1 MARK_FIRE_SKILL_B", "expect": "skill-b"}
{"utterance": "b正例2 MARK_FIRE_SKILL_B", "expect": "skill-b"}
{"utterance": "b正例3 MARK_FIRE_SKILL_B", "expect": "skill-b"}
{"utterance": "b負例1 MARK_NOFIRE", "expect": "skill-a"}
{"utterance": "b負例2 MARK_NOFIRE", "expect": "none"}
{"utterance": "b負例3 MARK_NOFIRE", "expect": "none"}
EOF
OUT=$(run --triggers-dir "$SYN"); RC=$?
expect_exit "skill-a が閾値外なので exit 1" 1 "$RC"
expect_out  "skill-a の正例発火率 2/3(67%)" "| skill-a | 2/3 (67%) |" "$OUT"
expect_out  "skill-a の誤発火率 1/3(33%)" "1/3 (33%) | 0 |" "$OUT"
expect_out  "取り違え: skill-a→skill-b" "skill-a→skill-b×1" "$OUT"
expect_out  "取り違え: skill-b→none（誤発火でなく取り違えの表にも出る）" "skill-b→none×1" "$OUT"
expect_out  "skill-b は 3/3(100%)・誤発火 0/3(0%)" "| skill-b | 3/3 (100%) | 0/3 (0%) | 0 |" "$OUT"
expect_out  "NG（閾値外）に skill-a だけ" "NG（閾値外）: skill-a" "$OUT"
expect_noout "skill-b は NG に出ない" "NG（閾値外）: skill-a, skill-b" "$OUT"

echo "[合成ケース: 閾値の変更で exit 0 になる]"
OUT=$(run --triggers-dir "$SYN" --min-hit 0.5 --max-miss 0.5); RC=$?
expect_exit "--min-hit 0.5 --max-miss 0.5 なら exit 0" 0 "$RC"

echo "[合成ケース: 判定不能（タイムアウト・非0終了）は exit 2]"
SYN2="$TMP/triggers2"; mkdir -p "$SYN2"
cat > "$SYN2/skill-a.jsonl" << 'EOF'
{"utterance": "timeout MARK_TIMEOUT", "expect": "skill-a"}
{"utterance": "crash MARK_CRASH", "expect": "skill-a"}
{"utterance": "ok MARK_FIRE_SKILL_A", "expect": "skill-a"}
{"utterance": "neg1 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg2 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg3 MARK_NOFIRE", "expect": "none"}
EOF
OUT=$(run --triggers-dir "$SYN2" --timeout 1); RC=$?
expect_exit "タイムアウト＋クラッシュがあると exit 2（閾値外より優先）" 2 "$RC"
expect_out  "判定不能 2 件を数える" "判定不能: 2 件" "$OUT"
expect_out  "判定不能ありの警告行" "判定不能あり（2 件）" "$OUT"

echo "[合成ケース: 全部良好なら exit 0]"
SYN3="$TMP/triggers3"; mkdir -p "$SYN3"
cat > "$SYN3/skill-a.jsonl" << 'EOF'
{"utterance": "ok1 MARK_FIRE_SKILL_A", "expect": "skill-a"}
{"utterance": "ok2 MARK_FIRE_SKILL_A", "expect": "skill-a"}
{"utterance": "ok3 MARK_FIRE_SKILL_A", "expect": "skill-a"}
{"utterance": "neg1 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg2 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg3 MARK_NOFIRE", "expect": "none"}
EOF
OUT=$(run --triggers-dir "$SYN3"); RC=$?
expect_exit "正例3/3・誤発火0/3なら exit 0" 0 "$RC"
expect_out  "取り違えは無し（-）" "| skill-a | 3/3 (100%) | 0/3 (0%) | 0 | - |" "$OUT"

echo "[--only は指定したスキルの jsonl だけ読む]"
OUT=$(run --triggers-dir "$SYN" --only skill-b --dry-run)
expect_out  "--only skill-b は 6 件だけ数える" "件数: 6（1 スキル × 6 発話 × --runs 1）" "$OUT"

echo "[--runs N は発話ごとに N 回 claude を呼ぶ]"
CALLLOG="$TMP/calls-runs.log"
SKILL_TRIGGER_CALLED_LOG="$CALLLOG" run --triggers-dir "$SYN3" --runs 3 >/dev/null
CALLS=$(wc -l < "$CALLLOG" | tr -d ' ')
[ "$CALLS" -eq 18 ] && ok "--runs 3・6発話で claude を 18 回呼ぶ" || ng "--runs 3・6発話で claude を 18 回呼ぶ" "$CALLS 回"

echo "[存在しない --only は exit 2]"
OUT=$(run --triggers-dir "$SYN" --only no-such-skill --dry-run); RC=$?
expect_exit "無い --only は exit 2" 2 "$RC"

# ---------------------------------------------------------------- [検証: B-25]
echo "[検証: B-25] 実API経路の fail-closed 確認"
V3="$TMP/triggers-v3"; mkdir -p "$V3"
cat > "$V3/skill-a.jsonl" << 'EOF'
{"utterance": "x1", "expect": "skill-a"}
{"utterance": "x2", "expect": "skill-a"}
{"utterance": "x3", "expect": "skill-a"}
{"utterance": "x4", "expect": "none"}
{"utterance": "x5", "expect": "none"}
{"utterance": "x6", "expect": "none"}
EOF
OUT=$(python3 "$SCRIPT" --triggers-dir "$V3" --claude /no/such/claude-binary-xyz 2>&1); RC=$?
expect_exit "claude 実行ファイルが無い(--dry-run 無し)と判定不能で exit 2" 2 "$RC"

echo "[検証: B-25] 未使用だった fixture マーカーで stream-json の揺れを埋める"
V4="$TMP/triggers-v4"; mkdir -p "$V4"
cat > "$V4/skill-a.jsonl" << 'EOF'
{"utterance": "other MARK_OTHER_TOOL", "expect": "skill-a"}
{"utterance": "neg1 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg2 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg3 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg4 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg5 MARK_NOFIRE", "expect": "none"}
EOF
OUT=$(run --triggers-dir "$V4" --only skill-a)
expect_out "最初の tool_use が Skill 以外（Read）なら発火なし＝0/1" "| skill-a | 0/1 (0%) |" "$OUT"

V5="$TMP/triggers-v5"; mkdir -p "$V5"
cat > "$V5/skill-a.jsonl" << 'EOF'
{"utterance": "legacy MARK_FIRE_LEGACY_NAME", "expect": "skill-a"}
{"utterance": "neg1 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg2 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg3 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg4 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg5 MARK_NOFIRE", "expect": "none"}
EOF
OUT=$(run --triggers-dir "$V5" --only skill-a)
expect_out "input.skill が無く input.name だけでもフォールバックで 1/1 命中" "| skill-a | 1/1 (100%) |" "$OUT"

echo "[検証: B-25] stream-json が壊れているとき「判定不能」になるべきだが、なっていない（赤）"
V1="$TMP/triggers-v1"; mkdir -p "$V1"
cat > "$V1/skill-a.jsonl" << 'EOF'
{"utterance": "badutf8 MARK_BADUTF8", "expect": "skill-a"}
{"utterance": "neg1 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg2 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg3 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg4 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg5 MARK_NOFIRE", "expect": "none"}
EOF
OUT=$(run --triggers-dir "$V1" --only skill-a); RC=$?
expect_exit "[赤] 非UTF-8のstdoutは例外を投げず判定不能(exit 2)にすべき" 2 "$RC"

V2="$TMP/triggers-v2"; mkdir -p "$V2"
cat > "$V2/skill-a.jsonl" << 'EOF'
{"utterance": "trunc MARK_TRUNCATED", "expect": "skill-a"}
{"utterance": "neg1 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg2 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg3 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg4 MARK_NOFIRE", "expect": "none"}
{"utterance": "neg5 MARK_NOFIRE", "expect": "none"}
EOF
OUT=$(run --triggers-dir "$V2" --only skill-a)
expect_out "[赤] 途中で切れたJSONは判定不能1件として数えるべき（実際は発火なし扱いに化ける）" "判定不能: 1 件" "$OUT"

echo "[検証: B-25] 戻すと赤: input.name フォールバックを外すと Case[input.name]が落ちるか"
cp "$SCRIPT" "$TMP/skill_trigger_eval.orig.py"
python3 - "$SCRIPT" << 'PY'
import sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
old = 'return inp.get("skill") or inp.get("name") or NONE_'
new = 'return inp.get("skill") or NONE_'
assert old in s, "対象の行が見つからない（実装が変わった?）"
open(p, "w", encoding="utf-8").write(s.replace(old, new, 1))
PY
OUT=$(run --triggers-dir "$V5" --only skill-a); RC=$?
if printf '%s' "$OUT" | grep -qF -- "| skill-a | 0/1 (0%) |"; then
  ok "戻すと赤: input.name フォールバックを外すと 1/1→0/1 に落ちて検知できる"
else
  ng "戻すと赤: input.name フォールバックを外すと 1/1→0/1 に落ちて検知できる" "落ちなかった（テストが空振り）: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-200)"
fi
cp "$TMP/skill_trigger_eval.orig.py" "$SCRIPT"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }

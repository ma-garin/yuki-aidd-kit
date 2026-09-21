#!/bin/bash
# test-check-approval.sh — check-approval.sh（check_approval.py）の回帰テスト
#
# 一時プロジェクトに init-lifecycle.sh で雛形を置き、工程の着手・承認・改変を再現して
# 「壊した箇所を検出できること」と「配布される雛形そのものが NG=0 で通ること」を両方確認する。
# 終了コードの契約（0=合格 / 1=未承認・失効・順序違反 / 2=判定不能）を全ケースで assert する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-160)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }

# 承認記録を書き換えるヘルパ。reviewed_hash は最後に実測で入れる（版に縛る仕組みをそのまま使う）
cat > "$TMP/fill.py" <<'PY'
import subprocess, sys, re
from pathlib import Path
proj, phase, verdict = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
opts = dict(a.split("=", 1) for a in sys.argv[4:])
p = proj / "docs/lifecycle/approvals" / f"phase-{phase}.md"
s = p.read_text(encoding="utf-8")

def meta(key, val):
    global s
    s = re.sub(rf"^\| {key} \| .*? \|$", f"| {key} | {val} |", s, count=1, flags=re.M)

s = s.replace("判定: 未記入", f"判定: {verdict}", 1)
meta("approver", opts.get("approver", "藤曲 雄基"))
meta("approved_at", opts.get("approved_at", "2026-09-19T10:00:00+09:00"))
meta("git_head", opts.get("git_head", "0123456789abcdef"))
if "covers" in opts:
    meta("covers", opts["covers"])
if opts.get("grounds", "1") == "1":
    s = s.replace("| 出口基準 | 確認方法・確認した対象 | 結果 |\n|---|---|---|",
                  "| 出口基準 | 確認方法・確認した対象 | 結果 |\n|---|---|---|\n"
                  "| 全 REQ-F が BD に割り当て済み | traceability-matrix.md の BD 列 12 行を目視 | 充足 |", 1)
if "condition" in opts:
    s = s.replace("| # | 条件 | 検証方法 | 期限 |\n|---|---|---|---|",
                  "| # | 条件 | 検証方法 | 期限 |\n|---|---|---|---|\n"
                  "| 1 | 外部I/Fの失敗時挙動を追記 | 02-basic-design.md の外部I/F表に行が増えること | 2026-09-30 |", 1)
if "reject" in opts:
    how = "" if opts["reject"] == "nohow" else "phase-2.md の根拠表に該当行が追加されること"
    state = "解消済み" if opts["reject"] == "resolved" else "未解消"
    s = s.replace("| ID | 内容 | 解消の検証方法 | 状態 |\n|---|---|---|---|",
                  "| ID | 内容 | 解消の検証方法 | 状態 |\n|---|---|---|---|\n"
                  f"| R-{phase}-1 | 外部I/Fの異常系が未定義 | {how} | {state} |", 1)
if "unknown" in opts:
    s = s.replace("**ここに項目が残っている限り",
                  "- REQ-N-003 の性能目標を実測できていない\n\n**ここに項目が残っている限り", 1)
p.write_text(s, encoding="utf-8")

# covers の実測ハッシュを入れる（opts["hash"] があればそれを優先＝不一致の再現用）
covers = re.search(r"^\| covers \| (.*?) \|$", s, re.M).group(1)
if "hash" in opts:
    h = opts["hash"]
else:
    args = [c.strip() for c in covers.split(",") if c.strip()]
    h = subprocess.run([sys.executable, str(Path(sys.argv[0]).parent / "phase-hash.py"), *args],
                       cwd=proj, capture_output=True, text=True).stdout.strip() or "error"
s = re.sub(r"^\| reviewed_hash \| .*? \|$", f"| reviewed_hash | {h} |", s, count=1, flags=re.M)
p.write_text(s, encoding="utf-8")
PY
cp "$KIT_DIR/tools/phase-hash.py" "$TMP/phase-hash.py"

proj() { # 新しい一時プロジェクトを作って雛形を置く
  local d="$TMP/p$RANDOM$RANDOM"; mkdir -p "$d"
  "$KIT_DIR/scripts/init-lifecycle.sh" "$d" >/dev/null; echo "$d"
}
start() { # 工程 $2 を「着手済み」にする（雛形の日付プレースホルダを実日付に置換）
  local f; f=$(ls "$1/docs/lifecycle/0$2-"*.md); sed -i 's/YYYY-MM-DD/2026-09-19/' "$f"
}
fill() { python3 "$TMP/fill.py" "$@"; }
run()  { python3 "$KIT_DIR/tools/check_approval.py" --root "$1" -o "$TMP/report.md" "${@:2}" 2>&1; }

echo "=== check-approval.sh 回帰テスト ==="

echo "[ケース1: 配布雛形（init-lifecycle.sh 直後）]"
P=$(proj); OUT=$(run "$P"); RC=$?
expect_exit "全工程が未着手なら exit 0" 0 "$RC"
expect_out  "結論に NG=0" "NG=0" "$OUT"
grep -q "工程承認検査レポート" "$TMP/report.md" && grep -q "| 2 | 基本設計 | 未着手 |" "$TMP/report.md" \
  && ok "工程別の状態表を書き出す" || ng "工程別の状態表を書き出す" "レポートに無い"

echo "[ケース2: 着手済みなのに承認記録が無い]"
P=$(proj); start "$P" 1; rm "$P/docs/lifecycle/approvals/phase-1.md"
OUT=$(run "$P"); RC=$?
expect_exit "exit 1" 1 "$RC"
expect_out  "種別「未承認」で検出" "未承認" "$OUT"

echo "[ケース3: 着手済み・判定が未記入]"
P=$(proj); start "$P" 1
OUT=$(run "$P"); RC=$?
expect_exit "exit 1" 1 "$RC"
expect_out  "未記入は判定値でなく未承認として扱う" "判定が未記入" "$OUT"

echo "[ケース4: 正しく承認されている]"
P=$(proj); start "$P" 1; fill "$P" 1 承認
OUT=$(run "$P"); RC=$?
expect_exit "exit 0" 0 "$RC"
expect_out  "承認済み 1 工程" "承認済み 1 工程" "$OUT"

echo "[ケース5: 承認後に成果物を変更（失効）]"
P=$(proj); start "$P" 1; fill "$P" 1 承認
echo "後から足した一文" >> "$P/docs/lifecycle/01-requirements.md"
OUT=$(run "$P"); RC=$?
expect_exit "exit 1" 1 "$RC"
expect_out  "種別「失効」で検出" "失効" "$OUT"
expect_out  "承認時と現在のハッシュを併記" "承認後に成果物が変更されています" "$OUT"

echo "[ケース6: 判定が3値のいずれでもない]"
P=$(proj); start "$P" 1; fill "$P" 1 OK
OUT=$(run "$P"); RC=$?
expect_exit "判定不能は exit 2" 2 "$RC"
expect_out  "種別「判定不能」で検出" "判定不能" "$OUT"

echo "[ケース7: 承認だが必須欄が未記入]"
P=$(proj); start "$P" 1; fill "$P" 1 承認 approved_at=未記入
OUT=$(run "$P"); RC=$?
expect_exit "exit 2" 2 "$RC"
expect_out  "未記入の欄名を出す" "approved_at" "$OUT"

echo "[ケース8: approver が人間でない]"
P=$(proj); start "$P" 1; fill "$P" 1 承認 approver=Claude
OUT=$(run "$P"); RC=$?
expect_exit "exit 2" 2 "$RC"
expect_out  "AI は承認できない旨を出す" "承認は人間しか行えません" "$OUT"
P=$(proj); start "$P" 1; fill "$P" 1 承認 approver=Verifier
OUT=$(run "$P"); RC=$?
expect_exit "AI 役名（Verifier）も弾く" 2 "$RC"

echo "[ケース9: 承認だが根拠表が空]"
P=$(proj); start "$P" 1; fill "$P" 1 承認 grounds=0
OUT=$(run "$P"); RC=$?
expect_exit "exit 2" 2 "$RC"
expect_out  "根拠が空である旨を出す" "「根拠」表が空です" "$OUT"

echo "[ケース10: 未確認事項を残したまま承認（判定不能を合格に数えない）]"
P=$(proj); start "$P" 1; fill "$P" 1 承認 unknown=1
OUT=$(run "$P"); RC=$?
expect_exit "exit 2" 2 "$RC"
expect_out  "未確認事項の残件を出す" "未確認事項が 1 件残ったまま" "$OUT"

echo "[ケース11: 未解消の差し戻し事項を残したまま承認]"
P=$(proj); start "$P" 1; fill "$P" 1 承認 reject=open
OUT=$(run "$P"); RC=$?
expect_exit "exit 2" 2 "$RC"
expect_out  "矛盾を検出" "未解消の差し戻し事項が残ったまま" "$OUT"
P=$(proj); start "$P" 1; fill "$P" 1 承認 reject=resolved
OUT=$(run "$P"); RC=$?
expect_exit "解消済みなら承認は有効（exit 0）" 0 "$RC"

echo "[ケース12: 条件付き承認]"
P=$(proj); start "$P" 1; fill "$P" 1 条件付き承認
OUT=$(run "$P"); RC=$?
expect_exit "条件表が空なら exit 2" 2 "$RC"
expect_out  "条件が必須である旨を出す" "条件表が空です" "$OUT"
P=$(proj); start "$P" 1; fill "$P" 1 条件付き承認 condition=1
OUT=$(run "$P"); RC=$?
expect_exit "条件があれば exit 0" 0 "$RC"

echo "[ケース13: 差し戻し]"
P=$(proj); start "$P" 1; fill "$P" 1 差し戻し reject=nohow
OUT=$(run "$P"); RC=$?
expect_exit "解消の検証方法が無ければ exit 2" 2 "$RC"
expect_out  "検証方法の欠落を指摘" "解消の検証方法" "$OUT"
P=$(proj); start "$P" 1; fill "$P" 1 差し戻し reject=open
OUT=$(run "$P"); RC=$?
expect_exit "正しい差し戻しは未承認（exit 1）" 1 "$RC"
expect_out  "未解消件数を出す" "差し戻し中" "$OUT"

echo "[ケース14: covers に実在しないパス]"
P=$(proj); start "$P" 1; fill "$P" 1 承認 covers=docs/lifecycle/99-nope.md
OUT=$(run "$P"); RC=$?
expect_exit "exit 2" 2 "$RC"
expect_out  "実在しない covers を指摘" "covers に実在しないパス" "$OUT"

echo "[ケース15: 工程順序 — 前工程が未承認のまま次工程に着手]"
P=$(proj); start "$P" 1; start "$P" 2
OUT=$(run "$P"); RC=$?
expect_exit "exit 1" 1 "$RC"
expect_out  "種別「工程順序」で検出" "工程順序" "$OUT"
expect_out  "伝播の理由を出す" "誤りが下流へ伝播します" "$OUT"

echo "[ケース16: 工程の省略は許容する（直前の着手済み工程だけを見る）]"
P=$(proj); start "$P" 1; fill "$P" 1 承認; start "$P" 3; fill "$P" 3 承認
OUT=$(run "$P"); RC=$?
expect_exit "第2工程を省略しても exit 0" 0 "$RC"
expect_noout "工程順序の NG を出さない" "工程順序" "$OUT"

echo "[ケース17: 後続工程を進めても前工程の承認は失効しない]"
P=$(proj); start "$P" 1; fill "$P" 1 承認
start "$P" 2; fill "$P" 2 承認
sed -i 's/YYYY-MM-DD/2026-09-19/' "$P/docs/lifecycle/traceability-matrix.md"
echo "| REQ-F-002 |  | RFD-001 | BD-002 | - | - | - | - | - | UAT-002 | 未着手 |" >> "$P/docs/lifecycle/traceability-matrix.md"
OUT=$(run "$P"); RC=$?
expect_exit "追跡表を更新しても exit 0（covers に追跡表を入れない設計）" 0 "$RC"
expect_noout "失効を出さない" "失効" "$OUT"

echo "[ケース18: --gate（この工程に着手してよいか）]"
P=$(proj); start "$P" 1
OUT=$(run "$P" --gate 2); RC=$?
expect_exit "前工程が未承認なら exit 1" 1 "$RC"
expect_out  "次の行動を出す" "/phase-review 1" "$OUT"
fill "$P" 1 承認
OUT=$(run "$P" --gate 2); RC=$?
expect_exit "前工程が承認済みなら exit 0" 0 "$RC"
P=$(proj)
OUT=$(run "$P" --gate 2); RC=$?
expect_exit "手前に着手済みが無ければ exit 0" 0 "$RC"
P=$(proj); start "$P" 1; fill "$P" 1 OK
OUT=$(run "$P" --gate 2); RC=$?
expect_exit "前工程が判定不能なら exit 2" 2 "$RC"

echo "[ケース19: --phase / --quiet]"
P=$(proj); start "$P" 1; fill "$P" 1 承認
OUT=$(run "$P" --phase 1); RC=$?
expect_exit "承認済みの工程は exit 0" 0 "$RC"
OUT=$(run "$P" --phase 5); RC=$?
expect_exit "未着手の工程は exit 1" 1 "$RC"
OUT=$(run "$P" --phase 99); RC=$?
expect_exit "範囲外の工程番号は exit 2" 2 "$RC"
P=$(proj); start "$P" 1
OUT=$(run "$P" --gate 2 --quiet); RC=$?
expect_exit "--quiet でも終了コードは同じ" 1 "$RC"
[ -z "$OUT" ] && ok "--quiet は何も出力しない" || ng "--quiet は何も出力しない" "出力: $OUT"

echo "[ケース20: 工程文書が無いプロジェクト]"
P="$TMP/empty"; mkdir -p "$P"
OUT=$(run "$P"); RC=$?
expect_exit "対象なしは exit 0" 0 "$RC"
expect_out  "スキップした旨を出す" "スキップ" "$OUT"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }

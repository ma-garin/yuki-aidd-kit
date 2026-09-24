#!/bin/bash
# test-e2e-history.sh — e2e_history.py（E2E のテスト単位の履歴と flaky 率。B27）の回帰テスト
#
# Playwright は入れない。JSON reporter の出力は合成 fixture（suites → specs → tests → results の形）で作る。
# 確かめること: add → report の往復、履歴 3 回未満は「判定不能」で合格に数えない、flaky 率、前回からの回帰、
# skipped を合格に数えない、同じ結果の二重追記をしない、壊れた JSON・壊れた履歴の行で落ちない。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="$KIT_DIR/02_共通/ツール/e2e_history.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-240)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }
H="$TMP/hist.jsonl"
hist() { python3 "$TOOL" "$@" --history "$H" 2>&1; }
row() { printf '%s\n' "$2" | grep -F "| $1 ›" | head -1; }   # report の表から 1 テストの行を取り出す

# 合成の JSON reporter 出力。引数: 出力先 startTime 「file|describe|title|project|status」...（status は expected/unexpected/flaky/skipped）
cat > "$TMP/gen.py" <<'PY'
import json, sys
out, start, *specs = sys.argv[1:]
files = {}
for s in specs:
    f, desc, title, proj, st = s.split("|")
    res = {"expected": ["passed"], "unexpected": ["failed", "failed"], "flaky": ["failed", "passed"], "skipped": ["skipped"]}[st]
    test = {"projectName": proj, "projectId": proj, "expectedStatus": "passed", "status": st,
            "results": [{"status": r, "duration": 1000, "retry": i, "errors": []} for i, r in enumerate(res)]}
    spec = {"title": title, "file": f, "line": 3, "ok": st != "unexpected", "tests": [test]}
    top = files.setdefault(f, {"title": f, "file": f, "specs": [], "suites": []})
    if desc:
        sub = next((x for x in top["suites"] if x["title"] == desc), None)
        if sub is None:
            sub = {"title": desc, "file": f, "specs": [], "suites": []}
            top["suites"].append(sub)
        sub["specs"].append(spec)
    else:
        top["specs"].append(spec)
json.dump({"config": {}, "suites": list(files.values()), "errors": [], "stats": {"startTime": start, "duration": 1.0}}, open(out, "w"))
PY
gen() { python3 "$TMP/gen.py" "$@"; }
# 1 回分を add する。引数: 回の番号 login の結果 cart の結果 flaky の結果 skip の結果
N=0
run_once() {
  N=$((N+1))
  gen "$TMP/r$N.json" "2026-09-2${N}T10:00:00.000Z" \
    "login.spec.ts|ログイン|正しいパスワードで入れる|chromium|$1" \
    "cart.spec.ts||カートに追加できる|chromium|$2" \
    "search.spec.ts|検索|候補が出る|chromium|$3" \
    "report.spec.ts||帳票を出せる|chromium|$4"
  hist add "$TMP/r$N.json" --commit "c$N"
}

echo "=== e2e_history.py 回帰テスト ==="

echo "[add と 1 回目の report: 履歴 3 回未満は判定不能]"
run_once expected expected expected skipped > "$TMP/out1" 2>&1; RC=$?; OUT=$(cat "$TMP/out1")
expect_exit "add が exit 0" 0 "$RC"
expect_out  "add が件数を出す（4 テスト）" "追記: 4 テスト" "$OUT"
[ "$(wc -l < "$H" | tr -d ' ')" -eq 4 ] && ok "テスト 1 本 = 1 行で追記される（4 行）" || ng "テスト 1 本 = 1 行で追記される" "$(wc -l < "$H") 行"
python3 -c 'import json,sys
d=[json.loads(l) for l in open(sys.argv[1])]
r=[x for x in d if x["file"]=="login.spec.ts"][0]
ok = r["title"]=="ログイン › 正しいパスワードで入れる" and r["project"]=="chromium" and r["commit"]=="c1" and r["time"].startswith("2026-09-21") and r["outcome"]=="pass" and r["duration_ms"]==1000
sys.exit(0 if ok else 1)' "$H" && ok "記録に file・describe を含む題名・project・commit・時刻・結果・所要が入る" || ng "記録の欄" "$(head -1 "$H")"
OUT=$(hist report); RC=$?
expect_exit "report が exit 0" 0 "$RC"
expect_out  "1 回だけのテストは判定不能" "判定不能 4" "$OUT"
expect_out  "判定不能を合格に数えない（合格 0）" "合格 0 /" "$OUT"
expect_out  "1 回目は変化「新規」" "| 新規 |" "$OUT"

echo "[二重追記をしない]"
OUT=$(hist add "$TMP/r1.json"); RC=$?
expect_exit "同じ結果の再 add は exit 0" 0 "$RC"
expect_out  "同じ結果の再 add は重ねない旨を出す" "追記済み" "$OUT"
[ "$(wc -l < "$H" | tr -d ' ')" -eq 4 ] && ok "再 add で行が増えない" || ng "再 add で行が増えない" "$(wc -l < "$H") 行"

echo "[3 回以上で判定: 合格・flaky・回帰・skipped]"
run_once expected unexpected expected skipped >/dev/null
run_once expected expected   expected skipped >/dev/null
run_once unexpected unexpected flaky skipped >/dev/null
OUT=$(hist report); RC=$?
expect_exit "report が exit 0" 0 "$RC"
# login: pass,pass,pass,fail → 回帰・失敗（flaky 率 1/4 = 25%）
expect_out  "前回 pass → 今回 fail を回帰として出す（揺れの少ないものは失敗）" "| 25% | pass → fail | 回帰 | 失敗 |" "$(row login.spec.ts "$OUT")"
FIRST=$(printf '%s\n' "$OUT" | grep '^| [a-z]' | head -1)
expect_out  "回帰を表の先頭に置く" "| 回帰 |" "$FIRST"
expect_out  "describe を含む題名と project を出す" "login.spec.ts › ログイン › 正しいパスワードで入れる [chromium]" "$OUT"
# cart: pass,fail,pass,fail → 切り替わり 3 / 4 = 75%
expect_out  "pass/fail が混在するテストの通過率 2/4 = 50%・flaky 率 3/4 = 75%" "| 4（4） | 50% | 75% |" "$(row cart.spec.ts "$OUT")"
expect_out  "flaky 率 30% 以上は今回 fail でも flaky（決定的な失敗と決めつけない）" "| 回帰 | flaky |" "$(row cart.spec.ts "$OUT")"
# search: pass,pass,pass,flaky → 1/4 = 25%。通過率 3/4（flaky は通過に数えない）
expect_out  "リトライで通った回（flaky）は通過に数えず flaky 率に入る（75%・25%）" "| 4（4） | 75% | 25% |" "$(row search.spec.ts "$OUT")"
# report: skipped×4 → 有効 0 回で判定不能
expect_out  "skipped だけのテストは有効 0 回で判定不能（合格に数えない）" "| 4（0） | — | — | — | — | 判定不能 |" "$(row report.spec.ts "$OUT")"
expect_out  "flaky 率 30% 以上の案内に failure-rules.md を出す" "failure-rules.md" "$OUT"

echo "[flaky の判定と直近 N 回]"
run_once expected expected expected skipped >/dev/null   # login: fail→pass（修正）
OUT=$(hist report --json); RC=$?
expect_exit "--json が exit 0" 0 "$RC"
python3 - "$OUT" <<'PY' && ok "--json: search は合格（20%）、login は修正・flaky（P,P,P,F,P = 40%）、cart は flaky（80%）、report は判定不能" || ng "--json の中身" "$(printf '%s' "$OUT" | head -c 400)"
import json, sys
d = json.loads(sys.argv[1])
t = {x["file"]: x for x in d["tests"]}
ok = (t["search.spec.ts"]["verdict"] == "合格" and abs(t["search.spec.ts"]["flaky_rate"] - 0.2) < 1e-9
      and t["login.spec.ts"]["change"] == "修正" and t["login.spec.ts"]["verdict"] == "flaky"
      and t["cart.spec.ts"]["verdict"] == "flaky" and abs(t["cart.spec.ts"]["flaky_rate"] - 0.8) < 1e-9
      and t["report.spec.ts"]["verdict"] == "判定不能"
      and d["summary"]["判定不能"] == 1 and d["summary"]["合格"] == 1 and d["summary"]["flaky"] == 2)
sys.exit(0 if ok else 1)
PY
OUT=$(hist report --last 2 --json)
python3 - "$OUT" <<'PY' && ok "--last 2 は直近 2 回だけを見る（2 回は判定不能）" || ng "--last 2" "$(printf '%s' "$OUT" | head -c 300)"
import json, sys
d = json.loads(sys.argv[1])
sys.exit(0 if all(x["records"] <= 2 and x["verdict"] == "判定不能" for x in d["tests"]) else 1)
PY
# 途中から壊れた（fail が続く）テストは flaky ではなく失敗: pass×5 のあと fail×5 → 切り替わり 1/10 = 10%
H2="$TMP/h2.jsonl"
for i in 1 2 3 4 5 6 7 8 9 10; do
  st=expected; [ "$i" -gt 5 ] && st=unexpected
  gen "$TMP/b$i.json" "2026-09-10T10:$((10 + i)):00Z" "broken.spec.ts||壊れた|chromium|$st"
  python3 "$TOOL" add "$TMP/b$i.json" --history "$H2" --commit x >/dev/null 2>&1
done
OUT=$(python3 "$TOOL" report --history "$H2" 2>&1)
expect_out  "途中から壊れて落ち続けるテストは失敗（flaky 率 10%）" "| 10% | fail → fail | 継続 Fail | 失敗 |" "$(row broken.spec.ts "$OUT")"

echo "[壊れた入力で落ちない]"
BEFORE=$(wc -l < "$H" | tr -d ' ')
printf '{"suites": [ {"title": "x", ' > "$TMP/broken.json"
OUT=$(hist add "$TMP/broken.json"); RC=$?
expect_exit "壊れた JSON は exit 2" 2 "$RC"
expect_noout "壊れた JSON でトレースバックを出さない" "Traceback" "$OUT"
expect_out  "壊れた JSON の旨を出す" "壊れている" "$OUT"
[ "$(wc -l < "$H" | tr -d ' ')" -eq "$BEFORE" ] && ok "壊れた JSON では履歴に追記しない" || ng "壊れた JSON では履歴に追記しない" "行数が変わった"
echo '{"foo": 1}' > "$TMP/other.json"
OUT=$(hist add "$TMP/other.json"); RC=$?
expect_exit "Playwright の出力でない JSON は exit 2" 2 "$RC"
OUT=$(hist add "$TMP/none.json"); RC=$?
expect_exit "結果ファイルが無ければ exit 2" 2 "$RC"
printf 'not json\n{"half": \n' >> "$H"
OUT=$(hist report); RC=$?
expect_exit "履歴に壊れた行があっても report は exit 0" 0 "$RC"
expect_noout "壊れた履歴でトレースバックを出さない" "Traceback" "$OUT"
expect_out  "壊れた行を読み飛ばした旨を出す" "壊れた行 2 行" "$OUT"
OUT=$(python3 "$TOOL" report --history "$TMP/nothing.jsonl" 2>&1); RC=$?
expect_exit "履歴が無ければ exit 2" 2 "$RC"
gen "$TMP/empty.json" "2026-09-29T10:00:00Z"
OUT=$(hist add "$TMP/empty.json"); RC=$?
expect_exit "テスト 0 件の結果は exit 0（記録しない）" 0 "$RC"
expect_out  "テスト 0 件の旨を出す" "0 件" "$OUT"

echo "[results から結果を決める（status が無い古い形）]"
python3 - "$TMP/old.json" <<'PY'
import json, sys
t = lambda rs: {"projectName": "", "results": [{"status": r, "duration": 10} for r in rs]}
json.dump({"suites": [{"title": "o.spec.ts", "file": "o.spec.ts", "specs": [
    {"title": "a", "file": "o.spec.ts", "tests": [t(["failed", "passed"])]},
    {"title": "b", "file": "o.spec.ts", "tests": [t(["timedOut"])]},
    {"title": "c", "file": "o.spec.ts", "tests": [t(["passed"])]}]}]}, open(sys.argv[1], "w"))
PY
H3="$TMP/h3.jsonl"
python3 "$TOOL" add "$TMP/old.json" --history "$H3" --commit x >/dev/null 2>&1
python3 -c 'import json,sys
d={x["title"]: x["outcome"] for x in map(json.loads, open(sys.argv[1]))}
sys.exit(0 if d=={"a":"flaky","b":"fail","c":"pass"} else 1)' "$H3" && ok "status が無ければ results から flaky / fail / pass を決める" || ng "results からの判定" "$(cat "$H3" 2>/dev/null | head -3)"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }

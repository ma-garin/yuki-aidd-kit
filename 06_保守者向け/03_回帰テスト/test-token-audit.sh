#!/bin/bash
# test-token-audit.sh — token-audit.sh（token_audit.py）と token_report.py の回帰テスト
# 「キット自身が NG=0 で通ること」と「配線漏れ・床の超過・MCP 過多を検出できること」を確認する。
# token_report.py --by は合成 transcript（fixtures/transcript-sample.jsonl。実物と同じ構造・偽の内容）で
# 回数・トークン・按分・requestId 重複除去・サブエージェントの合算を確かめ、壊れた入力で落ちないことも見る。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-160)"; }
run() { HOME="$TMP/nohome" python3 "$KIT_DIR/00_導入/03_点検/token_audit.py" --root "$1" -o "$TMP/report.md" 2>&1; }

echo "=== token-audit.sh 回帰テスト ==="

echo "[ケース1: キット自身]"
OUT=$(run "$KIT_DIR"); RC=$?
expect_exit "キット自身は exit 0" 0 "$RC"
expect_out  "床の推定 tok を出す" "床（常時読み込み・推定）≒" "$OUT"
expect_out  "配線済みの結論" "NG=0" "$OUT"
grep -q "手元でしか測れないもの" "$TMP/report.md" && ok "レポートに /context /usage /doctor の案内" || ng "レポートに /context /usage /doctor の案内" "無い"

echo "[ケース2: 配布先（export-project.sh 直後）]"
P="$TMP/proj"; mkdir -p "$P"; bash "$KIT_DIR/00_導入/02_プロジェクト配布/export-project.sh" "$P" >/dev/null 2>&1
OUT=$(run "$P"); RC=$?
expect_exit "配布直後も exit 0（.claude/settings.json と .claude/rules を見る）" 0 "$RC"
grep -q "settings: .*\.claude/settings.json" "$TMP/report.md" && ok "配布先の .claude/settings.json を読む（レポートに明記）" || ng "配布先の .claude/settings.json を読む" "$(grep 'settings:' "$TMP/report.md")"

echo "[ケース3: 配線漏れ]"
python3 - "$P/.claude/settings.json" <<'PY'
import json,sys; p=sys.argv[1]; d=json.load(open(p)); d.pop("effortLevel",None)
for grp in d["hooks"]["PreToolUse"]:
    grp["hooks"]=[h for h in grp["hooks"] if "filter-output" not in h["command"]]
json.dump(d,open(p,"w"),ensure_ascii=False,indent=2)
PY
OUT=$(run "$P"); RC=$?
expect_exit "effortLevel と filter-output.py を外すと exit 1" 1 "$RC"
expect_out  "種別「配線」で検出" "配線" "$OUT"
grep -q "filter-output.py が hooks に配線されていない" "$TMP/report.md" && ok "欠けた hook 名を出す" || ng "欠けた hook 名を出す" "無い"

echo "[ケース4: 実測ログの集計]"
P2="$TMP/proj2"; mkdir -p "$P2"; bash "$KIT_DIR/00_導入/02_プロジェクト配布/export-project.sh" "$P2" >/dev/null 2>&1
for i in 1 2 3; do printf '2026-09-19T10:00:00+0900\t{"file_path":"/x/CLAUDE.md"}\n' >> "$P2/.claude/instructions-loaded.log"; done
printf '2026-09-19T10:00:00+0900\t{"file_path":"/x/rules/speed-harness.md"}\n' >> "$P2/.claude/instructions-loaded.log"
run "$P2" >/dev/null
grep -q "CLAUDE.md×3" "$TMP/report.md" && ok "ログをファイル別に集計する（CLAUDE.md×3）" || ng "ログをファイル別に集計する" "$(grep '実測ログ' "$TMP/report.md")"

echo "[ケース5: MCP 過多は WARN（exit 0）]"
printf '{"mcpServers":{"a":{},"b":{},"c":{},"d":{}}}' > "$P2/.mcp.json"
OUT=$(run "$P2"); RC=$?
expect_exit "MCP 4 個でも exit 0（WARN）" 0 "$RC"
expect_out  "警告に MCP" "MCP" "$OUT"

# ---------------------------------------------------------------- token_report.py
TR="$KIT_DIR/00_導入/03_点検/token_report.py"
FX="$KIT_DIR/06_保守者向け/03_回帰テスト/fixtures/transcript-sample.jsonl"
trep() { python3 "$TR" "$@" 2>&1; }
expect_noout() { printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }

echo "[ケース6: token_report.py 既存の出力（合計と構成比）は変えない]"
OUT=$(trep "$FX"); RC=$?
expect_exit "--by 無しは exit 0" 0 "$RC"
expect_out  "応答数は message.id で 1 回ずつ（6 件）" "応答 6 件" "$OUT"
expect_out  "4 種の合計" "| 計 | 47,768 |" "$OUT"
expect_noout "--by 無しでは区分別を出さない" "区分別" "$OUT"
OUT_BY=$(trep --by skill,agent,mcp,tool "$FX")
[ "$(printf '%s\n' "$OUT_BY" | head -n "$(printf '%s\n' "$OUT" | wc -l)")" = "$OUT" ] && ok "--by を付けても既存の部分は同じ" || ng "--by を付けても既存の部分は同じ" "先頭が変わった"

echo "[ケース7: --by skill,agent,mcp,tool]"
expect_out  "表の見出し（区分・名前・回数・トークン・費用比・平均・最大）" "| 区分 | 名前 | 回数 | トークン | 費用比 | 平均 | 最大 |" "$OUT_BY"
expect_out  "skill: Skill の tool_use 2 回＋/demo-skill 1 回、トークン・費用比・平均・最大" "| skill | demo-skill | 3 | 7,200 | 14.81% | 2,400 | 6,150 |" "$OUT_BY"
expect_out  "按分: 1 応答の Read 2 個に usage を等分（平均 5,050）" "| tool | Read | 2 | 10,100 | 9.22% | 5,050 | 5,050 |" "$OUT_BY"
expect_out  "requestId 重複除去: 3 行に分かれた応答の usage は 1 回（Bash は 2 等分の 4,105）" "| tool | Bash | 1 | 4,105 |" "$OUT_BY"
expect_out  "mcp__<server>__ はサーバ名で数える" "| mcp | fakesrv | 1 | 4,105 |" "$OUT_BY"
expect_out  "agent: 生成した応答の分＋subagents/agent-*.jsonl の全消費（meta の toolUseId で対応）" "| agent | general-purpose | 1 | 15,110 |" "$OUT_BY"
expect_out  "agent: subagent_type が無ければ description" "| agent | 旧形式の委譲 | 1 | 1,050 |" "$OUT_BY"
expect_out  "サブエージェント内の tool_use も tool の表に出る" "| tool | Grep | 1 | 2,150 |" "$OUT_BY"
expect_out  "tool_use の無い応答は帰属なしとして合計だけ" "帰属なし（tool_use の無い応答）: 2 応答・14,558 tok" "$OUT_BY"
OUT=$(trep --by mcp "$FX")
expect_noout "--by mcp だけなら tool の行は出さない" "| tool |" "$OUT"
OUT=$(trep --by skills "$FX"); RC=$?
expect_exit "--by に使えない区分は exit 2" 2 "$RC"

echo "[ケース8: --skills-dir（一度も呼ばれない・呼ばれすぎ）]"
SK="$TMP/skills"; mkdir -p "$SK/demo-skill" "$SK/unused-skill"; touch "$SK/demo-skill/SKILL.md" "$SK/unused-skill/SKILL.md"
OUT=$(trep --skills-dir "$SK" "$FX"); RC=$?
expect_exit "--skills-dir は exit 0" 0 "$RC"
expect_out  "一度も呼ばれないスキルを出す" "一度も呼ばれないスキル（1 件）: unused-skill" "$OUT"
expect_out  "既定（10 回超）では呼ばれすぎ なし" "10 回を超えて呼ばれたスキル: なし" "$OUT"
OUT=$(trep --skills-dir "$SK" --over 2 "$FX")
expect_out  "--over 2 なら demo-skill（3 回）を出す" "2 回を超えて呼ばれたスキル: demo-skill（transcript-sample.jsonl: 3 回）" "$OUT"

echo "[ケース9: 壊れた transcript（usage 欠落・不明 tool・非 JSON 行）で落ちない]"
BR="$TMP/broken.jsonl"
python3 - "$FX" "$BR" <<'PY'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
out = ["{ これは JSON ではない"]
for e in rows:
    m = e.get("message") if isinstance(e.get("message"), dict) else None
    if e.get("type") == "assistant" and m:
        if e.get("requestId") == "req_sample_A":
            m.pop("usage", None)                           # usage 欠落
        if e.get("requestId") == "req_sample_D":
            m["usage"]["output_tokens"] = "abc"            # 数でない値
            for b in m["content"]:
                b.pop("name", None)                        # 名前の無い tool_use
        if e.get("requestId") == "req_sample_F":
            m["content"] = "文字列の content"               # 形の違う content
    out.append(json.dumps(e, ensure_ascii=False))
out.append(json.dumps({"type": "assistant", "message": None}))
out.append(json.dumps(["配列の行"]))
open(sys.argv[2], "w", encoding="utf-8").write("\n".join(out) + "\n")
PY
OUT=$(trep --by skill,agent,mcp,tool "$BR"); RC=$?
expect_exit "壊れた行があっても exit 0" 0 "$RC"
expect_out  "名前の無い tool_use は (不明) として数える" "| tool | (不明) | 2 |" "$OUT"
expect_out  "usage の無い応答の Skill も回数には数える" "| skill | demo-skill | 2 |" "$OUT"


echo "[ケース10: --skills-dir の一覧に無い名前は command に分ける]"
SK2="$TMP/skills2"; mkdir -p "$SK2/unused-skill"; touch "$SK2/unused-skill/SKILL.md"
OUT=$(trep --by skill --skills-dir "$SK2" --over 2 "$FX")
expect_out  "一覧に無い demo-skill は区分 command" "| command | demo-skill | 3 |" "$OUT"
expect_noout "skill の行には出さない" "| skill | demo-skill |" "$OUT"
expect_out  "呼ばれすぎは一覧にあるスキルだけ（demo-skill 3 回でも出さない）" "2 回を超えて呼ばれたスキル: なし" "$OUT"
OUT=$(trep --by skill "$FX")
expect_noout "--skills-dir が無ければ command に分けない（従来どおり skill）" "| command |" "$OUT"

# --- [検証: B-22] 検証担当が足した節（実装担当とは別。赤は赤のまま残す） ------------
echo "[検証: B-22]"
VF="$TMP/verify.jsonl"
python3 - "$VF" <<'PY'
import json, sys
L = []
def a(rid, content, usage=None):
    m = {"id": "msg_" + rid, "type": "message", "role": "assistant", "model": "claude-sample", "content": content}
    if usage is not None:
        m["usage"] = usage
    L.append({"type": "assistant", "requestId": rid, "message": m, "uuid": f"u-{rid}-{len(L)}"})
for _ in range(11):                                   # 組み込みコマンド（スキルではない）を 11 回
    L.append({"type": "user", "message": {"role": "user", "content": "<command-name>/clear</command-name>\n<command-message>clear</command-message>\n<command-args></command-args>"}})
U1 = {"input_tokens": 1, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 999}
for c in ([{"type": "thinking", "thinking": "x"}], [{"type": "text", "text": "x"}], [{"type": "tool_use", "id": "tu_x", "name": "Read", "input": {}}]):
    a("req_X", c, U1)                                  # 同じ requestId が 3 行
U2 = {"input_tokens": 1000, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 0}
for i, n in enumerate(("Grep", "Glob", "Bash")):
    a("req_Y", [{"type": "tool_use", "id": f"tu_y{i}", "name": n, "input": {}}], U2)   # 1 応答に tool_use 3 個
a("req_Z", [{"type": "tool_use", "id": "tu_z", "name": "Skill"}])                      # input 無し・usage 無し
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(json.dumps(e, ensure_ascii=False) for e in L) + "\n")
PY
OUT=$(trep --by skill,agent,mcp,tool "$VF"); RC=$?
expect_exit "[検証] input・usage の無い Skill があっても exit 0" 0 "$RC"
expect_out  "[検証] 既存の合計は requestId 3 行を 1 回（1,000）＋按分前の 1,000" "| 計 | 2,000 |" "$OUT"
expect_out  "[検証] 同じ requestId が 3 行でも Read は 1 回・1,000" "| tool | Read | 1 | 1,000 |" "$OUT"
SUM=$(printf '%s\n' "$OUT" | awk -F'|' '$2 ~ /^ (skill|agent|mcp|tool) $/ {g=$5; gsub(/[ ,]/, "", g); s+=g} END{print s+0}')
[ "$SUM" -eq 2000 ] && ok "[検証] 按分後のトークン列の合計が 計（2,000）と一致（丸めで合計が変わらない）" || ng "[検証] 按分後のトークン列の合計が 計 と一致" "表の合計 $SUM / 計 2000"
SK="$TMP/vskills"; mkdir -p "$SK/demo-skill"; touch "$SK/demo-skill/SKILL.md"
OUT=$(trep --skills-dir "$SK" "$VF")
expect_out  "[検証] --skills-dir に無い組み込みコマンド（/clear 11 回）を「呼ばれすぎのスキル」に出さない" "10 回を超えて呼ばれたスキル: なし" "$OUT"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }

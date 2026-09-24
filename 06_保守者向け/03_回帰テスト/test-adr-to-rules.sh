#!/bin/bash
# test-adr-to-rules.sh — 02_共通/ツール/adr-to-rules.py の回帰テスト（B-23 A15）
# 採用済み ADR と適用パスのある lessons だけが paths 付き rules（decisions-<slug>.md）になること、
# 却下・検討中は出ない・撤回で消える・paths が入る・slug が本文の編集で変わらないことを確かめる。
# ADR は実物のひな形（02_共通/ひな形/ADR-template.md）を埋めて作る（ひな形の欄とツールの読み方がずれたら赤になる）。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="$KIT_DIR/02_共通/ツール/adr-to-rules.py"
TPL="$KIT_DIR/02_共通/ひな形/ADR-template.md"
LTPL="$KIT_DIR/02_共通/ひな形/lessons.md"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit()  { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_file()  { [ -e "$2" ] && ok "$1" || ng "$1" "無い: $2"; }
expect_nofile(){ [ ! -e "$2" ] && ok "$1" || ng "$1" "在ってはいけない: $2"; }
expect_grep()  { grep -qF -- "$2" "$3" 2>/dev/null && ok "$1" || ng "$1" "'$2' が $3 に無い"; }
expect_nogrep(){ ! grep -qF -- "$2" "$3" 2>/dev/null && ok "$1" || ng "$1" "'$2' が $3 に在ってはいけない"; }
expect_out()   { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い"; }
expect_count() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 $2 / 実際 $3"; }

P="$TMP/proj"; R="$P/.claude/rules"; mkdir -p "$P/docs/adr" "$R"
# ひな形から ADR を作る: 番号, 題, 状態, 適用パス（; 区切り）, [置換先]
mk_adr() { python3 - "$TPL" "$P/docs/adr/ADR-$1.md" "$@" <<'PY'
import re, sys
tpl, out, no, title, status, paths = sys.argv[1:7]
sup = sys.argv[7] if len(sys.argv) > 7 else "なし"
t = open(tpl, encoding="utf-8").read()
t = t.replace("ADR-XXX: [決定のタイトル]", f"ADR-{no}: {title}")
t = re.sub(r"^\*\*状態\*\*: .*$", f"**状態**: {status}  ", t, flags=re.M)
t = re.sub(r"^\*\*置換先\*\*: .*$", f"**置換先**: {sup}  ", t, flags=re.M)
t = re.sub(r"^\*\*強制の区分\*\*: .*$", "**強制の区分**: テスト  ", t, flags=re.M)
items = "".join(f"- `{p}`\n" for p in paths.split(";") if p)
t = re.sub(r"^(\*\*適用パス\*\*.*:\n)", lambda m: m.group(1) + items, t, count=1, flags=re.M)
t = t.replace("**○○を採用する。**\n\n理由: ...", f"**{title}を採用する。**\n\n理由: 1 行目\n- 2 行目\n- 4 行目は切る")
t = t.replace("| B: △△ | |", "| B: 手書きの SQL | ISO 25010 保守性 |")
t = t.replace("| 例: 月次の該当エラーが 3 件を超える | 案 B に切り替える |", "| 月次の N+1 が 3 件を超える | 案 B に切り替える |")
open(out, "w", encoding="utf-8").write(t)
PY
}
run() { (cd "$P" && python3 "$TOOL" docs/adr docs/lessons.md --out .claude/rules 2>&1); }

echo "=== adr-to-rules.py 回帰テスト ==="
echo "[採用だけ書き出す]"
mk_adr 001 "ORM" "採用" "src/db/**/*.py;tests/db/**"
mk_adr 002 "GraphQL" "却下" "src/api/**"
mk_adr 003 "キャッシュ" "検討中" "src/cache/**"
mk_adr 004 "ログ形式" "採用" ""
cp "$TPL" "$P/docs/adr/ADR-template.md"          # 未記入のひな形（状態が選択肢のまま）
{ cat "$LTPL"; printf '\n## 2026-09-01 api retry\n\n**適用パス**:\n- `src/api/client.py`\n\n**Keep**\n- 退避は mv\n\n**Problem**\n- 再試行で二重送信した\n\n**Try**\n- [ ] 冪等キーを付ける\n'
  printf '\n## 2026-09-02 横断\n\n**Keep**\n- 見積を先に出す\n'; } > "$P/docs/lessons.md"
echo "mine" > "$R/decisions-manual.md"            # 人が書いた decisions-*.md（印が無い）
OUT=$(run); RC=$?
expect_exit "exit 0" 0 "$RC"
expect_file "採用 + 適用パス → decisions-adr-001.md" "$R/decisions-adr-001.md"
expect_nofile "却下は書き出さない" "$R/decisions-adr-002.md"
expect_nofile "検討中は書き出さない" "$R/decisions-adr-003.md"
expect_nofile "採用でも適用パスが無ければ書き出さない（常時読込にしない）" "$R/decisions-adr-004.md"
expect_out "適用パスの無い採用 ADR を警告する" "ADR-004.md: 採用だが適用パスが無い" "$OUT"
expect_count "未記入のひな形は書き出さない（decisions-* は ADR 1 + lessons 1 + 手書き 1）" 3 "$(ls "$R"/decisions-*.md | wc -l)"
F="$R/decisions-adr-001.md"
if python3 -c 'import sys
t = open(sys.argv[1], encoding="utf-8").read()
sys.exit(0 if t.startswith("---\npaths:\n  - \"src/db/**/*.py\"\n  - \"tests/db/**\"\n---\n") else 1)' "$F"; then
  ok "frontmatter の paths に適用パスが 1 行 1 つで入る"
else
  ng "frontmatter の paths に適用パスが 1 行 1 つで入る" "$(head -5 "$F" | tr '\n' ' ')"
fi
expect_grep "題に強制の区分" "決定 ADR-001: ORM（強制の区分: テスト）" "$F"
expect_grep "決定の要旨" "ORMを採用する。" "$F"
expect_nogrep "要旨は各 3 行まで（4 行目は切る）" "4 行目は切る" "$F"
expect_grep "捨てた案は表を 1 行 1 案に畳む" "- B: 手書きの SQL：ISO 25010 保守性" "$F"
expect_grep "撤回条件" "- 月次の N+1 が 3 件を超える：案 B に切り替える" "$F"
expect_nogrep "表の見出し行と「例:」の行は捨てる" "例:" "$F"
expect_grep "生成の印と元の ADR" "adr-to-rules.py が生成（元: docs/adr/ADR-001.md）" "$F"
L="$R/decisions-lesson-2026-09-01-api-retry.md"
expect_file "適用パスのある lessons → decisions-lesson-<日付>-<見出し>.md" "$L"
expect_grep "lessons の paths" '  - "src/api/client.py"' "$L"
expect_grep "lessons の Problem" "再試行で二重送信した" "$L"
expect_nogrep "lessons の本文に glob の行を混ぜない" "- \`src/api/client.py\`" "$L"
expect_count "適用パスの無い lessons・ひな形の記入例（コメント内）は書き出さない" 1 "$(ls "$R"/decisions-lesson-*.md | wc -l)"

echo "[slug が安定・上書き]"
SUM1=$(cd "$R" && cat decisions-*.md | cksum)
OUT=$(run)
expect_out "2 回目も同じ件数を書き出す" "書き出し 2 件" "$OUT"
expect_count "2 回目で内容が変わらない（冪等）" 0 "$([ "$SUM1" = "$(cd "$R" && cat decisions-*.md | cksum)" ]; echo $?)"
sed 's/## 背景（なぜこの決定が必要だったか）/## 背景（なぜこの決定が必要だったか）\nN+1 が多発した。/; s/理由: 1 行目/理由: 書き直した 1 行目/' "$P/docs/adr/ADR-001.md" > "$TMP/a" && mv "$TMP/a" "$P/docs/adr/ADR-001.md"
OUT=$(run)
expect_grep "本文を直すと同名ファイルを上書きする" "書き直した 1 行目" "$R/decisions-adr-001.md"
expect_count "本文を直しても slug（ファイル名）は変わらない" 3 "$(ls "$R"/decisions-*.md | wc -l)"

echo "[撤回で消える・置換・旧形式]"
sed 's/^\*\*状態\*\*: 採用/**状態**: 撤回/' "$P/docs/adr/ADR-001.md" > "$TMP/a" && mv "$TMP/a" "$P/docs/adr/ADR-001.md"
OUT=$(run)
expect_nofile "撤回にすると出力を削除する" "$R/decisions-adr-001.md"
expect_out "削除した件数を出す" "削除 1 件: decisions-adr-001.md" "$OUT"
expect_file "印の無い decisions-*.md（人が書いたもの）は消さない" "$R/decisions-manual.md"
expect_file "lessons の出力は残る" "$L"
mk_adr 005 "新 ORM" "採用" "src/db/**" "ADR-006"
mk_adr 006 "旧 ORM" "採用" "src/db/**"
OUT=$(run)
expect_file "置き換えた側（ADR-005）は書き出す" "$R/decisions-adr-005.md"
expect_grep "置き換えた決定を本文に書く" "置き換えた決定: ADR-006" "$R/decisions-adr-005.md"
expect_nofile "置き換えられた側（ADR-006）は採用のままでも書き出さない" "$R/decisions-adr-006.md"
expect_out "置き換えられた側を警告する" "ADR-006.md: ADR-005 に置き換えられている" "$OUT"
sed 's/^\*\*状態\*\*: .*/**ステータス**: 採用  /' "$P/docs/adr/ADR-003.md" > "$TMP/a" && mv "$TMP/a" "$P/docs/adr/ADR-003.md"
run >/dev/null
expect_file "旧ひな形の「ステータス: 採用」も読む" "$R/decisions-adr-003.md"

echo "[状態の表記ゆれ・適用パスの書き方]"
mk_adr 020 "条件付き" "採用（条件付き）" "src/c/**"
mk_adr 021 "済み" "採用済み" "src/d/**"
mk_adr 022 "英語" "Accepted" "src/e/**"
mk_adr 023 "誤記" "さいよう" "src/f/**"
mk_adr 024 "一行" "採用" ""
sed 's/^\(\*\*適用パス\*\*.*:\)$/\1 `src\/g\/**`; src\/h\/**, src\/i\/*.{js,jsx} (注記)/' "$P/docs/adr/ADR-024.md" > "$TMP/a" && mv "$TMP/a" "$P/docs/adr/ADR-024.md"
OUT=$(run); RC=$?
expect_exit "表記ゆれだけなら exit 0" 0 "$RC"
for n in 020 021 022; do expect_file "採用として扱う表記: ADR-$n" "$R/decisions-adr-$n.md"; done
expect_nofile "読めない状態は書き出さない" "$R/decisions-adr-023.md"
expect_out "読めない状態は警告する（黙って飛ばさない）" "ADR-023.md: 状態「さいよう」を読めない" "$OUT"
F="$R/decisions-adr-024.md"
if python3 -c 'import sys
t = open(sys.argv[1], encoding="utf-8").read()
sys.exit(0 if t.startswith("---\npaths:\n  - \"src/g/**\"\n  - \"src/h/**\"\n  - \"src/i/*.{js,jsx}\"\n---\n") else 1)' "$F" 2>/dev/null; then
  ok "同じ行の ; とカンマ（{…} の外だけ）で分け、注記を捨てる"
else
  ng "同じ行の ; とカンマ（{…} の外だけ）で分け、注記を捨てる" "$(head -6 "$F" 2>/dev/null | tr '\n' ' ')"
fi

echo "[入力の誤りは何も消さない]"
N_BEFORE=$(ls "$R"/decisions-*.md | wc -l)
OUT=$(cd "$P" && python3 "$TOOL" docs/adrr docs/lessons.md --out .claude/rules 2>&1); RC=$?
expect_exit "ADR のディレクトリが無ければ exit 2" 2 "$RC"
OUT=$(cd "$P" && python3 "$TOOL" docs/adr docs/lesson.md --out .claude/rules 2>&1); RC=$?
expect_exit "lessons.md が無ければ exit 2" 2 "$RC"
expect_count "入力の誤りでは既存の出力を消さない" "$N_BEFORE" "$(ls "$R"/decisions-*.md | wc -l)"
OUT=$(cd "$P" && python3 "$TOOL" docs/adr docs/lessons.md 2>&1); RC=$?
expect_exit "--out が無ければ exit 2（argparse）" 2 "$RC"

echo "[検証: B-23 adr-to-rules（検証担当が追加。赤は実装担当が直す）]"
P="$TMP/proj-v"; R="$P/.claude/rules"; mkdir -p "$P/docs/adr" "$R"; : > "$P/docs/lessons.md"
echo "hand" > "$R/functional-integrity.md"; echo "hand" > "$R/absolute.md"
mk_adr 010 "Alpha" "採用" "src/a/**"; mv "$P/docs/adr/ADR-010.md" "$P/docs/adr/ADR-010-alpha.md"
mk_adr 010 "Beta" "採用" "src/b/**"                      # 同じ番号の採用 ADR が 2 つ（番号の打ち間違い）
mk_adr 011 "TS" "採用" "src/**/*.{ts,tsx}"                # Claude Code の rules の例にある波括弧の glob
mk_adr 012 "API" "採用" "src/api/**"
sed 's/^- `src\/api\/\*\*`$/- `src\/api\/**`（API 層）/' "$P/docs/adr/ADR-012.md" > "$TMP/a" && mv "$TMP/a" "$P/docs/adr/ADR-012.md"
OUT=$(run); RC=$?
expect_exit "検証 同じ番号の採用 ADR が 2 つなら exit 1（指揮官の決定 7。書き出しは済ませる）" 1 "$RC"
expect_file "検証 同じ番号はファイル名順で最初（ADR-010-alpha.md）を採る" "$R/decisions-adr-010.md"
expect_grep "検証 同じ番号はファイル名順で最初（Alpha）" "ADR-010: Alpha" "$R/decisions-adr-010.md"
if { grep -qF 'src/a/**' "$R"/decisions-*.md && grep -qF 'src/b/**' "$R"/decisions-*.md; } || { printf '%s' "$OUT" | grep -qF 'ADR-010-alpha.md' && printf '%s' "$OUT" | grep -qF 'ADR-010.md'; }; then
  ok "検証 同じ番号の採用 ADR 2 つを黙って片方捨てない（両方書くか、両方の名前で警告）"
else
  ng "検証 同じ番号の採用 ADR 2 つを黙って片方捨てない（両方書くか、両方の名前で警告）" "decisions-adr-010.md に $(grep -h '^# ' "$R"/decisions-adr-010.md) だけ・警告なし"
fi
expect_grep "検証 波括弧の glob を割らない" '  - "src/**/*.{ts,tsx}"' "$R/decisions-adr-011.md"
expect_grep "検証 glob の後ろの注記（全角括弧）を paths に入れない" '  - "src/api/**"' "$R/decisions-adr-012.md"
expect_nogrep "検証 注記の断片が paths の 1 行にならない" '層）' "$R/decisions-adr-012.md"
if python3 - "$R" <<'PY'
import glob, json, re, sys
bad = []
for f in glob.glob(sys.argv[1] + "/decisions-*.md"):
    t = open(f, encoding="utf-8").read()
    fm = t.split("---\n")[1]
    try:
        import yaml
        d = yaml.safe_load(fm)
        ok = isinstance(d, dict) and isinstance(d.get("paths"), list) and all(isinstance(p, str) for p in d["paths"])
    except ImportError:
        ok = fm.startswith("paths:\n") and all(isinstance(json.loads(l.strip()[2:]), str) for l in fm.splitlines()[1:])
    body = t.split("---\n", 2)[2]
    ok = ok and all(len([l for l in s.splitlines()[1:] if l.strip()]) <= 3 for s in re.split(r"\n## ", body)[1:])
    if not ok:
        bad.append(f)
sys.exit(1 if bad else 0)
PY
then ok "検証 frontmatter の paths が YAML として読め、要旨は各節 3 行以内"; else ng "検証 frontmatter の paths が YAML として読め、要旨は各節 3 行以内" "壊れた出力がある"; fi
expect_file "検証 手書きの rules（functional-integrity.md）は消さない" "$R/functional-integrity.md"
expect_file "検証 手書きの rules（absolute.md）は消さない" "$R/absolute.md"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "✅ 全て正常"; exit 0
else
  echo "⚠ 失敗あり。02_共通/ツール/adr-to-rules.py と 02_共通/ひな形/ADR-template.md を確認してください"; exit 1
fi

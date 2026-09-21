#!/usr/bin/env bash
# 当たり前品質スキャン (汎用) — 対象リポジトリで実行する静的検出器。
# 目的:「症状の裏の欠陥クラス」を先に全列挙するための候補リストを出す。
# ヒットは"候補"であって結論ではない(偽陽性あり)。各ヒットは必ず実機(ブラウザ)で
# 描画を目視し、症状の裏に同種が無いか横断確認してから直すこと。
#
# 使い方: 対象プロジェクトのルートで
#   bash <path>/skills/atarimae-quality-audit/scan.sh
set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"; cd "$ROOT"

# HTMLテンプレの探索対象(Django/Jinja/一般HTML)
TPLDIRS=$(printf '%s ' templates */templates src public app 2>/dev/null)
inc='--include=*.html'
say() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
htgrep() { grep -rn $inc "$@" $TPLDIRS 2>/dev/null | grep -viE 'node_modules|/venv/|/dist/'; }

say "1) インライン塗りバグ (span を進捗バーの塗りに使い width:% → inlineは寸法無視で不可視)"
htgrep -E '<span[^>]*style="[^"]*width:\s*[{$]' || echo "  (該当なし)"
echo "  ※ ヒットしたクラスの CSS に display:block があるか確認。無ければ塗りが出ない。"

say "2) 破壊的操作なのに確認ダイアログが無いフォーム (誤クリックでデータ喪失)"
for f in $(grep -rln $inc -E 'method="post"|method=.post.' $TPLDIRS 2>/dev/null | grep -viE 'node_modules|/venv/'); do
  grep -qiE '削除|却下|除去|revoke|delete|remove|destroy' "$f" || continue
  grep -qE 'data-confirm|confirm\(' "$f" || echo "  [確認なし] $f"
done

say "3) 生の内部表現の露出 (Python None/[]/dict, 英語ステータス, 開発者コマンド)"
htgrep -E "manage\.py|os\.environ|: \[\]|'[a-z_]+':|In Progress|To Do|>None<|: None" \
  | grep -vE 'json_script|csrf' | head -20 || echo "  (該当なし)"

say "4) 軸/目盛/凡例の無いチャート (SVGは目視必須)"
grep -rln $inc '<svg' $TPLDIRS 2>/dev/null | grep -viE 'node_modules|/venv/|favicon' || echo "  (SVGなし)"

say "5) 一覧のページネーション欠如 (件数増で全件表示 → スケール破綻)"
for v in $(find . -maxdepth 3 -name views.py -not -path '*/venv/*' 2>/dev/null); do
  grep -qE 'list|index' "$v" 2>/dev/null || continue
  grep -q 'Paginator' "$v" || echo "  [Paginatorなし] $v"
done

say "6) 一覧テンプレの空状態 ({% empty %} 等) 欠如"
for f in $(grep -rln $inc -E '\{% for ' $TPLDIRS 2>/dev/null | grep -iE 'list|index' | grep -viE 'node_modules|/venv/'); do
  grep -qE '\{% empty %\}|ありません|まだ' "$f" || echo "  [空状態なし?] $f"
done

say "7) 認証情報系フォームのオートフィル対策 (autocomplete) 欠如"
for f in $(grep -rln $inc -E 'type="password"|api_token|token|password' $TPLDIRS 2>/dev/null | grep -viE 'node_modules|/venv/'); do
  grep -q 'autocomplete' "$f" || echo "  [autocomplete対策なし] $f"
done

say "8) 大きな数値の桁区切り欠如 (intcomma / toLocaleString)"
grep -rLn $inc -E 'intcomma|toLocaleString' \
  $(grep -rln $inc -E 'count|total|回数|件数' $TPLDIRS 2>/dev/null | grep -viE 'node_modules|/venv/') 2>/dev/null | head

say "9) 時刻/文脈非依存のハードコード文言 (例: 常に「おはよう」)"
htgrep -E 'おはよう|こんにちは|こんばんは|Good morning' | head || echo "  (該当なし)"

say "10) 破壊的/長時間ボタンに二重送信・処理中表示の共通制御があるか"
if grep -rqsE "addEventListener\(.submit|data-submitting|aria-busy" $(find . -maxdepth 4 -name '*.js' -not -path '*/venv/*' -not -path '*/node_modules/*' 2>/dev/null) 2>/dev/null; then
  echo "  共通の submit ハンドラあり (二重送信対策の可能性)"
else
  echo "  [共通submitハンドラ無し?] 長時間ボタンが多いなら base の JS で一括対応を検討"
fi

say "11) 健全性 (対象がDjangoなら)"
if [ -f manage.py ]; then
  ( [ -d venv ] && . venv/bin/activate 2>/dev/null; python manage.py check 2>&1 | grep -E 'System check|Error' | tail -1 )
else
  echo "  (manage.py なし。ビルド/型チェック/テストは対象に応じて実施)"
fi

printf '\n\033[1m--- 次にやること (発見者の作法) ---\033[0m\n'
cat <<'EOF'
- 各ヒットは"候補"。実機(Playwright等)で描画を目視し、症状の裏に同種が無いか横断確認。
- 系統的なもの(2,7,10)はテンプレ個別でなく共通基盤(共通JS/CSS/partial)で一括修正。
- 直したら実機スクショ + テスト。verified / 未verified を正直に区別する。
EOF

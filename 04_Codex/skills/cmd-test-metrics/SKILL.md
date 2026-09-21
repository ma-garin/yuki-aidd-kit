---
name: cmd-test-metrics
description: "/test-metrics — テスト工程の進捗と品質を数字で出す"
---
<!-- 生成物: 04_Codex/build_codex_skills.py が 03_ClaudeCode/ から生成する。直接編集しない -->
コマンド `/test-metrics` の Codex 版。引数は、呼び出し時にユーザーが続けて書いた文を `$ARGUMENTS` として読む。

# /test-metrics — テスト工程の進捗と品質を数字で出す

引数: $ARGUMENTS（レベル `UT` / `IT` / `ST` / `UAT`。空なら全レベル）

## 実行内容

1. `./scripts/test-metrics.sh [--level <引数>]` を実行する（status。常に exit 0）
   - 真実源は `docs/lifecycle/05〜08` のテスト表・欠陥表と `docs/system_test_cases.csv`。**集計値を文書に手書きしない**
2. 出力を読み解いて報告する
   - 数字: レベル別の消化率・合格率・欠陥密度・Critical/High 未解決。「算出できない」はそのまま伝える（0 と言い換えない）
   - 検知: `[unread]`（結果欄が語彙外。**分母に入っている**）／`[severe]`／`[stale]`（滞留）／`[bias]`（区分の偏り）／`[forecast]`（**推定。根拠文ごと伝える**）
   - 人が判定すること: GO/NO-GO、受容してよい欠陥か、テストを追加すべきか。**AI は判定しない**
3. 次の行動を 1〜3 行で提案する（例: unread の行を語彙に直す／DEF-001 の対応を決める／未実施 6 件の担当と日付）

## 要求されたときだけ

- `--gate`: `docs/test/TESTING_STRATEGY.md` §7 の基準で 0 進める / 1 進めない / 2 判定できない。**基準を緩めて通さない**
- `--history`: `docs/test/metrics-history.tsv` に 1 行追記（週次や工程の節目）
- `--into docs/test/iso29119-test-completion-report.md`: 完了報告書 §2 と基準評価を置き換える（判定は人が §6 に書く）

## 出力

①レベル別の数字（算出できないものは理由付き） ②検知の一覧 ③人が判定すること ④次の行動 ⑤レポートのパス（`test-metrics-report.md`）

# /lifecycle — 開発工程の実行（RFD〜保守運用）

引数: $ARGUMENTS（工程名 or 番号。例: `要件定義` / `1` / `詳細設計` / `結合テスト` / `status`）

## 実行内容

dev-lifecycle スキルに従い、指定工程の成果物を生成・更新してゲート判定まで行う。

1. **工程を特定する**（0:RFD / 1:要件定義 / 2:基本設計 / 3:詳細設計 / 4:実装 / 5:単体テスト / 6:結合テスト / 7:システムテスト / 8:受け入れテスト / 9:保守運用）
   - 引数が `status` の場合は、各工程の成果物の有無・`trace-check.sh`・`check-approval.sh`・`test-metrics.sh`（消化率・合格率・Critical/High 残）の結果だけを出して終了する
   - 引数が空なら、`docs/lifecycle/` の充足状況から次に着手すべき工程を提案して確認を取る
2. **入口基準を確認する**（`skills/dev-lifecycle/references/phase-gates.md`）
   - `./scripts/check-approval.sh --gate <工程番号>` を実行し、**exit 0 以外なら着手しない**（前工程が未承認・失効・差し戻し中）
   - 前工程の出口基準が未達なら**着手せず差し戻す**。次工程の作業で埋めない
3. **前工程の成果物だけを入力にする**
   - 例: 単体テストは `03-detailed-design.md` の `DD-xxx` から作る。実装コードを読んでから作らない（実装の写しになり欠陥を検出できない）
4. **成果物を生成・更新する**（`docs/lifecycle/` の該当ファイル。雛形は `./00_導入/init-lifecycle.sh .`）
   - ID は所有ファイル内の見出し先頭または表の第1セルに置く。他工程で再定義しない
5. **`traceability-matrix.md` を更新し `./scripts/trace-check.sh docs/lifecycle` を実行する**
6. **`/phase-review <工程番号>` で AI 3 役の指摘を出し切る**（`skills/phase-approval`）
   - 出力先は `docs/lifecycle/approvals/phase-<n>-ai.md`。**承認欄には触れない**（人間が埋める）
7. **出口基準を判定して報告する**
   - 出力: ①工程と入口基準の充足 ②成果物パス ③採番した ID 一覧 ④trace-check の結果
     ⑤`check-approval.sh --phase <n>` の結果 ⑥出口基準の未達項目
   - 未達がある場合は**完了と判定しない**。**AI が承認したことにしない**

## 工程別の接続

- 実装（4）は `/plan` → `/implement` の実装モードで行う
- テスト（5〜7）のコード生成・実行は `test-automation` スキル、観点は `references/test-levels.md`
- **全10工程の出口で人間の承認が必須**（記録: `docs/lifecycle/approvals/phase-<n>.md`）。
  承認は成果物の版に縛られ、承認後に成果物が変われば自動失効する
- 全工程完了時は `done-gate` を通してから `09-operations.md` へ引き継ぐ

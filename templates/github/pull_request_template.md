<!--
AIDD Kit の工程ライフサイクル用 PR テンプレート。
配置先: <project>/.github/pull_request_template.md
（./scripts/init-lifecycle.sh <target> --github で自動配置）
規約: skills/dev-lifecycle/SKILL.md
-->

## 概要

<!-- この PR で何が変わるかを1〜3行 -->

## 関係 ID（トレーサビリティ）

<!-- 追跡表と突き合わせるための必須欄。該当しない行は「-」 -->

| 区分 | ID |
|---|---|
| 要件 | REQ-F-xxx |
| 基本設計 | BD-xxx |
| 詳細設計 | DD-xxx |
| 実装タスク | T-xxx |
| テスト | UT-xxx / IT-xxx / ST-xxx / UAT-xxx |
| 欠陥（修正の場合） | DEF-xxx |

## 工程

- [ ] RFD / 要件定義 / 基本設計 / 詳細設計 / 実装 / 単体テスト / 結合テスト / システムテスト / 受け入れテスト / 保守運用 のいずれかを明記した

## 検証結果（evidence）

<!-- 「動作確認しました」は不可。実行したコマンドと出力、またはスクリーンショットのパスを書く -->

```text

```

## チェック

- [ ] `./scripts/trace-check.sh docs/lifecycle` が NG=0
- [ ] 対象工程の出口基準を満たす（`skills/dev-lifecycle/references/phase-gates.md`）
- [ ] テストが pass する（件数を上に記載）
- [ ] 設計から逸脱した箇所は設計書へ逆同期済み
- [ ] 秘密情報の混入なし
- [ ] Critical / High の指摘が残ゼロ（ISTQB severity）

## 影響範囲・リスク

<!-- 壊れうる箇所、ロールバック方法 -->

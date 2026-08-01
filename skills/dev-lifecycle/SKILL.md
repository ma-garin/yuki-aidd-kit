---
name: dev-lifecycle
description: RFD から保守運用までの開発工程（V字モデル）を AI エージェントに実行させるスキル。「RFD」「要件定義」「基本設計」「詳細設計」「単体テスト」「結合テスト」「システムテスト」「受け入れテスト」「UAT」「保守運用」「工程」「V字」「トレーサビリティ」「設計書を作って」「テスト仕様書」への言及があれば必ずこのスキルを使うこと。工程ごとの成果物・入口出口基準・ID体系・レビュー観点を統一し、要件からテストまでの追跡可能性を機械検証する。
---

# 開発工程ライフサイクル（RFD → 保守運用）

工程を分けずに実装へ飛ぶと、AI は「動くが要求を満たさないもの」を高速に量産する。本スキルは **成果物・ID・ゲート** の3点を固定して、各工程の完了を機械的に判定できる状態にする。

## 適用判断（最初に必ず決める）

| 進め方 | 適用条件 | 使う資産 |
|---|---|---|
| **軽量 SDD**（spec/plan/tasks の3ファイル） | 個人 PWA・単一 HTML ツール・PoC。工程分割のコストが回収できない規模 | `sdd-ecc-workflow` |
| **工程ライフサイクル**（本スキル） | 他者に納品/引き継ぐ・要件の合意が必要・テスト分割が必要・保守運用が続く | 本スキル ＋ `sdd-ecc-workflow` |

両者は排他ではなく**入れ子**。工程ライフサイクルの成果物と SDD ファイルの対応は下表で固定し、同じ内容を二重に書かない。

| 工程成果物 | SDD ファイル |
|---|---|
| `01-requirements.md`（要件定義） | `spec.md` の上位。spec.md は要件 ID を参照するだけにする |
| `02-basic-design.md`（基本設計） | `plan.md` に相当。plan.md 単体で足りる規模なら基本設計を省略してよい |
| `04-implementation.md`（実装記録） | `tasks.md` の T-ID をそのまま使う |

## 10工程・成果物・ID

成果物は `docs/lifecycle/` に置く（`./scripts/init-lifecycle.sh <対象>` で雛形を配置）。

| # | 工程 | 成果物 | 付番 | 主な判定 |
|---|---|---|---|---|
| 0 | RFD（提案・論点出し） | `00-rfd.md` | `RFD-001` | 課題・選択肢・決定が揃う |
| 1 | 要件定義 | `01-requirements.md` | `REQ-F-001` / `REQ-N-001` | 全要件に**観測可能な受入基準**がある |
| 2 | 基本設計 | `02-basic-design.md` | `BD-001` | 全要件が設計要素に割り当て済み |
| 3 | 詳細設計 | `03-detailed-design.md` | `DD-001` | I/F・データ・異常系が実装可能な粒度 |
| 4 | 実装 | `04-implementation.md` | `T-001` | 1タスク=1論理変更でコミット済み |
| 5 | 単体テスト | `05-unit-test.md` | `UT-001` | DD 単位で分岐・境界を網羅 |
| 6 | 結合テスト | `06-integration-test.md` | `IT-001` | BD の I/F・連携が通る |
| 7 | システムテスト | `07-system-test.md` | `ST-001` | REQ-N（非機能）を実測で満たす |
| 8 | 受け入れテスト | `08-acceptance-test.md` | `UAT-001` | 依頼者の受入基準に合格 |
| 9 | 保守運用 | `09-operations.md` | `OPS-001` | 監視・復旧手順・変更手順が動く |
| — | 追跡表 | `traceability-matrix.md` | — | REQ が設計とテストに全て紐づく |
| — | 欠陥 | 各テスト工程内 | `DEF-001` | ISTQB severity 付与済み |

**V字の対応**: REQ↔UAT / BD↔ST・IT / DD↔UT。テストを書く時は必ず「左側のどの ID を検証するのか」を先に書く。

## 工程ゲート（入口/出口基準）

各工程は前工程の出口基準を満たさない限り開始しない。詳細な判定項目は `references/phase-gates.md`。共通の出口基準は3つ。

1. 成果物に**未確定の `TBD` が残っていない**（残す場合は RFD へ差し戻すか、ADR で保留理由を明記）
2. 当該工程で採番した ID が全て追跡表に載っている（`./scripts/trace-check.sh` が NG=0）
3. `qa-review-standards` の観点で自己レビュー済み（Critical/High 残ゼロ、evidence-only）

## トレーサビリティ（このスキルの中核）

**規約**: ID は `<接頭辞>-<3桁>`。定義は所有ファイル内で「見出し行の先頭」または「表の第1セル」に置く。他工程からは参照のみ行い、再定義しない。

- 追跡の連鎖: `RFD → REQ → BD → DD → T → UT/IT/ST/UAT → OPS`
- 追跡表 `traceability-matrix.md` が唯一の突合先。工程文書側に対応表を複製しない
- 検証は手作業でなく **`./scripts/trace-check.sh [対象ディレクトリ]`** で行う（重複定義・未定義参照・要件の設計/テスト未カバー・孤立テストを検出）
- ID 体系と欠陥の扱いの詳細は `references/traceability.md`

## テストレベルの分担（重複させない）

| レベル | 検証対象 | 主な技法 | 実行 |
|---|---|---|---|
| 単体（UT） | DD-xxx の内部ロジック | 同値分割・境界値・分岐網羅 | `test-automation`（pytest/vitest） |
| 結合（IT） | BD-xxx の I/F・データ受渡し | I/F テスト・状態遷移・異常系 | `test-automation` |
| システム（ST） | REQ-N（非機能）と end-to-end | 性能・オフライン・端末幅・セキュリティ | `test-automation` ＋ `nfr-standards` |
| 受け入れ（UAT） | REQ-F の受入基準 | シナリオテスト・Whittaker ツアー | 依頼者または代理レビュー |

観点の詳細は `references/test-levels.md`。AI 出力の品質評価は本スキルではなく `agent-eval` の責務。

## 役割（工程をまたぐ）

- **Coordinator**: 工程の進行・ゲート判定のみ。設計もコードも書かない
- **Implementor**: 指定された ID の範囲のみ実装。範囲外に手を出さない
- **Verifier**: 実装と独立に、左側の ID の受入基準に対して evidence-only で判定
- **承認者（人間）**: RFD の決定・要件定義の確定・UAT 合格の3点は必ず人間が承認する。AI は承認しない

## 進め方（AI への標準手順）

1. `/rfd <テーマ>` で論点を出し、決定を人間から取る
2. `./scripts/init-lifecycle.sh <対象>` で `docs/lifecycle/` に雛形を配置
3. `/lifecycle <工程名>` で当該工程の成果物を生成・更新する（前工程の ID のみを入力とする）
4. `/trace` で追跡表を更新し `trace-check.sh` を通す
5. 出口基準を満たしたら次工程へ。満たさなければ差し戻す
6. 実装工程は `/plan` → `/implement` の実装モードに接続する
7. 全工程完了時は `done-gate` を通し、`09-operations.md` へ引き継ぐ

## 他スキルへの委譲（真実源の重複を作らない）

| 内容 | 真実源 |
|---|---|
| 非機能要件の既定値 | `skills/nfr-standards` |
| レビュー規格（ISO 25010 / ISTQB / ツアー） | `skills/qa-review-standards` |
| テストコードの生成・実行 | `skills/test-automation` |
| 完了判定のチェックリスト | `skills/done-gate` |
| SDD の 3 ファイルとガバナンス | `skills/sdd-ecc-workflow` |
| 画面の見た目・トークン | `skills/design-system` |
| プロセス改善の蓄積 | `skills/retro` |

## 出力

工程実行時は必ず「①対象工程と入口基準の充足②生成/更新した成果物のパス③採番した ID の一覧④`trace-check.sh` の結果⑤出口基準の未達項目」を提示する。未達がある場合、その工程を完了と判定しない。

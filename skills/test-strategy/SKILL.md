---
name: test-strategy
description: プロジェクトのテスト活動全体（テストレベル L1〜L4、ゲート基準、テスト種類、完了基準、ゲートの実行タイミング、ISO/IEC/IEEE 29119 文書、機能契約ハーネス、UI 検証マーカー）を設計・運用するスキル。「テスト戦略」「テスト計画」「テストレベル」「E2E をいつ回すか」「カバレッジ基準」「29119」「テスト完了報告」「インシデントレポート」「品質ゲート」「pre-commit で何を止めるか」「テストが陳腐化した」への言及があれば必ずこのスキルを使うこと。test-automation（テストコードの書き方）・done-gate（完了判定）・dev-lifecycle（工程）・e2e-cycle（E2E の回し方）と対になる「テスト活動の設計」の真実源。
---

# テスト戦略（Test Strategy）

出所: WebSpec2Doc での運用実測（2026-06〜08。テスト資産 17 件が 1 週間陳腐化した事故と、その是正を含む）。
準拠: ISO/IEC/IEEE 29119-2（プロセス）/ 29119-3（文書）/ 29119-4（技法）、ISTQB FL v4.0、IEEE 730。

## 原則

> **pytest が全 PASS であることは「完了」ではない。**それは「コードが壊れていない」という L1/L2 の確認にすぎない。
> L3（ブラウザで実フローを通す）と L4（依頼者が確認する）が終わって初めて「完了」である。

- L1+L2 が証明するもの: コードが壊れていないこと。証明しないもの: ユーザーが価値を受け取れること。
- テストは実装と独立に書く（Verifier 原則）。実装に合わせてテストを緩めない。
- 実行しなかったテストは「未実行」と明記して納品する。黙って省くのと明示して省くのは別物。

## テストレベルとゲート基準（プロジェクトの `docs/test/TESTING_STRATEGY.md` で具体値を埋める）

| レベル | 対象 | 既定ツール | ゲート | 証跡 |
|---|---|---|---|---|
| **L1 単体** | 関数・クラス・純ロジック | pytest / vitest | 1件でも FAIL → 不合格。行カバレッジ 80% 以上 | テスト結果 |
| **L2 統合** | API・サービス間結合・状態遷移 | pytest + test client / supertest | 1件でも FAIL → 不合格 | テスト結果 |
| **L3 システム（E2E）** | ブラウザ上の実フロー | Playwright（pytest-playwright / @playwright/test） | 1件でも FAIL → `.ui-verified` マーカー無し → UI 変更をコミット不可 | スクリーンショット（失敗時必須）、1280×800 + 1366×768 |
| **L4 受け入れ（UAT）** | ユーザーストーリー・非機能（使いやすさ） | 手動。ISTQB FL 相当の担当者が**初見・マニュアルなし**で実施 | 依頼者（PO）が承認。AI は承認しない | スクリーンショット + コメント |

テストレベルごとの設計観点（何を疑うか・落としてはいけないもの）は `skills/dev-lifecycle/references/test-levels.md` が真実源。ここには複製しない。

## テスト種類 × レベル

| 種類 | L1 | L2 | L3 | L4 | 実施条件 |
|---|---|---|---|---|---|
| 機能 | ✓ | ✓ | ✓ | ✓ | 全変更 |
| 回帰 | ✓ | ✓ | ✓ | — | 全変更 |
| ユーザビリティ | — | — | 一部 | ✓ | UI 変更時（`uiux_review` で全状態を目視） |
| セキュリティ | — | ✓ | — | — | 認証・入力処理の変更時（`security-review`） |
| 性能 | — | — | — | — | `nfr-standards` の基準値がある場合のみ |

## ゲートの実行タイミング（最優先で宣言する）

| タイミング | 実行するもの | 根拠 |
|---|---|---|
| 日常のコミット | 実行しない（`rules/speed-harness.md` H-7。`block-gates.py` が無断実行を止める） | 速度 |
| **マイルストーン**（機能の区切り・PR マージ前のまとまり・リリース判断） | **フルゲート**: L1/L2 + L3 + lint + security + `quality_harness.py` | 本節 |
| ユーザーが要求した時 | 要求されたもの（`GATES_REQUESTED=1`） | H-7 |

**この優先関係をプロジェクト文書に必ず書く。**書かれていなかったため、H-7 運用でゲートが 1 週間実行されず、テスト資産 17 件が陳腐化したまま放置された（2026-08-23 実損害）。迷ったらマイルストーンとして実行する。フルゲートの実測は約 5 分で、1 週間の腐敗より安い。実行したら結果を `docs/quality/evidence/` に保存する。

## 変更タイプ別の完了条件（詳細は `templates/test/DEFINITION_OF_DONE.md`）

| タイプ | 対象 | MANDATORY | PROHIBITED |
|---|---|---|---|
| A バックエンド | `*.py` / `*.ts`（UI 以外） | L1/L2 全 PASS、構文チェック、code-reviewer で HIGH 以上ゼロ | — |
| B フロントエンド ★ | `*.html` / `*.js` / `*.css` | L1/L2 + **L3 全 PASS + `.ui-verified`**、ブラウザで実操作（1920×1080 と 1366×768）、コンソールエラーなし、スクショ保存 | pytest PASS だけで完了とする / ブラウザ確認なしにコミット / 「動くはず」で完了宣言 |
| C ドキュメント | `docs/**/*.md` 等 | 内部リンク有効、関連文書の同時更新 | — |

## 完了基準（Exit Criteria）

1. L1+L2 全 PASS + カバレッジ基準達成
2. L3（UI 変更時）全 PASS + スクリーンショット目視済み
3. L4（新機能時）依頼者の承認
4. Critical / High の未解決指摘ゼロ（severity は `qa-review-standards`）
5. `quality_harness.py` PASS（critical/high 機能に failure_modes と失敗系テストがある）

## 機械的ゲート（人の注意力に頼らない）

| ゲート | 何を止めるか | 実装 |
|---|---|---|
| UI 検証マーカー | E2E 未実行・検証後に UI を変更したコミット | `scripts/ui-hash.py` + `scripts/pre-commit-ui-gate.sh`（`references/ui-verified-gate.md`） |
| 機能契約ハーネス | UI だけあって実行経路が無い機能、critical/high に失敗系テストが無い機能、契約未登録の新モジュール | `scripts/quality_harness.py` + `quality/feature_contracts.yml`（`references/feature-contracts.md`） |
| ゲートの無断実行 | 要求されていない pytest / make test | `claude-code/hooks/block-gates.py` |
| 秘密情報 | API キー等の混入 | `scripts/pre-commit` |

## ISO/IEC/IEEE 29119 文書との対応（雛形: `templates/test/`、配置: `./scripts/init-test-docs.sh <対象>`）

| 29119-3 文書 | 雛形 | 何を書くか | `dev-lifecycle` との分担 |
|---|---|---|---|
| テスト計画 | `iso29119-test-plan.md` | 対象/対象外、レベル×タイプ、リスクベース戦略、開始/終了/中断/再開基準、環境・データ、役割 | 工程文書（05〜08）はケースと結果。計画はこちらにだけ書く |
| テスト設計仕様 | `iso29119-test-design-spec.md` | 技法（同値・境界・状態遷移・探索）の適用状況、境界値の突合表、カバレッジの死角、追跡できない要求 | ケース本体は 05〜08 または `system_test_cases.csv` |
| テスト完了報告 | `iso29119-test-completion-report.md` | レベル別結果、計画との差異、25010 特性別到達、残存リスク、GO/NO-GO、申し送り | 結果の一次記録は 05〜08。報告はそれを参照する |
| インシデントレポート | `iso29119-incident-report.md` | 製品欠陥 / テスト陳腐化 / 環境依存 / flaky の分類と、テストと実装のどちらを直すかの判定 | 欠陥票は `templates/github/ISSUE_TEMPLATE/03-defect.md` |
| システムテストケース | `system_test_cases.csv` | ID・ロール・機能・**Whittaker ツアー観点**・前提・手順・期待結果・severity | `e2e-cycle` ステップ1 の出力形式 |

## リスク（全プロジェクト共通の既定）

| リスク | 対策 |
|---|---|
| E2E が flaky | 再試行 2 回まで。原因調査は必須。`time.sleep` 禁止（expect / wait_for） |
| テスト保守の遅延・陳腐化 | 機能追加と同一 PR にテストを必須化。マイルストーンでフルゲート |
| L3 省略の習慣化 | `.ui-verified` で機械的に強制。刷新期間は `.rebuild-mode` に理由を書いて明示的に免除 |
| L4 省略 | DoD にチェック欄を設け記録を残す |

## 他スキルへの委譲（真実源の重複を作らない）

| 内容 | 真実源 |
|---|---|
| テストコードの書き方・scaffold | `skills/test-automation` |
| E2E を設計→生成→実行→修整→コミットで回す | `skills/e2e-cycle` |
| レベル別の設計観点・技法 | `skills/dev-lifecycle/references/test-levels.md` |
| severity / ツアー / 25010 | `skills/qa-review-standards` |
| 完了判定チェックリスト | `skills/done-gate` |
| 実行経路の検証規範 | `rules/functional-integrity.md` |
| 非機能の基準値 | `skills/nfr-standards` |

# テスト戦略書 — <PROJECT>

**準拠規格**: ISO/IEC/IEEE 29119-2:2021, ISTQB Foundation Level Syllabus v4.0
**バージョン**: 1.0.0 / **作成日**: <YYYY-MM-DD> / **ステータス**: DRAFT
**次回見直し**: 機能追加・インシデント発生時

真実源の分担: 本書はレベル・ゲート・ツール・完了基準を定める。完了の判定は `DEFINITION_OF_DONE.md`、計画の詳細（リスク・環境・中断再開）は `iso29119-test-plan.md`、ケース本体は `system_test_cases.csv` / `docs/lifecycle/05〜08`。

## 1. 目的と適用範囲

**適用対象**: `<src/>`, `<web/>`, `<static/>`, `<templates/>`
**適用外**: `<output/>`（生成物）, `<venv/>`, `<node_modules/>`

## 2. テストレベルとゲート基準

| レベル | ツール | 対象 | 実行コマンド | ゲート | 証跡 |
|---|---|---|---|---|---|
| L1 単体 | <pytest / vitest> | 関数・クラス・純ロジック | `<make test>` | FAIL 0 件、行カバレッジ **80%** 以上 | テスト結果 |
| L2 統合 | <pytest + test client> | API・サービス間結合・状態遷移 | `<make test>` | FAIL 0 件 | テスト結果 |
| L3 システム（E2E） | <Playwright> | ブラウザ上の実フロー | `<make verify-ui>` | FAIL 0 件 → `.ui-verified` 生成。UI 変更コミットの前提 | `<tests/e2e/screenshots/>`、1280×800 + 1366×768 |
| L4 受け入れ | 手動（ISTQB FL 相当・初見・マニュアルなし） | ユーザーストーリー・非機能 | — | 依頼者が承認 | スクリーンショット + コメント |

> L1+L2 が証明するのは「コードが壊れていない」こと。「ユーザーが価値を受け取れる」ことは L3/L4 でしか証明できない。

## 3. テスト種類マトリクス

| 種類 | L1 | L2 | L3 | L4 | 実施条件 |
|---|---|---|---|---|---|
| 機能 | ✓ | ✓ | ✓ | ✓ | 全変更 |
| 回帰 | ✓ | ✓ | ✓ | — | 全変更 |
| ユーザビリティ | — | — | 一部 | ✓ | UI 変更時 |
| セキュリティ | — | ✓ | — | — | 認証・入力処理変更時 |
| 性能 | — | — | — | — | <対象外 / 基準値: nfr-standards> |

## 4. ゲートの実行タイミング（本書内で最優先）

| タイミング | 実行するもの |
|---|---|
| 日常のコミット | 実行しない（speed-harness H-7。`--no-verify` で直行） |
| **マイルストーン**（機能の区切り・PR マージ前・リリース判断） | フルゲート: `<make test>` / `<make verify-ui>` / `<make lint>` / `<make security>` / `python3 scripts/quality_harness.py`。結果を `docs/quality/evidence/` に保存 |
| ユーザーが要求した時 | 要求されたもの（`GATES_REQUESTED=1`） |

## 5. ツールチェーン

| カテゴリ | ツール | バージョン | 用途 |
|---|---|---|---|
| Unit / Integration | <pytest> | <>=8.0> | L1・L2 |
| Coverage | <pytest-cov> | | カバレッジ |
| E2E | <pytest-playwright / @playwright/test> | | L3 |
| ブラウザ | Chromium (Playwright) | | L3 |
| 機能契約 | `scripts/quality_harness.py` | | 実行経路・失敗系テストの存在検証 |
| Code Review | code-reviewer agent | | 静的品質 |
| Security | security-reviewer agent | | セキュリティ |
| Git Gates | `scripts/pre-commit` + `scripts/pre-commit-ui-gate.sh` | | 秘密情報 / UI 検証マーカー |

## 6. L4 受け入れシナリオ

| # | シナリオ | 合格基準 |
|---|---|---|
| UAT-01 | <主要フロー: 初見で最初の価値に到達する> | <エラーなし・結果が表示される> |
| UAT-02 | <1366×768 で全機能が操作できる> | 水平スクロールなし・ボタンが切れない |
| UAT-03 | <無効入力でエラーが日本語で分かりやすく出る> | 次に取るべき行動が示される |

実施記録: シナリオごとにスクリーンショットを `<tests/e2e/screenshots/uat-XX.png>` として保存する。

## 7. 完了基準（Exit Criteria）

1. L1+L2 全 PASS + カバレッジ 80%+ ／ 2. L3（UI 変更時）全 PASS + スクショ目視 ／ 3. L4（新機能時）依頼者の承認 ／ 4. Critical/High 未解決ゼロ ／ 5. `quality_harness.py` PASS

## 8. リスク管理

| リスク | 確率 | 影響 | 対策 |
|---|---|---|---|
| E2E が flaky | 中 | 中 | 再試行 2 回まで。原因調査必須。`time.sleep` 禁止 |
| テスト保守の遅延・陳腐化 | 高 | 高 | 機能追加と同一 PR にテスト必須。マイルストーンでフルゲート |
| L3 省略の習慣化 | 高 | 高 | `.ui-verified` で機械的に強制。刷新期間は `.rebuild-mode` に理由を書く |
| L4 の省略 | 中 | 高 | DoD にチェック欄を設け記録を残す |

## 9. 改訂ルール

インシデント発生後は必ず見直す。大幅なアーキテクチャ変更時はレベルの対象範囲を再定義する。

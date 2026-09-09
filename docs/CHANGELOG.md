# 変更履歴（AIDD Kit）

最新版の更新内容は `README.md` の冒頭にあります。ここには Ver.6.2 以前の履歴を保管します。

## Ver.6.2 での主な更新（2026-08-25）— テスト活動の設計と機械ゲート

WebSpec2Doc で運用してきたテスト活動（テスト戦略・DoD・ISO/IEC/IEEE 29119 文書・機能契約ハーネス・UI 検証マーカー）を汎用化して取り込みました。

- **`skills/test-strategy`**: テストレベル L1〜L4 とゲート基準、テスト種類マトリクス、**ゲートの実行タイミング**（日常は要求時のみ／マイルストーンはフルゲート — 宣言が無かったためテスト資産 17 件が 1 週間陳腐化した実損害から）、変更タイプ別 DoD、完了基準、29119 文書との対応表。references に機能契約ハーネスと `.ui-verified` ゲートの仕様
- **`skills/e2e-cycle`** + `/e2e-cycle`: E2E を設計→Playwright 生成→実行→ODC 分析・修整→コミットの 5 フェーズで、1 起動 1 フェーズで段階停止しながら回す
- **`templates/test/`**（8 本）: `TESTING_STRATEGY` / `DEFINITION_OF_DONE` / 29119 の計画・設計仕様・完了報告・インシデント / `system_test_cases.csv`（Whittaker ツアー観点・severity 列）/ `feature_contracts.yml`
- **`scripts/quality_harness.py`**: 機能契約を検証（実行経路の無い implemented、critical/high の失敗系テスト欠落、契約未登録モジュール、未実装マーカーなど 9 種。NG>0 で exit 1）。回帰テスト `scripts/test-quality-harness.sh` 11 ケース。**雛形が新規プロジェクトで PASS することもテスト**
- **`scripts/ui-hash.py` + `scripts/pre-commit-ui-gate.sh`**: E2E 合格時に git hash + UI hash + 時刻を `.ui-verified` に記録し、未検証・検証後変更の UI コミットを止める。刷新期間は `.rebuild-mode` で明示的に免除
- `scripts/init-test-docs.sh <対象> [--ci]` で一式を配置、`github-actions/test-gates.yml` で CI 実行
- `done-gate`（変更タイプ別・ゲート実行の明記）/ `test-automation` / `qa-review-standards`（29119 導線）/ `rules/functional-integrity.md`（機械検証への導線）を更新

```bash
./scripts/init-test-docs.sh <対象プロジェクト> --ci     # 文書雛形・契約・ゲートスクリプト・CI を配置
python3 scripts/quality_harness.py                       # 機能契約の検証（PASS / FAIL）
```

## Ver.6.1 での主な更新（2026-08-25）— 速度ハーネス・機能完全性・UI/UX 実機レビュー

2026-08 に実プロジェクト（WebSpec2Doc / UX_Auto_Reviewer / my_forward）で育った運用を、キットへ還流しました。

- **`rules/`（新設・常時読み込み）**: `absolute-rules.md`（A-1〜A-10）/ `speed-harness.md`（往復×12秒の見積・環境チートシート・バッチ検証・委譲の型・見積の既定値・進捗の逐次提示）/ `functional-integrity.md`（実行経路を検証するまで完了と言わない）
- **`skills/uiux_review`**: 画面を実際に開いて全状態を確認し、「作った」を「効いている」と報告しない手順（観点表 `references/viewpoints.md` 付き）
- **hooks 3本追加**: `block-gates.py`（pytest / make test / lint をユーザー要求時以外 deny）/ `progress.py` + `statusline.py`（進行中タスクの経過・見積・残りをステータスラインに表示）
- **`templates/settings.sandbox.json`**: sandbox・denyRead・network allowlist・permissions deny の雛形
- `CLAUDE.md.template` / `AGENTS.md.template` を「速度最優先」「必須プロセス」「完了条件」で改訂。「指定外ファイルは読まない」「セッション分割を提案」は廃止（AUDIT-2026-07 C-02 / X-4）
- `install.sh` / `export-project.sh` / `verify.sh` / `test-hooks.sh` が rules と `.py` hooks を扱うよう更新（hooks 回帰テスト 19 ケース）

## Ver.6.0 での主な更新（2026-08）— 開発工程ライフサイクル

RFD から保守運用までの10工程を AI に実行させる層を追加しました。既存の軽量 SDD（spec/plan/tasks）はそのまま残り、**工程分割が必要な案件だけ**がこの層を使います（使い分けの判断表は `skills/dev-lifecycle/SKILL.md` の冒頭）。

```text
RFD → 要件定義 → 基本設計 → 詳細設計 → 実装 → 単体テスト → 結合テスト → システムテスト → 受け入れテスト → 保守運用
      └── V字の対応: 要件↔受け入れ / 基本設計↔システム・結合 / 詳細設計↔単体 ──┘
```

- `skills/dev-lifecycle`: 10工程の成果物・ID 体系・工程ゲート（入口/出口基準）・役割・他スキルへの委譲を規定。詳細は references（`phase-gates.md` / `traceability.md` / `test-levels.md`）
- `templates/lifecycle/`: 工程成果物の雛形11本。`./scripts/init-lifecycle.sh <対象>` で配置（既存ファイルは上書きしない）
- **`scripts/trace-check.sh`**: 要件が設計・実装・テストへ紐づいているかを目視でなく機械検証する。重複定義／未定義参照／所有ファイル違反／追跡表未記載／カバー漏れ／孤立テストの6種別を検出し、NG>0 で exit 1（CI でそのまま落とせる）
- コマンド `/rfd`・`/lifecycle <工程名>`・`/trace` を追加
- GitHub 連携: Issue テンプレート（RFD・要件・欠陥）、関係 ID 欄付き PR テンプレート、PR で trace-check を回す `lifecycle-check.yml`
- 回帰テスト `scripts/test-trace-check.sh`（15ケース）。**配布する雛形が最初から NG=0 で始まること**もテスト対象

```bash
./scripts/init-lifecycle.sh <対象プロジェクト> --github   # 工程文書＋GitHub テンプレート一式
./scripts/trace-check.sh docs/lifecycle                   # 追跡の機械検証（NG=0 で合格）
```

## Ver.5.0 での主な更新（2026-07）

- `context-compression` スキルと `/compact-work` コマンドを追加（3層要約・grep/glob優先・決定論的作業のスクリプト化）
- 全資産を監査し修正を適用（`docs/AUDIT-2026-07.md`）。特に **hooks が入力を受け取れず無言で機能停止していた不具合を修復**し、`scripts/test-hooks.sh` で回帰テスト化
- キット自体の自己文書化: `docs/Vision.md` / `docs/PRD.md` / `docs/Roadmap.md`（前提知識ゼロのモデルが開発を継続できる作業台帳）
- `templates/design-system.md`: コード無しで見た目を再現するための視覚的指示書（Webアプリ／HTMLスライド／管理画面）
- `INDEX.md` を2層＋タグ＋参照コストで再構成。ECC 対応表の真実源を `docs/ECC-ASSET-MAP.md` に一本化
- `verify.sh` のチェックリストをリポジトリ実体からの自動導出に変更（資産追加時の更新不要）


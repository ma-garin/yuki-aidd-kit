# AIDD Kit

AI 駆動開発を、QA・E2E・仕様駆動・個人PWA・ローカル業務ツールに最適化するための個人用キットです。

**全資産の入口は `INDEX.md`**（DAILY／LIBRARY の2層＋タグ＋参照コスト）。エージェントにも人間にも、まず INDEX.md から読むことを推奨します。キット自体の目的・要求・開発継続手順は `docs/Vision.md`・`docs/PRD.md`・`docs/Roadmap.md` にあります。

## Ver.6.3 での主な更新（2026-08-25）— デザイン: トークン実物・画面の作り方・フレームワーク別適用

- **`templates/tokens.css`**: デザイントークンの実物（ライト＋ダーク、`prefers-color-scheme` と `data-theme` 両対応、reduced-motion、タップ最小 44px）。WebSpec2Doc の `on-primary` / `surface-3` / `border-strong` / severity `-border` / `motion-*`、UX_Auto_Reviewer の本文幅 68ch を統合
- **`design-system` に「画面の作り方」を追加**: 直値禁止のトークン運用（色 105 種・角丸 11 種・文字 21 段階を整理した実績から）、骨格（globalbar / sidebar / topbar / content）、**操作には必ず結果を返す**（成功＝消えるトースト／失敗＝消えない＋次の行動／処理中／0 件／危険操作の確認、`textContent` で入れる）、アイコン（同梱・CDN 禁止・慣用の形）、文言規約（ボタンは動作名、見出しに動詞を入れない、「（任意）」を付けない）
- **`design-system/references/frameworks.md`**: 単一 HTML / React+Vite（Tailwind は CSS 変数参照で登録）/ Streamlit（`config.toml` + `ui/theme.py` 集約）/ Flask・Django 別の当て方と、ECC `frontend-patterns`・`frontend-design`・`ckm:design`・`uiux_review` との分担表
- `templates/design-system.md` の再現チェックリストに直値・フィードバック・文言・アイコンの項目を追加

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

## 導入（2つの方式。併用が前提）

**① グローバル導入** — 自分のPC1台で複数プロジェクトを横断する日常運用向け。

```bash
cd <YOUR_WORKSPACE>/yuki-aidd-kit
./scripts/install.sh     # ~/.claude へ配置
./scripts/verify.sh      # 配置確認（リストは自動導出）
./scripts/test-hooks.sh  # hooks の回帰テスト（11ケース）
```

**② プロジェクト配布** — Codex・リモート/エフェメラルな Claude Code 環境・teammate の clone 先など、`~/.claude` へのグローバル導入が効かない/望ましくない環境向け。対象プロジェクト直下に `.claude/` と `AGENTS.md`・`CLAUDE.md` を書き出し、そのプロジェクトの git にコミットして持ち運ぶ。

```bash
./scripts/export-project.sh <対象プロジェクトのパス>
cd <対象プロジェクトのパス> && git add .claude AGENTS.md CLAUDE.md && git commit -m "chore: add AIDD Kit"
```

Codex ローカル利用のみで済む場合は `AGENTS.md.template` を `~/.codex/AGENTS.md` にコピーする方法もあります。claude.ai の Projects で使う場合は `claude-projects-setup.md` を参照。

## 取り扱い説明書

初心者向けの HTML 版ガイドを同梱しています。ブラウザで開くと、サイドメニュー付きでキットの使い方、ECC との関係、プロジェクト別の使い分けを確認できます。

```bash
open docs/yuki-aidd-kit-manual.html
```

## 推奨する使い方

普段の開発では、まずこの順で使います。

1. `INDEX.md` を読み、今の作業タグに合う DAILY／LIBRARY だけ開く
2. `ecc-daily-router` で対象プロジェクトに合う ECC 資産を選ぶ
3. 進め方を決める: 工程分割が要る案件（納品・引き継ぎ・要件合意・保守運用）は `dev-lifecycle`、個人PWA/単一HTML/PoC は軽量な `sdd-ecc-workflow` で spec / plan / tasks に分ける
4. 長い調査・集計は `context-compression`（または `/compact-work`）で3層要約＋スクリプト化する
5. 実装後は `test-automation` と ECC の `verification-loop` を使う
6. UI / UX / QA 観点は `qa-review-standards` と ECC の `browser-qa` / `accessibility` を併用する
7. 完了前に `done-gate` を通す
8. つまずきや改善は `retro` で `lessons.md` に蓄積する

## ECC との連携

ECC（外部キット）の資産は全部読まず、プロジェクトごとに DAILY／LIBRARY に絞って使います。**プロジェクト別の対応表の真実源は `docs/ECC-ASSET-MAP.md`**（ここには複製しません）。分類の実行は `ecc-daily-router` スキルまたは `/ecc-daily` コマンドで行います。

アプリ群の棚卸しを更新する場合:

```bash
./scripts/audit-app-workspace.sh <APP_WORKSPACE>
```

## キット構成

```text
yuki-aidd-kit/
├── README.md                 # この文書（入口の案内）
├── INDEX.md                  # 全資産の索引（DAILY/LIBRARY・タグ・参照コスト）
├── AGENTS.md.template        # 他エージェント用グローバル設定
├── CLAUDE.md.template        # Claude Code 用グローバル設定
├── claude-projects-setup.md  # claude.ai Projects のセットアップ
├── docs/
│   ├── Vision.md / PRD.md / Roadmap.md   # キット自体の目的・要求・作業台帳
│   ├── ECC-ASSET-MAP.md                  # ECC 対応表（真実源）
│   ├── AUDIT-2026-07.md                  # 資産監査の記録
│   ├── OPERATING-MODE.md                 # 標準作業モード
│   ├── PROJECT-FIT-REPORT.md             # 実プロジェクト適合レポート
│   └── yuki-aidd-kit-manual.html         # HTML 取説
├── rules/                    # 常時読み込みの規律 3本（absolute-rules / speed-harness / functional-integrity）
├── skills/                   # 19スキル（各 SKILL.md、一部 references/ 付き）
│   ├── dev-lifecycle/        # 工程ライフサイクル（+ phase-gates / traceability / test-levels）
│   ├── test-strategy/        # テスト活動の設計（+ feature-contracts / ui-verified-gate）
│   ├── e2e-cycle/            # 段階停止型 E2E ワークフロー
│   └── uiux_review/          # UI/UX 実機レビュー（+ references/viewpoints.md）
├── claude-code/
│   ├── commands/             # 16スラッシュコマンド
│   └── hooks/                # 7 hooks（sh 4 + py 3）+ settings.json（statusLine 含む）
├── scripts/
│   ├── install.sh / verify.sh / test-hooks.sh   # グローバル導入
│   ├── export-project.sh                        # プロジェクト配布
│   ├── init-lifecycle.sh / trace-check.sh / test-trace-check.sh  # 工程ライフサイクル
│   ├── init-test-docs.sh / quality_harness.py / test-quality-harness.sh  # テスト活動
│   ├── ui-hash.py / pre-commit-ui-gate.sh          # UI 検証マーカー
│   ├── init-project.sh / audit-app-workspace.sh / pre-commit
├── templates/
│   ├── design-system.md      # 視覚的指示書
│   ├── tokens.css            # デザイントークンの実物（ライト＋ダーク）
│   ├── settings.sandbox.json # sandbox / denyRead / network allowlist / permissions の雛形
│   ├── lifecycle/            # 工程成果物の雛形11本（RFD〜保守運用＋追跡表）
│   ├── test/                 # テスト戦略・DoD・29119 文書・テストケース CSV・機能契約の雛形8本
│   ├── github/               # Issue（RFD/要件/欠陥）・PR テンプレート
│   └── CURRENT_STATE.md / ADR-template.md / lessons.md / implement-profile.md
└── github-actions/           # 配布用サンプル（deploy / secret-scan / lifecycle-check / test-gates）
```

## 今後の開発時の合言葉

- 「このプロジェクトに合うECCだけ選んで」 → `ecc-daily-router`
- 「要件定義から順番に、工程を分けて進めたい」 → `dev-lifecycle`（`/rfd` → `/lifecycle <工程名>`）
- 「要件がテストまで漏れなく落ちているか確認して」 → `/trace`（`scripts/trace-check.sh`）
- 「仕様から進めたい」 → `sdd-ecc-workflow`
- 「トークンを節約して進めて」 → `/compact-work`（`context-compression`）
- 「UI/UXを見て」 → `qa-review-standards` + ECC `browser-qa`
- 「E2E/動作確認」 → `test-automation` + ECC `e2e-testing`
- 「完成判定」 → `done-gate` + ECC `verification-loop`
- 「キット自体を直したい」 → `docs/Roadmap.md` の作業ルールに従う

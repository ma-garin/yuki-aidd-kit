# AIDD Kit — INDEX

AI 駆動開発を高速・高品質にするための統合キット。Claude Code / Codex / claude.ai / ECC 横断。
**このファイルが全資産の入口。まずここを読み、必要なファイルだけを開く**（参照コスト＝およその行数）。

## 2層の読み方

| 層 | 基準 | 読むタイミング |
|---|---|---|
| **DAILY** | どのプロジェクトでも進め方を制御する横断資産 | セッション開始時・作業の節目に該当スキルを読む |
| **LIBRARY** | 特定のプロジェクト種別・場面でだけ効く資産 | タグが今の作業に一致した時だけ開く |

## クイックスタート

```bash
cd <YOUR_WORKSPACE>/yuki-aidd-kit
./scripts/install.sh && ./scripts/verify.sh   # グローバル導入と確認（自分のPC・複数プロジェクト横断）
./scripts/test-hooks.sh                       # hooks の回帰テスト（11ケース）
./scripts/test-trace-check.sh                 # トレーサビリティ検査の回帰テスト（15ケース）
./scripts/export-project.sh <target>          # プロジェクト配布（Codex・エフェメラル環境・teammate向け）
./scripts/init-project.sh my-app pwa          # 新規プロジェクト（pwa | html | streamlit）
./scripts/init-lifecycle.sh <target> --github # 工程文書一式＋GitHub Issue/PR/CI テンプレートを配置
./scripts/trace-check.sh docs/lifecycle       # 要件→設計→実装→テストの追跡を機械検証（NG=0 で合格）
./scripts/audit-app-workspace.sh <APP_WORKSPACE>  # アプリ群の棚卸し
open docs/yuki-aidd-kit-manual.html           # HTML版の取り扱い説明書
```

**導入方式は2つ**（併用が前提。`docs/Vision.md` の「配置の2層」参照）:
- **グローバル導入**（`install.sh`）: 自分のPC1台で複数プロジェクトを横断する日常運用
- **プロジェクト配布**（`export-project.sh`）: 対象プロジェクト直下に `.claude/` と `AGENTS.md`/`CLAUDE.md` を書き出し、そのプロジェクトの git にコミット。Codex・リモート/エフェメラルな Claude Code 環境・teammate の clone 先でも install 不要でそのまま効く

## DAILY スキル（進め方の制御）

| スキル | 1行要約 | タグ | コスト |
|---|---|---|---|
| `dev-lifecycle` | RFD→要件定義→基本/詳細設計→実装→単体/結合/システム/受け入れテスト→保守運用。工程ゲートとトレーサビリティ | #lifecycle #process | 105行 |
| `context-compression` | 出力の3層要約・grep/glob優先・決定論的作業のスクリプト化でトークンを推論に温存 | #token #process | 56行 |
| `ecc-daily-router` | プロジェクトに合うECC資産をDAILY/LIBRARYに分類（真実源は ECC-ASSET-MAP） | #ecc #routing | 57行 |
| `sdd-ecc-workflow` | 仕様駆動開発の10ステップ。spec/plan/tasks生成と役割分離 | #sdd #process | 53行 |
| `qa-review-standards` | ISO 25010・ISTQB severity・Whittakerツアーをレビューに注入。evidence-only | #qa #review | 43行 |
| `atarimae-quality-audit` | 当たり前品質(Kano must-be)を発見者として徹底監査。症状の裏の欠陥クラスを全列挙し実機で目視 | #qa #audit | 71行 |
| `test-automation` | Playwright/pytestで「動いた」をテスト実行判定に置き換える | #qa #test | 49行 |
| `done-gate` | 完了宣言前のDefinition of Doneチェック | #qa #process | 43行 |
| `uiux_review` | 画面を実際に開いて全状態（通常/実行中/失敗/0件/狭い画面/モーダル）を確認。「作った」を「効いている」と報告しない | #ui #qa #review | 199行 |
| `retro` | AIDDの進め方の学びを lessons.md に蓄積しキットへ還流 | #process #improve | 38行 |

## LIBRARY スキル（種別・場面で選ぶ）

| スキル | 1行要約 | タグ | コスト |
|---|---|---|---|
| `design-system` | AIDDツール群のカラー・タイポ・レイアウトの具体値（CSS変数の真実源） | #ui #design | 183行 |
| `nfr-standards` | PWA/単一HTML/Streamlit別の非機能要件デフォルト値 | #nfr #spec | 89行 |
| `agent-eval` | LLM/RAG/エージェント出力の品質をデータセット＋スコアラーで回帰評価 | #ai #eval | 67行 |
| `code-doc-search` | 技術ドキュメント検索のクエリ最適化 | #search #docs | 55行 |
| `single-html-tool` | 単一HTMLツール（社内配布・PoC）の開発規約 | #html #tool | 36行 |
| `personal-pwa` | GitHub Pages PWA・localStorage・折りたたみ端末対応の開発規約 | #pwa #mobile | 30行 |
| `streamlit-rag-app` | Streamlit+RAG業務アプリ（特定プロジェクト前提）の開発規約 | #streamlit #rag | 32行 |

## rules/（常時読み込みの規律。install で `~/.claude/rules/aidd-kit/`、export で `.claude/rules/` へ）

| ルール | 1行要約 | タグ | コスト |
|---|---|---|---|
| `absolute-rules` | A-1〜A-10: 着手前の目的1行・予実の実測・弱点の添付・未検証を断定しない・放置しない | #process #must | 112行 |
| `speed-harness` | 往復×12秒の見積、環境チートシート、バッチ検証、委譲の型、見積の既定、ゲートは要求時のみ、進捗の逐次提示 | #speed #process | 115行 |
| `functional-integrity` | UI→API→backend→出力→永続化→エラー→証跡 の実行経路を確認するまで完了と言わない | #qa #done | 39行 |

## claude-code/hooks/（settings.json で配線）

| hook | 発火 | 役割 |
|---|---|---|
| `pre-write-check.sh` | PreToolUse Write/Edit | 秘密情報ファイル・単一HTMLの CSS/JS 分割を警告 |
| `post-write-html.sh` | PostToolUse Write/Edit | HTML 保存後のレポート（500行超で部分編集を推奨） |
| `block-explore.sh` | PreToolUse Read/Grep/Glob | 実装モード（`.claude/mode` あり）で探索をブロック |
| `block-gates.py` | PreToolUse Bash | pytest / make test / lint をユーザー要求時（`GATES_REQUESTED=1`）以外は deny |
| `progress.py` | 手動（bash に連結） | `start/step/done` で progress.json を管理 |
| `statusline.py` | statusLine | 進行中タスクの経過/見積/残りを表示。無ければ従来表示へ素通し |
| `session-summary.sh` | Stop | セッション終了サマリ |

回帰テスト: `./scripts/test-hooks.sh`

## スラッシュコマンド（呼んだ時だけコストが発生）

| コマンド | 1行要約 | タグ | コスト |
|---|---|---|---|
| `/rfd` | RFD（提案・論点出し）を起票し、決定を人間に求める | #lifecycle | 24行 |
| `/lifecycle` | 指定工程の成果物を生成し入口/出口基準で判定（`status` で進捗確認） | #lifecycle | 28行 |
| `/trace` | トレーサビリティの更新と `trace-check.sh` による機械検証 | #lifecycle #qa | 22行 |
| `/plan` | 方針を確定し実装モードを解除（探索を許可）。PLAN.md を生成 | #process | 18行 |
| `/implement` | 実装モード開始（plan 必須。Read/Grep/Glob を hook で物理ブロック） | #process | 19行 |
| `/compact-work` | context-compression 規約で作業（3層要約・スクリプト化） | #token | 13行 |
| `/ecc-daily` | プロジェクトに合うECC資産の分類を実行 | #ecc | 26行 |
| `/app-scan` | アプリワークスペースの軽量棚卸し | #ecc #scan | 20行 |
| `/sdd-start` | SDDのspec/plan/tasks/CLAUDE.mdを一気に生成 | #sdd | 28行 |
| `/new-pwa` | 新規個人PWAのspec〜スキャフォールド生成 | #pwa | 27行 |
| `/qa-review` | ISO/ISTQB準拠のレビュー実行 | #qa | 28行 |
| `/eval` | AIシステムのeval実行（スコアラー選定〜回帰判定） | #ai #eval | 20行 |
| `/doc-search` | 技術ドキュメント特化検索 | #search | 14行 |
| `/retro` | レトロ実行と lessons.md 追記 | #improve | 17行 |
| `/token-check` | トークン使用量の確認と最適化提案 | #token | 23行 |

## ECC 連携

ECC 資産のプロジェクト別 DAILY/LIBRARY 対応は **`docs/ECC-ASSET-MAP.md`（147行）が唯一の真実源**。ここには複製しない。

## docs/（キット自体の文書）

| ファイル | 1行要約 | コスト |
|---|---|---|
| `docs/Roadmap.md` | キット開発の作業台帳。**開発を継続するモデルはまずこれ** | 115行 |
| `docs/Vision.md` | キットの目的・到達点・Non-Goals | 47行 |
| `docs/PRD.md` | FR/NFR（Claude Code と他エージェント双方で動作、が最重要NFR） | 64行 |
| `docs/ECC-ASSET-MAP.md` | ECCプロジェクト別対応表（真実源） | 148行 |
| `docs/AUDIT-2026-07.md` | 2026-07 資産監査の記録と適用済み修正 | 114行 |
| `docs/OPERATING-MODE.md` | 日常の標準作業モード | 75行 |
| `docs/PROJECT-FIT-REPORT.md` | 実プロジェクト群への適合レポート（2026-06 時点） | 48行 |
| `docs/yuki-aidd-kit-manual.html` | 初心者向けHTML取説（読み物。デザイン適用除外ジャンル） | 1337行 |

templates/: `design-system.md`（視覚的指示書）/ `settings.sandbox.json`（sandbox・denyRead・network allowlist・permissions の雛形）/ `CURRENT_STATE.md` / `ADR-template.md` / `lessons.md` / `implement-profile.md`

## templates/lifecycle/ — 工程成果物の雛形（`dev-lifecycle` 用）

`00-rfd` / `01-requirements` / `02-basic-design` / `03-detailed-design` / `04-implementation` /
`05-unit-test` / `06-integration-test` / `07-system-test` / `08-acceptance-test` / `09-operations` / `traceability-matrix`

配置は `./scripts/init-lifecycle.sh <対象>`（既存ファイルは上書きしない）。工程の入口/出口基準は
`skills/dev-lifecycle/references/phase-gates.md`、ID 体系は `references/traceability.md`、
テストレベル別の観点は `references/test-levels.md`。

## templates/github/ — GitHub 連携（`--github` で配置）

`ISSUE_TEMPLATE/`（RFD / 要件 / 欠陥）と `pull_request_template.md`（関係 ID とゲートのチェック欄）。
CI は `github-actions/lifecycle-check.yml`（PR で `trace-check.sh` を実行し、追跡漏れを落とす）。

## 運用原則

- 工程分割が要る案件（他者へ納品/引き継ぐ・要件合意が要る・保守が続く）は `dev-lifecycle`、個人PWA/単一HTML/PoC は軽量な `sdd-ecc-workflow`。判断表は `skills/dev-lifecycle/SKILL.md` 冒頭
- 全量導入より、対象プロジェクトに合う DAILY だけを読む。LIBRARY は削除せず必要時に検索・参照
- ファイルを読む前に grep/glob で絞る（`context-compression` 参照）
- 着手前に `目的:` `見積:` `検証:` の3行を出す（`rules/speed-harness.md` H-1）。所要時間 ≒ 往復回数 × 12秒
- UI変更は `uiux_review` で全状態を実機で開いて確認する。実行経路の検証なしに「完了」と言わない（`rules/functional-integrity.md`）
- AI出力品質は `agent-eval`、コード動作は `test-automation`、完了判定は `done-gate` で分ける
- セッション終了時は `CURRENT_STATE.md` と `lessons.md` を更新する

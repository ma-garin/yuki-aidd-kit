# AIDD Kit — INDEX

AI 駆動開発を高速・高品質にするための統合キット。Claude Code / Codex / claude.ai / ECC 横断。
**全資産の地図。** エージェントは `AGENTS.md`（`CLAUDE.md` が import）の「読む範囲」表から入り、**表に無い・迷ったときだけ**ここを開く（参照コスト＝およその行数。毎セッション読むものではない）。

## 2層の読み方

| 層 | 基準 | 読むタイミング |
|---|---|---|
| **DAILY** | どのプロジェクトでも進め方を制御する横断資産 | セッション開始時・作業の節目に該当スキルを読む |
| **LIBRARY** | 特定のプロジェクト種別・場面でだけ効く資産 | タグが今の作業に一致した時だけ開く |

## クイックスタート

```bash
cd <YOUR_WORKSPACE>/yuki-aidd-kit
./scripts/install.sh && ./scripts/verify.sh   # グローバル導入と確認（自分のPC・複数プロジェクト横断）
./scripts/test-json-envelope.sh               # 検査スクリプトの --json 出力契約の回帰テスト（13ケース）
./scripts/test-skill-route-check.sh           # スキル発火の機械判定の回帰テスト（20ケース）
./scripts/test-hooks.sh                       # hooks の回帰テスト（106ケース）
./scripts/test-trace-check.sh                 # トレーサビリティ検査の回帰テスト（15ケース）
./scripts/install-guard.sh                   # 指示優先の 3 hook だけを ~/.claude に導入（既存 settings.json に merge・冪等。Claude Code 全体に効く）
./scripts/test-install.sh                     # 導入・配布・初期化の回帰テスト（116ケース）
./scripts/test-git-gates.sh                   # git ゲート（秘密情報・.ui-verified・UI hash）の回帰テスト（27ケース）
./scripts/check-docs.sh                       # 文書整合の機械検査（INDEX 参照コスト・掲載漏れ・ケース数・参照切れ。--changed で「変更を説明する文書の未更新」も。NG=0 が合格）
./scripts/check-design.sh [対象パス]           # デザイン検査（直値・未定義トークン・外部 CDN・alert()。既定 templates/ui templates/components。NG=0 が合格）
./scripts/skill-route-check.sh [--min-rank1 N] # スキル発火の機械判定（evals/routing/ の依頼文で description の発火・誤発火・衝突を検査。--explain "<依頼文>" で順位。NG=0 が合格）
./scripts/export-project.sh <target>          # プロジェクト配布（.claude/ と .codex/hooks.json。Codex・エフェメラル環境・teammate向け）
./scripts/init-project.sh my-app pwa          # 新規プロジェクト（pwa | html | streamlit）
./scripts/init-lifecycle.sh <target> --github # 工程文書一式＋GitHub Issue/PR/CI テンプレートを配置
./scripts/trace-check.sh docs/lifecycle       # 要件→設計→実装→テストの追跡を機械検証（NG=0 で合格）
./scripts/test-metrics.sh [--gate]           # テスト工程の消化率・合格率・欠陥密度・滞留・完了予測を表から集計（--gate は §7 の基準で 0/1/2）
./scripts/token-audit.sh                      # トークン節約の仕組みの点検（床の推定・hook と設定の配線・MCP 数。実測は /context /usage）
./scripts/check-approval.sh                   # 工程承認の機械検査（記録の有無・版の一致=失効・工程順序。0=合格 1=未承認 2=判定不能）
./scripts/audit-app-workspace.sh <APP_WORKSPACE>  # アプリ群の棚卸し
open docs/userguide.html                      # ユーザーガイド（概要・導入手順。初学者向け）
open docs/yuki-aidd-kit-manual.html           # HTML版の取り扱い説明書（13 章）
```

検査スクリプト（`check-docs` / `check-approval` / `check-design` / `quality_harness` / `test-metrics` / `floor-guard --check` / `skill-route-check`）は `--json` で 1 行の JSON `{ok, exit, data, meta, error{type, message, hint, retry_argv}}` を返す（エージェント向け。NG のときは `error.hint` が次の一手、`retry_argv` が直した後の再実行）。

**導入方式は2つ**（併用が前提。`docs/Vision.md` の「配置の2層」参照）:
- **グローバル導入**（`install.sh`）: 自分のPC1台で複数プロジェクトを横断する日常運用
- **プロジェクト配布**（`export-project.sh`）: 対象プロジェクト直下に `.claude/`・`.codex/hooks.json`（Codex 用 hook 5 本。Codex の `/hooks` で信頼）・`AGENTS.md`/`CLAUDE.md` を書き出し、そのプロジェクトの git にコミット。Codex・リモート/エフェメラルな Claude Code 環境・teammate の clone 先でも install 不要でそのまま効く

テスト活動の雛形（戦略・DoD・29119 文書・機能契約・UI 検証ゲート）:

```bash
./scripts/init-test-docs.sh <対象プロジェクト> --ci
```

## DAILY スキル（進め方の制御）

| スキル | 1行要約 | タグ | コスト |
|---|---|---|---|
| `dev-lifecycle` | RFD→要件定義→基本/詳細設計→実装→単体/結合/システム/受け入れテスト→保守運用。工程ゲートとトレーサビリティ | #lifecycle #process | 114行 |
| `context-compression` | 出力の3層要約・grep/glob優先・決定論的作業のスクリプト化でトークンを推論に温存 | #token #process | 59行 |
| `ecc-daily-router` | プロジェクトに合うECC資産をDAILY/LIBRARYに分類（真実源は ECC-ASSET-MAP） | #ecc #routing | 57行 |
| `sdd-ecc-workflow` | 仕様駆動開発の10ステップ。spec/plan/tasks生成と役割分離 | #sdd #process | 55行 |
| `qa-review-standards` | ISO 25010・ISTQB severity・Whittakerツアーをレビューに注入。evidence-only。references/personas.md に検証ペルソナ 16 体（作った本人に検証させない・順次）と準拠の主張範囲 | #qa #review | 54行 |
| `atarimae-quality-audit` | 当たり前品質(Kano must-be)を発見者として徹底監査。症状の裏の欠陥クラスを全列挙し実機で目視 | #qa #audit | 71行 |
| `test-automation` | Playwright/pytestで「動いた」をテスト実行判定に置き換える | #qa #test | 55行 |
| `test-strategy` | テストレベル L1〜L4・ゲート基準・実行タイミング・変更タイプ別 DoD・29119 文書・機能契約ハーネス・UI 検証マーカー | #qa #test #process | 111行 |
| `e2e-cycle` | E2E を設計→Playwright 生成→実行→ODC 分析・修整→コミットの 5 フェーズで段階停止しながら回す | #qa #e2e | 95行 |
| `phase-approval` | 工程の出口で AI 3 役を順次レビューし人間の承認に渡す。AI は承認しない。承認は成果物の版に縛る | #lifecycle #qa #process | 93行 |
| `done-gate` | 完了宣言前のDefinition of Doneチェック | #qa #process | 60行 |
| `uiux_review` | 画面を実際に開いて全状態（通常/実行中/失敗/0件/狭い画面/モーダル）を確認。「作った」を「効いている」と報告しない | #ui #qa #review | 199行 |
| `retro` | AIDDの進め方の学びを lessons.md に蓄積しキットへ還流 | #process #improve | 40行 |

## LIBRARY スキル（種別・場面で選ぶ）

| スキル | 1行要約 | タグ | コスト |
|---|---|---|---|
| `design-system` | AIDDツール群のトークン（CSS変数の真実源・ダーク対応）＋画面の作り方（骨格・操作フィードバック・アイコン・文言・直値禁止）。references/ に tokens.md（値の理由）・components.md（部品の使い分けと落とし穴）・frameworks.md（分担）。実物は templates/tokens.css・templates/ui/ | #ui #design | 117行 |
| `nfr-standards` | PWA/単一HTML/Streamlit別の非機能要件デフォルト値 | #nfr #spec | 89行 |
| `agent-eval` | LLM/RAG/エージェント出力の品質をデータセット＋スコアラーで回帰評価 | #ai #eval | 67行 |
| `code-doc-search` | 技術ドキュメント検索のクエリ最適化 | #search #docs | 55行 |
| `single-html-tool` | 単一HTMLツール（社内配布・PoC）の開発規約 | #html #tool | 36行 |
| `personal-pwa` | GitHub Pages PWA・localStorage・折りたたみ端末対応の開発規約 | #pwa #mobile | 30行 |
| `streamlit-rag-app` | Streamlit+RAG業務アプリ（特定プロジェクト前提）の開発規約 | #streamlit #rag | 32行 |

## rules/（規律。`paths` 無し＝毎セッション自動読み込み／`paths` 付き＝該当ファイルを触ったときだけ。install で `~/.claude/rules/aidd-kit/`、export で `.claude/rules/` へ。根拠と原文は `docs/rules-rationale/`）

| ルール | 1行要約 | タグ | コスト |
|---|---|---|---|
| `absolute-rules` | A-1〜A-10 を「発動 / 出力 / 要点」の表で。目的1行・予実の実測・残課題・未検証を断定しない・放置しない | #process #must | 22行 |
| `speed-harness` | H-1〜H-8: 着手前4行（目的・終了条件・見積・検証）・環境チートシート・バッチ検証（上限2周）・委譲・見積の既定・ゲートは要求時のみ・進捗の逐次提示 | #speed #process | 53行 |
| `model-routing` | Pro＋Sonnet の規律: 既定 Sonnet・Opus へ上げる3条件・effort・`/clear`・委譲は隔離目的のみ・上限時の手順・週1で `/usage` | #speed #token | 16行 |
| `functional-integrity` | UI→API→backend→出力→永続化→エラー→証跡 の実行経路を確認するまで完了と言わない。**`paths` 付き＝コード/UI を触ったときだけ読み込み** | #qa #done | 17行 |

## claude-code/hooks/（settings.json で配線）

| hook | 発火 | 役割 |
|---|---|---|
| `pre-write-check.sh` | PreToolUse Write/Edit | 秘密情報ファイル・単一HTMLの CSS/JS 分割を警告 |
| `post-write-html.sh` | PostToolUse Write/Edit | HTML 保存後のレポート（500行超で部分編集を推奨） |
| `pre-read-guard.py` | PreToolUse Read | ロックファイル・minified・node_modules・生成レポートを deny。800 行超を範囲指定なしで読むと先頭 300 行に絞る（続きは offset） |
| `block-explore.sh` | PreToolUse Read/Grep/Glob | 実装モード（`.claude/mode` あり）で探索をブロック |
| `block-phase.py` | PreToolUse Write/Edit | 前工程が未承認のまま次工程の成果物を書くのを deny（`.claude/phase-gate` あり時のみ）。承認記録への書き込みは常に許可 |
| `filter-output.py` | PreToolUse Bash | テスト・install・build・`git log`・`git diff` の出力を Claude が読む前に絞る（`updatedInput`）。全量は `FULL_OUTPUT=1` |
| `block-gates.py` | PreToolUse Bash | pytest / make test / lint をユーザー要求時（`GATES_REQUESTED=1`）以外は deny |
| `floor-guard.py` | PreToolUse Bash（Codex も） | `git commit` の前に「基準を下げる差分」（テストの skip・assert 減・テスト削除・抑止コメント・スタブ・しきい値の緩和・除外リスト追加）を deny（A-12）。厳しくする変更は通す。正当な変更は `Floor-Guard-Allow: <理由>`。CLI `--check` は exit 0/1/2 |
| `docs-gate.py` | PreToolUse Bash（キット開発用） | `git commit` の前に `check-docs.sh --only-changed` を回し、変更を説明する文書が同じ差分に無ければ deny。配布先（`scripts/check_docs.py` 無し）では何もしない |
| `instruction-guard.py` | PreToolUse（全ツール） | 保守者の発言（ターン冒頭・途中の queued_command・enqueue）に日本語で応答するまで deny。理由に指示の先頭を載せる（読み飛ばし防止）。バイパス無し |
| `reply-language.py` | Stop | 最後の応答に日本語が無い／指示に未応答のまま終わろうとしたら block で続行させる（stop_hook_active で 1 回だけ）。日本語の最終応答の**型**も見る: 冒頭の宣言文（承知しました・まず・以下に）・末尾の申し出（必要であれば・以上です）・「結論:」ラベル行があれば block（A-9） |
| `prompt-priority.py` | UserPromptSubmit | 「今すぐ・報告・説明・なぜ・止め」を含む発言に「作業より優先」を注入 |
| `context-guard.py` | UserPromptSubmit | 55 分以上空いた再開・4 MB 超の会話で `/clear` `/compact` を促す注入（止めない） |
| `pre-compact.py` | PreCompact | 圧縮時に「残す／捨てる」を注入 |
| `log-instructions.py` | InstructionsLoaded | 指示ファイルの読み込みを `.claude/instructions-loaded.log` に記録（実測用。Claude には返さない） |
| `progress.py` | 手動（bash に連結） | `start/step/done` で progress.json を管理 |
| `statusline.py` | statusLine | 進行中タスクの経過/見積/残りを表示。無ければ従来表示へ素通し |
| `session-summary.sh` | Stop | セッション終了サマリ |

回帰テスト: `./scripts/test-hooks.sh`

## スラッシュコマンド（呼んだ時だけコストが発生）

| コマンド | 1行要約 | タグ | コスト |
|---|---|---|---|
| `/rfd` | RFD（提案・論点出し）を起票し、決定を人間に求める | #lifecycle | 24行 |
| `/lifecycle` | 指定工程の成果物を生成し入口/出口基準で判定（`status` で進捗確認） | #lifecycle | 33行 |
| `/trace` | トレーサビリティの更新と `trace-check.sh` による機械検証 | #lifecycle #qa | 22行 |
| `/test-metrics` | テスト工程の進捗・品質を数字で出し、検知と「人が判定すること」を分けて報告 | #qa #test | 23行 |
| `/phase-review` | 工程の出口で AI 3 役を順次レビュー。差し戻し事項を出し切って人間の承認へ渡す | #lifecycle #qa | 26行 |
| `/plan` | 方針を確定し実装モードを解除（探索を許可）。PLAN.md を生成 | #process | 21行 |
| `/implement` | 実装モード開始（plan 必須。Read/Grep/Glob を hook で物理ブロック） | #process | 19行 |
| `/compact-work` | context-compression 規約で作業（3層要約・スクリプト化） | #token | 13行 |
| `/ecc-daily` | プロジェクトに合うECC資産の分類を実行 | #ecc | 26行 |
| `/app-scan` | アプリワークスペースの軽量棚卸し | #ecc #scan | 20行 |
| `/sdd-start` | SDDのspec/plan/tasks/CLAUDE.mdを一気に生成 | #sdd | 28行 |
| `/new-pwa` | 新規個人PWAのspec〜スキャフォールド生成 | #pwa | 27行 |
| `/qa-review` | ISO/ISTQB準拠のレビュー実行 | #qa | 30行 |
| `/e2e-cycle` | E2E の 1 フェーズだけ実行して停止（1〜5 / help） | #qa #e2e | 25行 |
| `/eval` | AIシステムのeval実行（スコアラー選定〜回帰判定） | #ai #eval | 20行 |
| `/doc-search` | 技術ドキュメント特化検索 | #search | 14行 |
| `/retro` | レトロ実行と lessons.md 追記 | #improve | 17行 |
| `/token-check` | トークン使用量の確認と最適化提案 | #token | 28行 |

## ECC 連携

ECC 資産のプロジェクト別 DAILY/LIBRARY 対応は **`docs/ECC-ASSET-MAP.md`（148行）が唯一の真実源**。ここには複製しない。

## spec/（キット現況の仕様書）— 本体を触る前にここ

全 126 ファイルを読み切った記録。**キット自体を作り込むセッションは `spec/README.md` から始める**。
設計値の再定義はせず、現況の事実・残課題・バックログだけを持つ（真実源の重複を作らない）。

| ファイル | 1行要約 |
|---|---|
| `spec/README.md` | 読む順序・位置づけ・更新規約 |
| `spec/00-overview.md` | 目的・思想・配置の2層・規模・版歴 |
| `spec/01-inventory.md` | 全 126 ファイルの目録（行数・役割） |
| `spec/02-architecture.md` | 読み込み経路・真実源マップ・発火機構・依存 |
| `spec/03-skills.md` 〜 `08-quality-gates.md` | 資産別の詳細（スキル/コマンド・hooks/スクリプト/テンプレート/rules・docs/品質ゲート） |
| `spec/09-findings.md` | 現況の残課題（severity・evidence つき） |
| `spec/10-backlog.md` | 作り込みバックログ（完了条件・検証手順つき） |

**本体を変更したら同じコミットで `spec/` を更新する。**

## docs/（キット自体の文書）

| ファイル | 1行要約 | コスト |
|---|---|---|
| `docs/Roadmap.md` | キット開発の作業台帳。**開発を継続するモデルはまずこれ** | 301行 |
| `docs/maintainer-tendencies.md` | 保守者の指摘・要望の傾向 30 項目（第 1 回 14: 言葉の規約／第 2 回 16: 実装者に課す手順の型。複数リポジトリの記録から原文つきで抽出）と反映先。同じ指摘を 2 回受けたら行を足す | 81行 |
| `docs/Vision.md` | キットの目的・到達点・Non-Goals | 47行 |
| `docs/PRD.md` | FR/NFR（Claude Code と他エージェント双方で動作、が最重要NFR） | 89行 |
| `docs/ECC-ASSET-MAP.md` | ECCプロジェクト別対応表（真実源） | 148行 |
| `docs/AUDIT-2026-07.md` | 2026-07 資産監査の記録と適用済み修正 | 114行 |
| `docs/OPERATING-MODE.md` | 日常の標準作業モード | 80行 |
| `docs/PROJECT-FIT-REPORT.md` | 実プロジェクト群への適合レポート（2026-06 時点） | 48行 |
| `docs/userguide.html` | 初学者向けユーザーガイド。たとえ話→言葉 8 つ→中身→導入 A/B（期待出力付き）→はじめての会話（対話例）→3 つの約束→ハンズオン（事例を通しで）→1 日の流れ→言い方表→品質チェック（手動）→**V字・W字との対応（SVG 図 2 枚・工程別の機械検証表・対外説明の 3 文）**→Pro/Sonnet→見た目→困ったとき→用語集（読み物。デザイン適用除外ジャンル） | 1169行 |
| `docs/yuki-aidd-kit-manual.html` | 初心者向けHTML取説（読み物。デザイン適用除外ジャンル）。冒頭から `userguide.html`・事例・V字章へ導線 | 1444行 |

`docs/rules-rationale/`（3本）: rules の根拠・失敗事例・原文と、H-6 の実測記録の追記先。毎回は読まない。
`docs/examples/library-loan/`（7本）: 事例「貸出管理を Excel から Web へ。HTML でモック」。依頼 1 行 → 単一 HTML モック（完成品 `library-loan.html`・`app.css` `app.js`・`build.py`・`spec.md`・`CURRENT_STATE.md`・README）。ハンズオン教材（`docs/userguide.html`）。

templates/: `design-system.md`（視覚的指示書。チェックリストは機械/目視の別付き）/ `tokens.css`（デザイントークンの実物。**値の唯一の真実源**。ライト＋ダーク）/ `ui/`（`components.css` 部品 / `layout.css` 骨格 / `tailwind.config.js` / `streamlit-config.toml` / `streamlit_theme.py` / `README.md` FW 別1枚表）/ `components/`（`feedback.js` `icons.js` `demo.html` `demo-shell.html`）/ `settings.sandbox.json`（sandbox・denyRead・network allowlist・permissions の雛形）/ `CURRENT_STATE.md`（決まっていること・未検証の確かめ方・最初の 5 分つき）/ `ADR-template.md`（判断基準を規格名で・捨てた案）/ `lessons.md` / `implement-profile.md`（止まる条件つき・言い訳と事実の表）/ `work-order.md`（別モデルへ渡す作業指示書: 守ること表・Step 完了条件・止まる条件・質問節）

## templates/lifecycle/ — 工程成果物の雛形（`dev-lifecycle` 用）

`00-rfd` / `01-requirements` / `02-basic-design` / `03-detailed-design` / `04-implementation` /
`05-unit-test` / `06-integration-test` / `07-system-test` / `08-acceptance-test` / `09-operations` / `traceability-matrix`

配置は `./scripts/init-lifecycle.sh <対象>`（既存ファイルは上書きしない）。工程の入口/出口基準は
`skills/dev-lifecycle/references/phase-gates.md`、ID 体系は `references/traceability.md`、
テストレベル別の観点は `references/test-levels.md`。

## templates/test/ — テスト活動の雛形（`test-strategy` 用。配置: `./scripts/init-test-docs.sh <対象> [--ci]`）

`TESTING_STRATEGY.md`（レベル・ゲート・実行タイミング）/ `DEFINITION_OF_DONE.md`（変更タイプ別）/
`iso29119-test-plan.md` / `iso29119-test-design-spec.md` / `iso29119-test-completion-report.md` / `iso29119-incident-report.md` /
`system_test_cases.csv`（ツアー観点・severity 列）/ `feature_contracts.yml`（機能契約）。
機械ゲート: `scripts/quality_harness.py`（契約検証・NG>0 で exit 1、回帰テスト `scripts/test-quality-harness.sh`）/ `scripts/ui-hash.py` + `scripts/pre-commit-ui-gate.sh`（`.ui-verified`）/ CI `github-actions/test-gates.yml`。
工程文書（`templates/lifecycle/05〜08`）はケースと結果、こちらは計画・完了報告・インシデント。重複させない。

## templates/github/ — GitHub 連携（`--github` で配置）

`ISSUE_TEMPLATE/`（RFD / 要件 / 欠陥）と `pull_request_template.md`（関係 ID とゲートのチェック欄）。
CI は `github-actions/lifecycle-check.yml`（手動起動で `trace-check.sh` を実行し、追跡漏れを落とす。自動実行はしない）。

## 運用原則

- 工程分割が要る案件（他者へ納品/引き継ぐ・要件合意が要る・保守が続く）は `dev-lifecycle`、個人PWA/単一HTML/PoC は軽量な `sdd-ecc-workflow`。判断表は `skills/dev-lifecycle/SKILL.md` 冒頭
- 全量導入より、対象プロジェクトに合う DAILY だけを読む。LIBRARY は削除せず必要時に検索・参照
- ファイルを読む前に grep/glob で絞る（`context-compression` 参照）
- 着手前に `目的:` `終了条件:` `見積:` `検証:` の4行を出す（`rules/speed-harness.md` H-1）。所要時間 ≒ 往復回数 × 12秒
- UI変更は `uiux_review` で全状態を実機で開いて確認する。実行経路の検証なしに「完了」と言わない（`rules/functional-integrity.md`）
- AI出力品質は `agent-eval`、コード動作は `test-automation`、完了判定は `done-gate` で分ける
- セッション終了時は `CURRENT_STATE.md` と `lessons.md` を更新する

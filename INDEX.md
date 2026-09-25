# AIDD Kit — INDEX

AI 駆動開発を高速・高品質にするための統合キット。Claude Code / Codex / claude.ai / ECC 横断。
**全資産の地図。** エージェントは `AGENTS.md`（`CLAUDE.md` が import）の「読む範囲」表から入り、**表に無い・迷ったときだけ**ここを開く（参照コスト＝およその行数。毎セッション読むものではない）。

## 2層の読み方

| 層 | 基準 | 読むタイミング |
|---|---|---|
| **DAILY** | どのプロジェクトでも進め方を制御する横断資産 | セッション開始時・作業の節目に該当スキルを読む |
| **LIBRARY** | 特定のプロジェクト種別・場面でだけ効く資産 | タグが今の作業に一致した時だけ開く |

## 配置（8.0.0 — 番号 01〜04 は配布、05〜06 は非配布。命名規則は `05_プロジェクト管理/構成管理/構成管理計画書.md`）

| ディレクトリ | 中身 | 導入先へ |
|---|---|---|
| `00_導入/` | キットの checkout から実行する入口（install / export / init-* / verify / check-design / token-audit） | 実行元 |
| `01_利用者向け資料/` | 利用ガイド・操作マニュアル・claude-projects-setup・OPERATING-MODE・ECC-ASSET-MAP・`サンプル/図書貸出/` | 配る（export で `<対象>/.claude/docs/`、install で `~/.claude/docs/aidd-kit/`） |
| ↳ 操作マニュアル「困ったときの一覧」 | `01_利用者向け資料/02_操作マニュアル.html#lookup` — 環境変数 AIDD_*・逃がし口・ログ・hook の理由文と対処 | 配る（同上） |
| `02_共通/` | Claude Code・Codex 共通: `rules/`・`ひな形/`・`ツール/`（導入先の `scripts/` で動く道具） | 配る（rules は `.claude/rules/`、ひな形は `.claude/templates/`、ツールは `<対象>/scripts/`） |
| `03_ClaudeCode/` | `CLAUDE.md.template`・`skills/`・`commands/`・`agents/`・`hooks/` | 配る（install で `~/.claude/` 直下、export で `<対象>/.claude/` 直下） |
| `04_Codex/` | `AGENTS.md.template`・配置の説明 | 配る（`AGENTS.md`） |
| `05_プロジェクト管理/` | 要求仕様・ロードマップ・構想・`構成管理/`（構成管理計画書・構成品目一覧） | 配らない |
| `06_保守者向け/` | `内部仕様/`・`学んだこと.md`・`設計判断の根拠/`・`回帰テスト/`（回帰テスト 20 本と check-docs）・監査レポート | 配らない |

## クイックスタート

```bash
# キットの checkout で実行（導入・配布・保守）
cd <YOUR_WORKSPACE>/yuki-aidd-kit
./00_導入/01_インストール/install.sh && ./00_導入/01_インストール/verify.sh   # グローバル導入と確認（自分のPC・複数プロジェクト横断）
./00_導入/01_インストール/install-guard.sh                    # 指示優先の 3 hook だけを ~/.claude に導入（既存 settings.json に merge・冪等。Claude Code 全体に効く）
./00_導入/02_プロジェクト配布/export-project.sh <target>          # プロジェクト配布（Codex・エフェメラル環境・teammate向け）。道具は <target>/scripts/ へ
./00_導入/02_プロジェクト配布/install-git-hooks.sh <target>      # 秘密情報と UI 検証の git hook を配線（Codex でも効く唯一の強制層。--uninstall で復元）
./00_導入/02_プロジェクト配布/init-project.sh my-app pwa          # 新規プロジェクト（pwa | html | streamlit）
./00_導入/02_プロジェクト配布/init-lifecycle.sh <target> --github # 工程文書一式＋GitHub Issue/PR/CI テンプレートを配置
./00_導入/02_プロジェクト配布/init-test-docs.sh <target> --ci     # テスト活動の雛形（戦略・DoD・29119 文書・機能契約・UI 検証ゲート）＋CI サンプル
./00_導入/03_点検/check-design.sh [対象パス]           # デザイン検査（直値・未定義トークン・外部 CDN・alert()。既定 02_共通/ひな形/ui 02_共通/ひな形/components。NG=0 が合格）
./00_導入/03_点検/token-audit.sh [--root <target>]    # トークン節約の仕組みの点検（床の推定・hook と設定の配線・MCP 数。実測は /context /usage）
./00_導入/03_点検/audit-app-workspace.sh <APP_WORKSPACE>  # アプリ群の棚卸し
open 01_利用者向け資料/01_利用ガイド.html                      # ユーザーガイド（概要・導入手順。初学者向け）
open 01_利用者向け資料/02_操作マニュアル.html                  # HTML版の取り扱い説明書（13 章）

# 保守者だけ（06_保守者向け/ は配布しない）
./06_保守者向け/03_回帰テスト/test-hooks.sh                            # hooks の回帰テスト（918ケース）
./06_保守者向け/03_回帰テスト/test-install.sh                          # 導入・配布・初期化の回帰テスト（210ケース）
./06_保守者向け/03_回帰テスト/test-agents.sh                           # エージェント定義の回帰テスト（83ケース）
./06_保守者向け/03_回帰テスト/test-trace-check.sh                      # トレーサビリティ検査の回帰テスト（94ケース）
./06_保守者向け/03_回帰テスト/test-git-gates.sh                        # git ゲート（秘密情報・.ui-verified・UI hash）の回帰テスト（27ケース）
./06_保守者向け/03_回帰テスト/test-skill-trigger-eval.sh                # skill_trigger_eval.py（スキル発火判定）の回帰テスト（29ケース。B-25）
./06_保守者向け/03_回帰テスト/check-docs.sh                            # 文書整合の機械検査（INDEX 参照コスト・掲載漏れ・ケース数・参照切れ・目録同期。NG=0 が合格）
```

**導入方式は2つ**（併用が前提。`05_プロジェクト管理/構想.md` の「配置の2層」参照）:
- **グローバル導入**（`install.sh`）: 自分のPC1台で複数プロジェクトを横断する日常運用
- **プロジェクト配布**（`export-project.sh`）: 対象プロジェクト直下に `.claude/` と `AGENTS.md`/`CLAUDE.md`、道具を `scripts/` に書き出し、そのプロジェクトの git にコミット。Codex・リモート/エフェメラルな Claude Code 環境・teammate の clone 先でも install 不要でそのまま効く

```bash
# 導入先プロジェクトで実行（export / init-* が <target>/scripts/ に置いた道具。キット内の実体は 02_共通/ツール/）
./scripts/trace-check.sh docs/lifecycle       # 要件→設計→実装→テストの追跡を機械検証（NG=0 で合格）
./scripts/check-approval.sh                   # 工程承認の機械検査（記録の有無・版の一致=失効・工程順序。0=合格 1=未承認 2=判定不能）
./scripts/test-metrics.sh [--gate]            # テスト工程の消化率・合格率・欠陥密度・滞留・完了予測を表から集計（--gate は §7 の基準で 0/1/2）
python3 scripts/quality_harness.py            # 機能契約ハーネス（契約に沿って実装・テストが揃っているか。NG>0 で exit 1）
python3 scripts/md-section.py search <語>     # Markdown 文書を見出し単位で検索（見出しパス・行範囲・推定トークン）。get <file>#<見出し> で節だけ取り出す
python3 scripts/req-lint.py <要件の文書>      # 要件の検査（EARS 型・曖昧語・数値の無い非機能目標・列挙数・ID 重複）。check_approval.py --gate 2 が隣のこれを呼ぶ
python3 scripts/pw-spec-lint.py tests        # Playwright テストの静的検査（固定待ち・.only・理由の無い skip・旧 API。NG=0 が合格）
python3 scripts/test-weaken-check.py --base main  # テストの弱体化検査（assert 削除・skip/only 追加・retries 増・toBeTruthy 置換。正当なものは weaken-ok: <理由>）
```

## エージェント（自走する実行主体。install で `~/.claude/agents/`、export で `.claude/agents/` へ）

成果物レベルの依頼（「図書管理システムを作って」）は `aidd-lead` が受ける。**どのスキルを使うか・デザインをどうするか・次にどの工程へ進むかを人間に聞かない。**
人間が入るのは **要件定義の合意** と **受け入れ判定** の 2 点だけで、工程 2〜7 はエージェントが自分でループを回して収束させる。
スキルは基準の真実源として残り、エージェントがそれを読んで実行する（基準を複製しない）。Codex にはサブエージェント構造が無いため配らず、スキルのまま縮退する。

| エージェント | 担当 | ループの終了条件（機械判定） | コスト |
|---|---|---|---|
| `aidd-lead` | 統括。種別判定・進め方の選択・工程の駆動・差し戻しの配分 | 工程 2〜7 が収束し受け入れ材料が揃う | 79行 |
| `spec-agent` | 工程 2・3（基本設計・詳細設計） | `trace-check.sh` NG=0・TBD 残ゼロ | 50行 |
| `build-agent` | 工程 4（実装＋デザイン。指示が無くても design-system を適用する） | `check-design.sh` NG=0・実行経路の疎通 | 50行 |
| `verify-agent` | 工程 5〜7（単体・結合・システムテスト。生成→実行→ODC 分析→修整→再実行） | Critical/High 残ゼロ・`test-metrics.sh --gate` exit 0 | 54行 |
| `gate-agent` | 各工程の出口（機械判定＋3 役レビュー。差し戻し事項を該当エージェントへ返す） | 差し戻し 0 件。**承認欄は空のまま人間へ** | 45行 |

AI は `approver` 欄を埋めない（`skills/phase-approval` の越えない線）。中間工程は「AI 検証完了・承認待ち」として積み、受け入れ時に人間がまとめて判定する。

## DAILY スキル（進め方の制御）

| スキル | 1行要約 | タグ | コスト |
|---|---|---|---|
| `dev-lifecycle` | RFD→要件定義→基本/詳細設計→実装→単体/結合/システム/受け入れテスト→保守運用。工程ゲートとトレーサビリティ | #lifecycle #process | 119行 |
| `context-compression` | 出力の3層要約・grep/glob優先・決定論的作業のスクリプト化でトークンを推論に温存 | #token #process | 65行 |
| `ecc-daily-router` | プロジェクトに合うECC資産をDAILY/LIBRARYに分類（真実源は ECC-ASSET-MAP） | #ecc #routing | 61行 |
| `sdd-ecc-workflow` | 仕様駆動開発の10ステップ。spec/plan/tasks生成と役割分離 | #sdd #process | 61行 |
| `qa-review-standards` | ISO 25010・ISTQB severity・Whittakerツアーをレビューに注入。evidence-only。references/personas.md に検証ペルソナ 16 体（作った本人に検証させない・順次）と準拠の主張範囲 | #qa #review | 60行 |
| `atarimae-quality-audit` | 当たり前品質(Kano must-be)を発見者として徹底監査。症状の裏の欠陥クラスを全列挙し実機で目視 | #qa #audit | 76行 |
| `test-automation` | Playwright/pytestで「動いた」をテスト実行判定に置き換える | #qa #test | 66行 |
| `test-strategy` | テストレベル L1〜L4・ゲート基準・実行タイミング・変更タイプ別 DoD・29119 文書・機能契約ハーネス・UI 検証マーカー | #qa #test #process | 122行 |
| `e2e-cycle` | E2E を設計→Playwright 生成→実行→ODC 分析・修整→コミットの 5 フェーズで段階停止しながら回す | #qa #e2e | 112行 |
| `phase-approval` | 工程の出口で AI 3 役を順次レビューし人間の承認に渡す。AI は承認しない。承認は成果物の版に縛る | #lifecycle #qa #process | 98行 |
| `done-gate` | 完了宣言前のDefinition of Doneチェック | #qa #process | 67行 |
| `uiux_review` | 画面を実際に開いて全状態（通常/実行中/失敗/0件/狭い画面/モーダル）を確認。「作った」を「効いている」と報告しない | #ui #qa #review | 200行 |
| `retro` | AIDDの進め方の学びを lessons.md に蓄積しキットへ還流 | #process #improve | 47行 |

## LIBRARY スキル（種別・場面で選ぶ）

| スキル | 1行要約 | タグ | コスト |
|---|---|---|---|
| `design-system` | AIDDツール群のトークン（CSS変数の真実源・ダーク対応）＋画面の作り方（骨格・操作フィードバック・アイコン・文言・直値禁止）。references/ に tokens.md（値の理由）・components.md（部品の使い分けと落とし穴）・frameworks.md（分担）。実物は templates/tokens.css・templates/ui/ | #ui #design | 121行 |
| `nfr-standards` | PWA/単一HTML/Streamlit別の非機能要件デフォルト値。references/ に LLM・Agentic Top10 の点検表 | #nfr #spec | 101行 |
| `security-audit`（8.5.0〜） | 走査器の結果＋スタック別 OWASP/ASVS 観点表でセキュリティ監査。明示の依頼だけ（`ecc-daily-router` からは自動で振らない） | #qa #security | 82行 |
| `agent-eval` | LLM/RAG/エージェント出力の品質をデータセット＋スコアラーで回帰評価 | #ai #eval | 72行 |
| `code-doc-search` | 技術ドキュメント検索のクエリ最適化 | #search #docs | 59行 |
| `single-html-tool` | 単一HTMLツール（社内配布・PoC）の開発規約 | #html #tool | 41行 |
| `personal-pwa` | GitHub Pages PWA・localStorage・折りたたみ端末対応の開発規約 | #pwa #mobile | 35行 |
| `streamlit-rag-app` | Streamlit+RAG業務アプリ（特定プロジェクト前提）の開発規約 | #streamlit #rag | 37行 |

## 02_共通/rules/（規律。`paths` 無し＝毎セッション自動読み込み／`paths` 付き＝該当ファイルを触ったときだけ。install で `~/.claude/rules/aidd-kit/`、export で `.claude/rules/` へ。根拠と原文は `06_保守者向け/02_設計判断の根拠/`）

| ルール | 1行要約 | タグ | コスト |
|---|---|---|---|
| `absolute-rules` | A-1〜A-10 を「発動 / 出力 / 要点」の表で。目的1行・予実の実測・残課題・未検証を断定しない・放置しない | #process #must | 23行 |
| `speed-harness` | H-0〜H-10: 出力量・着手前4行（目的・終了条件・見積・検証）・環境チートシート・バッチ検証（上限2周）・委譲・見積の既定・ゲートは要求時のみ・進捗の逐次提示・自己ウェイク禁止・往復と読み込みの規律 | #speed #process #token | 59行 |
| `model-routing` | Pro＋Sonnet の規律: 既定 Sonnet・Opus へ上げる3条件・effort・`/clear`・委譲は隔離目的のみ・上限時の手順・週1で `/usage` | #speed #token | 18行 |
| `functional-integrity` | UI→API→backend→出力→永続化→エラー→証跡 の実行経路を確認するまで完了と言わない。**`paths` 付き＝コード/UI を触ったときだけ読み込み** | #qa #done | 17行 |

## 03_ClaudeCode/hooks/（settings.json で配線）

| hook | 発火 | 役割 |
|---|---|---|
| `pre-write-check.sh` | PreToolUse Write/Edit | 秘密情報ファイル・単一HTMLの CSS/JS 分割を警告 |
| `post-write-html.sh` | PostToolUse Write/Edit | HTML 保存後のレポート（500行超で部分編集を推奨） |
| `pre-read-guard.py` | PreToolUse Read | ロックファイル・minified・node_modules・生成レポートを deny。800 行超を範囲指定なしで読むと先頭 300 行に絞る（続きは offset） |
| `block-explore.sh` | PreToolUse Read/Grep/Glob | 実装モード（`.claude/mode` あり）で探索をブロック |
| `block-phase.py` | PreToolUse Write/Edit | 前工程が未承認のまま次工程の成果物を書くのを deny（`.claude/phase-gate` あり時のみ）。承認記録への書き込みは常に許可 |
| `filter-output.py` | PreToolUse Bash | テスト・install・build・`git log`・`git diff` の出力を Claude が読む前に絞る（`updatedInput`）。全量は `FULL_OUTPUT=1` |
| `block-gates.py` | PreToolUse Bash | pytest / make test / lint をユーザー要求時（`GATES_REQUESTED=1`）以外は deny |
| `block-ci.py` | PreToolUse（全ツール） | ScheduleWakeup・CronCreate・send_later 等の自己ウェイク／定期実行と、`gh run watch` 等の CI 起動・待機を deny（Bash は `CI_REQUESTED=1` で許可） |
| `instruction-guard.py` | PreToolUse | 未応答の指示・言語・見積の欠落に加え、**自分が問うた直後の着手**を検出して待たせる（A-13・A-2・A-7） |
| `reply-language.py` | Stop | 日本語・相槌のみ・実測の無い報告・散文 12 行超・予実の乖離で block（傾向 #32〜36）。完了主張（「完了しました」等）と直近のテスト系実行結果の食い違いも block（同一ターン2回まで。B-27） |
| `prompt-priority.py` | UserPromptSubmit | 「今すぐ・報告・説明・なぜ・止め」を含む発言に「作業より優先」を注入 |
| `block-destructive.py` | PreToolUse(Bash) | 取り返しのつかない操作を deny（reset --hard / clean -fd / stash drop / checkout -- / push --force / add -A / rm -rf）。代替手段を理由に載せる。ラッパー（bash -c・sudo・env・xargs 等）を剥がしてから照合し、秘密ファイルを読むコマンドも deny（B-19） |
| `block-protected.py` | PreToolUse(Write/Edit/MultiEdit, Bash) | `.claude/settings*.json`・`.claude/hooks/`・`.git/hooks/` 等の書き換えを realpath 解決の上で deny。`AIDD_ALLOW_CONFIG_EDIT=1` で解除。判定不能は deny（B-19） |
| `secret_patterns.py` | （hook ではなく部品。他の hook から import） | 秘密ファイル名・秘密値の正規表現・コマンドのラッパー剥がしを1か所に持つ共通判定。`--check-consistency`/`--self-test`/`--pre-write` の CLI も持つ（B-19） |
| `injection-guard.py` | PostToolUse(WebFetch/WebSearch/mcp__*/プロジェクト外の Read) | 取得内容の指示形の文（英日の注入句）を正規化（NFKC・ゼロ幅・双方向制御・base64・URL エンコード）して検知し additionalContext で「データとして扱う」を通知。`.claude/injection-guard.log` に記録。**止めない**（警告専用・fail-open）（B-23） |
| `tool-timer.py` | PreToolUse / PostToolUse / UserPromptSubmit | 経過時間を積算する（実測の真実源。`report` が `実測: N分` の1行、`--full` で内訳、`reset-session` で通算も 0 に） |
| `subagent-context.py` | SubagentStart | サブエージェント起動時に保守者の時計・委譲先の規約（H-4）・approver 欄を埋めない旨を注入。検証系には「壊れている箇所を探せ」を追加 |
| `context-guard.py` | UserPromptSubmit | 55 分以上空いた再開・4 MB 超の会話で `/clear` `/compact` を促す注入（止めない） |
| `pre-compact.py` | PreCompact | 圧縮時に「残す／捨てる」を注入 |
| `session-context.py`（8.6.0〜） | SessionStart（matcher `compact\|resume`） | `CURRENT_STATE.md` の「現在の作業」「制約」「次の一手」節から合計12行以内を additionalContext で再注入。最終更新から30日超は「古い」と明記。`startup` は対象外。ファイル無し・fail-open（B-31） |
| `log-instructions.py` | InstructionsLoaded | 指示ファイルの読み込みを `.claude/instructions-loaded.log` に記録（実測用。Claude には返さない） |
| `progress.py` | 手動（bash に連結） | `start/step/done` で progress.json を管理 |
| `statusline.py` | statusLine | 1 行目を model \| dir \| context \| cache ｜ Σ累計トークン ｜ API 換算料金 $（¥）直近 の順で出す。料金は transcript の usage を model 別に単価表で自前計算（入力・5m/1h キャッシュ書込・読出・出力）。従来表示の本体は同梱の `statusline.sh`。入力に `context_window`／`rate_limits` が来たときだけ末尾に ctx%・5h%（・7d%）を足す（5h 80% 以上で ⚠。表示だけ） |
| `session-summary.sh` | Stop | セッション終了サマリ |
| `.claude/hook-decisions.log` | （hook ではなく記録。deny・override を JSONL で 1 行ずつ） | `secret_patterns.log_decision` が書く判定の記録。`token_report.py --hooks` の入力（B12） |

回帰テスト: `./06_保守者向け/03_回帰テスト/test-hooks.sh`

## スラッシュコマンド（呼んだ時だけコストが発生）

| コマンド | 1行要約 | タグ | コスト |
|---|---|---|---|
| `/rfd` | RFD（提案・論点出し）を起票し、決定を人間に求める | #lifecycle | 24行 |
| `/lifecycle` | 指定工程の成果物を生成し入口/出口基準で判定（`status` で進捗確認） | #lifecycle | 33行 |
| `/trace` | トレーサビリティの更新と `trace-check.sh` による機械検証 | #lifecycle #qa | 25行 |
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
| `/retro` | レトロ実行と lessons.md 追記 | #improve | 18行 |
| `/token-check` | トークン使用量の確認と最適化提案 | #token | 31行 |
| `/security-audit` | 導入済みの無料走査器（依存・SAST・秘密）でセキュリティ監査。未検査は合格に数えない | #qa #security | 30行 |

## ECC 連携

ECC 資産のプロジェクト別 DAILY/LIBRARY 対応は **`01_利用者向け資料/05_ECC資産対応表.md`（148行）が唯一の真実源**。ここには複製しない。

## 06_保守者向け/内部仕様/（キット現況の仕様書。配布しない）— 本体を触る前にここ

全 126 ファイルを読み切った記録。**キット自体を作り込むセッションは `06_保守者向け/01_内部仕様/README.md` から始める**。
設計値の再定義はせず、現況の事実・残課題・バックログだけを持つ（真実源の重複を作らない）。

| ファイル | 1行要約 |
|---|---|
| `06_保守者向け/01_内部仕様/README.md` | 読む順序・位置づけ・更新規約 |
| `06_保守者向け/01_内部仕様/00_概要.md` | 目的・思想・配置の2層・規模・版歴 |
| `06_保守者向け/01_内部仕様/01_構成品目目録.md` | 全 126 ファイルの目録（行数・役割） |
| `06_保守者向け/01_内部仕様/02_アーキテクチャ.md` | 読み込み経路・真実源マップ・発火機構・依存 |
| `06_保守者向け/01_内部仕様/03_スキル.md` 〜 `08_品質ゲート.md` | 資産別の詳細（スキル/コマンド・hooks/スクリプト/テンプレート/rules・docs/品質ゲート） |
| `06_保守者向け/01_内部仕様/09_指摘事項.md` | 現況の残課題（severity・evidence つき） |
| `06_保守者向け/01_内部仕様/10_バックログ.md` | 作り込みバックログ（完了条件・検証手順つき） |

**本体を変更したら同じコミットで `06_保守者向け/01_内部仕様/` を更新する。**

## docs/（利用者向け文書）

| ファイル | 1行要約 | コスト |
|---|---|---|
| `01_利用者向け資料/01_利用ガイド.html` | 初学者向けユーザーガイド。たとえ話→言葉 8 つ→中身→導入 A/B（期待出力付き）→はじめての会話（対話例）→3 つの約束→ハンズオン（事例を通しで）→1 日の流れ→言い方表→品質チェック（手動）→**V字・W字との対応（SVG 図 2 枚・工程別の機械検証表・対外説明の 3 文）**→Pro/Sonnet→見た目→困ったとき→用語集（読み物。デザイン適用除外ジャンル） | 1357行 |
| `01_利用者向け資料/02_操作マニュアル.html` | 初心者向けHTML取説（読み物。デザイン適用除外ジャンル）。冒頭から `01_利用ガイド.html`・事例・V字章へ導線 | 1923行 |
| `01_利用者向け資料/03_ClaudeProjects設定手順.md` | claude.ai Projects「AIDDラボ」のセットアップ手順（Project Instructions とナレッジ） | 58行 |
| `01_利用者向け資料/04_運用モード.md` | 日常の標準作業モード | 106行 |
| `01_利用者向け資料/05_ECC資産対応表.md` | ECCプロジェクト別対応表（真実源） | 148行 |

`01_利用者向け資料/90_サンプル/図書貸出/`（7本）: 事例「貸出管理を Excel から Web へ。HTML でモック」。依頼 1 行 → 単一 HTML モック（完成品 `library-loan.html`・`app.css` `app.js`・`build.py`・`spec.md`・`CURRENT_STATE.md`・README）。ハンズオン教材（`01_利用者向け資料/01_利用ガイド.html`）。

## internal/（保守者専用。配布しない）

| ファイル | 1行要約 | コスト |
|---|---|---|
| `05_プロジェクト管理/ロードマップ.md` | キット開発の作業台帳。**開発を継続するモデルはまずこれ** | 310行 |
| `06_保守者向け/保守者の傾向.md` | 保守者の指摘・要望の傾向 30 項目（第 1 回 14: 言葉の規約／第 2 回 16: 実装者に課す手順の型。複数リポジトリの記録から原文つきで抽出）と反映先。同じ指摘を 2 回受けたら行を足す | 106行 |
| `05_プロジェクト管理/構想.md` | キットの目的・到達点・Non-Goals | 47行 |
| `05_プロジェクト管理/要求仕様.md` | FR/NFR（Claude Code と他エージェント双方で動作、が最重要NFR） | 86行 |
| `06_保守者向け/学んだこと.md` | キット自身の AIDD プロセス改善ログ（Keep / Problem / Try。数値は実測だけ） | 215行 |
| `06_保守者向け/04_監査記録/AUDIT-2026-07.md` | 2026-07 資産監査の記録と適用済み修正 | 114行 |
| `06_保守者向け/04_監査記録/PROJECT-FIT-REPORT.md` | 実プロジェクト群への適合レポート（2026-06 時点） | 48行 |

`06_保守者向け/02_設計判断の根拠/`（3本）: rules の根拠・失敗事例・原文と、H-6 の実測記録の追記先。毎回は読まない。
`06_保守者向け/01_内部仕様/`（14本）: 現況仕様。上記「internal/spec/」節。

templates/: `design-system.md`（視覚的指示書。チェックリストは機械/目視の別付き）/ `tokens.css`（デザイントークンの実物。**値の唯一の真実源**。ライト＋ダーク）/ `ui/`（`components.css` 部品 / `layout.css` 骨格 / `tailwind.config.js` / `streamlit-config.toml` / `streamlit_theme.py` / `README.md` FW 別1枚表）/ `components/`（`feedback.js` `icons.js` `demo.html` `demo-shell.html`）/ `settings.sandbox.json`（sandbox・denyRead・network allowlist・permissions の雛形）/ `CURRENT_STATE.md`（決まっていること・未検証の確かめ方・最初の 5 分つき）/ `ADR-template.md`（判断基準を規格名で・捨てた案）/ `lessons.md` / `implement-profile.md`（止まる条件つき）/ `work-order.md`（別モデルへ渡す作業指示書: 守ること表・Step 完了条件・止まる条件・質問節）

## 02_共通/ひな形/lifecycle/ — 工程成果物の雛形（`dev-lifecycle` 用）

`00-rfd` / `01-requirements` / `02-basic-design` / `03-detailed-design` / `04-implementation` /
`05-unit-test` / `06-integration-test` / `07-system-test` / `08-acceptance-test` / `09-operations` / `traceability-matrix`

配置は `./00_導入/02_プロジェクト配布/init-lifecycle.sh <対象>`（既存ファイルは上書きしない）。工程の入口/出口基準は
`skills/dev-lifecycle/references/phase-gates.md`、ID 体系は `references/traceability.md`、
テストレベル別の観点は `references/test-levels.md`。

## 02_共通/ひな形/test/ — テスト活動の雛形（`test-strategy` 用。配置: `./00_導入/02_プロジェクト配布/init-test-docs.sh <対象> [--ci]`）

`TESTING_STRATEGY.md`（レベル・ゲート・実行タイミング）/ `DEFINITION_OF_DONE.md`（変更タイプ別）/
`iso29119-test-plan.md` / `iso29119-test-design-spec.md` / `iso29119-test-completion-report.md` / `iso29119-incident-report.md` /
`system_test_cases.csv`（ツアー観点・severity 列）/ `feature_contracts.yml`（機能契約）。
機械ゲート（導入先の `scripts/` に置かれる。キット内の実体は `tools/`）: `02_共通/ツール/quality_harness.py`（契約検証・NG>0 で exit 1、回帰テスト `06_保守者向け/03_回帰テスト/test-quality-harness.sh`）/ `02_共通/ツール/ui-hash.py` + `02_共通/ツール/pre-commit-ui-gate.sh`（`.ui-verified`）/ CI `02_共通/ひな形/github/workflows/test-gates.yml`。
工程文書（`templates/lifecycle/05〜08`）はケースと結果、こちらは計画・完了報告・インシデント。重複させない。

## 02_共通/ひな形/github/ — GitHub 連携（`--github` で配置）

`ISSUE_TEMPLATE/`（RFD / 要件 / 欠陥）と `pull_request_template.md`（関係 ID とゲートのチェック欄）。
CI は `02_共通/ひな形/github/workflows/lifecycle-check.yml`（手動起動で `trace-check.sh` を実行し、追跡漏れを落とす。自動実行はしない）。

## 運用原則

- 工程分割が要る案件（他者へ納品/引き継ぐ・要件合意が要る・保守が続く）は `dev-lifecycle`、個人PWA/単一HTML/PoC は軽量な `sdd-ecc-workflow`。判断表は `skills/dev-lifecycle/SKILL.md` 冒頭
- 全量導入より、対象プロジェクトに合う DAILY だけを読む。LIBRARY は削除せず必要時に検索・参照
- ファイルを読む前に grep/glob で絞る（`context-compression` 参照）
- 着手前に `目的:` `終了条件:` `見積:` `検証:` の4行を出す（`rules/speed-harness.md` H-1）。所要時間 ≒ 往復回数 × 12秒
- UI変更は `uiux_review` で全状態を実機で開いて確認する。実行経路の検証なしに「完了」と言わない（`rules/functional-integrity.md`）
- AI出力品質は `agent-eval`、コード動作は `test-automation`、完了判定は `done-gate` で分ける
- セッション終了時は `CURRENT_STATE.md` と `lessons.md` を更新する

# AIDD Kit

AI 駆動開発を、QA・E2E・仕様駆動・個人PWA・ローカル業務ツールに最適化するための個人用キットです。

**全資産の入口は `INDEX.md`**（DAILY／LIBRARY の2層＋タグ＋参照コスト）。エージェントにも人間にも、まず INDEX.md から読むことを推奨します。使い方は `01_利用者向け資料/01_利用ガイド.html`（初学者向け）と `01_利用者向け資料/02_操作マニュアル.html`。キット自体の目的・要求・作業台帳は `06_保守者向け/`（保守者専用。配布しない）にあります。

**版**: `VERSION` ファイルと git tag（`vX.Y.Z`）に対応。版ごとの変更内容は `CHANGELOG.md`。`install.sh` / `export-project.sh` は導入先に `KIT_VERSION`（版・commit・日付）を刻印し、`verify.sh` が表示する。

## 導入（2つの方式。併用が前提）

**① グローバル導入** — 自分のPC1台で複数プロジェクトを横断する日常運用向け。

```bash
cd <YOUR_WORKSPACE>/yuki-aidd-kit
./00_導入/01_インストール/install.sh          # ~/.claude へ配置（skills / commands / hooks / rules / 工程承認の判定スクリプト）
./00_導入/01_インストール/install-guard.sh    # 指示優先の 3 hook だけを ~/.claude に導入（既存 settings.json に merge。冪等。Claude Code 全体に効く）
./00_導入/01_インストール/verify.sh           # 配置確認（リストは自動導出。NG>0 で exit 1）
```

**② プロジェクト配布** — Codex・リモート/エフェメラルな Claude Code 環境・teammate の clone 先など、`~/.claude` へのグローバル導入が効かない/望ましくない環境向け。対象プロジェクト直下に `.claude/` と `AGENTS.md`・`CLAUDE.md`、道具を `scripts/` に書き出し、そのプロジェクトの git にコミットして持ち運ぶ。

```bash
./00_導入/02_プロジェクト配布/export-project.sh <対象プロジェクトのパス>
cd <対象プロジェクトのパス> && git add .claude AGENTS.md CLAUDE.md scripts && git commit -m "chore: add AIDD Kit"
```

Codex は `AGENTS.md`（export で `<対象>/AGENTS.md`、グローバルは `~/.codex/AGENTS.md`。install 完了時に案内が出る）を直接読みます。`CLAUDE.md` は `@AGENTS.md` を import するので、両者は同じ本体を読みます。スキル・コマンドは Codex 用に変換したもの（コマンドは `cmd-<名前>`）38 本を install で `~/.agents/skills/`、export で `<対象>/.agents/skills/` に配り、`$done-gate` `$cmd-trace` のように `$名前` で呼びます（スラッシュメニューにも並ぶ）。claude.ai の Projects で使う場合は `01_利用者向け資料/03_ClaudeProjects設定手順.md` を参照。

続きの手順（新規プロジェクトの雛形・工程文書・テスト文書・CI サンプルの配置、導入先で動かす道具）は `INDEX.md` のクイックスタートにまとめてあります。

## 取り扱い説明書

HTML 版のガイドを 2 冊同梱しています。**初めて導入するなら `01_利用者向け資料/01_利用ガイド.html`**（概要・導入手順・最初のセッション・毎日の流れ・品質チェック・Pro/Sonnet のコツ）、使い始めてからは `01_利用者向け資料/02_操作マニュアル.html`（スキルの選び方・コマンド一覧・ECC との関係・プロジェクト別の使い分け・困った時）。

```bash
open 01_利用者向け資料/01_利用ガイド.html        # 概要と導入（初学者向け）
open 01_利用者向け資料/02_操作マニュアル.html    # 取り扱い説明書（13 章）
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

ECC（外部キット）の資産は全部読まず、プロジェクトごとに DAILY／LIBRARY に絞って使います。**プロジェクト別の対応表の真実源は `01_利用者向け資料/05_ECC資産対応表.md`**（ここには複製しません）。分類の実行は `ecc-daily-router` スキルまたは `/ecc-daily` コマンドで行います。

アプリ群の棚卸しを更新する場合:

```bash
./00_導入/03_点検/audit-app-workspace.sh <APP_WORKSPACE>
```

## キット構成

`05_プロジェクト管理/` と `06_保守者向け/` 以外は導入先へ配る（`install.sh` は `~/.claude/` へ、`export-project.sh` は `<対象>/.claude/` と `<対象>/scripts/` へ。利用者向け資料は install で `~/.claude/docs/aidd-kit/`、export で `<対象>/.claude/docs/`）。`00_導入/` だけは配らずに「キットの checkout から実行する入口」。

```text
yuki-aidd-kit/
├── README.md                 # この文書（導入の入口）
├── CHANGELOG.md              # 版ごとの変更内容（版の真実源は VERSION）
├── VERSION                   # 版（git tag と対応）
├── INDEX.md                  # 全資産の索引（DAILY/LIBRARY・タグ・参照コスト）。導入先にも同梱
│
│  ── 導入先へ配る ──
├── 03_ClaudeCode/             # Claude Code の規約どおりの配布物（導入先では ~/.claude/ か <対象>/.claude/ の直下に置かれる）
│   ├── CLAUDE.md.template    # @AGENTS.md + Claude Code 固有（実装モード・hooks・トークン）
│   ├── skills/               # スキル（skills/<name>/SKILL.md、一部 references/ 付き）
│   ├── commands/             # スラッシュコマンド（/<name>）
│   └── hooks/                # hooks + settings.json（statusLine 含む）
├── 04_Codex/                  # Codex 用の配布物
│   ├── AGENTS.md.template     # 共通規約の本体（Codex は直接、Claude Code は CLAUDE.md の @AGENTS.md で読む）
│   ├── build_codex_skills.py  # skills・commands から Codex 用スキル 38 本を生成
│   └── skills/                # 生成物（install で ~/.agents/skills/、export で <対象>/.agents/skills/ へ配る）
├── 02_共通/rules/              # 規律 4 本（absolute-rules / speed-harness / model-routing ＝常時、functional-integrity ＝コード/UI 編集時のみ）
├── 02_共通/ひな形/                # 雛形: design-system / tokens.css / ui / components / lifecycle / test / github（Issue・PR・workflows）ほか
├── 02_共通/ツール/                    # 導入先の scripts/ に置かれて動く道具（trace-check / quality_harness / ui-hash / pre-commit-ui-gate / check-approval / phase-hash / test-metrics / pre-commit）
│
│  ── キットの checkout から実行する入口 ──
├── 00_導入/                  # 01_インストール（install/verify/install-guard）・02_プロジェクト配布（export-project/init-project/init-lifecycle/init-test-docs）・03_点検（check-design/token-audit/audit-app-workspace）
│
│  ── 利用者向け文書（install で ~/.claude/docs/aidd-kit/、export で <対象>/.claude/docs/ へ配る） ──
├── 01_利用者向け資料/
│   ├── 01_利用ガイド.html            # 初学者向け（概要・導入・最初のセッション・ハンズオン）
│   ├── 02_操作マニュアル.html        # 取り扱い説明書（13 章）
│   ├── 03_ClaudeProjects設定手順.md  # claude.ai Projects のセットアップ
│   ├── 04_運用モード.md         # 標準作業モード
│   └── 05_ECC資産対応表.md          # ECC 対応表（真実源）
├── 01_利用者向け資料/90_サンプル/図書貸出/    # 事例: 貸出管理モック（完成品・app.css/js・build.py・spec・CURRENT_STATE）。ハンズオン教材
│
│  ── 配布しない ──
├── 05_プロジェクト管理/       # キット開発の計画: 要求仕様.md・ロードマップ.md（作業台帳）・構想.md・構成管理/構成管理計画書.md・構成品目一覧.md
├── 06_保守者向け/             # 保守者専用: 01_内部仕様/（現況仕様）・02_設計判断の根拠/・03_回帰テスト/（回帰テスト 10 本と check-docs。キット自身の CI が呼ぶ）・04_監査記録/・保守者の傾向.md・学んだこと.md
└── .github/workflows/        # kit-ci.yml（キット自身の CI。手動起動のみ。GitHub が直下しか読まないためここ）
```

## キット自体を作り込むとき

`06_保守者向け/01_内部仕様/` に全資産を読み切った現況仕様がある。**まず `06_保守者向け/01_内部仕様/README.md` を読む**（読む順序・更新規約）。
現況の残課題は `06_保守者向け/01_内部仕様/09_指摘事項.md`、次にやることは `06_保守者向け/01_内部仕様/10_バックログ.md`、作業台帳は `05_プロジェクト管理/ロードマップ.md`。
本体を変更したら同じコミットで `06_保守者向け/01_内部仕様/` を更新し、回帰テストと文書整合検査を通す。

```bash
for t in ci/test-*.sh; do bash "$t"; done   # 回帰テスト 10 本（hooks / install / trace-check / quality-harness / git-gates / check-approval / test-metrics / token-audit / check-docs / check-design）
./06_保守者向け/03_回帰テスト/check-docs.sh                            # 文書整合（INDEX 参照コスト・掲載漏れ・ケース数・参照切れ・目録同期。NG=0 が合格）
./00_導入/03_点検/check-design.sh                     # デザイン検査（直値・未定義トークン・外部 CDN・alert()）
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
- 「キット自体を直したい」 → `05_プロジェクト管理/ロードマップ.md` の作業ルールに従う

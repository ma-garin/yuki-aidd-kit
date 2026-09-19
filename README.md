# AIDD Kit

AI 駆動開発を、QA・E2E・仕様駆動・個人PWA・ローカル業務ツールに最適化するための個人用キットです。

**全資産の入口は `INDEX.md`**（DAILY／LIBRARY の2層＋タグ＋参照コスト）。エージェントにも人間にも、まず INDEX.md から読むことを推奨します。キット自体の目的・要求・開発継続手順は `docs/Vision.md`・`docs/PRD.md`・`docs/Roadmap.md` にあります。

**版**: `VERSION` ファイルと git tag（`vX.Y.Z`）に対応。`install.sh` / `export-project.sh` は導入先に `KIT_VERSION`（版・commit・日付）を刻印し、`verify.sh` が表示する。

## Ver.6.4 での主な更新（2026-09-19）— 工程承認ゲート: 要求どおり作られているかを工程ごとに止めて確かめる

AIDD では「プロセスが正しく回っているか」を見ても、企業が知りたい「**SDD で要求したものが確実に作られているか**」には答えられません。誤りが成果物として出てから見つかると手戻りが最大になります。各工程の出口に**人間の承認**を置き、**承認を成果物の版に縛る**ことで、誤りの伝播を工程 1 つ分に閉じ込めます。

- **承認記録**（`docs/lifecycle/approvals/phase-0..9.md`）: 承認欄があったのは 10 工程中 3 つだけだったのを全工程に。判定は 3 値（承認 / 条件付き承認 / 差し戻し）。差し戻し事項には**解消の検証方法**を必須にし、未確認事項を残したままの「承認」を認めない
- **版に縛る**（`scripts/phase-hash.py`）: 承認時の成果物のハッシュを記録に残す。**承認後に成果物が 1 文字でも変われば承認は自動失効**する。判子を押した後に中身が差し替わるのと同じ状態を機械が検出する
- **`scripts/check-approval.sh`**（20 ケース 54 アサーションの回帰テスト付き）: 記録の有無・必須欄・版の一致・未解消の差し戻し・承認者が人間か・工程順序を機械判定。終了コードは 0（合格）／1（未承認・失効）／2（**判定不能**）の 3 値で、判定不能を合格に数えない
- **`claude-code/hooks/block-phase.py`**: 前工程が未承認のまま次工程の成果物を書こうとすると**その場で止める**。`.claude/phase-gate` を置いたプロジェクトでだけ発動し、承認記録そのものへの書き込みは常に許可。**バイパス用の環境変数は作らない**（止めるなら marker を消す＝git 差分に残る）
- **`skills/phase-approval` ＋ `/phase-review`**: 人間が判子を押す前に AI 3 役（追跡・仕様一致・リスク）を**順次**で回して指摘を出し切る。並列委譲はトークンが約 7 倍になるため使わない。**AI は承認しない**（`approver` 欄には触れない）
- `docs/userguide.html` に「工程の承認ゲート」章（実際に止まったときの画面つき）

**機械が見るのは「承認記録の形式的な健全性と版の一致」まで。その設計が本当に要件を満たすかは人間しか判定できません。** この線を曖昧にすると「AI が承認した」ことになり、第三者検証としての価値が消えます。

## Ver.6.4 での主な更新（2026-09-17）— 土台: 回帰テスト・CI・版の刻印・文書整合

2026-10 の Claude Pro（Sonnet 基盤・Codex 併用）への移行に備え、**Sonnet が触って壊しても機械が気づける状態**を先に作りました。全 126 ファイルの読解記録と運用条件・作り込み計画は `spec/`（入口は `spec/README.md`）。

- **`scripts/test-install.sh`**（82 ケース）: `install.sh` / `verify.sh` / `export-project.sh` / `init-project.sh` / `init-test-docs.sh` を HOME 差し替えで検証。キットの「入口」が初めてテストされた
- **`scripts/test-git-gates.sh`**（27 ケース）: 秘密情報スキャン・`.ui-verified`・UI hash の全分岐を一時 git リポジトリで検証（従来は手動確認のみ）
- **`scripts/check-docs.sh`**: INDEX の参照コスト・掲載漏れ・回帰テストのケース数・キット内参照切れ・SKILL frontmatter・`spec/01` の同期を機械判定（NG>0 で exit 1）。手書きの数値が実体とズレる問題（AUDIT 以来の再発）を検査で止める
- **`.github/workflows/kit-ci.yml`**: 上記と既存3本の回帰テストを **Actions 画面から手動起動したときだけ**実行（`workflow_dispatch` のみ。PR や push では自動実行しない。`github-actions/` の配布用サンプルとは別物）
- `verify.sh` が NG>0 で exit 1 を返す。`VERSION` と `KIT_VERSION`（導入先への刻印）で版を追跡できる

**Pro 移行準備（M16）— 常時読み込み層のダイエットとモデル規律**

- **`CLAUDE.md = @AGENTS.md + Claude Code 固有`** に変更。共通規約の本体は `AGENTS.md.template` 一本になり、Claude Code は import で、Codex は直接読む。「両テンプレを同時に更新する」ルールは不要になった（`install.sh` は `~/.claude/AGENTS.md` も配置）
- **`rules/` を規範だけに圧縮**: `absolute-rules` 112→19行（表形式）、`speed-harness` 115→51行。根拠・失敗事例・原文と H-6 の実測記録は `docs/rules-rationale/` へ（`rules/` 配下は再帰的に自動ロードされるため外に置く）
- **`functional-integrity` に `paths:` frontmatter**: コード/UI（`.py .js .ts .tsx .jsx .html .css .vue .svelte`）を触ったときだけ読み込まれる
- **`INDEX.md` を毎回読むのをやめた**: `AGENTS.md` の「読む範囲」表（タスク種別 → 最初に使うスキル/コマンド）から直行し、表に無いときだけ INDEX を開く
- **`rules/model-routing.md`（新設）**: 既定 Sonnet、Opus へ上げる3条件、effort、`/clear`、委譲は隔離目的のみ、上限時の手順、週1で `/usage`
- 常時読み込みの床（推定）: **10,810 → 5,028 トークン**（rules 2本 + CLAUDE.md/AGENTS.md。INDEX 4,456 は必要時のみ）。実トークンは `/context` で要実測
- `check-docs.sh` の「常時読込 rules ≦ 100 行」を WARN から **NG に昇格**（逆戻りを CI が止める）

**デザイン出荷物（M17）— 散文を減らし、出荷物を増やす（Sonnet に書かせず読ませる）**

- **`templates/ui/components.css`**（部品）/ **`templates/ui/layout.css`**（骨格）: `skills/design-system` の散文 CSS 17 ブロックを `var(--*)` だけで実体化。読み込むだけで管理画面の骨格と部品が揃う。`templates/components/demo.html` / `demo-shell.html` で Playwright 確認済み（ライト／ダーク／360px）
- **`templates/ui/`** にフレームワーク別の出荷物: `tailwind.config.js`（CSS 変数参照）、`streamlit-config.toml` + `streamlit_theme.py`（`apply_theme()` / `badge()` / `kpi()` / `empty_state()` / `callout()`）、`README.md`（単一 HTML / PWA / React+Vite / Streamlit / Flask・Django の置き場所・読み込み順の1枚表）
- **`scripts/check-design.sh`**（36 ケースの回帰テスト付き）: 直値（色は全域・px は余白角丸文字サイズ系）・未定義トークン・未使用トークン(WARN)・外部 CDN・`alert()`・`tokens.css` 未読込を機械判定。`templates/design-system.md` の再現チェックリストは機械 5 項目／目視 9 項目に分けた。CI に追加
- **`skills/design-system/SKILL.md` を 473 → 115 行に**: 値の唯一の真実源を `templates/tokens.css` に一本化し、決めの理由は `references/tokens.md`、部品の使い分けと落とし穴（実不具合由来 7 件）は `references/components.md` へ。`check-docs.sh` の「SKILL ≦ 200 行」を **NG に昇格**
- `tokens.css` に `--color-medium-text` / `--color-scrim` / `--color-tooltip-bg/-text` / `--color-knob` を追加（直値解消のため）
- **`docs/lessons.md`**（新設）: キット自身の改善ログ。本セッションと移行準備が最初のエントリ。移行後の週次 `/usage` 記録欄付き
- **`docs/examples/library-loan/`**（新設）: 事例「社内図書館の貸出管理を Excel から Web へ。HTML でモック」。依頼文 1 行からキットの手順だけで作った完成品・ソース・仕様・引き継ぎメモ。`docs/userguide.html` の「ハンズオン」章の教材。この検証でキットの欠陥 3 件（F-14〜F-16）を見つけて是正
- `export-project.sh` の settings.json に `block-explore.sh`（Read/Grep/Glob）を配線。グローバル導入と配布先で `/implement` の振る舞いが同じになった

## Ver.6.3 での主な更新（2026-08-25）— デザイン: トークン実物・画面の作り方・フレームワーク別適用

- **`templates/tokens.css`**: デザイントークンの実物（ライト＋ダーク、`prefers-color-scheme` と `data-theme` 両対応、reduced-motion、タップ最小 44px）。WebSpec2Doc の `on-primary` / `surface-3` / `border-strong` / severity `-border` / `motion-*`、UX_Auto_Reviewer の本文幅 68ch を統合
- **`design-system` に「画面の作り方」を追加**: 直値禁止のトークン運用（色 105 種・角丸 11 種・文字 21 段階を整理した実績から）、骨格（globalbar / sidebar / topbar / content）、**操作には必ず結果を返す**（成功＝消えるトースト／失敗＝消えない＋次の行動／処理中／0 件／危険操作の確認、`textContent` で入れる）、アイコン（同梱・CDN 禁止・慣用の形）、文言規約（ボタンは動作名、見出しに動詞を入れない、「（任意）」を付けない）
- **`design-system/references/frameworks.md`**: 出荷物への導線と、ECC `frontend-patterns`・`frontend-design`・`ckm:design`・`uiux_review` との分担表（Ver.6.4 で FW 別の置き場所は `templates/ui/README.md` へ移動）
- `templates/design-system.md` の再現チェックリストに直値・フィードバック・文言・アイコンの項目を追加
- **`templates/components/`**: `feedback.js`（トースト／消えない失敗＋次の行動／処理中／空状態／確認ダイアログ。自己完結）、`icons.js`（Material Symbols 同梱）、`demo.html`（ライト／ダークの実機確認ページ。Playwright で確認済み）
- `github-actions/test-gates.yml` を Python / Node 両対応（ファイルの有無で自動判定）

## Ver.6.2 での主な更新（2026-08-25）— テスト活動の設計と機械ゲート

WebSpec2Doc で運用してきたテスト活動（テスト戦略・DoD・ISO/IEC/IEEE 29119 文書・機能契約ハーネス・UI 検証マーカー）を汎用化して取り込みました。

- **`skills/test-strategy`**: テストレベル L1〜L4 とゲート基準、テスト種類マトリクス、**ゲートの実行タイミング**（日常は要求時のみ／マイルストーンはフルゲート — 宣言が無かったためテスト資産 17 件が 1 週間陳腐化した実損害から）、変更タイプ別 DoD、完了基準、29119 文書との対応表。references に機能契約ハーネスと `.ui-verified` ゲートの仕様
- **`skills/e2e-cycle`** + `/e2e-cycle`: E2E を設計→Playwright 生成→実行→ODC 分析・修整→コミットの 5 フェーズで、1 起動 1 フェーズで段階停止しながら回す
- **`templates/test/`**（8 本）: `TESTING_STRATEGY` / `DEFINITION_OF_DONE` / 29119 の計画・設計仕様・完了報告・インシデント / `system_test_cases.csv`（Whittaker ツアー観点・severity 列）/ `feature_contracts.yml`
- **`scripts/quality_harness.py`**: 機能契約を検証（実行経路の無い implemented、critical/high の失敗系テスト欠落、契約未登録モジュール、未実装マーカーなど 9 種。NG>0 で exit 1）。回帰テスト `scripts/test-quality-harness.sh` 11 ケース。**雛形が新規プロジェクトで PASS することもテスト**
- **`scripts/ui-hash.py` + `scripts/pre-commit-ui-gate.sh`**: E2E 合格時に git hash + UI hash + 時刻を `.ui-verified` に記録し、未検証・検証後変更の UI コミットを止める。刷新期間は `.rebuild-mode` で明示的に免除
- `scripts/init-test-docs.sh <対象> [--ci]` で一式を配置、`github-actions/test-gates.yml` で CI 実行（手動起動のみ）
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
- `install.sh` / `export-project.sh` / `verify.sh` / `test-hooks.sh` が rules と `.py` hooks を扱うよう更新（hooks 回帰テスト 63 ケース）

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
- GitHub 連携: Issue テンプレート（RFD・要件・欠陥）、関係 ID 欄付き PR テンプレート、手動起動で trace-check を回す `lifecycle-check.yml`
- 回帰テスト `scripts/test-trace-check.sh`（15ケース）。**配布する雛形が最初から NG=0 で始まること**もテスト対象

```bash
./scripts/init-lifecycle.sh <対象プロジェクト> --github   # 工程文書＋GitHub テンプレート一式
./scripts/trace-check.sh docs/lifecycle                   # 追跡の機械検証（NG=0 で合格）
./scripts/check-approval.sh                               # 工程承認の機械検査（0=合格 / 1=未承認・失効 / 2=判定不能）
./scripts/check-approval.sh --gate 3                      # 「第3工程に着手してよいか」だけを判定（hook もこれを呼ぶ）
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
./scripts/verify.sh      # 配置確認（リストは自動導出。NG>0 で exit 1）
./scripts/test-hooks.sh  # hooks の回帰テスト（63ケース）
./scripts/test-install.sh    # 導入・配布・初期化スクリプトの回帰テスト（82ケース。実 ~/.claude には触らない）
./scripts/test-check-design.sh && ./scripts/check-design.sh   # デザイン検査（直値・未定義トークン・CDN・alert()）の回帰テストと本検査
./scripts/test-git-gates.sh  # 秘密情報スキャン・.ui-verified・UI hash の回帰テスト（27ケース）
./scripts/test-check-approval.sh && ./scripts/check-approval.sh   # 工程承認ゲートの回帰テストと本検査
```

**② プロジェクト配布** — Codex・リモート/エフェメラルな Claude Code 環境・teammate の clone 先など、`~/.claude` へのグローバル導入が効かない/望ましくない環境向け。対象プロジェクト直下に `.claude/` と `AGENTS.md`・`CLAUDE.md` を書き出し、そのプロジェクトの git にコミットして持ち運ぶ。

```bash
./scripts/export-project.sh <対象プロジェクトのパス>
cd <対象プロジェクトのパス> && git add .claude AGENTS.md CLAUDE.md && git commit -m "chore: add AIDD Kit"
```

Codex は `AGENTS.md` を直接読みます（グローバルは `ln -s ~/.claude/AGENTS.md ~/.codex/AGENTS.md`）。`CLAUDE.md` は `@AGENTS.md` を import するので、両者は同じ本体を読みます。claude.ai の Projects で使う場合は `claude-projects-setup.md` を参照。

## 取り扱い説明書

HTML 版のガイドを 2 冊同梱しています。**初めて導入するなら `userguide.html`**（概要・導入手順・最初のセッション・毎日の流れ・品質チェック・Pro/Sonnet のコツ）、使い始めてからは `yuki-aidd-kit-manual.html`（スキルの選び方・コマンド一覧・ECC との関係・プロジェクト別の使い分け・困った時）。

```bash
open docs/userguide.html             # 概要と導入（初学者向け・Ver.6.4）
open docs/yuki-aidd-kit-manual.html  # 取り扱い説明書（13 章）
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
├── AGENTS.md.template        # 共通規約の本体（Codex は直接、Claude Code は CLAUDE.md の @AGENTS.md で読む）
├── CLAUDE.md.template        # @AGENTS.md + Claude Code 固有（実装モード・hooks・トークン）
├── claude-projects-setup.md  # claude.ai Projects のセットアップ
├── docs/
│   ├── Vision.md / PRD.md / Roadmap.md   # キット自体の目的・要求・作業台帳
│   ├── ECC-ASSET-MAP.md                  # ECC 対応表（真実源）
│   ├── AUDIT-2026-07.md                  # 資産監査の記録
│   ├── OPERATING-MODE.md                 # 標準作業モード
│   ├── PROJECT-FIT-REPORT.md             # 実プロジェクト適合レポート
│   ├── rules-rationale/                  # rules の根拠・原文・実測記録（毎回は読まない）
│   ├── lessons.md                        # キット自身の改善ログ（Keep / Problem / Try、週次 /usage）
│   ├── examples/library-loan/            # 事例: 貸出管理モック（完成品・app.css/js・build.py・spec・CURRENT_STATE）
│   ├── userguide.html                    # ユーザーガイド（概要・導入。初学者向け）
│   └── yuki-aidd-kit-manual.html         # HTML 取説（13 章）
├── rules/                    # 規律 4本（absolute-rules / speed-harness / model-routing ＝常時、functional-integrity ＝コード/UI 編集時のみ）
├── skills/                   # 19スキル（各 SKILL.md、一部 references/ 付き）
│   ├── dev-lifecycle/        # 工程ライフサイクル（+ phase-gates / traceability / test-levels）
│   ├── test-strategy/        # テスト活動の設計（+ feature-contracts / ui-verified-gate）
│   ├── e2e-cycle/            # 段階停止型 E2E ワークフロー
│   ├── design-system/        # デザイン規律（+ references/tokens.md / components.md / frameworks.md）
│   └── uiux_review/          # UI/UX 実機レビュー（+ references/viewpoints.md）
├── claude-code/
│   ├── commands/             # 16スラッシュコマンド
│   └── hooks/                # 7 hooks（sh 4 + py 3）+ settings.json（statusLine 含む）
├── scripts/
│   ├── install.sh / verify.sh / test-hooks.sh / test-install.sh   # グローバル導入と回帰テスト
│   ├── check-docs.sh (check_docs.py) / test-check-docs.sh / test-git-gates.sh  # 文書整合・git ゲートの検査
│   ├── check-design.sh (check_design.py) / test-check-design.sh  # デザイン検査（直値・トークン・CDN・alert()）
│   ├── export-project.sh                        # プロジェクト配布
│   ├── init-lifecycle.sh / trace-check.sh / test-trace-check.sh  # 工程ライフサイクル
│   ├── check-approval.sh (check_approval.py) / phase-hash.py / test-check-approval.sh  # 工程承認ゲート
│   ├── init-test-docs.sh / quality_harness.py / test-quality-harness.sh  # テスト活動
│   ├── ui-hash.py / pre-commit-ui-gate.sh          # UI 検証マーカー
│   ├── init-project.sh / audit-app-workspace.sh / pre-commit
├── templates/
│   ├── design-system.md      # 視覚的指示書
│   ├── tokens.css            # デザイントークンの実物（ライト＋ダーク。値の唯一の真実源）
│   ├── ui/                   # components.css / layout.css / tailwind.config.js / streamlit-config.toml / streamlit_theme.py / README.md
│   ├── components/           # feedback.js / icons.js / demo.html / demo-shell.html
│   ├── settings.sandbox.json # sandbox / denyRead / network allowlist / permissions の雛形
│   ├── lifecycle/            # 工程成果物の雛形11本（RFD〜保守運用＋追跡表）
│   ├── test/                 # テスト戦略・DoD・29119 文書・テストケース CSV・機能契約の雛形8本
│   ├── github/               # Issue（RFD/要件/欠陥）・PR テンプレート
│   └── CURRENT_STATE.md / ADR-template.md / lessons.md / implement-profile.md
├── github-actions/           # 配布用サンプル（deploy / secret-scan / lifecycle-check / test-gates。いずれも手動起動のみ）
├── .github/workflows/kit-ci.yml  # キット自身の CI（手動起動のみ）
├── VERSION                   # 版（git tag と対応）
└── spec/                     # 現況仕様・運用条件・作り込み計画（キット自体を触るならまずここ）
```

## キット自体を作り込むとき

`spec/` に全資産を読み切った現況仕様がある。**まず `spec/README.md` を読む**（読む順序・更新規約）。
現況の残課題は `spec/09-findings.md`、次にやることは `spec/10-backlog.md`。
本体を変更したら同じコミットで `spec/` を更新する。

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

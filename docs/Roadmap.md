# Roadmap — yuki-aidd-kit

このファイルは、前提知識ゼロのモデル（Opus 4.8 等）がキット開発を継続するための作業台帳。チェックボックスを上から順に消化する。

## 作業ルール（毎回ここから）

1. まず `INDEX.md` を読み、次に本ファイルの未完了項目（先頭の `[ ]`）だけを見る。他ファイルは各項目の「対象」に書かれたものだけ開く
2. 上位文書: 目的は `docs/Vision.md`、要求と非機能制約は `docs/PRD.md`。迷ったら PRD の非機能要求（特に「Claude Code と他エージェント双方で動作」）に反しないか確認する
3. 1項目完了ごとに: `./scripts/install.sh` → `./scripts/verify.sh` が NG=0 → 完了条件を確認 → チェックを付け本ファイルを更新 → Conventional Commits で個別コミット
4. 禁止: 実在しないファイル・ECC 資産への参照の新規作成／真実源の重複（デザイン値は `skills/design-system`、ECC 対応は `docs/ECC-ASSET-MAP.md`）／承認なしの大規模リファクタ
5. 設計判断に迷ったら選択肢を提示して保守者の確認を取る（勝手に決めない）

## M1: コンテキスト圧縮（完了 2026-07）

- [x] `skills/context-compression/SKILL.md` 新設（3層要約規約／grep・glob 優先／決定論的作業のスクリプト化）
- [x] `claude-code/commands/compact-work.md` 追加（スキル呼び出し）
- [x] `scripts/verify.sh` の確認リストに両者を追加

## M2: 資産監査と修正（完了 2026-07）

- [x] 全資産（skills 14 / commands 10 / hooks 4）の監査表を `docs/AUDIT-2026-07.md` に出力
- [x] 承認済み修正の適用（hooks の stdin JSON 化＝A-01、端末幅 360×820 統一＝A-02、ECC プリセットの MAP 一本化＝A-03、ほか A-05〜A-09。詳細は AUDIT の適用記録）

## M3: 自己文書化（完了 2026-07）

- [x] `docs/Vision.md` / `docs/PRD.md` / `docs/Roadmap.md`（本ファイル）を新設

## M4: デザインシステム指示書（完了 2026-07）

- [x] `templates/design-system.md` を新設する
  - 対象: `templates/design-system.md`（新規）。参照してよいもの: `skills/design-system/SKILL.md`（トークンの真実源）、`docs/yuki-aidd-kit-manual.html`（既存スタイルの実例）
  - 内容: 基準トークン（primary `#1976D2`、Noto Sans JP + JetBrains Mono、MD3 light）を前提に、①Web アプリ ②HTML スライド ③管理画面 の3パターンを、コード無しでも他モデルが再現できる「視覚的指示書」（配置・比率・余白・階層・状態の言葉による指定）で記述する
  - 制約: `skills/design-system/SKILL.md` の CSS 変数値と矛盾させない（値の再定義はせず参照する。AUDIT の D-02 を悪化させない）。`docs/yuki-aidd-kit-manual.html` の見た目とも矛盾しないこと
  - 完了条件: 3パターンそれぞれに「レイアウト構造」「タイポグラフィ階層」「色の役割」「余白・密度」「状態表現（hover/選択/エラー）」の指定があり、具体値は design-system スキルへの参照で解決できる
  - 検証: `./scripts/verify.sh` NG=0（このファイル自体は verify 対象外なので、目視で完了条件を確認して記録する）

## M5: 検索構造の再設計（完了 2026-07）

- [x] `INDEX.md` を DAILY／LIBRARY の2層＋タグで再構成する
  - 対象: `INDEX.md`。参照: 全 `skills/*/SKILL.md` の frontmatter と `claude-code/commands/*.md` の1行目、各ファイルの行数（`wc -l`）
  - 内容: 各スキル・コマンドに「1行要約」「タグ（例: #qa #pwa #token #eval）」「参照コスト（読むべき行数目安）」を付与。ECC 連携表は `docs/ECC-ASSET-MAP.md` への参照1行に置換する（AUDIT の A-04 解消）
  - 完了条件: 全14スキル・10コマンドが掲載され、DAILY/LIBRARY の判定基準が冒頭に明記されている
- [x] `CLAUDE.md.template` に導線を追記する
  - 対象: `CLAUDE.md.template`。内容: 「まず `INDEX.md` を読み、必要ファイルのみ開く」動線をトークン規律セクションに追加
  - 完了条件: install 後の `~/.claude/CLAUDE.md` を読んだエージェントが、最初に INDEX.md へ誘導される記述になっている
- [x] 両変更後に `./scripts/install.sh` → `./scripts/verify.sh` NG=0 → コミット

## M6: バックログ（優先度順・未着手）

- [x] hooks の回帰テストをスクリプト化する（完了 2026-07）
  - 対象: `scripts/test-hooks.sh`（新規）。stdin JSON を3 hook に流し、期待出力（秘密ファイル警告／CSS・JS 警告／HTML レポート）を assert する。M2 A-01 の再発防止を自動化する
  - 完了確認: 8ケース PASS=8/FAIL=0 で exit 0。INDEX.md クイックスタートから辿れる
- [x] `verify.sh` のリスト自動生成化（完了 2026-07。保守者が「自動導出化」を選択）
  - 適用: verify.sh がリポジトリ実体（skills/ commands/ hooks/）からチェックリストを導出して `~/.claude` と突合する方式に変更。資産追加時の verify.sh 更新が不要になった。欠落検知（NG カウント）の動作確認済み
- [ ] retro 運用の実績を反映する
  - 対象: `templates/lessons.md` の運用実績を見て、`skills/retro/SKILL.md` の「キットへのフィードバック」手順を実測に合わせて更新する。lessons.md にエントリが溜まってから着手（前提条件）
- [x] streamlit-rag-app スキルの前提明記（完了 2026-07）
  - 対象: `skills/streamlit-rag-app/SKILL.md`。冒頭に特定プロジェクト前提である旨と、一般 Streamlit アプリへは「実装規律」節のみ流用可である旨を明記した（AUDIT 監査表の備考対応）

## M7: ドキュメント全体整備（完了 2026-07）

- [x] README.md を Ver.5.0 反映で刷新（INDEX.md 導線、構成ツリー更新、ECC 表の複製を ECC-ASSET-MAP 参照に置換）
- [x] manual.html を更新（context-compression／`/compact-work`／test-hooks.sh を追記、ECC 節に真実源の注記、生プレースホルダ `<...>` が未知タグ扱いで非表示になるバグをエスケープ修正）
- [x] AGENTS.md.template に INDEX.md 導線を追加（CLAUDE.md.template と同等。PRD の互換性 NFR 対応）
- [x] claude-projects-setup.md のツール固有名を汎用化、ナレッジ一覧に INDEX.md を追加
- [x] OPERATING-MODE.md に INDEX.md と context-compression の参照を追加
- [x] INDEX.md の参照コスト（行数）を実測値に更新

## M8: プロジェクト配布機構（完了 2026-07）

グローバル運用（install.sh）に加え、Codex・リモート/エフェメラルなClaude Code環境・teammateへの配布を両立させる（保守者確認済み: 対象範囲=キット一式フルコピー、CLAUDE.md生成=する、Vision Non-Goals=意味を限定）。

- [x] `scripts/export-project.sh <target>` を新設。対象プロジェクト直下に `.claude/skills,commands,hooks,settings.json,INDEX.md` を全コピーし、`AGENTS.md`・`CLAUDE.md` を生成する（INDEX.md 参照は `.claude/INDEX.md` の相対パスに変換）
  - 検証: スクラッチディレクトリへの初回エクスポート・再実行時の `.bak` 退避・hooks の相対パス動作（cwd=プロジェクトルート想定）を確認済み
- [x] `docs/Vision.md` に「配置の2層」節を追加し、Non-Goals を「不特定多数へのOSS公開はしない」に意味を限定
- [x] `docs/PRD.md` に FR-04a（プロジェクト配布）を追加し、互換性NFRに「グローバル導入とプロジェクト配布のどちらでも同一の振る舞い」を追記

## M9: デザインシステムのダーク対応・是正（完了 2026-07）

Harness ToDo モック（サイドバー全高＋折りたたみ、ℹ️ツールチップ、列フィルタ、ページネーション、ダークテーマ）で検証したパターンを `skills/design-system/SKILL.md` と `templates/design-system.md` に反映した。既存の `--color-*` 変数名は変更していない（非破壊）。

- [x] ダークテーマトークンを追加（`prefers-color-scheme`+`data-theme`。既存変数の上書きのみで新規リネームなし）
- [x] フォント読み込み方針を是正: CDN前提を「オンライン確定時の任意強化」に格下げし、システムフォントスタックを既定にした（single-html-tool/nfr-standardsのオフライン制約との矛盾を解消）
- [x] 永続サイドバー（全高・独立ヘッダー・折りたたみ）パターンを追加。旧2ペインパターンは軽量ツール向けとして残す
- [x] 検証済みコンポーネントを追加: 情報ツールチップ（ℹ️、画面端はみ出し対策を含む）／テーブル列フィルタ／ページネーション／トグル・セグメントコントロール
- [x] `templates/design-system.md` のパターン1・パターン3にサイドバー構造とダーク対応の参照を追記

## M10: モーダル・通知・空状態・フォームエラーの反映（完了 2026-07）

Harness ToDo モックに実クリックで動くインタラクティブなモーダル/ダイアログ・通知ドロップダウン・空状態・ログインエラー状態を実装し、実際の操作で検証してから `skills/design-system/SKILL.md` に反映した。

- [x] モーダル/ダイアログ（新規作成フォーム・破壊的操作の確認。動的にタイトルを埋め込む実装を検証）
- [x] 通知/リッチポップオーバー（未読/既読の区別、右揃え配置、外側クリックで閉じる）
- [x] 空状態（0件表示。フィルタ結果0件と新規ユーザーの2用途を区別）
- [x] フォームのバリデーション/エラー（バナー＋フィールド直下エラーの2段構え）
- [x] 実装中に発見した不具合を修正: 常時表示の情報ツールチップが下の行のクリックを妨げていた問題（ホバー時のみ表示に変更）

## M11: 開発工程ライフサイクル（完了 2026-08）

RFD から保守運用までの10工程を AI に実行させる層を追加した。既存の軽量 SDD（spec/plan/tasks）は残し、**工程分割が要る案件だけが本層を使う**という入れ子関係にして真実源の重複を避けた（対応表は `skills/dev-lifecycle/SKILL.md` の1箇所のみ）。

- [x] `skills/dev-lifecycle/` を新設（SKILL.md ＋ references: `phase-gates.md` / `traceability.md` / `test-levels.md`）
  - 適用判断（軽量 SDD との使い分け）・10工程の成果物と ID・V字の対応・工程ゲート・役割・他スキルへの委譲表を規定
- [x] `templates/lifecycle/` に工程成果物の雛形11本を新設（RFD／要件定義／基本設計／詳細設計／実装記録／単体・結合・システム・受け入れテスト／保守運用／追跡表）
- [x] `scripts/trace-check.sh` を新設。要件→設計→実装→テストの追跡を機械検証する（重複定義／未定義参照／所有ファイル違反／追跡表未記載／カバー漏れ／孤立テストの6種別）。出力は context-compression の3層要約に従い、全件は詳細レポートへ書き出す
- [x] `scripts/init-lifecycle.sh` を新設（工程雛形の配置。`--github` で Issue/PR/CI テンプレートも配置。既存ファイルは上書きしない）
- [x] `scripts/test-trace-check.sh` で回帰テスト化（15ケース PASS）。**雛形が最初から NG=0 で始まること**をテストに含めた（雛形が NG を出すと利用者が検査結果を無視するようになるため）
- [x] `claude-code/commands/` に `/rfd`・`/lifecycle`・`/trace` を追加
- [x] GitHub 連携: `templates/github/`（RFD・要件・欠陥の Issue テンプレート、関係 ID 欄付き PR テンプレート）と `github-actions/lifecycle-check.yml`（PR で trace-check を実行）
- [x] 既存資産との接続: `done-gate` に工程ゲート項目、`sdd-ecc-workflow` に使い分けの導線、`CLAUDE.md.template`・`AGENTS.md.template`・`INDEX.md`・`README.md` に工程の導線を追加。`export-project.sh` が `templates/` と `trace-check.sh` を同梱するよう更新
- 検証記録: `./scripts/install.sh` → `./scripts/verify.sh` NG=0、`./scripts/test-hooks.sh` 8/8、`./scripts/test-trace-check.sh` 15/15

## M12: 実プロジェクト運用の還流（完了 2026-08-25）

2026-08 に WebSpec2Doc / UX_Auto_Reviewer / my_forward で育った運用ルール・hook・スキルをキットへ取り込んだ。合わせてローカルと GitHub で分岐していた履歴を GitHub 側に統一し、`atarimae-quality-audit` を載せ直した。

- [x] `rules/` を新設: `absolute-rules.md`（A-1〜A-10）/ `speed-harness.md`（プロジェクト固有の H-2 を雛形化、実測から H-5「見積の既定」を抽出）/ `functional-integrity.md`
- [x] `skills/uiux_review/` を追加（SKILL.md + references/viewpoints.md）
- [x] hooks: `block-gates.py` / `progress.py` / `statusline.py` を追加し `settings.json` に配線（PreToolUse Bash・statusLine）
- [x] `templates/settings.sandbox.json` を追加
- [x] `CLAUDE.md.template` / `AGENTS.md.template` を「速度最優先・必須プロセス・完了条件」で改訂（両ファイル同時、X-5）。C-02「指定外は読まない」と X-4「セッション分割」を廃止
- [x] `install.sh`（rules → `~/.claude/rules/aidd-kit/`、同名既存はスキップ）/ `export-project.sh`（rules → `.claude/rules/`、py hooks、statusLine）/ `verify.sh` / `test-hooks.sh`（+8 ケース）
- [x] `docs/yuki-aidd-kit-manual.html` に「速度と完了のルール」節・uiux_review / atarimae 行・用語 rules を追加
- [x] `docs/OPERATING-MODE.md` §4〜6 に H-1 着手前3行・H-3 バッチ検証・functional-integrity・progress.py を反映
- [x] `docs/PRD.md` FR-03 を 7 hook に更新し FR-03a（rules 供給）を追加。`claude-projects-setup.md` の「指定外ファイルを読まない」を速度・完了条件の記述に置換
- 検証記録: `./scripts/test-hooks.sh`（実行結果は PR 本文に記載）。`install.sh` はグローバル環境を上書きするため本作業では未実行（`verify.sh` 未計測）

## M13: テスト活動の設計と機械ゲート（完了 2026-08-25）

WebSpec2Doc のテスト運用（TESTING_STRATEGY / DEFINITION_OF_DONE / 29119 文書 4 本 / quality_harness / .ui-verified）を汎用化して取り込んだ。真実源の分担: レベルの設計観点は `dev-lifecycle/references/test-levels.md`、ケースと結果は `templates/lifecycle/05〜08`、計画・完了報告・インシデントは `templates/test/`。

- [x] `skills/test-strategy/`（SKILL.md + references: `feature-contracts.md` / `ui-verified-gate.md`）
- [x] `skills/e2e-cycle/` と `/e2e-cycle`（`help` 引数で使い方を表示）
- [x] `templates/test/` 8 本（`feature_contracts.yml` は新規プロジェクトで PASS することを回帰テストで保証）
- [x] `scripts/quality_harness.py`（設定駆動の汎用版）+ `scripts/test-quality-harness.sh`（11 ケース PASS）
- [x] `scripts/ui-hash.py` + `scripts/pre-commit-ui-gate.sh`（マーカー不在・期限切れ・hash 不一致で BLOCKED、`.rebuild-mode` で WARN。手動 4 ケース確認）
- [x] `scripts/init-test-docs.sh`（`--ci` で `github-actions/test-gates.yml` も配置）、`export-project.sh` がゲートスクリプトを同梱
- [x] `done-gate` / `test-automation` / `qa-review-standards` / `rules/functional-integrity.md` / 両テンプレートに導線を追加
- [ ] `docs/yuki-aidd-kit-manual.html` の非エンジニア向け説明（テストレベルと「テストが通った≠完了」）は本 PR で最小限。図解は未着手
- 検証記録: `test-quality-harness.sh` 11/11、`init-test-docs.sh` dry-run で 12 ファイル配置・雛形契約 PASS、`pre-commit-ui-gate.sh` 4 状態確認。AUDIT-2026-07 で指摘された「ISO 29119 が 0 件」を解消

## M14: デザイン — トークン実物・画面の作り方・フレームワーク別適用（完了 2026-08-25）

- [x] `templates/tokens.css`（SKILL.md の値を真実源として実物化。WebSpec2Doc / UX_Auto_Reviewer の追加トークンを統合）
- [x] `skills/design-system/SKILL.md` に「画面の作り方」（トークン運用の規律・骨格・操作フィードバック・アイコン・文言）を追加、description を拡張
- [x] `skills/design-system/references/frameworks.md`（単一 HTML / React+Vite+Tailwind / Streamlit / Flask・Django、デザイン系スキルの分担）
- [x] `templates/design-system.md` に導線とチェック項目を追加
- [x] `templates/components/feedback.js` / `icons.js` / `demo.html`（tokens.css 前提に自己完結化。2026-08-26）
- [x] `github-actions/test-gates.yml` を Python / Node 両対応に（2026-08-26）
- [x] 「弱点」表記を「残課題」に変更（A-3。分かっている不足は申告で済ませず対応する）
- 検証記録: `demo.html` を Playwright でライト／ダーク・トースト・確認ダイアログ・空状態を実機確認（2026-08-26）

## M15: 土台 — Sonnet が壊しても機械が気づける状態にする（完了 2026-09-17）

背景: 2026-10 の Claude Pro（Sonnet 基盤・Codex 併用）への移行を前に、`spec/`（全 126 ファイル読解の記録）で
入口スクリプトと git ゲートが未テスト・CI 不在・版の刻印なし・文書の数値が実体とズレる（F-01〜F-03, F-06, F-07, F-09, F-11, F-12）
ことが分かった。運用条件と設計含意は `spec/11-target-operating-model.md`、実行順は `spec/10-backlog.md`。

- [x] `scripts/verify.sh` が NG>0 で exit 1 を返す（S1。CI・テストから合否を機械判定できる）
- [x] 版の刻印（S2）: `VERSION` を新設し、`install.sh` / `export-project.sh` が導入先に `KIT_VERSION`（版・commit・日付）を書く。`verify.sh` が表示
- [x] `scripts/test-install.sh`（S3、66 ケース）: install / verify / export / init-project / init-test-docs を HOME 差し替えで検証。実 `~/.claude` には触らない
- [x] `scripts/test-git-gates.sh`（S4、27 ケース）: pre-commit（簡易パターン経路）/ ui-hash.py / pre-commit-ui-gate.sh の全分岐を一時 git リポジトリで検証
- [x] `scripts/check_docs.py` + `check-docs.sh` + `test-check-docs.sh`（S5）: INDEX 参照コスト・掲載漏れ・ケース数・参照切れ・frontmatter・常時読込 rules 行数（WARN）・SKILL 行数目安（WARN）・spec/01 の同期を機械判定
- [x] `.github/workflows/kit-ci.yml`（S5）: 6 本の回帰テストと check-docs を実行（`github-actions/` の配布用サンプルとは別物）。**2026-09-17 保守者決定で `workflow_dispatch` のみに変更**（PR / push での自動実行はしない。ゲートは要求時だけ、の規律を CI にも適用）
- [x] 数値の是正と spec 同期（S6）: check-docs が検出した INDEX 11 件・manual 2 件を是正。`spec/01` を実測に同期
- 検証記録: test-hooks 19/19・test-trace-check 15/15・test-quality-harness 11/11・test-install 66/66・test-git-gates 27/27・test-check-docs 全 PASS・`check-docs.sh` NG=0（WARN 2: rules 268 行 > 100、design-system 465 行 > 200 — M16 / M17 で解消）
- 残: `git tag v6.3.0` は main へのマージ時に保守者が打つ

## M16: Pro 移行準備 — 常時読み込み層のダイエットとモデル規律（完了 2026-09-17）

条件: `spec/11-target-operating-model.md`（Pro ＋ Sonnet ＋ Codex 併用）。一次情報: Claude Code `memory` docs（`paths` 付き rules は該当ファイルを触ったときだけ読み込まれる／`@AGENTS.md` import／`rules/` は再帰的に自動ロード）。

- [x] `rules/absolute-rules.md` を表形式に圧縮（112→19行）、`rules/speed-harness.md` を規範だけに（115→51行）。根拠・失敗事例・原文と H-6 の実測記録は `docs/rules-rationale/` へ（S7a）
- [x] `rules/functional-integrity.md` に `paths:` frontmatter（コード/UI 編集時のみ読み込み。17行）（S7a）
- [x] `AGENTS.md.template` を共通規約の本体にし、「読む範囲」を **タスク種別 → 最初に使うスキル/コマンド** の表に。`INDEX.md` は「表に無い・迷ったときだけ」に降格（S7b）
- [x] `CLAUDE.md.template` を `@AGENTS.md` ＋ Claude Code 固有（実装モード・hooks・トークン）の 21 行に。`install.sh` が `~/.claude/AGENTS.md` も配置、`verify.sh` が確認。二重管理のルール（M12 の X-5）は廃止（S7c）
- [x] `rules/model-routing.md`（15行）: 既定 Sonnet／Opus へ上げる3条件（暫定）／effort／`/clear`／委譲は隔離目的のみ／上限時の手順／週1で `/usage`。根拠は `docs/rules-rationale/model-routing.md`（S8）
- [x] `check_docs.py` の検査6（`paths` 無し rules ≦ 100 行）を NG に昇格。`test-install.sh` に AGENTS.md・`@AGENTS.md`・`paths` の保持を追加（71 ケース）
- 実測（文字数からの推定）: 常時の床 10,810 → **5,028 tok**（rules 2本 2,511 ＋ CLAUDE.md/AGENTS.md 2,518）。INDEX 4,456 は必要時のみ。**実トークンは保守者が `/context` で計測し `spec/11` U-2 に記録する**
- 残: Opus へ上げる3条件は暫定。移行後1週間の `/usage` 実測で見直す（Q-7）

## M17: デザイン出荷物 — 散文を減らし、出荷物を増やす（完了 2026-09-17）

計画: `spec/12-design-framework.md`（DS-1〜DS-6、受け入れ条件 A-1〜A-4）。判断軸は「Sonnet に書かせず、読ませる形になっているか」。

- [x] `templates/ui/components.css`（S9、DS-1）: SKILL.md の CSS 17 ブロックを `var(--*)` だけで実体化。直値解消のため `tokens.css` に `--color-medium-text` / `--color-scrim` / `--color-tooltip-bg/-text` / `--color-knob` を追加。`demo.html` を読み込み形式に変更
- [x] `templates/ui/layout.css`（S10、DS-2）: `.app` 骨格（globalbar / sidebar 折りたたみ・off-canvas / topbar / content）と `.layout-2pane`、ブレークポイント 1366 / 768 / 360。`demo-shell.html` を追加し Playwright でライト／ダーク／360px／1920px を確認
- [x] `scripts/check_design.py` + `check-design.sh` + `test-check-design.sh`（S11、DS-4、36 ケース）: 直値・未定義トークン・未使用トークン(WARN)・外部 CDN・`alert()`・`tokens.css` 未読込。`kit-ci.yml` に追加。`feedback.js` の `::backdrop` 直値を検出→是正（赤→緑を確認）
- [x] フレームワーク別の出荷物（S12、DS-3）: `tailwind.config.js` / `streamlit-config.toml` / `streamlit_theme.py` / `templates/ui/README.md`（1枚表）。`references/frameworks.md` は 47→36 行の導線に
- [x] `skills/design-system/SKILL.md` を 473 → 115 行（S13、DS-5、F-04）: 値の唯一の真実源を `templates/tokens.css` に一本化（Q-9）。`references/tokens.md`（理由）/ `references/components.md`（使い分けと落とし穴・実不具合 7 件を保持）。`check_docs.py` 検査7を NG に昇格
- [x] `templates/design-system.md` のチェックリストに機械 5 / 目視 9 の別（S14、DS-6）
- [x] `docs/lessons.md` 新設（S15、B-05、F-05）: 本セッションが最初のエントリ。`export-project.sh` に `block-explore.sh` を配線し `/implement` の非対称を解消（B-06、F-08、Q-3）。`test-install.sh` 73 ケース
- 検証記録: test-check-design 36/36・test-install 73/73・test-check-docs 25/25・`check-design.sh` NG=0（WARN 6: 未使用トークン `--color-medium` `--leading-loose` `--motion-slow` `--radius-xl` `--shadow-md` `--shadow-lg`）・`check-docs.sh` NG=0 WARN=0
- 残: A-4（`design-system` 発火時コストが半分以下）は保守者が `/context` で実測（推定: 473→115 行なので 1/4 程度）

## M18: 工程承認ゲート — 要求どおり作られているかを工程ごとに止めて確かめる（完了 2026-09-19）

背景: AIDD では「プロセスが回っているか」を見ても、企業が知りたい「**SDD で要求したものが確実に作られているか**」には答えられない。
誤りが成果物として出てから見つかると手戻りが最大になる。調査の結果、承認欄は 10 工程中 3 つにしか無く（F-17）、
承認という概念を機械が一切知らなかった（F-18）。保守者決定は Q-11（hook で物理的に止める／AI レビューは 3 役を順次）。

- [x] 承認記録の雛形と配置（S16）: `templates/lifecycle/approvals/{phase-approval.md,README.md}`。`init-lifecycle.sh` が `phase-0..9.md` を工程名・covers を差し込んで生成
- [x] `scripts/phase-hash.py`（S17）: 承認を版に縛る。対象0件は `empty`（対象なしを「一致」にしない）。`ui-hash.py` は UI 専用版として据え置き
- [x] `scripts/check-approval.sh` ＋ `check_approval.py` ＋ `test-check-approval.sh`（S18、20 ケース 54 アサーション）: exit 0/1/2 の 3 値契約、判定不能を合格に数えない、工程順序の検出（省略された工程は飛ばす）。`covers` に追跡表を入れない設計へ修正（F-19）
- [x] `claude-code/hooks/block-phase.py`（S19）: `.claude/phase-gate` オプトイン。未承認・失効・判定不能で deny、承認済み工程の成果物の書き換えも deny、`approvals/` は常に許可、バイパス用の環境変数は作らない。settings.json / export-project.sh / install.sh に配線
- [x] `skills/phase-approval` ＋ `/phase-review`（S20）: 3 役を**順次**（追跡・仕様一致・リスク）。Agent 並列はトークン約 7 倍で使わない。AI は `approver` を埋めない
- [x] 既存資産への配線（S21）: 全 10 工程テンプレートに「## 承認」節、`phase-gates.md` に承認ゲート節と機械／人間の境界表、共通出口基準 3→4、`dev-lifecycle/SKILL.md`・`/lifecycle`・`done-gate`・`verify.sh`・`kit-ci.yml`
- [x] 文書化（S22）: `docs/userguide.html` に「工程の承認ゲート」章（実測した deny メッセージ付き）、PRD FR-14、`spec/09` F-17〜F-19、`spec/10` Q-11
- 検証記録: test-hooks 32/32・test-install 79/79・test-check-approval 54/54・test-trace-check 15/15・test-quality-harness 11/11・test-git-gates 27/27・test-check-docs 25/25・test-check-design 44/44・`check-docs.sh` NG=0・`check-design.sh` NG=0。配布した実プロジェクトで「未承認→deny／承認→許可／成果物の変更→失効→再び deny」を端から端まで確認
- 残: 実プロジェクトで 1 工程を実際に承認し、deny の false positive 頻度を `docs/lessons.md` に記録する（保守者）

## M19: トークン節約を仕組みに — 散文を hook・設定・検査へ（完了 2026-09-19）

背景: 節約策のうち機械が強制していたのは 3 つだけで、残りは AI が自分で読んで自分で守る散文だった（F-20）。
公式の削減策「hook で前処理してから渡す」は未活用（B-15）。保守者決定は Q-12（既定 ON・effort high・再開は警告・Read 切り詰め）。

- [x] `filter-output.py`（S23、B-15）: テスト→失敗行＋集計、install/build→末尾 40 行、git log→-20、git diff→--stat。終了コード保持。`FULL_OUTPUT=1` で全量。自分の回帰テストは絞られない
- [x] `pre-read-guard.py`（S24）: ロックファイル・minified・node_modules・生成レポートを deny。800 行超は先頭 300 行＋続きの読み方を systemMessage で
- [x] `context-guard.py` / `pre-compact.py` / `log-instructions.py`（S25）: 55 分超の再開・4 MB 超で `/clear` `/compact` を促す（止めない）／圧縮の残す・捨てる／指示ファイルの実ロードを記録
- [x] settings 3 キー（S26）: `effortLevel: high` / `autoCompactWindow: 200k` / `BASH_MAX_OUTPUT_LENGTH: 12000`。キット本体・export の両方
- [x] `token-audit.sh` ＋ `check-docs.sh` 検査 9（S27）: 床の推定・実測ログ集計・配線・MCP 数・スキル肥大。CLAUDE+AGENTS ≦ 200 行。`/token-check` を書き換え
- [x] 散文の置き換え（S28）: CLAUDE.md.template / model-routing / speed-harness H-7 / context-compression / rules-rationale。rules 87 行 ≦ 100
- [x] 文書化（S29）: userguide「トークンを減らす仕組み」章（実測の systemMessage 付き）、PRD FR-15、spec/09 F-20・F-21、spec/10 Q-12、spec/11 §2 更新
- 検証記録: test-hooks 63/63・test-install 82/82・test-check-docs 27/27・test-token-audit 12/12・他 5 スイート PASS・`check-docs.sh` NG=0・`token-audit.sh` NG=0（床 ≒ 6,200 tok 推定）。偽の pytest で「102 行 → 7 行、exit 1 保持」を実測
- 残: 移行後 1 週間の `/usage`・`/context` 実測で `READ_GUARD_MAX_LINES` / `CONTEXT_GUARD_IDLE_MIN` / `effortLevel` の既定を見直す（保守者）。F-21（警告 hook の stdout）の確認

## M20: テスト工程のメトリクス — 表を埋めれば機械が数える（完了 2026-09-19）

背景: 保守者（QA・外部結合〜受入担当）の最初の優先事項。実行記録が機械可読でなく、進捗・品質を目視で数えていた（F-22）。
保守者決定は Q-13（記録は工程文書の表・CSV も対象・基準は §7・status と gate を分ける）。

- [x] 記録の形式（S30）: 05〜08 のテスト表に実施日・実施者、欠陥表に起票日、結果の語彙を固定。CSV に 4 列。§7 を機械が読める表（しきい値＋出典）に。完了報告書に metrics:begin/end
- [x] `test-metrics.sh` ＋ `test_metrics.py` ＋ `test-test-metrics.sh`（S31、10 ケース 40 アサーション）: レベル別＋全体の指標、検知（unread / severe / stale / bias / duplicate / forecast）、status（常に 0）/ `--gate`（0/1/2）/ `--history` / `--into`
- [x] 配線（S32）: `/test-metrics`、`/lifecycle status`、done-gate、phase-approval 役 3、test-strategy「測る」、test-levels の語彙表、CI（手動）、INDEX / README。test-install のスキル・コマンド個数をリポジトリ実体から導出
- [x] 事例で実測（S33）: 図書館貸出の ST 8 / UAT 5 / DEF 3 で status → history × 2 → gate → into を端から端まで。配布スクリプトの同梱漏れ（F-23）を検出して是正
- [x] 文書化（S34）: userguide「テストの進みと品質を数字で見る」章（実測付き）、PRD FR-16、spec/09 F-22・F-23、spec/10 Q-13
- 検証記録: test-test-metrics 40/40・test-install 84/84・test-trace-check 15/15・test-check-approval 54/54・他 6 スイート PASS・`check-docs.sh` NG=0
- 残: 単体テストの結果 XML からの自動転記（`filter-output.py` の集計行から）、Jira / Excel 取り込み（qa-autopilot の mapping 方式）は次の計画

## M21: 保守者の傾向を規約・検査に反映（完了 2026-09-19）

背景: 保守者「他のリポジトリの記録も含め、私の指摘や要望の傾向を分析し、キットに反映して」。
本セッションの 30 通と qa-autopilot（CLAUDE.md・constitution・PROMPT_FOR_CODEX・IA_DECISION・plan_0909）・
istqb_genai_study・qa_viewpoint の記録から 14 の傾向を抽出（`docs/maintainer-tendencies.md`）。

- [x] `rules/absolute-rules.md` に A-11 止まらない（手段が塞がれたら代替を 1 つ取る）・A-12 基準を緩めない（3 回連続失敗で止まる）。rules 89 行 ≦ 100
- [x] `AGENTS.md.template`: 報告の型 4 項目（感想・自己評価を書かない）、損益の判断軸と「委ねられたら実行まで」、厳しい評価、利用者向け文言の規約、禁止事項（自動起動・stash/reset/clean・依頼なしのコミット）
- [x] `/plan`: 見積（分）・推奨モデル・トークン節約を必須項目に
- [x] `check-docs.sh` 検査 10: 「スキル N・コマンド N・hooks N」の直値を実数と突合（WARN）。導入直後に userguide の hooks 7（実数 13）を検出
- [x] `docs/rules-rationale/absolute-rules.md` に A-11 / A-12 の出所と「準拠」の扱い
- 検証記録: test-check-docs 29/29・test-install 84/84・`check-docs.sh` NG=0
- 運用: 同じ指摘を 2 回受けたら `maintainer-tendencies.md` に行を足し、反映先（hook / 検査 → rules → AGENTS → スキル）を決める。散文に書いて終わりにしない

### M21 第 2 回（同日。保守者「やはり浅すぎる」を受けて深掘り）

未読だった qa-autopilot の `harness/loop.md`・HANDOVER・VERIFICATION_REPORT（30 ペルソナ）・WORK_ORDER・personas・standards・specs/006 と
キット自身の OPERATING-MODE・Vision・AUDIT を読み、**実装者に課している手順の型** 16 傾向（#15〜#30）を追加。反映先は rules でなく手順が走る場所（Q-15）。

- [x] `rules/speed-harness.md` H-1 を 4 行に（`終了条件:`）。A-12 の出力を「止まる報告 5 項目」に。rules 90 行 ≦ 100
- [x] `/plan`: 着手前の 5 つの質問（答えられなければ `/implement` に入らない）と `templates/work-order.md` への導線
- [x] `templates/implement-profile.md` 止まる条件表／`templates/work-order.md`（新規: 守ること表・Step 完了条件・止まる条件・質問節）
- [x] `templates/CURRENT_STATE.md` に決まっていること・未検証（項目／確かめ方）・次にやるなら・最初の 5 分／`templates/ADR-template.md` に判断基準（規格名）と捨てた案
- [x] `skills/qa-review-standards/references/personas.md`（16 ペルソナ・判定一覧の型・順次）＋ SKILL の多ペルソナ検証・準拠の主張範囲、`/qa-review` 手順 6
- [x] `skills/done-gate`: 受入基準を検証するテストだけを PASS に数える・0 件実行・未検証の確かめ方。`AGENTS.md.template` 完了条件・報告の型 ③（分と往復数）
- [x] `skills/design-system`: 並びは利用者の目的順。`skills/retro`: 反映候補は Vision の 3 基準に照らす
- [x] `check-docs.sh` 検査 11: 利用者向け文書・雛形の絶対パス（WARN）。userguide の `/Users/you/...` 5 箇所を修正
- 検証記録: test-hooks 63 / trace-check 15 / quality-harness 11 / install 84 / git-gates 27 / check-docs 32 / check-design 44 / check-approval 54 / token-audit 12 / test-metrics 40 すべて PASS・`check-docs.sh` NG=0 WARN=0
- 残: 検査 11 は WARN（配布先の文書は対象外）。`/qa-review` のペルソナ順次実行を実プロジェクトで 1 回回して所要往復数を `docs/lessons.md` に記録する

## 完了の定義（全マイルストーン共通）

`skills/done-gate/SKILL.md` の全種別共通チェックに加え、本キット固有の条件: ①verify.sh NG=0 ②真実源の重複を新設していない ③本ファイルのチェック状態を更新済み ④`./scripts/check-docs.sh` NG=0（M15 以降）⑤`spec/` を同じコミットで更新済み。

## M22: 指示優先を hook で強制（完了 2026-09-19）

背景: 作業中に届いた保守者の指示を読み飛ばし、英語で途中報告を続けた（`spec/09` F-25、Critical）。保守者「仕組みで改善しなさい」。

- [x] `rules/absolute-rules.md` A-13 指示優先（指示 ＞ 計画 ＞ 自分の規範）。rules 91 行 ≦ 100
- [x] `claude-code/hooks/instruction-guard.py`（PreToolUse 全ツール）: transcript 末尾を後ろから走査。発言の後に日本語の応答が無ければ deny、理由に指示の先頭。サブエージェント・機械由来タグ・transcript 無しは fail-open
- [x] `reply-language.py`（Stop、判定を共有）／`prompt-priority.py`（UserPromptSubmit、緊急語に注入）
- [x] 配線: `claude-code/hooks/settings.json`・`export-project.sh` ヒアドキュメント・キット自身の `.claude/settings.json`（`$CLAUDE_PROJECT_DIR` 参照）
- [x] `test-hooks.sh` 16 ケース追加（63 → 79）。本セッションの実 transcript の応答前断面で deny・応答後で許可を確認
- [x] `AGENTS.md.template` 必須プロセス・`CLAUDE.md.template` hooks 一覧・INDEX・spec/01・spec/09 F-25・spec/10 Q-16・PRD FR-17・`maintainer-tendencies.md` #31
- 残: Codex には hook が無い。`AGENTS.md` の散文のみ（移行後の実測 U-5 で見直す）

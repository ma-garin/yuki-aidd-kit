# D3-supply-chain 供給網（ソフトウェアサプライチェーン）: 段1 広域調査

- 対象: `.github/workflows/kit-ci.yml`、`02_共通/ひな形/github/workflows/*.yml`（4 本）、`00_導入/` 配下のスクリプトと `external-skills.json`、`.claude-plugin/`（plugin.json・marketplace.json・hooks.json）、`03_ClaudeCode/hooks/`・`02_共通/ツール/` の外部取得、依存宣言ファイル
- 調べた方法: `git ls-files` で対象の列挙、`git grep -nE`（`uses:`・`permissions:`・`curl|wget|npx|pip install|uvx|git clone|npm i|brew install`・`urlopen|requests.|https://`）、`external-skills.json` を python で集計、`doctor.py` D9 と `block-deps.py`・`verify.sh` の該当部の読み取り。Web は参照していない。CI・テスト・依存導入は実行していない。
- 調べた件数/全件数: workflow 5/5 本（kit-ci.yml＋ひな形 4 本。`uses:` と `permissions:` は全件、本文は kit-ci.yml・secret-scan.yml・test-gates.yml の該当部のみ）、plugin 定義 3/3、external-skills.json 54/54 件、導入スクリプト `00_導入/**/*.sh` の外部取得 grep は全件、hook の外部通信 grep は `03_ClaudeCode/hooks/*.py|*.sh` 全件
- 実行環境: 対象コミット 3ef90fd（origin/main）の作業ツリー（`scratchpad/kit-audit`）。macOS。読み取りのみ。
- 照合した外部基準: SLSA v1.0（Build L1 の来歴・Source の版固定）、OpenSSF Scorecard の Pinned-Dependencies・Token-Permissions・Dependency-Update-Tool・Security-Policy・Signed-Releases・Binary-Artifacts の各項目

## 全体所見（事実）
- 外部から取得する経路は 4 つ: ①`npx skills add`（external-skills.json の 15 件に install 行）②`/plugin marketplace add`・`git clone`（README.md:17・24）③ひな形 workflow の `uses:`・`pip install`・`npm ci` ④利用者環境の gitleaks（コマンドの有無だけ）。hook・導入スクリプト（`install.sh` 等）から `curl|wget|uvx|brew install` は検出されなかった（grep 0 件。`verify.sh` の検出パターンとしての出現を除く）。
- 依存宣言ファイルは kit 本体に無い（`git ls-files | grep -iE 'requirements|pyproject'` → ひな形の `01-requirements.md` のみ）。lock・checksum・dependabot・SECURITY.md・署名・SBOM のいずれも `git ls-files` に無い。

---

## D3-supply-chain-01 外部スキルの導入が無固定の `npx skills add`。登録した hash は導入時に使われない
- 種別: 欠陥（版固定・完全性検証の欠落）
- 深刻度: High
- 根拠: `00_導入/01_インストール/external-skills.json` の install 行は 15 件すべて `npx skills add <owner/repo> -g --skill <名>` で、版・コミット・ref の指定が無い（例 :30, :154, :593）。`remoteHeadAtRegistration` は注記に「導入時点のコミットではない」と明記（:3）。`sha256` は `doctor.py:240-244`（D9）が導入「後」の実体と突き合わせる WARN のみで、導入「前」の検証・取得元の固定には使われない（doctor.py は D9 を差分すべて WARN と宣言: :21）。導入元の上位は heygen-com/hyperframes 9 件・obra/superpowers 2 件など外部 6 リポジトリ（python 集計）。
- 状態: 実証（grep と集計）。`npx skills add` が実際に最新 HEAD を取る挙動は未確認（`--help` を実行していない）。
- 改善の方向: install 行に `owner/repo#<コミット SHA>` 等の固定、または導入後に sha256 不一致を NG にする。SLSA の「版固定された入力」、Scorecard Pinned-Dependencies に相当。

## D3-supply-chain-02 plugin / clone の配布元が無固定で、利用者は常に最新の main を信頼する
- 種別: 欠陥（配布物の来歴・版固定）
- 深刻度: Medium
- 根拠: `README.md:17-18` `/plugin marketplace add ma-garin/yuki-aidd-kit`、`:24` `git clone https://github.com/ma-garin/yuki-aidd-kit`（タグ・SHA 指定なし）。`.claude-plugin/marketplace.json` の plugins[0] は `"source": "./"` で ref・sha 無し。git タグ・署名・リリース成果物・チェックサムの掲載は無い（`ls-files` に署名・SHA256 系ファイル 0 件）。導入物は hook（任意コマンド実行）を含む（`.claude-plugin/hooks.json`）。
- 状態: 実証。Claude Code 側が marketplace の ref を解決する仕様の詳細は未確認。
- 改善の方向: README の導入手順にタグ固定（`@v8.7.0` 等）と、タグへの署名・リリースノートでの SHA 掲載。Scorecard Signed-Releases・SLSA Provenance 相当。既存 S2-cc-plugins-01（版固定で更新が届かない）とは逆向きの論点（固定が無いこと）で別件。

## D3-supply-chain-03 gitleaks-action がタグ参照。他者製サードパーティ action で、トークンを渡す
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `02_共通/ひな形/github/workflows/secret-scan.yml:21` `gitleaks/gitleaks-action@v2`（GitHub 公式でない他者製）、`:23` `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` を env に渡す。同ファイルに `permissions:` 無し。タグは作者側で付け替え可能。ひな形は配布先プロジェクトへ複製されるため、固定されない参照が各プロジェクトに広がる。
- 状態: 実証（grep）。
- 改善の方向: コミット SHA 固定＋`permissions: contents: read`。Scorecard Pinned-Dependencies・Token-Permissions。公式 action（checkout 等）の固定は Low だが、サードパーティは優先度が上。

## D3-supply-chain-04 workflow の `permissions:` が 5 本中 4 本に無い（既存 I4-ci-13 を配布ひな形へ拡張）
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `git grep 'permissions:' -- '*.yml'` の一致は `02_共通/ひな形/github/workflows/deploy.yml:12` の 1 件のみ。kit-ci.yml・lifecycle-check.yml・secret-scan.yml・test-gates.yml は無指定 → リポジトリ既定のトークン権限（設定次第で書き込み可）になる。kit-ci.yml の同指摘は既存 I4-ci-13 と同じ。ここでの新規性は、配布ひな形 3 本（lifecycle-check・secret-scan・test-gates）にも無く、配布先へ複製される点。いずれも `workflow_dispatch` のみ起動（kit-ci.yml:12-13、secret-scan.yml:10-11、test-gates.yml:10-11）なので露出は限定的。
- 状態: 実証。
- 改善の方向: 各ひな形に `permissions: contents: read` を既定で入れる。I4-ci-13 の修正と同じ PR で扱う。

## D3-supply-chain-05 全 workflow の `uses:` がタグ参照（SHA 固定 0 件）。既存 I4-ci-13 の件数による補強
- 種別: 欠陥
- 深刻度: Low
- 根拠: `git grep -nE 'uses:' -- '*.yml'` で一致 21 行（うち test-gates.yml:67・70 はコメント内）。40 桁 SHA 固定は 0 件。`actions/checkout@v4`・`setup-python@v5`・`upload-artifact@v4`・`setup-node@v4`・`configure-pages@v5`・`upload-pages-artifact@v3`・`deploy-pages@v4`。公式 `actions/*` に限る（サードパーティは D3-supply-chain-03 に分離）。
- 状態: 実証。
- 改善の方向: SHA 固定＋コメントで版を併記。Dependabot の github-actions 更新（D3-supply-chain-08）と組み合わせる。

## D3-supply-chain-06 ひな形 test-gates.yml が無固定の pip install と `|| true`で、失敗も握りつぶす
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `02_共通/ひな形/github/workflows/test-gates.yml:39-43` `python -m pip install --upgrade pip` ・`pip install pytest pytest-cov`（版指定なし）・`pip install -e . 2>/dev/null || true`（導入失敗を無視して先へ進む）。`--require-hashes`・lock 利用なし。`:55` の `npm ci` は lock があれば固定される（lock の存在確認は無い）。
- 状態: 実証（読み取り）。`npm ci` の lock 存在チェックは `:47-55` 近辺を全読していないため未確認。
- 改善の方向: pytest 等の版固定、`|| true` を外す（失敗を赤にする）。A-12「基準を緩めない」との整合も要確認。

## D3-supply-chain-07 外部スキルの出所が 39/54 件で不明（tracked=false）なのに、導入方法・取得元が無い
- 種別: 欠陥（来歴不明）
- 深刻度: Medium
- 根拠: python 集計: `tracked` が True 15 件・False 39 件、`install` 行が無い（`source` も無い）のが 39 件。注記（:3）は「tracked=false は ~/.agents/.skill-lock.json に記録が無いもので、出所は未確認（推測で埋めない）」と自認。これらは doctor D9 で sha256 一致を見るだけで、再導入や出所確認の手段が無い。ECC・superpowers 等の取り込み元の版（コミット）も、導入物としては `remoteHeadAtRegistration` が参考値だけ。
- 状態: 実証（集計）。39 件のうち中身が外部由来かは未確認（自作・kit 由来を含む可能性）。
- 改善の方向: 出所不明は「自作」「外部」「不明」に分類し、外部は取得元とコミットを必須項目にする。SLSA の「来歴（provenance）」相当。

## D3-supply-chain-08 依存更新の自動検出・脆弱性報告窓口・依存宣言が無い
- 種別: 欠落
- 深刻度: Low
- 根拠: `git ls-files | grep -iE 'dependabot|SECURITY|requirements|pyproject|package|\.lock'` → ひな形の `01-requirements.md` 以外 0 件（SECURITY.md・dependabot.yml なし）。kit 自体は標準ライブラリ中心で依存宣言が無く、これは設計上の長所でもある（未検証: 全 `*.py` の import を未集計）。`03_ClaudeCode/hooks/block-deps.py` は AI による新規依存追加を人の承認待ちにするが、これは「追加の関門」であり、既存の取得元の更新追跡や脆弱性窓口の代わりにならない。
- 状態: 実証（ファイル無し）。
- 改善の方向: SECURITY.md（報告窓口）と、workflow 用の Dependabot（github-actions のみで足りる）。Scorecard Security-Policy・Dependency-Update-Tool。

## D3-supply-chain-09 配布ひな形の gitleaks 利用: コマンドの有無だけで版・取得元を見ない
- 種別: 欠陥
- 深刻度: Low
- 根拠: `02_共通/ツール/pre-commit:4-6` は `command -v gitleaks` なら実行、無ければ簡易パターンにフォールバック（既存 I4-ci-07・I4-ci-12 と同系統）。ここでの新規点は、利用する gitleaks の版・取得元・完全性を何も確かめない点（PATH 上の同名コマンドを信頼する）。
- 状態: 実証（読み取り）。PATH 上書き攻撃の実行可能性は未再現。
- 改善の方向: 優先度は低い。PATH の信頼は環境前提と明記する程度でよい。

## D3-supply-chain-10 検査の死角: `verify.sh` の取得物監査は settings の hook / MCP だけで、kit 自身の導入経路を見ない
- 種別: 観測（良い点を含む）
- 深刻度: Low
- 根拠: `00_導入/01_インストール/verify.sh:98-101,183,193` は利用者設定の hook command の `curl|sh` と MCP の `npx -y`（@scope なし）を検出する。良い点: kit の hook 自体は外部通信しない（`03_ClaudeCode/hooks/` の `urlopen|requests.|curl|wget` grep で実行コードの一致 0 件、一致はコメント・検出パターンのみ。`https://` の数件は文字列リテラルとして目視していない: 未検証）。一方 `npx skills add`（D3-supply-chain-01）は同種の「取得して実行」だが検査対象外。
- 状態: 実証（grep）。
- 改善の方向: `npx skills add` 経路も verify の監査に含め、固定の有無を WARN にする。

## D3-supply-chain-11 plugin.json に依存・最低版・hash の宣言が無い（既存 S2-cc-plugins-14 と同じ）
- 種別: 既存 ID と同じ
- 深刻度: Low
- 根拠: 既存 S2-cc-plugins-14 と同じ（`.claude-plugin/plugin.json` に dependencies・engines 無し）。新しい番号の発見ではないため詳細は書かない。

## D3-supply-chain-12 plugin と install.sh の二重導入で hook が二重に動く（既存 S2-cc-plugins-03・D1-distribution-08 と同じ）
- 種別: 既存 ID と同じ
- 深刻度: —
- 根拠: 既存 ID と同じ。供給網の観点（二重に入ると取得元が 2 つになる）の付加価値は無いため再掲しない。

---

## 調べなかったこと
- `npx skills add` が実際に何を取得するか（版・ref の扱い）。`--help` を実行していない（外部ツールの実行を避けた）
- GitHub 側の設定（ブランチ保護・Actions のトークン既定権限・Dependabot alerts・secret scanning の有効化）。`gh api` を叩いていない
- 配布先プロジェクトに複製された後のひな形の実態、lifecycle-check.yml と deploy.yml の本文の全読
- 全 `*.py` の import 一覧（標準ライブラリ以外への暗黙依存）、`06_保守者向け/03_回帰テスト/` のテストが取得する外部物
- 04_Codex 側の導入手順（`04_Codex/` 配下の install 系）と ECC・superpowers を別経路（`~/.claude/plugins`）で入れた場合の固定
- `docs/` 配下の過去の調査文書内の取得コマンド（実行物ではないため除外）
- 外部 6 リポジトリ自体の信頼性・権限の実査（Web 未参照）

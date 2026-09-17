# 06 — templates（36件）と github-actions（4件）

配置スクリプトとの対応:
`init-lifecycle.sh` → `lifecycle/` + `github/`／`init-test-docs.sh` → `test/` + ゲートスクリプト／
`export-project.sh` → `templates/` 全体を `.claude/templates/` へ／`init-project.sh` → `CURRENT_STATE.md`

---

## 1. 単体テンプレート（7件）

### `tokens.css`（107行）— デザイントークンの実物

`skills/design-system/SKILL.md` を真実源として実体化したもの。**値を変えるときはスキル側を先に直す。**

| 群 | 変数 | 要点 |
|---|---|---|
| 色: 基調 | `--color-primary/-light/-dark/-on-primary`, `--color-bg`, `--color-surface/-2/-3`, `--color-border/-strong`, `--color-divider`, `--color-text/-secondary/-disabled` | `--color-on-primary` が無いと「直値禁止」を白に対して守れない、という理由つき |
| 色: 状態 | `--color-{critical,high,medium,low,info}` ＋ `-bg` ＋ **`-border`** | ISTQB severity と対応。重大度と結果の伝達にだけ使う |
| 書体 | `--font-main` / `--font-mono` | 既定はシステムフォントスタック。CDN は任意強化 |
| 文字サイズ | `--text-xs`〜`--text-2xl`（7段）＋ `--leading-*` ＋ **`--text-measure: 68ch`** | 段の間は2px 以上（1px 差は「別の役割」と読まれない） |
| 余白 | `--space-1..12`（4px 倍数。5=20px を含む） | — |
| 角丸 | `--radius-sm/md/lg/xl/full` | 内側は外側より小さく |
| 影 | `--shadow-sm/md/lg` ＋ **`--shadow-pop`** | 影で語らずボーダーで区切る。影は浮かせる要素だけ |
| 動き | `--motion-fast/normal/slow`（.12/.2/.3s） | — |
| 触れる大きさ | `--tap-min: 44px` | — |

**ダーク対応**: `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }` と
`:root[data-theme="dark"]` の**両方**に同じ値を書く（メディアクエリだけでは明示切替ができない）。

**基本適用の最小セット**も持つ: `html{color-scheme:light dark}` / `body` の背景・文字・書体・行間 /
`code,pre,kbd,.mono` / `button,a,[role=button]` に `--tap-min` / `prefers-reduced-motion` で
`transition-duration` と `animation-duration` を 0 に。

**出所**: kit design-system（MD3 Light）＋ WebSpec2Doc `static/tokens.css`（on-primary / surface-3 / border-strong / severity-border / motion）＋ UX_Auto_Reviewer `style.css`（本文幅・reduced-motion）。

### `design-system.md`（83行）— 視覚的指示書

コードを一切見なくても同じ見た目を再現するための言語化。**値は再定義せず `skills/design-system` を参照**（AUDIT D-02 対応）。

- **全パターン共通の文法6条**: 地と図（薄グレー背景＋白カード＋1px ボーダー＋弱い影）/ 角丸は小さい部品ほど小さく / 余白は4px 倍数のみ / **色の禁欲**（プライマリ＋ステータス色＋グレー階調以外を持ち込まない）/ タッチターゲット44px / 日本語 UI（行間1.7・英数字は等幅）
- **パターン1 Web アプリ**: 2ペイン（240px サイドナビ）。SaaS 型はサイドバーを画面最上部から独立 / 見出しレベルは3段まで / **塗りボタンは1画面に1つだけ** / カードグリッド最小300px / alert ダイアログを使わない
- **パターン2 HTML スライド**: 1スライド1メッセージ / 16:9 / 左右余白8%・上下10% / 本文の型は3種のみ（箇条書き最大5点 / 比較表 / 図解）/ 基本はグレー階調＋プライマリ1色 / 背景色付きスライド禁止
- **パターン3 管理画面**: KPI カード列（3〜5枚）→フィルタ行→テーブル / 罫線は横線のみ・数値は右揃え等幅 / 表示件数可変（5/10/30/50/100/すべて）/ 情報密度を1段高く / **KPI カードへの背景色塗り禁止**
- **適用除外**: `docs/yuki-aidd-kit-manual.html` のような**読み物ページは3パターンの対象外**（Qiita 風・緑系アクセント。意図的な別ジャンル）
- **再現チェックリスト10項目**: プライマリの用途 / 書体の使い分け / 塗りボタン1つ / 4px 倍数 / 360px / スキル変数との一致 / **CSS に直値が残っていない** / 全操作に結果が返る / 文言規約 / アイコン同梱

### `settings.sandbox.json`（83行）

- `sandbox.enabled: true` / `allowUnsandboxedCommands: false`（脱出口封鎖）
- `filesystem.denyRead`: `~/.aws/credentials` `~/.aws/config` `~/.ssh` `~/.gnupg` `~/.config/gh/hosts.yml` `~/.netrc`
- `network.allowedDomains`: github.com / api.github.com / registry.npmjs.org / pypi.org / files.pythonhosted.org（ホワイトリスト方式）
- `permissions.allow`: npm/vite/git/grep/find/ls/mkdir/wc の定型（プロンプト削減）
- `permissions.deny`: `git push --force*` 4パターン / `git reset --hard*` / `git clean -f*` / `git checkout -- .` / `git branch -D *` / `rm -rf *` / `curl *` / `wget *` / `chmod 777` / `sudo *` / `eval *` / `nc *` / `Read(./.env*)` / `Read(**/*.pem|*.key|*credentials*|*secret*)`
- 出所 my-forward（2026-08）。**deny は最優先で Always allow でも上書き不可**とコメントに明記

### `CURRENT_STATE.md`（41行）/ `ADR-template.md`（28行）/ `lessons.md`（34行）/ `implement-profile.md`（21行）

| ファイル | 記録するもの | 混同してはいけない相手 |
|---|---|---|
| `CURRENT_STATE.md` | 今どこまで進んだか（フェーズ・直近完了・次タスク・判断待ち・既知の問題・設計決定メモ）＋セッション開始時の指示テンプレート | ADR / lessons |
| `ADR-template.md` | なぜその設計にしたか（背景・選択肢比較表・決定・結果影響・関連） | CURRENT_STATE / lessons |
| `lessons.md` | **AIDD の進め方の知見**（Keep/Problem/Try、1エントリ3-5行）。記入例がコメントで同梱 | CURRENT_STATE / ADR |
| `implement-profile.md` | 実装モードの行動規範（再探索しない・plan 準拠・小さく実装→軽量テスト・done-gate・逸脱時の4手順） | — |

**`lessons.md` は現在エントリ0件**（雛形のまま）。Vision の到達点③「自己改善ループ」が未稼働である証拠。

---

## 2. `lifecycle/`（11件・587行）

`dev-lifecycle` の成果物雛形。**`init-lifecycle.sh` 直後に `trace-check.sh` が NG=0 を返すことが回帰テストで保証されている**（`test-trace-check.sh` ケース4）。
未採番のプレースホルダは `-0xx` 表記にしてあり、3桁連番に置き換えるまで検査対象外になる設計。

| ファイル | 特徴的な要求 |
|---|---|
| `00-rfd.md` | 選択肢表に **C「何もしない」の行が最初から入っている** / 決定＋却下理由 / スコープ外 / 未解決の論点 / **承認欄（人間）** |
| `01-requirements.md` | REQ-F は MoSCoW ＋**観測可能な受入基準**（×「使いやすい」○「3タップ以内で保存でき、リロード後もデータが残る」）/ REQ-N は 25010 分類＋**測定条件つき判定基準** / 「AかつB」は2要件に分割 / **承認欄** |
| `02-basic-design.md` | 全 REQ-F を BD に割り当て（未割当ゼロ）/ 画面の視覚仕様は design-system 参照で**値を書き写さない** / データモデル（version・マイグレーション・export 範囲）/ 外部 I/F の失敗時挙動 / 技術選定の比較表 |
| `03-detailed-design.md` | DD ごとに入出力表・処理手順・事前事後条件・**異常系**（入力不正/外部失敗/容量超過）・**境界値**（下限/上限/0件空）・状態遷移。*「異常系」「境界値」の2節は UT の入力に直結するため省略しない* |
| `04-implementation.md` | T 表（対応 DD・依存・コミット/PR）/ 作業ログに **設計からの逸脱と逆同期の済/未** / 検証結果は「動作確認した」でなく**実行コマンドと出力** / 秘密情報チェック |
| `05-unit-test.md` | **正常系・異常系・境界値の3区分を各 DD に1件以上** / 外部依存はモック化 / 実行結果 evidence（pass/fail/skip 件数）/ 「実装に合わせて期待値を緩めていない」の出口確認 |
| `06-integration-test.md` | 必須観点5（I/F 契約・順序と状態・外部 I/F の失敗・**FedEx Tour のデータライフサイクル**・永続化とマイグレーション）/ **モックは外部サービス境界まで** |
| `07-system-test.md` | **実測値必須**（「速い」は不合格の書き方）/ 観点6（性能・デバイス・信頼性・セキュリティ・a11y・長時間稼働）/ severity と priority を混同しない |
| `08-acceptance-test.md` | **業務シナリオ単位**で通し / 受入基準の文言をそのまま手順に（書き換えられないなら要件定義へ差し戻す）/ 探索的テスト1周（Money / Saboteur）/ 不合格項目は「修正/次リリース/受容」を必ず決める / **承認欄** |
| `09-operations.md` | 稼働環境 / 監視 OPS（**異常の判断基準＝しきい値**）/ 変更・ロールバック手順（**1度実行して確認済みのチェック欄**）/ 障害一次切り分け表 / 既知の制約（ST・UAT からの引き継ぎ）/ 定期作業 / **引き継ぎ時に読む順序** |
| `traceability-matrix.md` | 記入規則: カンマ区切り併記 / **空欄禁止・非該当は `-`** / REQ-F は UAT 必須・REQ-N は ST 必須 / 状態5値。REQ-F 表・REQ-N 表・DEF 追跡・OPS 引き継ぎの4表 |

---

## 3. `test/`（8件・435行）

| ファイル | 要点 |
|---|---|
| `TESTING_STRATEGY.md` | §2 レベル表（L1 カバレッジ80%・L3 は `.ui-verified` 生成が UI コミットの前提・L4 は**初見・マニュアルなし**）／§3 種類マトリクス／**§4 ゲートの実行タイミング（本書内で最優先）**／§5 ツールチェーン／§6 L4 シナリオ3件／§7 完了基準5項目／§8 リスク4件／§9 改訂ルール |
| `DEFINITION_OF_DONE.md` | 冒頭に「**pytest 全 PASS は完了ではない**」／「ゲートの実行タイミング（本書内で最優先）」で**各所の『スキップ不可』はマイルストーン時点の要求として読む**と明示／Type A・**Type B ★**・Type C／Type B の PROHIBITED 4項目／pre-commit の判定フロー図／違反時は 5 Whys / FMEA / CAPA を名指しで使う |
| `iso29119-test-plan.md` | §1.1 で**既存文書との責務分担表**（矛盾させない）／§2 対象と対象外（理由付き）／§4 **プロダクトリスク登録簿を実モジュール名で**＋優先度別のテスト強度／§5 開始・終了・中断・再開／§6 環境と**個人情報を含まないテストデータ**／§7 役割（**合否判定は人、受け入れ承認は依頼者。AI は承認しない**） |
| `iso29119-test-design-spec.md` | 「どの技法をどこに適用したか・していないか」を**実測**で示す。ケース本体は書かない／規模の実測（`pytest --collect-only -q`）／ブラックボックス5技法の適用表／**境界値の1対1突合表**／カバレッジの死角／経験ベース技法の資産対応／追跡できない要求の列挙／**§9 この分析の限界** |
| `iso29119-test-completion-report.md` | 対象ビルド識別（git hash / UI hash）／レベル別結果と失敗の内訳（incident-report と分類を一致させる）／計画との差異／**25010 特性別到達**／残存リスク／**GO / 条件付き GO / NO-GO**／是正処置／申し送り／**§9 この報告書の限界** |
| `iso29119-incident-report.md` | 分類 = **製品欠陥 / テスト陳腐化 / 環境・データ依存 / flaky / 未判定**／最優先3件を**肯定側・否定側の根拠を並べて**判定／§4 テストと実装のどちらが正か（根拠は仕様・RFD・要件 ID）／§5 再実行 n 回中 PASS m 回／**§8 複数件に共通するプロセス上の根本原因（CAPA）** |
| `system_test_cases.csv` | 列 = テストID / ロール / 対象機能 / **ツアー観点** / テスト目的 / 前提条件 / 手順 / 期待される結果 / **severity**。記入例6行（Saboteur 未認証遮断・Guidebook ログイン・Money 主要機能・Intellectual 境界値・FedEx ライフサイクル・Landmark 1366×768） |
| `feature_contracts.yml` | JSON 互換 YAML。`harness`（required_docs / source_roots / source_suffixes / **unregistered_allowlist は理由を値に書く** / scan_roots / suspicious_terms）＋ `features[]` に `example_feature`（`status: planned` なのでファイル未指定でも PASS する） |

---

## 4. `github/`（4件・181行）

| ファイル | 要点 |
|---|---|
| `ISSUE_TEMPLATE/01-rfd.md` | `title: "[RFD-000] "` / labels `rfd` / 選択肢表に「何もしない」/ **決定（人間が承認）** / 完了条件3項目 |
| `ISSUE_TEMPLATE/02-requirement.md` | `title: "[REQ-F-000] "` / 「AかつB」は2 Issue に分ける / 受入基準の良い例・悪い例をコメントで提示 / **工程の進捗チェック8項目**（BD→DD→T→UT→IT→ST→UAT→追跡表更新） |
| `ISSUE_TEMPLATE/03-defect.md` | `title: "[DEF-000] "` / severity 4段の定義つきチェック / **severity と priority を混同しない** / **evidence が空なら起票しない** / 対応（修正 / 次リリース / 受容→09-operations へ） |
| `pull_request_template.md` | **関係 ID 表**（要件/基本設計/詳細設計/実装/テスト/欠陥）/ 工程の明記 / **検証結果 evidence（「動作確認しました」は不可）** / チェック6項目（trace-check NG=0・出口基準・テスト pass 件数・逆同期・秘密情報・Critical/High 残ゼロ）/ 影響範囲とロールバック |

---

## 5. `components/`（4件・618行）

### `feedback.js`（282行）

`skills/design-system`「操作には必ず結果を返す」の実装。**自己完結**（CSS を自分で `<style id="feedback-css">` に注入）。

| API | 挙動 |
|---|---|
| `Feedback.ok(msg, opts)` | 3.2秒で自動的に消える |
| `Feedback.error(msg, {detail, action})` | **消えない**（`AUTO_HIDE_MS.error = 0`）。`role="alert"`。detail 省略時は既定文「時間をおいて…続くときは管理者に連絡」を自動で足す |
| `Feedback.info(msg)` | 4秒 |
| `Feedback.busy(msg)` | 回転アイコン。返り値 `done({ok}\|{error})` を呼ぶと消えて結果トーストに変わる |
| `Feedback.emptyState({title, description, icon, action})` | 0件表示の DOM を返す |
| `Feedback.confirm({title, consequence, actionLabel, danger})` | `<dialog>` を使い `Promise<boolean>` を返す。既定ラベルは「やめる」「実行する」（**「はい／いいえ」を使わない**） |

**設計上の要点**:
- 文字は必ず `textContent`（サーバから返ったエラー文が混ざるため HTML として解釈させない）。アイコンだけ自前 SVG なので `innerHTML`
- `safeHref()` が `http:`/`https:` 以外を拒否（**`javascript:` が入ると押した瞬間に任意コードが動く**）
- トーストホストは `role="status" aria-live="polite"`
- `pointerdown` を capture で拾って**直前に押した要素の近くに出す**（画面隅に固定すると押した結果と結び付かない）
- `icons.js` があればそれを使い、無ければ内蔵の Lucide 風線画6種にフォールバック
- `prefers-reduced-motion` で transition を無効化
- 出所: UX_Auto_Reviewer `web/components/feedback.js`

### `icons.js`（152行）

- Material Symbols（**Apache-2.0**。ライセンス表記はファイル冒頭コメントで満たす）から48種を写して同梱
- **外部 CDN を読み込まない**（閉じたネットワークでアイコンだけ欠ける）
- `<span data-icon="settings" data-icon-size="18">` を自動置換。装飾なので `aria-hidden="true"`
- **Lucide 由来の旧名エイリアス15件**を保持（`house→home` `x→close` `check→check-circle` 等）。*一度に全部書き換えると直し漏れた箇所のアイコンが黙って消えるため*
- 知らない名前は要素ごと削除（壊れた四角を出さない）
- viewBox は Material の `0 -960 960 960`・`fill="currentColor"`（線画の Lucide とは前提が違う）
- `document.readyState === 'loading'` の間は **MutationObserver で組み立てられた端から差し込む**（DOMContentLoaded まで待つと字だけの画面が一瞬映ってちらつく）

### `demo.html`（113行）

部品の実機確認ページ。`../tokens.css` → `../ui/components.css` の順に読み込み、**デモ固有の体裁（`.page` `.row` `.grid-3` `.theme-btn`）だけ**を `<style>` に持つ。
severity バッジ6種 / ボタン（primary・ghost・danger・disabled）/ 入力（`.field` `.input.err` `.select`）/ KPI・スコアカード /
カードと表（`.table-wrap` 横スクロール・列フィルタ・チップ・セグメント・トグル・情報ツールチップ・ページャ・スケルトン）/ コールアウト / モーダル（3経路で閉じる）/ 空状態 / テーマ切替。
Playwright でライト・ダーク・360px・モーダル・トーストを確認済み（2026-09-17）。

### `demo-shell.html`（71行）

骨格の実機確認ページ。`layout.css` の `.app`（globalbar / sidebar / topbar / content）に KPI 列・フィルタ行・表を載せる。
サイドバーの折りたたみ（72px）と 768px 以下の off-canvas 開閉（`.open`）を JS 4行で動かす。1366×768 / 1920×1080 / 360×820 とダークで横スクロールなしを確認済み。

---

## 5b. `ui/`（2件・274行）— デザインシステムの実物（M17）

### `components.css`（175行）

`skills/design-system/SKILL.md` の CSS ブロックを **`var(--*)` だけで**1ファイルに実体化。直値は `token-exempt` コメント付きのヘアライン（2〜3px）と部品固有の幅・高さのみ。

- 群: ボタン `.btn .btn--primary .btn--ghost .btn--danger`（`aria-busy` で二重送信対策）/ 入力 `.input .select .textarea .field .field-err-text .banner-err` / バッジ `.badge-*`（medium の文字色は `--color-medium-text`）/ カード `.card .card-grid` / `.score-card` / `.kpi` / 表 `.table .table-wrap .col-filter-btn .col-pop .pagebar .pager` / `.toggle` `.seg` / `.info-ic .tooltip`（`.edge-left/.edge-right`）/ `.modal-backdrop .modal .modal-{head,body,foot}`（`.modal-head .modal-close` に限定して footer のボタンを壊さない）/ `.notif-pop .notif-item.unread` / `.empty-state`（`feedback.js` と同じクラス名。静的マークアップ用）/ `.callout--*` / `.skeleton` / ユーティリティ
- 含まない: トースト・確認ダイアログ（`feedback.js` が自己注入）
- SKILL.md 側の直値（`#856404` / `#20242B` / `#F2F4F7` / `rgba(8,12,18,.46)` / `#fff`）は `tokens.css` に `--color-medium-text` `--color-tooltip-bg/-text` `--color-scrim` `--color-knob` を追加して解消（真実源も同時更新）

### `layout.css`（99行）

- A) `.app` = `.app-globalbar`（44px 固定・折り返さない）+ `.app-body`（`.sidebar` 240px sticky・本文と別スクロール・`.collapsed` 72px + `.maincol`（`.app-topbar` min 56px sticky + `.app-content` がスクロール））
- B) `.layout-2pane` + `.sidenav`（軽量ツール）
- `.kpi-row` `.filter-row` `.chip`、`.app.is-settings` で裏側の地色を変える、`.measure` で本文幅
- ブレークポイント: ≦1366 sidebar 200px / ≦768 off-canvas（`.open`）・globalbar のラベル非表示 / ≦360 見出し縮小・KPI 1列

## 6. `github-actions/`（4件・177行）— 配布用サンプル

| ファイル | トリガー | 内容 |
|---|---|---|
| `test-gates.yml` | PR / push(main) / dispatch | job `contracts`（`quality_harness.py`）＋ job `unit-integration`。**`hashFiles()` でスタックを自動判定**（pyproject/requirements → pytest --cov-fail-under=80、package.json → npm test。両方無ければ `::warning::` で「未実行」と明示）。`GATES_REQUESTED=1` を付けて実行。L3 はコメントアウトで同梱 |
| `lifecycle-check.yml` | PR（`docs/lifecycle/**`・`scripts/trace-check.sh`）/ push(main) / dispatch | `trace-check.sh docs/lifecycle -o trace-check-report.md` → **失敗時もレポートを artifact 化**し `$GITHUB_STEP_SUMMARY` へ出力 |
| `deploy.yml` | push(main) / dispatch | GitHub Pages（`./docs` を公開。ルート公開なら `./` に変更）。`concurrency: pages` |
| `secret-scan.yml` | push / PR / dispatch | gitleaks（`fetch-depth: 0` で全履歴） |

**注**: これらは配布先へ置くサンプル。**キット自身の `.github/workflows/` は存在しない**（`spec/09-findings.md` F-07 / `spec/10-backlog.md` B-01）。

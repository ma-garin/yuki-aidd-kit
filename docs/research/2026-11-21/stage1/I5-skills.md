# I5-skills 内部実装: skills（段1 広域）

- 対象: worktree `research-20261121`（origin/main）の SKILL.md 全件。`03_ClaudeCode/skills/`（27・真実源）、`04_Codex/skills/`（71・`04_Codex/build_codex_skills.py` の生成物）、`04_Codex/native-skills/aidd-kit`（1。`04_Codex/skills/aidd-kit` と同一内容を `diff -q` で確認）。リポジトリ直下に `skills/` は無い（`ls skills` → No such file）
- 調べた方法: `find . -name SKILL.md`／自作の frontmatter 解析（Python, `-I`）／description の「」発火語・キーワードの重複集計／`wc -lc` と文字数集計／本文中のパス参照 370 件の実在検査（スキル相対・キット相対・basename 検索）／`0[0-6]_` で始まるキット相対パスの実在検査／`02_共通/ツール/skill-lint.py` の静的読解と実行（読むだけの検査器）／Codex 版 `agents/openai.yaml` の `allow_implicit_invocation` 集計／製品文書 2 件の取得
- 調べた件数/全件数: SKILL.md 99/99（frontmatter 全件解析）。本文の精読は Claude Code 版 27 件のうち description 全件と、矛盾検査に必要な箇所（design-system・personal-pwa・nfr-standards・test-automation・uiux_review・phase-approval）。Codex 版は生成物のため差分と生成ロジックのみ確認（`diff 03…/done-gate 04…/done-gate` → 差は生成注記 1 行のみ）
- 参照した製品文書（取得日 2026-11-21）: https://code.claude.com/docs/en/skills（先頭 100,000 字のみ読了）、https://agentskills.io/specification

## 実測値（要約）

| 項目 | 値 |
|---|---|
| CC 版 SKILL.md 本文合計 | 82,696 字（27 件） |
| 最大の本文 | design-system 8,152 字・143 行 |
| 最大行数 | uiux_review 200 行（全件 500 行未満） |
| CC 版 description 合計 | 6,587 字（毎セッション一覧に載る） |
| 「必ず」を含む description | 18/27 |
| skill-lint 実行結果 | `OK: スキル 27 件・NG=0 WARN=1` |

---

## 発見

### I5-skills-01 Codex 版で `cmd-*` 25 件がすべて暗黙発火可。`cmd-implement`・`cmd-ralph`・`cmd-security-audit` も自動で起動しうる
- 種別: 欠陥
- 深刻度: High
- 根拠: `04_Codex/skills/*/agents/openai.yaml` を集計 → `cmd true 25`（false 0）。`04_Codex/build_codex_skills.py:135` `implicit = fm.get("disable-model-invocation", "").lower() != "true"` で、frontmatter の無いコマンド（`03_ClaudeCode/commands/implement.md` 先頭は `# /implement — 実装モードの開始（探索ブロックON）`、frontmatter なし）は既定 true になる。`cmd-retro` の description は「/retro — レトロと学びの蓄積」（`04_Codex/skills/cmd-retro/SKILL.md:3`）で、同じく implicit true の `retro` と二重に発火候補になる。security-audit 本体は「明示に依頼された時と /security-audit で使う」「ecc-daily-router からは自動で振らない」（`03_ClaudeCode/skills/security-audit/SKILL.md:3`）と書くのに `cmd-security-audit` は implicit true
- 状態: 実証（集計と生成ロジックの読解。Codex 上での誤発火の再現は未確認）
- 改善の方向: コマンド由来の `cmd-*` は既定で `allow_implicit_invocation: false` にし、skill-lint の照合対象に `04_Codex/skills/cmd-*` を加える

### I5-skills-02 デバイス方針がスキル間で矛盾（design-system=PC のみ／nfr-standards・test-automation=360px 必須）
- 種別: 矛盾
- 深刻度: High
- 根拠: `03_ClaudeCode/skills/design-system/SKILL.md:67`「検証幅は 1366×768 / 1920×1080（PC のみ）。360・768 の確認と off-canvas は利用者が明示したときだけ」・同 `:143`「モバイル対応を独立した要件として追加しない」。一方 `03_ClaudeCode/skills/nfr-standards/SKILL.md:28`「折りたたみAndroid端末 カバー画面: 360×820px で主要機能が使えること」・`:31` タッチ 44px、`03_ClaudeCode/skills/test-automation/SKILL.md:26`「折りたたみ端末カバー幅（360px）でレイアウトが崩れない」。nfr-standards の description は「AIDDプロジェクト向け」で対象を PWA に限定していない。グローバル AGENTS.md の完了条件も「狭い画面」を全状態に含める
- 状態: 実証（grep で行を確認）
- 改善の方向: 2026-11-15 の PC 既定方針を nfr-standards・test-automation（と AGENTS.md の「狭い画面」）へ反映し、モバイル基準は personal-pwa の範囲に限定する

### I5-skills-03 description が存在しないパスを指す（design-system・phase-approval の `templates/…`）
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `design-system/SKILL.md:3`「値の実物は templates/tokens.css、部品は templates/ui/components.css、骨格は templates/ui/layout.css」、`phase-approval/SKILL.md:3`「承認記録の形式は templates/lifecycle/approvals/」。`ls templates` → No such file。実体は `02_共通/ひな形/tokens.css`・`02_共通/ひな形/ui/*.css`・`02_共通/ひな形/lifecycle/approvals`。導入後も `00_導入/01_インストール/install.sh:62-66` が `~/.claude/templates/` へ写すのは `tokens.css` と `components/{ui_catalog.py,ui-catalog.json,feedback.js,icons.js}` だけで、`ui/` と `lifecycle/` は写さない。design-system 本文は `02_共通/ひな形/…` を使っており description と食い違う
- 状態: 実証
- 改善の方向: description のパスを本文と同じ実在パスにそろえるか、パスを description から外して本文へ寄せる

### I5-skills-04 skill-lint の検査範囲が狭く、上記の欠陥を通す
- 種別: 欠落
- 深刻度: Medium
- 根拠: `02_共通/ツール/skill-lint.py` は `--skills` 既定が `03_ClaudeCode/skills` のみ（L120 付近）で、`04_Codex/skills` の生成物（cmd-*/agent-*/rules-*/style-*）の frontmatter を検査しない。name の文字種（小文字英数とハイフン）を検査しない（`uiux_review` が通る）。本文・description 中のパス実在を検査しない（03 を通す）。`parse_frontmatter` は 1 行の `key: value` だけを読むため `description: >` の複数行は「>」1 字と判定され長さ検査をすり抜ける（現状 0 件で実害なし: `grep "^description: *[>|]"` → 0）。KNOWN_KEYS に Claude Code の正式キー `arguments`・`disallowed-tools`・`background`・`shell` が無い（使うと誤 WARN）。実行結果 `OK: スキル 27 件・NG=0 WARN=1`
- 状態: 実証（静的読解＋実行）
- 改善の方向: 生成物も対象に含め、name 文字種・参照パス実在・ブロックスカラーの検査を足し、KNOWN_KEYS を製品文書の一覧に合わせる

### I5-skills-05 `uiux_review` の name がアンダースコアを含み、Agent Skills 仕様に違反
- 種別: 欠陥
- 深刻度: Medium
- 根拠: agentskills.io/specification「May only contain unicode lowercase alphanumeric characters (a-z, 0-9) and hyphens (-)」。`ls 03_ClaudeCode/skills 04_Codex/skills` で `_` を含むのは `uiux_review` のみ（両方）。Codex 版は `~/.agents/skills/` に置かれ（install.sh:58）、この仕様に準拠するクライアントが読む。Claude Code の文書には文字種の制限の記載が無く（取得範囲内）、Claude Code 側では動作している
- 状態: 実証（仕様との照合）／Codex での読み込み失敗は未確認
- 改善の方向: `uiux-review` へ改名し、参照（AGENTS.md・各スキル・hook）を一括置換

### I5-skills-06 「レビュー」「完了」系の発火語が複数スキルで競合
- 種別: 矛盾
- 深刻度: Medium
- 根拠: description の集計で「レビュー」7 件（dev-lifecycle, ecc-daily-router, phase-approval, qa-review-standards, security-audit, single-html-tool, uiux_review）、「完了」7 件（advisor, atarimae-quality-audit, done-gate, test-strategy, uiux_review, work-metering, work-report-html）、「設計」8 件。具体的な衝突: `uiux_review` は「レビューを頼まれたとき、完了報告をする前に使う」と無条件（`uiux_review/SKILL.md:3`）で、qa-review-standards の「レビューして」、done-gate の「これで完了」、advisor の「完了と言う前」と同じ場面を取り合う。uiux_review の description だけ「使わない場面」・分担先を持たない（qa-review-standards・e2e-cycle・test-automation は分担を明記）
- 状態: 実証（集計）／実際の誤発火率は未計測
- 改善の方向: uiux_review の発火を「画面・UI」に限定する語を先頭に置き、分担先（qa-review-standards / done-gate）を 1 文で書く

### I5-skills-07 ecc-daily-router の発火語が汎用語の羅列で、他スキルの発火を奪う
- 種別: 過剰
- 深刻度: Medium
- 根拠: `ecc-daily-router/SKILL.md:3`「PWA、Playwright、Python、React、Django、E2E、「QAレビュー」「ECC活用」への言及があればこのスキルを使う」。「PWA」は personal-pwa、「Playwright」「E2E」は test-automation・e2e-cycle、「QAレビュー」は qa-review-standards と重なる。security-audit 側は「ecc-daily-router からは自動で振らない」と防御的に書いている
- 状態: 実証（文面）／誤発火の観測は未確認
- 改善の方向: 発火語を「ECC 資産の選択・ルーティング」の意図語に絞り、技術名の羅列を外す

### I5-skills-08 single-html-tool の「HTMLファイルの修正依頼でも適用する」が過剰
- 種別: 過剰
- 深刻度: Low
- 根拠: `single-html-tool/SKILL.md:3`。HTML を扱う work-report-html・design-system・security-audit・test-automation の description と重なる（「HTML」を含む description 5 件）。単一 HTML 規約（CSS/JS 分割禁止）が無関係な HTML（例: 生成レポート、複数ファイル構成のアプリ）に掛かりうる
- 状態: 実証（文面）／誤適用の観測は未確認
- 改善の方向: 「自己完結の単一 HTML ツール」の修正に限定する

### I5-skills-09 配布キットの description に個人プロジェクト名・未置換プレースホルダが残る
- 種別: 欠陥
- 深刻度: Low
- 根拠: `personal-pwa/SKILL.md:3`「GitHub Pages（<GITHUB_OWNER>）」— 導入先のスキル一覧でも `&lt;GITHUB_OWNER&gt;` と表示される（本セッションの system のスキル一覧で確認。Claude Code 文書「Angle brackets in the description show as &lt; and &gt;」）。固有名: streamlit-rag-app（business_agent_app・VeriRAG・PMO支援）、single-html-tool（QA Lens・UX audit tool）、design-system（UX audit tool・QA Lens・personal accounting PWA）、agent-eval（business_agent）、ecc-daily-router（QA document generator 他）。他者の環境では一致しない語で発火枠を消費する
- 状態: 実証
- 改善の方向: プレースホルダを導入時に置換するか description から外し、固有名は本文の例へ移す

### I5-skills-10 kit 外スキルへの依存を description で前提にしている
- 種別: 欠落
- 深刻度: Low
- 根拠: done-gate→`verification-before-completion`、qa-review-standards→`code-review`、e2e-cycle・test-automation→`agent-browser`・`playwright-cli`、code-doc-search→`research`・`find-skills`、test-strategy→`tdd`。いずれも `03_ClaudeCode/skills` に無い（`ls` で確認）。`00_導入/01_インストール/external-skills.json` に外部スキルとして登録はあるが（agent-browser 等を確認、全名の照合は未実施）、install.sh 本体はそれらを導入しない（`grep verification-before-completion 00_導入` は external-skills.json のみヒット）
- 状態: 実証（存在確認）／external-skills.json に全 7 名が載っているかは未確認
- 改善の方向: 依存スキルを skill-lint か doctor.py で突き合わせ、未導入なら description の分担文を条件付きにする

### I5-skills-11 description 合計 6,587 字が毎セッション常駐。design-system は 508 字で skill-lint の WARN
- 種別: 過剰
- 深刻度: Low
- 根拠: 自作集計（CC 版 27 件の description 文字数合計 6,587、最大 design-system 508・test-strategy 411・security-audit 368）。skill-lint `WARN S4 design-system/SKILL.md: description が 508 字 > 500`。design-system の description の後半（references の案内・既存ツール名）は本文に置ける情報。Claude Code 文書: description＋when_to_use は一覧で 1,536 字で切られる（全件この上限未満）。agentskills.io は metadata を「~100 tokens」と想定
- 状態: 実証（字数）／トークン換算は未計測（日本語の字→トークン比を測っていない）
- 改善の方向: description は「何を・いつ」の 1〜2 文に絞り、ファイル案内・既存ツール名は本文へ移す

### I5-skills-12 `when_to_use` を一件も使わず、発火条件と機能説明が 1 欄に混在
- 種別: 機会
- 深刻度: Low
- 根拠: frontmatter キー集計 → `name 27・description 27・disable-model-invocation 1` のみ。Claude Code 文書は `when_to_use` を正式フィールドとして挙げ「Put the key use case first」と書く。work-metering の description は大半が「使わない場面」で、先頭に用途が来ていない（`work-metering/SKILL.md:3`）
- 状態: 実証（キー集計）／分けた場合の発火精度の差は未確認
- 改善の方向: Claude Code 版は発火語を `when_to_use` へ分離（Codex 生成時は結合）し、用途を先頭に置く

### I5-skills-13 本文で basename だけの参照が多く、導入先での解決先が曖昧
- 種別: 機会
- 深刻度: Low
- 根拠: 参照 370 件の検査で、スキル相対・キット相対で解決できず basename でのみ見つかったもの 119 件（例: `verify.sh` 7 回→`00_導入/01_インストール/verify.sh`、`scripts/quality_harness.py` 4 回→実体は `02_共通/ツール/quality_harness.py`、`CURRENT_STATE.md` は 2 か所に同名）。どこにも無いもの 29 件は、`package.json`・`tasks.md`・`security-report.md` 等の導入先プロジェクトのファイルで、キットの参照切れではないと判断。キット相対（`0[0-6]_…`）で書かれたパスは全件実在（不在 0。`metering.py:96` の部分一致 1 件のみ）
- 状態: 実証
- 改善の方向: 「キット内のパス」と「導入先に配置されるパス」を表記で区別する（例: `<kit>/…` と `<project>/scripts/…`）

### I5-skills-14 本文サイズは仕様内だが、design-system は推奨上限に近い可能性
- 種別: 機会
- 深刻度: Low
- 根拠: 行数は全件 500 行未満（最大 uiux_review 200 行）で、Claude Code 文書と agentskills.io の「Keep SKILL.md under 500 lines」を満たす。agentskills.io は本文「< 5000 tokens recommended」。design-system 本文 8,152 字・16,253 バイトで、日本語の字→トークン比次第で 5,000 を超える可能性がある
- 状態: 未確認（トークン数を測っていない）
- 改善の方向: 実トークン数を計測し、超えるなら作業手順以外を references へ分離

## 調べられなかったこと
- Codex・Claude Code での実際の誤発火・非発火（発火率の実測）。評価用の発火テスト（クエリ集→発火スキル）を走らせていない
- 各スキル本文のトークン数（トークナイザで未計測。字数・バイト数のみ）
- Claude Code 文書の後半 19,731 字（スキル一覧の文字予算・環境変数名の記述がある可能性）。一覧全体の予算超過で description が落ちるかは未確認
- 本文の規約（AGENTS.md・absolute-rules）との矛盾の全数照合。PC/モバイル方針以外は精読していない
- `external-skills.json` に依存スキル 7 名がすべて載っているか
- Codex 版 71 件の本文の個別精読（生成物のため差分と生成ロジックのみ）
- WebSearch は使っていない（製品文書 2 件の WebFetch で足りたため）

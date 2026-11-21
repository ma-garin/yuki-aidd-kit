# E5-context 研究: コンテキスト設計（段1・広域）

- 対象: キットが毎セッション載せる規約（`~/.claude/CLAUDE.md`＋`@AGENTS.md`、`~/.claude/rules/` の paths なし規則、リポジトリ `CLAUDE.md`、hook の注入文）と、長文脈劣化・指示数と遵守率・プロンプトキャッシュ・規約文書の効果に関する研究と公式文書
- 調べた方法: `wc -l/-m/-c`・frontmatter の paths 判定（awk）・`grep -n`・`git grep origin/main`・hook ソースの静的読解（実行していない）。外部は WebFetch/WebSearch（取得日 2026-11-21）
- 調べた件数/全件数: 規約ファイル 18/18（`~/.claude/rules` 配下 *.md 18 件、うち常時読込 6 件＋CLAUDE.md 2 件＋AGENTS.md 1 件）、注入 hook 3/3（prompt-priority / session-context / subagent-context）、外部資料 8 件（研究 5・製品文書 3）

## 実測（常時載る量）

| ファイル | 行 | 文字 |
|---|---|---|
| ~/.claude/CLAUDE.md | 38 | 1,727 |
| ~/.claude/AGENTS.md（@import） | 172 | 10,392 |
| rules/common/core・engineering・research | 73 | 3,271 |
| rules/aidd-kit/absolute-rules・speed-harness・model-routing | 92 | 9,529 |
| リポジトリ CLAUDE.md | 19 | 1,054 |
| 合計 | 394 | 25,973 |

- 判定: `02_共通/rules/*.md` の frontmatter を awk で抽出し、paths なし＝常時は absolute-rules / model-routing / speed-harness の 3 件（他 7 件は paths あり）。`~/.claude/rules/python/*` は全て paths あり
- 列挙項目（`- ` / `| ` / `1. ` 始まりの行）は 220 行（`grep -cE`）。1 行に複数の指示を含むため指示数の下限の目安
- 最長行 1,470 字（speed-harness.md。awk length）。行数より文字数が実量を表す
- トークン数は未計測（`/context` やトークン計数 API を使っていない）
- これとは別に UserPromptSubmit で毎発言 約 600 字の `[estimate]`/`[計測行]` が会話に積み上がる（`03_ClaudeCode/hooks/prompt-priority.py:66-77`）

## 外部根拠（要点）

- R1 製品文書: Claude Code memory（https://code.claude.com/docs/en/memory ）「target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence」「Imports ... don't reduce its context cost」「if two instructions contradict each other, Claude may pick one arbitrarily」「if a user rule and a project rule conflict, Claude may follow either one」「The more specific and concise your instructions, the more consistently Claude follows them」。`/doctor prompt-audit` で矛盾検出の機能あり。HTML コメントは注入前に除去される
- R2 製品文書: Anthropic "Effective context engineering for AI agents"（2025-09-29, https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ）context rot、attention budget「Every new token introduced depletes this budget」、「smallest possible set of high-signal tokens」、edge case の laundry list を避け canonical examples を選べ
- R3 研究: Jaroslawicz et al. "How Many Instructions Can LLMs Follow at Once?"（arXiv:2507.11538, NeurIPS 2025）。課題=業務レポート作成に 10〜500 個のキーワード包含指示。20 モデル。claude-sonnet-4: 10→100%、100→94.4%、250→77.2%、500→42.9%。claude-opus-4: 100→94.6%、250→67.9%、500→44.6%。誤りは密度とともに「省略」に偏る（omission:modification 比 sonnet-4 で 250 指示時 2.77）。初頭効果（後ろの指示ほど破られる）は 150〜200 指示付近で最大。キーワード包含という単純指示での測定で、行動規範の遵守とは条件が違う
- R4 研究: Gloaguen et al. "Evaluating AGENTS.md"（arXiv:2602.11988, ICLR 2026）。SWE-bench（LLM 生成の context file）と AGENTbench（開発者が書いたファイル）。context file は成功率を概ね改善せず、推論コストを平均 20% 超増やす。指示自体は守られ、テスト・探索が増える。非標準の慣行を指定する用途では有用。著者の結論: 不要な要件はタスクを難しくする、最小限の要件だけ書く
- R5 研究: Liu et al. "Lost in the Middle"（arXiv:2307.03172, TACL）。複数文書 QA・KV 検索で、関連情報が入力の先頭か末尾にあるとき最高、中央で低下
- R6 研究: Chroma "Context Rot"（2025-07, https://research.trychroma.com/context-rot ）18 モデル（Claude 4 含む）で入力長の増加とともに単純課題でも性能が不安定化、主題の近い妨害文ほど悪化（二次情報経由の把握。数値は本文未確認）
- R7 研究: NoLiMa（arXiv:2502.05167）13 モデル、32K で 11 モデルが短文脈ベースラインの半分未満。GPT-4o 99.3%→69.7%
- R8 製品文書: Prompting best practices（https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices ）新しいモデルは system prompt への反応が強く、「CRITICAL: You MUST ...」のような強い言い回しは過剰発火を招く→普通の言い方に和らげる。理由（motivation）を添えると的確になる
- R9 製品文書: Prompt caching（https://platform.claude.com/docs/en/build-with-claude/prompt-caching ）prefix 順 tools→system→messages、上位の変更は以降を無効化。既定 TTL 5 分・1 時間オプション、書込 1.25×/2×、読取 0.1×（Opus 5.5・Sonnet 5.5 は 0.05×）

## 発見

### E5-context-01／常時規約が公式の目安 200 行を超え、指示数は遵守率が落ち始める帯にある
- 種別: 過剰
- 深刻度: High
- 根拠: `wc -l` で ~/.claude/CLAUDE.md 38＋import の AGENTS.md 172＝210 行（R1 は import もコストに数えると明記）。常時合計 394 行・25,973 字、列挙項目 220 行。R3 では Claude Sonnet 4/Opus 4 の遵守率が 100 指示で約 95%、250 指示で 68〜77%
- 状態: 実証（行・字数）／主張（遵守率への影響。R3 は課題条件が違い、キットでの遵守率は未計測）
- 改善の方向: 常時層を「憲法＋索引」に絞り、手順・根拠・事例は paths 付き rules か skill に移して常時の指示数を 100 未満に下げる

### E5-context-02／A-3 残課題の規定が常時載る 2 ファイルで正反対
- 種別: 矛盾
- 深刻度: High
- 根拠: `~/.claude/rules/common/core.md:5`「『残課題』を書かない」 vs `02_共通/rules/absolute-rules.md:9`・`~/.claude/AGENTS.md:47`「`残課題: ...` を1〜3行」。どちらも paths なしで常時読込。R1「Claude may pick one arbitrarily」
- 状態: 実証（grep）
- 改善の方向: 同じ ID（A-3）の定義を 1 か所に固定し、他方は削除する。core.md はキット外（`git grep rules/common origin/main` で 0 件）なので導入先側の整理も要る

### E5-context-03／応答の長さ規定が 5 通り併存
- 種別: 矛盾
- 深刻度: High
- 根拠: absolute-rules.md:15「既定3行」、core.md:28「完了報告は5行以内…見出し3つ以内」、AGENTS.md:36「完了報告は3行以内…計画は行数制限なし」、AGENTS.md:52「報告の型（10 行以内）」、speed-harness.md:5「結果1行＋依頼1行…表は1個まで…目安150字」。さらに AGENTS.md:53 は表の作り方を細かく規定し speed-harness は「表は1個まで」
- 状態: 実証（grep）
- 改善の方向: 応答長の規定を 1 表（場面→上限）に統合し、他の箇所は参照だけにする

### E5-context-04／「優先する」の主張が複数節で競合し、優先順位が決まらない
- 種別: 矛盾
- 深刻度: Medium
- 根拠: 常時テキストで「優先」14 回（grep -o）。AGENTS.md「速く届ける進め方（…他の節より優先）」「見積・中間報告（…旧規定より優先）」「応答と計測表示（…旧書式より優先）」「最優先: 速度」、core.md「保守者の発言は…優先」。R1 はユーザー規則とプロジェクト規則の間に上書き関係は無いと明記
- 状態: 実証（grep）／影響は主張
- 改善の方向: 旧規定を本文から削除し「〜より優先」という差分表現を無くす（優先の宣言でなく単一の現行規定にする）

### E5-context-05／git stash の扱いが矛盾
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `02_共通/rules/speed-harness.md:40`「変更を stash した素の状態で同じ失敗が再現したら」 vs `04_Codex/AGENTS.md.template:111`（導入先 AGENTS.md:120）「`git stash` … 禁止」
- 状態: 実証（grep）
- 改善の方向: H-7 の切り分け手順を stash 不使用（worktree で origin/main を検証）に書き換える

### E5-context-06／「利用者に聞く／聞かない」の規定が衝突
- 種別: 矛盾
- 深刻度: Medium
- 根拠: core.md:31「好みが絡む変更は…AskUserQuestion で2〜4案を1回だけ聞く」 vs CLAUDE.md:8「種別判定・進め方・デザイン…を人間に聞かない」、AGENTS.md:6「完成形の見本を最初の 1 回で出して…小出しで質問しない」
- 状態: 実証（grep）
- 改善の方向: 「デザイン判断は聞かず見本で確かめる」等、適用場面を分けた 1 規定にする

### E5-context-07／同一規定の多重掲載（常時層＋毎発言注入）
- 種別: 過剰
- 深刻度: Medium
- 根拠: 中間報告間隔「60÷5」が常時テキストに 5 回（grep -o）。A-2a の書式が absolute-rules.md:18、リポジトリ CLAUDE.md:5、AGENTS.md 冒頭節、さらに prompt-priority.py:70-73 が毎発言再注入（約 600 字/発言、長いセッションで線形に累積）。kit 内にも `06_保守者向け/02_設計判断の根拠/estimate-format-single-source.md` があるのに単一化されていない
- 状態: 実証（grep・静的読解）
- 改善の方向: 常時層は 1 か所に定義、hook 注入は可変部（現在時刻・係数）だけに縮める。R5/R3 の初頭・末尾効果を使うなら「末尾に毎回 1 行のリマインド」程度で足りるかを計測で確かめる

### E5-context-08／強い言い回しの多用（新モデルで過剰発火の恐れ）
- 種別: 機会
- 深刻度: Medium
- 根拠: 常時テキストで「必ず」11・「優先」14・「絶対」4・「例外なし」3・「最悪」1・太字 `**` 142 個（71 箇所）。CLAUDE.md の「違反は『最悪のインシデント』」。R8 は Opus 4.5 以降で強い言い回しを和らげるよう推奨（過剰発火の実例は道具の呼び出し）
- 状態: 実証（件数）／主張（影響。キットでの過剰発火は未計測）
- 改善の方向: 強調は hook が機械強制しない少数の規定だけに限り、理由（なぜ）を 1 句添える書き方に寄せる

### E5-context-09／規約の効果をキット自身で測っていない
- 種別: 欠落
- 深刻度: Medium
- 根拠: `git grep -n "lost in the middle\|context rot\|IFScale\|遵守率" origin/main` で研究への言及は外部 OSS 一覧 CSV のみ。token-economics.md はトークン量の内訳を扱うが規約量と遵守の関係は扱わない（`grep -n` で確認）。R4 は「context file の効果は導入前に厳密に評価せよ」、成功率は改善せずコスト 20% 超増
- 状態: 実証（grep）
- 改善の方向: 規約を減らした版と現行版で同じ課題を回し、A-2 遵守率・違反件数・トークンを比べる A/B 手順を agent-eval に置く

### E5-context-10／行が長すぎ 1 行に多数の指示が詰まる（末尾ほど落ちやすい形）
- 種別: 欠陥
- 深刻度: Low
- 根拠: speed-harness.md の 400 字超の行 8 本、最長 1,470 字（awk length）。H-4 の 1 行に委譲の規定が 10 件以上。R3 の初頭効果（後ろの指示ほど破られる）・R5（中央の情報が使われにくい）
- 状態: 実証（字数）／主張（影響）
- 改善の方向: 1 行 1 規定に割り、根拠・事例（日付付きの事故例）は `06_保守者向け/02_設計判断の根拠/` へ移す

### E5-context-11／常時層に事故の経緯・日付・根拠が混在（high-signal でない）
- 種別: 過剰
- 深刻度: Low
- 根拠: 常時テキストに「2026-xx-xx 保守者指示」「2026-10-25 事故」等の経緯が多数（AGENTS.md「2026-10-25 事故の再発防止」節、speed-harness H-4 内の事例）。R2「smallest possible set of high-signal tokens」「laundry list of edge cases を避ける」。R1: HTML コメントは注入前に除去される
- 状態: 実証（目視・grep）／効果は主張
- 改善の方向: 経緯は `<!-- -->` か根拠文書へ移し、規定文だけを残す

### E5-context-12／AGENTS.md の配布テンプレートと導入先の乖離
- 種別: 欠陥
- 深刻度: Low
- 根拠: `diff 04_Codex/AGENTS.md.template ~/.claude/AGENTS.md` で差分 36 行、文字数 8,204 vs 10,392。absolute-rules.md もリポジトリと導入先で DIFF（`diff -q`）。導入先にだけある節（速く届ける進め方・見積・中間報告 2026-11-14）が常時層を増やしている
- 状態: 実証（diff）
- 改善の方向: 導入先の追記をキットに取り込むか削るかを決め、install 時に差分検査を出す

### E5-context-13／キャッシュの扱いは概ね妥当、ただし TTL 記述が API 既定と違う
- 種別: 機会
- 深刻度: Low
- 根拠: speed-harness.md:50「セッション途中で CLAUDE.md を書き換えない（キャッシュ prefix が壊れる）」は R9 の prefix 無効化規則と整合。可変の現在時刻・係数は UserPromptSubmit の additionalContext（messages 側）に入れており system を壊さない設計（prompt-priority.py:62-77 の静的読解。実際の配置は未確認）。一方 model-routing の根拠は「サブスクのキャッシュ寿命 1 時間（usage credits 使用中は5分）」で、R9 の API 既定は 5 分。Claude Code の契約別 TTL は本調査で未確認
- 状態: 主張（静的読解・文書）
- 改善の方向: TTL を契約別に出典付きで書き分け、context-guard の 55 分閾値の前提を明示する

## 調べられなかったこと

- 常時層の正確なトークン数（`/context`・count_tokens API を未使用。日本語の字数→トークン換算も未検証）
- キットでの実際の遵守率（A-2 の欠落率など）と規約量の相関。R3 はキーワード包含課題で、行動規範の遵守には外挿できない
- Chroma Context Rot の一次数値（二次情報で把握のみ）
- Claude Code における hook の additionalContext の正確な配置（system か messages か）と、サブスクリプションでのキャッシュ TTL
- SessionStart（session-context.py）の注入量の実測（静的に読んだのみ、実行していない）
- skill 一覧（description）が毎回載る量（このセッションで見えている一覧は長いが、キット由来分の字数は未計測）

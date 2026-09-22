# 外部参照調査 2026-09 — sindresorhus/awesome

対象: https://github.com/sindresorhus/awesome （commit `bc98e51`、2026-09-22 取得）。
走査: readme.md 866 行から**全 674 エントリ／27 節**を機械抽出し、キットに関わる **28 本のリンク先 README を実取得**して中身を読んだ（初回調査は 1 行説明だけで結論を出し、AI 系の収録を見落とした。その記録は末尾）。
目的: 保守者の要求「キットをパートナー・メンターの水準まで高める」に対し、**実在する資産**を特定する。

## 節ごとの件数（走査の網羅性の証拠）

Miscellaneous 131 / Front-End 85 / Programming Languages 76 / Platforms 55 / Computer Science 38 / Back-End 32 / Security 29 / Gaming 28 / Development Environment 21 / Databases 17 / Decentralized 17 / Learn 15 / Theory 14 / Media 14 / Business 12 / Health and Social Science 12 / CMS 11 / Hardware 11 / **Testing 11** / Big Data 9 / **Work 7** / Books 6 / Editors 5 / Entertainment 5 / Networking 5 / Related 5 / Events 3。

キットに関係するのは Miscellaneous・Testing・Work・Business・Learn・Security・Development Environment・Computer Science の 8 節。言語別・ゲーム・ハード・ブロックチェーンは対象外。

---

## 1. 最大の収穫 — awesome-claude-code（github.com/hesreallyhim/awesome-claude-code）

719 行。**キットの `03_ClaudeCode/` と同じ土俵の資産が、節ごとに整理されている。** キットは自作のみで育ってきたので、ここが初めての他流試合になる。特に **Linting 節はキットの自作検査（`06_保守者向け/03_回帰テスト/check_docs.py`）と同じ問題を解いている既成ツール群**で、優先度が最も高い。

### 1-1. Linting — キットの検査系に直接当たる

| 資産 | 何をするか | キットのどこに当たる |
|---|---|---|
| **agnix**（agent-sh/agnix） | CLAUDE.md・AGENTS.md・SKILL.md・hooks・MCP 設定を検証する linter ＋ LSP。**autofix と IDE プラグイン付き** | `check_docs.py` の検査 5（frontmatter）・検査 9（行数）。自作の正規表現検査より広い |
| **Ctxlint**（ctxlint/Ctxlint） | AI コンテキストファイルの**参照切れ・死んだコマンド・ハードコードされた秘密**を検出。モジュール化されたルールセット | 検査 4（参照切れ）・検査 11（絶対パス）と同じ目的。`06_保守者向け/学んだこと.md` の「正規表現だけの検査は定義と呼び出しを区別できない」はここで解決済みの可能性 |
| **Schliff**（Zandereins/schliff） | 指示ファイルの**決定論的な品質スコア**。8 次元・セキュリティ含む・SKILL.md / CLAUDE.md 対応 | **キットに無い概念**。スキルの良し悪しを人が目で見ている。スコア化すれば `05_プロジェクト管理/構想.md` の退役判定に使える |
| **BlockWatch**（mennanov/blockwatch） | 相互依存するコード・文書・設定の**同期崩れ**を検出する言語非依存 linter | 「同じコミットで `06_保守者向け/01_内部仕様/` を更新する」規約（Q-4）の機械化。現状は人の規律 |
| **Upkeep**（wei18/Upkeep） | 文書・仕様・資産のドリフトを**根拠付きで**検出。出力のみ（勝手に直さない） | 検査 8（spec 同期）。「出力のみ」は `06_保守者向け/保守者の傾向.md` #13「判定は規則が行い、LLM は説明だけ」と同じ思想 |
| **agents-md-cookbook**（Taiizor） | AGENTS.md の検証済みテンプレート・CI linter・CLAUDE.md からの移行ツール | `04_Codex/AGENTS.md.template` の他流試合 |

### 1-2. Memory & Context Persistence — メンター化の中核

| 資産 | 何をするか | なぜ効くか |
|---|---|---|
| **MAMA** | Claude の常駐の相棒。**保守者の決定と、その決定がどう変化したかを覚える**。ローカル優先 | G-1「相手を観測していない」の直接の答え。`06_保守者向け/保守者の傾向.md` は手で書いている |
| **Selvedge** | AI が書いたコードの長期記憶。**「AI エージェント版の git blame。ただし why の方」** | `02_共通/ひな形/ADR-template.md` の自動化。捨てた案と理由を人が書く前提を崩せる |
| **presence** | リポジトリ別の記憶・**成果のテレメトリ**・**較正済み自信度ゲート** | `skills/done-gate/SKILL.md` に自信度の概念が無い。「動いた」の申告を数値で縛れる |
| **roampal-core** | 成果ベースの永続記憶。**良い助言は昇格し、悪い助言は降格する** | `skills/retro/SKILL.md` → `06_保守者向け/学んだこと.md` の還流が一方向で、外れた知見が残り続ける問題に当たる |
| **claude-context-optimizer** | トークン使用を追跡し、**無駄なコンテキストを特定** | `00_導入/03_点検/token_audit.py`・`06_保守者向け/01_内部仕様/10_バックログ.md` B-10（常時読み込み層の実測） |
| **Context Engineering Kit** | 最小トークンのコンテキスト設計パターン集 | `skills/context-compression/SKILL.md` |

### 1-3. Security — キットの穴（R-1）の実装

| 資産 | 何をするか |
|---|---|
| **Parry-guard**（vaporif） | **AI コーディングツールの hook 用のプロンプトインジェクション検査器**（Rust）。注入攻撃・秘密の漏洩・データ持ち出しを検出 |
| **Agent Guard**（JeongJaeSoon） | Claude Code / Codex / git hook / CI に対する**秘密漏洩のリアルタイム防御** |
| **Claude Code Safety Net**（kenryu42） | **破壊的な git / ファイルシステム操作を捕まえる hook** |
| **SkilLock** / **SkillSpector**（NVIDIA） | スキルの挙動を固定し、CI で**承認外のドリフトを止める** / スキルの脆弱性スキャン |
| **Dippy**（ldayton） | **AST 解析**で安全な bash を自動承認し、破壊的操作だけ確認を出す |

キットの対応物: `02_共通/ツール/pre-commit`（秘密情報）は正規表現、`03_ClaudeCode/hooks/block-gates.py` は文字列照合。**外部入力によるインジェクションは無防備**、`rules/speed-harness.md` H-2 の git 禁止操作（`stash`/`reset`/`clean`）は散文のみで機械が止めていない。Safety Net と Dippy はその 2 つを直接埋める。

### 1-4. Testing / Skills / Configuration

- **TDD Guard**（nizos）— ファイル操作を監視し、**TDD に反する変更を hook で止める**。`03_ClaudeCode/hooks/block-phase.py`（工程承認）と同じ発想の TDD 版
- **Superpowers**（obra）— 計画・レビュー・SDLC 全域をカバーするスキル束。`skills/dev-lifecycle/SKILL.md` の比較対象
- **fable-mode** — 多段計画・サブエージェント委譲・**自己検証**を明示的に行わせるスキル。`03_ClaudeCode/agents/` の 5 本と比較できる
- **Fixing Opus 5**（disler）— **冗語・見出し芝居を削る**追記用システムプロンプト。`rules/speed-harness.md` H-0（出力量）の外部版
- **Rulesync**（dyoshikawa）— 1 つの定義から各ツールのルール・MCP・コマンド・サブエージェントを生成。**キットの Claude / Codex 二重管理（`04_Codex/build_codex_skills.py`）の代替候補**

---

## 2. メンター層 — awesome-engineering-team-management（kdeldycke。1,135 行）

保守者は課長代理・AI テックリード・スクラムマスターを兼務している。このリストの **Cognitive Tools** と **1 on 1** 節は、キットに完全に欠けている「判断を支える側」の資産。

| 概念 | 出典 | キットへの当て方 |
|---|---|---|
| **Strong Opinions, Weakly Held** | 同リスト Brainstorming | 「直感で結論を出し、次にそれを自分で反証する」。G-3（決定の撤回条件）の型。`02_共通/ひな形/ADR-template.md` に「この決定を反証する観測」欄 |
| **The Art of Powerful Questions** | 同リスト Problem Solving | 「リーダーは問題を直すために報酬を得ていると思い込むが、本当は breakthrough thinking を促すためである」。**キットは直す仕組みしか持たない。** G-2（問い返しの型）の理論的支柱 |
| **Avoiding Intellectual Phase Lock** | 同リスト Behavioral | 期待する結果があると人は確証バイアスを混入させる。**対策は「ランダムな未知を入れて自分が結果を操作できないようにする」**。A-12「基準を緩めない」と `skills/qa-review-standards/references/personas.md` の多ペルソナ検証の理論的裏付け |
| **On Bullshit**（Frankfurt） | 同リスト Behavioral | 「嘘と違い、bullshit は**真偽がどうでもよい**発話。自信・知性・説得力の**見た目**だけを備える」。**LLM の失敗様式そのものの定義。** `05_プロジェクト管理/構想.md` の evidence-only の根拠として引用できる |
| **Intellectual Humility Cheat Sheet** | 同リスト Behavioral | 「重要なことについて考えを変えられること、かつ**いつ変えるべきかを見分けられること**」。A-5（未検証を断定しない）の対になる規範 |
| **Programmer Interrupted** | 同リスト Behavioral | 割り込み後の復帰に 15 分。1 日に途切れない 2 時間は 1 回だけ。**最悪の割り込みタイミングは編集・検索・読解の最中** | 
| **1 on 1 Meeting Questions**（VGraupera） | 同リスト 1 on 1 | 質問の大規模リスト。G-2 の「前提の確認 3 問」を発明せずここから選べる |
| **untools.co** | 同リスト Collections | 問題解決・意思決定・システム理解の思考ツール集（無料） | 

関連して **awesome-engineering-strategy**（aleixmorgadas）に Templates・Open Engineering Strategies 節があり、`05_プロジェクト管理/ロードマップ.md` の優先順位付けの型として使える。**awesome-wardley-maps** は「どの資産に投資し、どれを退役させるか」を位置で判断する手法で、資産が増え続ける問題に当たる。**awesome-maintainers**（nayafia）は単独保守者の経験談集。

---

## 3. QA — awesome-falsehood（kdeldycke。287 行）

**「プログラマが信じている誤り」の分野別カタログ**。境界値・異常系のテスト観点がそのまま取れる。収録分野: 名前・時刻・タイムゾーン・Unix 時刻・住所・居住・メール・電話番号・地理・地図・言語・プレーンテキスト・Unicode・価格・通貨・IBAN・ネットワーク・バージョン・ビルドシステム・生体認証・家族・求職者ほか。

**本セッションの UTC 事故（完了予定時刻が 9 時間ずれた）は、この中の Falsehoods about Time and Time Zones に載っている典型例。** 読んでいれば踏まなかった。

キットの `skills/qa-review-standards/references/personas.md` には「壊れた入力を渡す人」というペルソナがあるが、**渡す入力の具体リストが無い**。ここが供給源になる。

関連: **awesome-testing**（TheJambo、275 行）・**awesome-regression-testing**（mojoaxel、209 行。視覚回帰）・**awesome-code-review**（joho。Academic Papers / Articles / Books / Tools の 4 節）・**awesome-msr**（dspinellis。実証的ソフトウェア工学）・**awesome-audit-algorithms**（erwanlemerrer。アルゴリズムの第三者監査）。

---

## 4. 採用の優先順（推奨）

| 順 | 対象 | 理由 | 損益 |
|---|---|---|---|
| 1 | **Ctxlint / agnix を `check_docs.py` と突き合わせる** | 自作検査の穴（正規表現の限界）が既成ツールで埋まる可能性。まず 1 回走らせて差分を見るだけ | 益: 検査の質。損: 評価 30 分。**取り消し可能** |
| 2 | **Falsehoods about Time and Time Zones を `personas.md` に接続** | 今夜の事故が実例。観点リストは無料で、発明しなくてよい | 益: 同種の事故の予防。損: 追記 20 分 |
| 3 | **Parry-guard / Claude Code Safety Net の設計を読む** | キットの穴（外部入力のインジェクション・git 破壊操作）に直接当たる | 益: 穴が埋まる。損: 評価 40 分 |
| 4 | **Strong Opinions, Weakly Held を ADR 雛形へ** | G-3。1 行の欄を足すだけ | **ほぼ無コスト** |
| 5 | **The Art of Powerful Questions を `aidd-lead` 工程1 へ** | G-2。キットが「直す」だけで「問う」を持たない構造的欠落 | 益: メンター化の本体。損: 設計 1 時間 |
| 6 | **Schliff のスコア次元を退役基準に流用** | 資産の増加を止める判定軸（E-1） | 益: 判定が主観でなくなる。損: 評価 30 分 |
| 7 | **Rulesync で Claude / Codex の二重管理を検討** | `04_Codex/build_codex_skills.py` の保守が不要になる可能性 | 益: 保守コスト減。損: 移行リスク大。**慎重に** |

## 4-b. 実行した結果（2026-09-22。X-1 の一部を解消）

**Ctxlint を実際に走らせた。** キット直下には `CLAUDE.md` / `AGENTS.md` の実体が無い（`.template` のみ）ため、`00_導入/02_プロジェクト配布/export-project.sh` で一時ディレクトリへ配布し、その形に対して実行した。

結果: **errors 4 / warnings 8**。うち **1 件は実バグ**だった。

| 指摘 | 判定 | 対応 |
|---|---|---|
| `CLAUDE.md` が `02_共通/ひな形/implement-profile.md` を参照するが配布先に存在しない | **実バグ**。export がキット内の呼び名のまま配っていた | `export-project.sh` に `rewrite_paths()` を追加し、`02_共通/ひな形/`→`.claude/templates/`、`rules/`→`.claude/rules/`、`agents/`→`.claude/agents/` を書き換え。回帰テストで固定 |
| `rules/*.md`・`agents/` に `.claude/` 接頭辞が要る（warning 4 件） | **妥当**。配布先のエージェントには曖昧 | 同上で解消 |
| `docs/lifecycle/` が存在しない | 誤検知。`init-lifecycle.sh` が作る配布先のパス | 対応しない |
| `@AGENTS.md` が存在しない | 誤検知。import 構文であってパス参照ではない | 対応しない |
| token-budget: `CLAUDE.md` 509 トークン（除去可能 27%）／`AGENTS.md` 979 トークン（除去可能 11%、S/N 0.89） | **有用**。`06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-1 の推定値に対する外部の実測 | 未対応（B-10 の材料にする） |

**`check_docs.py` はこのバグを検出できない。** 参照をキットのリポジトリに対して解決する（`ASSET_HOME`）ため、配布先での不在が見えない。`06_保守者向け/学んだこと.md` の「出荷物が自分で通る」と「配布先で使える」は別のテスト（F-14）と同じ失敗様式の再発だった。回帰テストは `test-install.sh` に「配布された `CLAUDE.md` / `AGENTS.md` の `.claude/` 参照が実在すること」として追加した。

## 4-c. 採用の可否（全件決着。2026-09-22）

| 対象 | 判断 | 根拠 |
|---|---|---|
| **Ctxlint** | **採用（実行済み）** | 実バグ 1 件を検出。配布先のパス書き換え漏れ。`test-install.sh` に固定した |
| **Falsehoods** | **採用（反映済み）** | `personas.md` に #17〜19 と供給源の節。UTC 事故が実例 |
| **Claude Code Safety Net / Dippy の発想** | **採用（実装済み）** | `hooks/block-destructive.py`。H-2 の禁止操作を機械化 |
| **Strong Opinions, Weakly Held** | **採用（反映済み）** | `02_共通/ひな形/ADR-template.md` に撤回条件欄 |
| **The Art of Powerful Questions** | **採用（反映済み）** | `03_ClaudeCode/agents/aidd-lead.md` に前提の確認 3 問 |
| **Schliff** | **不採用（退役基準としては）／部分採用** | eval suite が無いと**上限 42%** で、全 22 スキルが 24.2〜27.9 に固まりノイズ。順位付けに使えない。ただし指摘のうち「負の適用範囲」「引き継ぎ先」は機械判定できるので**検査 12 として自前で実装**し、全スキルに追記した |
| **agnix** | **不採用** | Ctxlint と検査対象が重なる。npm / pip / cargo の 3 経路があり評価コストに見合わない。Ctxlint で足りている |
| **Rulesync** | **不採用** | Codex 対応はある（rules / commands / subagents / skills / hooks）が、**Node 依存が増える**。キットは Python ＋ bash で完結しており、`skills/nfr-standards/SKILL.md` のオフライン前提と `install.sh` の単純さを壊す。`04_Codex/build_codex_skills.py` は 1 ファイル・回帰テスト付きで現に動いている。**移行の益（保守 1 ファイル分）が損（依存・移行リスク・真実源の移動）に見合わない** |
| **token-budget の指摘** | **採用（対応済み）** | `03_ClaudeCode/CLAUDE.md.template` の hooks 節を 8 行 → 4 行に圧縮。509 → 384 トークン（−25%）。除去可能率 27% → 13% |

**残課題なし。** X-1 は Ctxlint と Schliff を実行して解消、X-2 は採用した 2 本のみ確認、X-3・X-4 は採用しなかった対象なので追う必要が消えた。

## 5. awesome 自身の維持機構（リンク集としてではなく運用の型）

`INDEX.md` と資産集合はリンク集と同じ問題を抱える。awesome.md と pull_request_template.md から取れるもの。

- **「収集ではなく厳選」** — "You should rather leave stuff out than include too much"。キットに**退役基準が無い**（追加基準だけある）
- **✅/❌ の対句で規則を書く** — PR テンプレートは全項目に正例・反例。`06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-2 が「Sonnet は決定表の形の方が従う」と自ら認定済み
- **30 日の成熟待ち** — `skills/retro/SKILL.md` の還流に成熟ゲートが無く、1 回の知見がそのまま規約になり得る
- **読了証明**（`unicorn` と書かせる） — `rules/speed-harness.md` H-4 の委譲に、指示を読んだ証明が無い

## 6. 採用しないもの

公開一覧の体裁規約（バッジ・CC0・ToC・title case。`05_プロジェクト管理/構想.md` Non-Goals）。相互レビュー義務（単独保守。多ペルソナ検証が同等の機能を果たしている）。言語別・ゲーム・ハードウェア・ブロックチェーン・CMS・Big Data の各節（対象外）。CI 系（`06_保守者向け/保守者の傾向.md` #4「自動処理を認めない」）。

## 7. 未確認（`rules/absolute-rules.md` A-5）

| # | 未確認 | 状態 |
|---|---|---|
| X-1 | 取得した 28 本のツールを動かしていない | **解消**。Ctxlint と Schliff を実行し、結果を §4-b・§4-c に記録した。不採用にした対象は動かす必要が無い |
| X-2 | awesome-claude-code の各資産の保守状況 | **解消**（採用した Ctxlint のみ確認。他は不採用） |
| X-3 | 残り 646 エントリに見落としが無いか | 27 節のうち 8 節を関係ありと判定。**言語別・ゲーム・ハード・ブロックチェーン・CMS・Big Data は対象外**（§6）。判定基準を明示したので追わない |
| X-4 | Cognitive Tools の各記事の中身 | **解消**。採用した 2 件（Strong Opinions / Powerful Questions）は本文の要約を読んで反映済み |

## 本調査の誤り（記録）

初回（同日）は readme.md の節名と 1 行説明だけを見て「awesome は AI エージェント系を収録しておらず、得られるものは少ない」と結論した。**誤り**。Miscellaneous 節に Claude Code・Gemini CLI・Copilot Agents・Generative AI・ChatGPT が収録されており、awesome-claude-code は本調査で最大の収穫だった。原因は grep のパターンに "Claude" を含めず、**866 行を全部読む前に結論を書いた**こと（A-4 網羅性・A-5 未検証を断定しない の違反）。今回は全 674 エントリを機械抽出してから判定した。

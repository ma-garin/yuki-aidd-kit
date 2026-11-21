# C4-bmad-agentos 競合: BMAD・agent-os（段1 広域）

## 対象・調べた方法・調べた件数/全件数

- 対象
  - BMAD-METHOD: `git clone --depth 1`、HEAD `e435a22`（2026-11-12）、v7 preview alpha ブランチ（README で安定版は v6.12、と記載）
  - agent-os: `git clone --depth 1`、HEAD `e892e61`（2026-10-07）、v3.0
  - キット: worktree `research-20261121`、HEAD `7e80b79`（origin/main 相当）
- 方法: clone して静的に読んだ（clone 内のスクリプト・ビルドは実行していない。`render_skill.py`・`project-install.sh` も動かしていない）。キット側は `03_ClaudeCode/agents/*.md`、`phase-approval`、`phase-gates.md`、`check_approval.py`、`block-phase.py` を読み、grep で有無を確かめた。WebSearch・WebFetch は使っていない
- 調べた件数/全件数
  - BMAD: 693 ファイル中 約 16 本を読んだ（README、CHANGELOG の一部、`skills/method/bmad-build/` の SKILL・workflow・step-01〜04・customize.toml・review-prompts/verification-gap.md、`bmod-method/roster.toml`・`retired.toml`、`bmad-project-context/SKILL.md`）
  - agent-os: 22 ファイル中 5 本（README、CHANGELOG、config.yml、shape-spec.md・inject-standards.md は見出しと要点を grep）
  - キット: 役割エージェント 6 本中 6 本（advisor を含む）、関連する規約・検査 5 本
- 根拠の種別: 両競合とも **製品文書（プロンプト・設定ファイル）** だけ。効果を測った研究・規格は無い。「BMAD の方が品質が高い」と言える実測は無い

## 同じ課題 3 つでの比較表

### 課題 A: 作った本人が自分の成果物を検証しない仕組み

| 項目 | BMAD v7 | agent-os v3 | キット |
|---|---|---|---|
| 書く役 | 文脈を持たない実装サブエージェント | 担当なし（plan mode 任せ） | build / spec / verify |
| 見る役 | 文脈なしのレンズを並列 4 本 | 担当なし | gate-agent 1 本の中で 3 役 |
| 指摘の採否 | 本線が 1 件ずつ検証して判定 | 該当なし | 役 3 が付けた severity をそのまま採用 |
| 見る側のモデル | 本線と同じ能力 | 該当なし | sonnet 固定 |

- BMAD の根拠: `bmad-build/step-04-review.md:11-12`（同じ能力・同期で並列）、`customize.toml:121-180`（blind-hunter / edge-case-hunter / verification-gap / intent-alignment。どれも「context-free subagent」）、`step-04-review.md:53`（"Disregard any severity a reviewing subagent assigned"）
- キットの根拠: `03_ClaudeCode/agents/gate-agent.md:4`（tools に Task が無い）、`gate-agent.md:17-33`、`04_Codex/skills/phase-approval/SKILL.md:23-26`（「同一セッションで 1 役ずつ」）

### 課題 B: 意図が曖昧なまま実装へ進ませない工程ゲート

| 項目 | BMAD v7 | agent-os v3 | キット |
|---|---|---|---|
| 人間が止める点 | 変更ごとの計画承認 | plan mode の承認 | 要件定義と受入の 2 点 |
| 実装前の基準 | Ready for Development 6 項目 | standards の注入 | 工程の出口基準と trace-check |
| 差し戻しの行き先 | 原因で 4 分類 | 該当なし | 指摘 ID で担当へ返す |
| 周回の上限 | 5 回 | 該当なし | 2〜3 周（場所でばらつく） |

- BMAD の根拠: `workflow.md:12-21`（Actionable/Logical/Testable(GWT)/Complete/Sufficient/Coherent）、`step-02-plan.md:65-71`（Approve and continue / Approve and stop / Review plan）、`step-04-review.md:78-98`（intent_gap / bad_plan / patch / defer）、`step-04-review.md:84`（`review_loop_iteration` が 5 を超えたら HALT）、`step-01-clarify-and-route.md:75`（作業ツリーが汚れている・ブランチが合わない → HALT）
- agent-os の根拠: `commands/agent-os/shape-spec.md:13-23`（plan mode でなければ停止）、CHANGELOG `[3.0]`（「Implementation/orchestration phases retired」）
- キットの根拠: `aidd-lead.md:12-22,51-65`

### 課題 C: 長い工程での文脈の受け渡し（膨張と欠落）

| 項目 | BMAD v7 | agent-os v3 | キット |
|---|---|---|---|
| 渡す物 | 計画ファイル 1 つが唯一の入力 | spec フォルダと standards.md | 規定なし |
| 意図の固定 | 凍結ブロックに原文を残す | shape.md の Decisions | 要件承認の版縛り |
| 中断と再開 | status で再開位置を決める | 規定なし | 工程単位の承認記録だけ |
| 規約の注入 | context: 一覧を担当が自分で読む | index.yml から選んで注入 | paths で自動、エージェントは読む物を列挙 |

- BMAD の根拠: `step-03-implement.md:21-33`（`baseline_revision` を記録、「the plan is the subagent's sole source of truth」、`context:` は担当が自分で読む）、`customize.toml:85-88`（"Launch a subagent with no prior conversation context"）、`workflow.md:25-31`（計画は 1 目標・900〜1600 トークン。上限・下限とも利用者が上書きできる提案値）、`step-02-plan.md:10`（`<frozen-after-approval>` を `preserved_intent` として保持）
- agent-os の根拠: `inject-standards.md:59-92`（`agent-os/standards/index.yml` の説明文と作業内容を照合して提案）、`shape-spec.md:181-229`（shape.md / standards.md を保存）
- キットの根拠: `aidd-lead.md:56-59`（「担当エージェントに作らせる」だけで、渡す内容の型が無い）、`phase-gates.md:9-11`（承認を版に縛る）

## 発見

### C4-bmad-agentos-01 aidd-lead の流れが承認検査と工程ブロックに必ず引っかかり、終了条件に届かない
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - `03_ClaudeCode/agents/aidd-lead.md:19-21`: 工程 2〜7 は止めずに進め、承認欄は空のまま積む
  - `aidd-lead.md:70`: 終了条件は「`check-approval.sh` が『要件定義のみ承認済み・以降は AI 検証完了』の状態」
  - `02_共通/ツール/check_approval.py:200`: 状態は「未着手 / 未承認 / 失効 / 判定不能 / 承認済み / 条件付き承認」だけ。`grep -nE 'AI 検証完了|ai-verified' check-approval.sh` は 0 件
  - `check_approval.py:304-313` `check_order`: 着手済みの工程の手前に未承認の着手済み工程があれば「工程順序」NG（exit 1）。工程 2〜7 が着手済み・未承認なら、工程 3 以降すべてで NG になる
  - `03_ClaudeCode/hooks/block-phase.py:8,13`: `.claude/phase-gate` があると、直前工程が未承認のときは `docs/lifecycle/0<n>-*.md` への書き込みを deny する。aidd-lead は工程 3 の成果物を書けない
  - `02_共通/rules/absolute-rules.md:13`（A-7「設計文書の提出後は承認前に下流へ進まない」）とも食い違う
- 状態: 主張（コードの静的読解。fixture を作っての実行はしていない）
- 改善の方向: 「AI 検証完了・人間承認待ち」を `check_approval` の状態として定義し、`check_order` と `block-phase` に aidd-lead 用の扱いを入れる。入れないなら aidd-lead の終了条件と A-7 の扱いを書き直す（どちらかに決める）

### C4-bmad-agentos-02 gate-agent の「3 役」が 1 つの文脈で動くため、役ごとに読む範囲を分けられない
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - `gate-agent.md:4`: tools は Read/Grep/Glob/Bash/Write/Edit で、Task が無い。サブエージェントを起動できない
  - `phase-approval/SKILL.md:23-26`: トークン約 7 倍を理由に、意図して「同一セッションで 1 役ずつ」にしている
  - 役 2「実装コードを読まない」（`gate-agent.md:29-30`）は、同じ文脈に前の役が読んだ内容が残るので強制できない。後の役が前の役の出力を読む順序なので、先に出た指摘に引きずられる（アンカリング）
  - 比較: BMAD は 4 本のレンズを文脈なしのサブエージェントで同時に起動し、全部返るまで他のレンズの結果を扱わない（`step-04-review.md:11-12,39`、`customize.toml:121-180`）
- 状態: 主張（定義ファイルの読解。挙動差の実測は無い）
- 改善の方向: 役 2（仕様一致）だけでも文脈なしの別起動にする。トークン制約で 3 本にできない場合は、仕様一致の 1 本だけを分ける費用対効果を測る

### C4-bmad-agentos-03 aidd-lead から各担当へ渡す内容の型（受け渡し契約）が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - `aidd-lead.md:56-59`: 「担当エージェントに作らせる」としか書いていない。`grep -rnE '委譲(の)?(プロンプト|指示書)|唯一の(入力|真実)|sole source' 03_ClaudeCode/agents` は 0 件
  - 担当側は「読む」一覧を持つ（`spec-agent.md:12-19` など）。ただし、どの工程の版・どの REQ 範囲・前周の差し戻し ID を渡すかは決まっていない
  - 比較: BMAD は計画ファイル 1 つを唯一の入力にし、目標の言い直し・ファイル一覧・CLAUDE.md の規則を受け渡しに足すことを禁じる（`step-03-implement.md:31-33`）
- 状態: 主張
- 改善の方向: aidd-lead に受け渡しの雛形（対象工程・入力ファイルと版・差し戻し ID・終了条件・返答の形）を置き、担当がそれだけを入力にする

### C4-bmad-agentos-04 レビューの指摘を本線が検証しないまま採用している
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - `gate-agent.md:31-32`: 役 3 が ISTQB severity を付けて差し戻し事項にする。「検証方法を書けない指摘は差し戻さない」という足切りはある（`gate-agent.md:34-35`）が、指摘が実際に起きるかを確かめる段は無い
  - 比較: BMAD は見る側が付けた severity を捨て、本線が引用箇所で実害を確かめて high / medium / low / false / maybe-false の 1 つを付ける。全件を Review Triage Log に 1 行で残し、前の周で判定した指摘は再検証しない（`step-04-review.md:53-75`）
- 状態: 主張
- 改善の方向: gate の出力に「指摘ごとの採否判定（偽陽性を含む）と根拠 1 行」を足し、`phase-<n>-ai.md` に残す

### C4-bmad-agentos-05 差し戻しを原因で分けず、上流の文書を直すべき指摘もコードの直しへ流れうる
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - `aidd-lead.md:61-62`: 差し戻しは「a へ戻す」だけ。`verify-agent.md:31` には「設計の欠陥 → aidd-lead へ差し戻す」があるが、gate-agent からの差し戻しには分類が無い（`gate-agent.md:57` は返す先を 3 つから選ぶだけ）
  - 比較: BMAD は 4 分類する。意図の欠け（intent_gap）は人間へ戻す。計画の不備（bad_plan）は、残すべき点（KEEP）を書き出し、コードを戻してから計画を直して作り直す。軽微な直し（patch）は同じ実装担当に直させる。持ち越し（defer）は deferred-work.md へ回す。計画の変更は Plan Change Log の制約を守らせる（`step-04-review.md:78-103`）
- 状態: 主張
- 改善の方向: 差し戻し事項に「原因の所在（要件 / 設計 / 実装 / 既存）」欄を必須にし、所在に応じて返す先と、作り直しか差分修整かを決める

### C4-bmad-agentos-06 工程の途中で中断すると、新しいセッションが再開位置を判断できない
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - `grep -rnE 'resume|再開|中断|status:' 03_ClaudeCode/agents/` の該当は `advisor.md:52` だけ。aidd-lead・担当エージェントに作業状態の記録が無い。工程単位の承認記録（`phase-<n>-ai.md`）はある
  - 比較: BMAD は計画の frontmatter `status`（draft → ready-for-dev → in-progress → in-review → done など）で再開する段を決め（`step-01-clarify-and-route.md:20`）、「承認して止める → 新しいセッションで実装から再開」を正式な選択肢にしている（`step-02-plan.md:68`）
- 状態: 主張
- 改善の方向: `docs/lifecycle/` に工程内の状態（担当・周回数・未解消の差し戻し ID）を 1 ファイルで残し、aidd-lead は起動時にそれを読む

### C4-bmad-agentos-07 build / verify に作業開始時点のリビジョン記録と、作業ツリーの事前確認が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - `grep -rnlE 'baseline_revision|基準リビジョン|ベースライン.*(HEAD|コミット)' 03_ClaudeCode/agents 03_ClaudeCode/skills/dev-lifecycle` は 0 件。`verify-agent.md:32` は修整の差分を `git apply -R` で逆適用するが、差分の起点を記録する規定が無い
  - 比較: BMAD は実装前に `baseline_revision`（HEAD の完全な識別子）を記録し、再開しても上書きしない。レビューはその起点からの差分ファイルを入力にする。作業ツリーが汚れていれば HALT する（`step-03-implement.md:21`、`step-04-review.md:29`、`step-01-clarify-and-route.md:75`）
- 状態: 主張
- 改善の方向: build-agent の開始時に起点のリビジョンを記録し、gate・verify は「起点からの差分」を入力にする

### C4-bmad-agentos-08 build-agent が全 DD を 1 本で実装し、委譲 1 本の上限（H-4）と食い違う
- 種別: 矛盾
- 深刻度: Medium
- 根拠:
  - `build-agent.md:25-33`: 1 本の中で DD-xxx を順に全部実装する。分割の規定は無い
  - `02_共通/rules/speed-harness.md:21`: 1 本は 10 分以内・触るファイル 1〜3 個・ツール 15 回以内
  - 比較: BMAD は計画を「1 つの利用者向け目標・900〜1600 トークン」に収め、独立して出荷できる成果物が 2 つ以上あれば分ける（`workflow.md:23-31`）
- 状態: 主張
- 改善の方向: aidd-lead が工程 4 で DD を独立単位に分け、build-agent を並列に起動する規定を足す

### C4-bmad-agentos-09 周回の上限が場所ごとにばらばら（2 周 / 3 周 / 3 回）
- 種別: 矛盾
- 深刻度: Low
- 根拠: `aidd-lead.md:61`（同一工程 2 周）、`spec-agent.md:30` と `build-agent.md:30`（3 周）、`verify-agent.md:36`（同一欠陥 2 周）、`phase-approval/SKILL.md` 手順 6（2 ラウンド）、`absolute-rules.md` A-12（3 回で止まる）。BMAD は 1 か所で 5 回（`step-04-review.md:84`）
- 状態: 主張
- 改善の方向: 上限の定義を A-12 の 1 か所に寄せ、エージェントは参照だけにする

### C4-bmad-agentos-10 レビュー担当のモデルが本線より低い能力に固定されている
- 種別: 機会
- 深刻度: Low
- 根拠: `gate-agent.md:5` は `model: sonnet`、`aidd-lead.md:5` は `model: inherit`。BMAD は「All review subagents must run at the same model capability as the current session」（`step-04-review.md:11`）。キットは費用の理由で既定を Sonnet にしている（`rules/model-routing.md`）ので、意図した選択でもある
- 状態: 主張（品質差の実測は無い）
- 改善の方向: ゲートの指摘の見逃しを、Sonnet と本線のモデルで同じ成果物について 1 回比べてから決める

### C4-bmad-agentos-11 差分を起点に「テストで捕まらない変更」を探す観点が無い
- 種別: 欠落
- 深刻度: Low
- 根拠: BMAD の verification-gap レンズは 4 つの型を探す。回帰を捕まえるテストが無い、新しい振る舞いを採り入れていない箇所がある、テストが働いていない、テストが変更で古くなった（`review-prompts/verification-gap.md:1-14`）。キットの verify-agent はテストを設計・実行する（`verify-agent.md:21-36`）が、変更差分に対して「このテストが無いと回帰が捕まらない」を探す段は無い
- 状態: 主張
- 改善の方向: gate の役 3（テスト工程）に、差分を起点にした検証の穴の観点を足す

### C4-bmad-agentos-12 競合 2 つとも役割ペルソナを減らしており、キットの 5 役は増やす向き
- 種別: 機会（過剰の兆候）
- 深刻度: Low
- 根拠:
  - BMAD CHANGELOG:410「Consolidate three agent personas into Developer agent (Amelia): remove Barry quick-flow-solo-dev, Quinn QA agent, and Bob Scrum Master agent」
  - `retired.toml:7-9`（removed: bmad-agent-sm, bmad-agent-qa）
  - agent-os CHANGELOG [2.1.0]「Retired the short-lived "roles" system. Too complex」、[3.0]「Implementation/orchestration phases retired—frontier models handle this well on their own now」
  - BMAD の現行の役割は roster.toml の 6 人（analyst / pm / po / ux / architect / dev）。検証は役ではなくレンズ（観点）で持つ
- 状態: 主張（各社の判断理由は自己申告で、効果の実測は無い）
- 改善の方向: verify と gate の役割の重なりを洗い、「役（エージェント）」と「観点（レンズ）」を分けて持つかを検討する

### C4-bmad-agentos-13 どの規約を適用したかを成果物側に残していない
- 種別: 機会
- 深刻度: Low
- 根拠: agent-os は `standards/index.yml` の説明文と作業内容を照合して規約を選び（`inject-standards.md:59-92`）、選んだ規約を spec フォルダの `standards.md` に保存する（`shape-spec.md:189,222-229`）。キットは paths による自動読み込みと、エージェントごとの「読む」一覧で規約を与える（`build-agent.md:15-20`）が、成果物にどの規約を当てたかの記録が無い
- 状態: 主張
- 改善の方向: 工程の成果物に「適用した規約とその版」の欄を足し、gate が照合できるようにする

### C4-bmad-agentos-14 意図との整合を見る観点はキットにもある（同等）
- 種別: 機会
- 深刻度: Low
- 根拠: BMAD の intent-alignment は、意図の原文だけを渡して「妥当な読み方を列挙 → 差分がどれを実装したか → 食い違い」を報告させる（`customize.toml:170-180`）。キットの役 2（仕様一致担当）は、上流と当該工程だけを見て落ち・変質・増分を出す（`gate-agent.md:29-30`）。目的はほぼ同じ。違いは「妥当な読み方を列挙させる」手順の有無だけ
- 状態: 主張
- 改善の方向: 役 2 の手順に「要件の妥当な読み方を列挙してから照合する」を 1 行足す

### C4-bmad-agentos-15 実装前の基準は BMAD とほぼ同等（GWT・TBD ゼロ・矛盾ゼロ）
- 種別: 機会（同等の確認）
- 深刻度: Low
- 根拠: BMAD の Ready for Development（`workflow.md:12-21`）と、キットの spec-agent の終了条件（TBD ゼロ・trace NG=0）、req-lint（EARS）、phase-gates の出口基準（`spec-agent.md:34-46`）は、意図がほぼ重なる。BMAD 側にだけあるのは、各タスクにファイルパスと具体的な作業を求める「Actionable」
- 状態: 主張
- 改善の方向: 詳細設計の出口基準に「DD ごとに対象ファイルと作業を書く」があるかを確かめる（未確認）

## 調べられなかったこと

- BMAD 安定版 v6.12（npm 配布）の中身。今回 clone したのは v7 preview alpha のブランチで、v6 の SM/QA を含む工程は CHANGELOG でしか見ていない
- BMAD の bmad-loop（エピック単位で無人実行）、Test Architect モジュール。別リポジトリなので未確認
- agent-os v2 の orchestrate-tasks・implement-tasks の実物。v3 で削除済みで、CHANGELOG の記述しか見ていない
- 両競合を実際に動かしたときの挙動・トークン消費・品質差。スクリプトを実行していない（`render_skill.py` の Jinja 展開結果も未確認）
- BMAD の docs-site、`bmad-agent-po` の workflow（チケット分割と受入）の詳細。未読
- キットの `check_approval.py` に、AI 検証完了を表す別の仕組みが無いか。`grep` で状態の列挙を見ただけで、全 400 行余りは読んでいない
- 両競合の採用実績・効果を示す第三者の研究。WebSearch を使っていない

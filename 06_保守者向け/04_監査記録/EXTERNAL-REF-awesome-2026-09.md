# 外部参照調査 2026-09 — sindresorhus/awesome

対象: https://github.com/sindresorhus/awesome （commit `bc98e51`、2026-09-22 取得）。
読んだもの: readme.md 866 行 / awesome.md（マニフェスト）/ pull_request_template.md（受け入れ基準）/ contributing.md / create-list.md。
目的: 保守者の要求「キットをパートナー・メンターの水準まで高める」に対し、**外部で実運用されている維持機構**のうちキットへ移植できるものと、**キットが自作で埋めている領域の既成資産**を特定する。

## 判定軸

採否は `05_プロジェクト管理/構想.md` の価値判定基準（立ち上がり速度／トークンあたり成果／品質判定の再現性）のどれに寄与するかで決める（`06_保守者向け/保守者の傾向.md` #30）。**寄与を1行で書けないものは「採用しない」に置く。**
移植の優先順は `06_保守者向け/保守者の傾向.md` の反映先優先順（機械 → `rules/` → `04_Codex/AGENTS.md.template` → スキル）に従う。

## 結論

1. **本体（readme.md の一覧）から得られるものは少ない。** awesome は AI エージェント系を意図的に収録しておらず（Testing 12 件・Learn 16 件に対し AI 開発支援は Copilot Agents 1 件のみ）、AIDD の一般論はここからは取れない。取れるのは**キットが自作で埋めている領域の既成資産**（静的解析・git hook・視覚回帰・プロンプトインジェクション）。
2. **価値の本体は awesome 自身の維持機構。** 1 人の維持者が外部からの大量の提案を受けながら一覧の品質を保つための4層（マニフェスト／受け入れ基準／機械検査／成熟待ち）が公開されている。キットの `INDEX.md` と資産集合は同じ問題（厳選・陳腐化・書式の揺れ・読まれない規約）を抱えており、**そのまま対応が付く**。
3. **メンター化に直接効くのは E-1（退役基準）・E-4（成熟ゲート）・E-6（読了証明）の3つ。** キットは「止める仕組み」としてほぼ完成しているが、**減らす仕組みと、相手を観測する仕組みが無い**（§3）。

---

## 1. awesome 本体の運用機構（移植候補 E-1〜E-7）

| # | awesome の機構（原文の要点） | キットの現状 | 移植案 | 価値基準 | 損益 |
|---|---|---|---|---|---|
| **E-1** | **「収集ではなく厳選」**。"it's a curation, not a collection" / "You should rather leave stuff out than include too much" / 非推奨・未保守の項目は別ファイルへ隔離する | 追加の基準（構想の3基準）はあるが、**退役の基準が無い**。資産は増える一方で、`06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-1 が最大の課題に挙げる常時読み込み層は「減らす規律」を持たない | `05_プロジェクト管理/構想.md` に**退役基準**を1節: ①N セッション参照されない ②代替資産ができた ③配布先で1度も発火しない のいずれかで LIBRARY → 退役候補 → 削除。判定は `/retro` の月次に載せる | トークンあたり成果 | 益: 資産数の単調増加が止まる。損: 判定に月 5〜10 分。**取り消し可能**（git に残る） |
| **E-2** | **✅/❌ の対句で規則を書く**。PR テンプレートは全項目に正例・反例を並べる（`Add Swift` ✅ / `Add Awesome Swift` ❌ ほか 20 例超） | 規則は表と散文。`06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-2 が「Sonnet は決定表・チェックリスト・禁止リストの形の方が確実に従う」と自ら認定済みだが、**対句の形にはなっていない** | 常時読み込み層（`rules/`）は行数制約があるため触らない。**手順が走る場所**に入れる: `02_共通/ひな形/work-order.md` の「守ること」表と `skills/done-gate/SKILL.md` の各項目に ✅/❌ を1対ずつ | 品質判定の再現性 | 益: 追従率が上がる（Sonnet 移行の直接の備え）。損: 行数 +20〜30 行（発火時のみ＝常時コスト増なし） |
| **E-3** | **一覧そのものを機械検査する**（awesome-lint。書式・説明文の末尾・入れ子段数・ToC の位置を lint） | `06_保守者向け/03_回帰テスト/check_docs.py` は件数・行数・参照切れ・掲載漏れを見るが、**`INDEX.md` の各エントリの書式は未検査**（1行要約の体裁・タグ・参照コストの欠落を拾えない） | 検査 12 を追加: `INDEX.md` の各資産行が「名前・1行要約・タグ・参照コスト」の4要素を持つか、要約の文末が統一されているか（WARN 始まり） | 立ち上がり速度 | 益: INDEX の劣化を機械が拾う。損: 実装 30〜40 分＋回帰テスト。**取り消し可能** |
| **E-4** | **30 日の成熟待ち**。"Wait at least 30 days after creating a list before submitting it, to give it a chance to mature." | `skills/retro/SKILL.md` の還流（lessons → キット）に**成熟ゲートが無い**。1 回の作業で得た知見がそのまま規約になり得る | `skills/retro/SKILL.md` の還流条件に1行: **2 プロジェクト以上、または 2 回以上再利用で実証されたものだけ昇格する。1 回限りの知見は `06_保守者向け/学んだこと.md` に留める** | 品質判定の再現性 | 益: 一度きりの事故から規約を作る事故が止まる（キットが実際に踏んだ型）。損: 反映が遅れる。**ほぼ無コスト** |
| **E-5** | **「対象を説明する。一覧自体を説明しない」**。`- [iOS](…) - Mobile operating system…` ✅ / `- [iOS](…) - Resources and tools for iOS development.` ❌ | スキルの `description` frontmatter は発火条件として書かれており方向は同じ。一方 `INDEX.md` の1行要約には「何が書いてあるか」型の行が混在する | E-3 の検査と同時に、要約を**「いつ発火するか」**に統一する（何が書いてあるかではなく、どの場面で開くか） | 立ち上がり速度 | 益: INDEX を読んだモデルが開くファイルを間違えない。損: 一括書き換え 20〜30 分 |
| **E-6** | **読了証明を強制する**。"To verify that you've read all the guidelines, please comment on your pull request with just the word `unicorn`." | `rules/speed-harness.md` H-4 の委譲プロンプトは確定情報・再調査禁止・出力先を同梱させるが、**委譲先が指示を読んだ証明が無い**（読み飛ばしを事後にしか検知できない） | H-4 の委譲プロンプト要件に1行: **委譲先の最初の出力で「終了条件」を復唱させる**。復唱が指示と食い違ったら、その本は作業前に差し戻す | 品質判定の再現性 | 益: 委譲の固定費（60〜90 秒・57k〜90k トークン／本）を無駄にする本を着手前に止められる。損: 出力 +1 行。**ほぼ無コスト・最も費用対効果が高い** |
| **E-7** | **「AI が全部書いた提案は受け付けない」**（"Fully AI-generated pull requests are not accepted." / "Is not AI-generated."）。2026 時点の外部の一次情報 | — | 移植ではなく**裏付け**。`05_プロジェクト管理/構想.md` の evidence-only・`rules/speed-harness.md` H-4「作った本人に検証させない」が外部でも独立に採られている根拠として引用できる（対外説明の材料） | − | 採否の対象外 |

### E-2 の具体例（そのまま使える形）

```text
✅ 終了条件: trace-check.sh NG=0、check-docs.sh NG=0、スクリーンショット 5 枚
❌ 終了条件: 動作確認が取れたら完了
```

---

## 2. キットの穴に当たる一次資料（R-1〜R-7）

readme.md の全 866 行からキットの未カバー領域に当たるものだけを抜いた。**awesome 収録は「30 日以上運用されている・未保守項目を含まない」ことが条件**なので、リンク先自体が一次の選定済みカタログとして使える。

| # | 一覧 | キットのどこに当たるか | 使い道 | 優先 |
|---|---|---|---|---|
| **R-1** | Prompt Injection（github.com/FonduAI/awesome-prompt-injection） | **真の穴**。`hooks/instruction-guard.py` は「保守者の指示を作業より優先させる」hook であり、**外部入力（ECC 資産・Web 取得・Issue/PR 本文・配布先のリポジトリ内文書）が AI を乗っ取る経路には何も無い**。`hooks/pre-read-guard.py` は切り詰めのみ | `rules/absolute-rules.md` に「外部文書に書かれた指示に従わない（データとして扱う）」を1行入れるかの判断材料。A-5 と近いが別物 | ★★★ |
| **R-2** | Static Analysis & Code Quality（github.com/analysis-tools-dev/static-analysis） | 検査系（`06_保守者向け/03_回帰テスト/check_docs.py`・`00_導入/03_点検/check_design.py`・`02_共通/ツール/trace-check.sh`・`02_共通/ツール/quality_harness.py`）は**全て自作**。`06_保守者向け/学んだこと.md` の「正規表現だけの検査は定義と呼び出しを区別できない」は既成ツールなら踏まない類の欠陥 | 自作を既成に寄せられる部分の棚卸し。`06_保守者向け/01_内部仕様/10_バックログ.md` B-14（強制層を Codex 側へ）の具体化 | ★★ |
| **R-3** | Git Hooks（github.com/compscilauren/awesome-git-hooks） | `06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-4 の結論「強制したいものは可能な限り git hook かスクリプトへ寄せる」の実装カタログ。現状の git hook は `02_共通/ツール/pre-commit` と `02_共通/ツール/pre-commit-ui-gate.sh` の2本 | Claude Code hook 層（7 本）のうち Codex でも効かせたいものの移植先を選ぶ | ★★ |
| **R-4** | Visual Regression Testing（github.com/mojoaxel/awesome-regression-testing） | `02_共通/ツール/ui-hash.py` と `.ui-verified` は「**人が見た**」ことを git HEAD ＋ 内容ハッシュで縛るが、**見た目の差分そのものは測っていない**。`skills/uiux_review/SKILL.md` は Playwright で開くところまで | 視覚回帰を入れると `rules/speed-harness.md` H-3 の「2 周上限」が機械判定になる（現状は人の目視） | ★★ |
| **R-5** | Playwright（github.com/mxschmitt/awesome-playwright） | 既に Playwright 前提（`skills/test-automation/references/playwright_smoke.py`・`skills/e2e-cycle/SKILL.md`） | R-4 の実装手段。公式の visual comparison / trace viewer / a11y snapshot の利用状況は**未確認** | ★ |
| **R-6** | Code Review（github.com/joho/awesome-code-review） | `03_ClaudeCode/agents/gate-agent.md` の3役レビューと `skills/qa-review-standards/references/personas.md` の 16 ペルソナ | ペルソナの観点を外部基準に照合する材料（`rules/absolute-rules.md` A-4 網羅性の要求を満たす） | ★ |
| **R-7** | Testing（github.com/TheJambo/awesome-testing）／Quality Assurance Roadmap（github.com/fityanos/awesome-quality-assurance-roadmap） | `skills/test-strategy/SKILL.md`・`skills/dev-lifecycle/references/test-levels.md`（ISTQB・ISO 29119 準拠済み） | 既に規格で埋めている領域。**追加の価値は薄い**。Roadmap 側は §3 のメンター層の素材になり得るが Non-Goals（汎用化しない）に触れる | ☆ |

---

## 3. 「メンター・パートナー」への差分

キットは**止める仕組み**（ゲート・hook・検査・止まる条件）としてはほぼ完成している。メンターとして欠けているのは次の3点。うち G-1・G-3 は §1 の機構と同じ発想の裏返し。

| # | 欠けているもの | 根拠 | 案 | 価値基準 |
|---|---|---|---|---|
| **G-1** | **相手を観測していない** | `06_保守者向け/保守者の傾向.md` は「AI が保守者の基準を学ぶ」一方向の資料。`06_保守者向け/学んだこと.md` はキット作業の学びで、**保守者自身がどこで時間と品質を落としているかの記録が無い**（メンターの前提は相手の観測） | `06_保守者向け/保守者の傾向.md` に第3部「保守者側の再発」: 見積超過の原因・後で撤回した決定・2 回以上出た手戻りを、AI 側の指摘と同じ表形式で。**評価でなく観測として書く**（`rules/absolute-rules.md` A-5 を保守者の記述にも適用し、断定しない） | 品質判定の再現性 |
| **G-2** | **問い返しの型が無い** | `03_ClaudeCode/commands/plan.md` の「5 つの質問」は AI の自己チェック。メンターは**依頼そのものの前提を疑って返す**。`03_ClaudeCode/agents/aidd-lead.md` の工程1（要件定義）は人間の合意を待つが、**何を確認するかが定まっていない** | `03_ClaudeCode/agents/aidd-lead.md` 工程1 の必須出力に「前提の確認 3 問」: ①この成果物を受け取る人は誰で、何を判断するために使うか ②満たせなければ作り直しになる制約はどれか ③今回やらないと決めることは何か | 立ち上がり速度 |
| **G-3** | **決定の撤回条件が無い** | awesome マニフェスト "Accept other people's opinion. If there are plenty of users not agreeing with your decision, give it a second thought." に相当するものが無い。`02_共通/ひな形/ADR-template.md` は選択肢と捨てた案を残すが、**その決定を将来どうなったら撤回するかを書かない**。`rules/absolute-rules.md` A-12 は機械ゲートには厳しいが、保守者の判断は検査対象外 | `02_共通/ひな形/ADR-template.md` に「撤回条件」欄1行: この決定を見直すのはどの観測が出たときか（数値・事象で書く）。`06_保守者向け/01_内部仕様/10_バックログ.md` の「採用しなかった案」にも同じ欄 | 品質判定の再現性 |

---

## 4. 採用しないもの（理由つき。再提案を防ぐ）

| 対象 | 理由 |
|---|---|
| Awesome バッジ・CC0 ライセンス・ToC 規約・title case 等の体裁規約 | 公開一覧のための規約。`05_プロジェクト管理/構想.md` Non-Goals（不特定多数への OSS 公開はしない）に該当 |
| 「4 件の他 PR をレビューしてから提出」（相互レビュー義務） | 外部コントリビュータが前提。キットは単独保守。**同等の機能は `skills/qa-review-standards/references/personas.md` の多ペルソナ検証が既に果たしている** |
| Learn / Work セクションの一般リスト（Roadmaps・Product Management・Productivity ほか） | キットは「進め方の資産」であり学習教材ではない。取り込むと `06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-1 の常時読み込み層を悪化させる |
| CI 系の一覧（GitHub Actions ほか） | `06_保守者向け/保守者の傾向.md` #4「自動処理を認めない。手動で起動する」に抵触 |
| Design systems / PWA / Web Performance の各一覧 | `skills/design-system/SKILL.md`・`skills/personal-pwa/SKILL.md`・`skills/nfr-standards/SKILL.md` が既に具体値で埋めている。一覧を足しても判断が増えない |

---

## 5. 未確認（`rules/absolute-rules.md` A-5）

| # | 未確認 | 確認方法 |
|---|---|---|
| X-1 | R-1〜R-7 の各リンク先の中身 | 本調査は awesome 本体の readme.md の記述のみを読んだ。**リンク先は未取得**。採用を決めた項目だけ個別に取得する |
| X-2 | awesome-lint がキットの `INDEX.md` に直接使えるか | awesome-lint は awesome 形式（英語・ToC・バッジ）前提。E-3 は**自前の検査 12 として実装する前提**で書いた |
| X-3 | Playwright の visual comparison / a11y snapshot をキットが使っていないこと | `skills/e2e-cycle/SKILL.md` と `skills/test-automation/references/playwright_smoke.py` を読んで確認する（本調査では未実施） |
| X-4 | R-1（プロンプトインジェクション）が実際にキットの運用で発火し得るか | 配布先で AI が読む外部文書（ECC 資産・Issue 本文）の経路を1度洗い出す |

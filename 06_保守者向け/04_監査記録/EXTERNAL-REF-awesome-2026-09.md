# 外部参照調査 2026-09 — sindresorhus/awesome

対象: https://github.com/sindresorhus/awesome （commit `bc98e51`、2026-09-22 取得）。readme.md 866 行の全エントリを走査した。
目的: キットの各資産に対し、**外部で 30 日以上運用され選定済みのカタログ**がどこにあるかを対応付ける。awesome の収録条件（30 日以上の運用・未保守項目を含まない・厳選）により、リンク先自体が一次のカタログとして使える。

**使い方**: 本ファイルは「どのリストを開けば何が埋まるか」の索引。リンク先の中身は未取得（X-1）。キットへ反映するときは、該当リストを 1 本だけ開いて必要な項目を抜く。

## 1. 直撃するもの（キットと同じ対象を扱っている）

| リスト | キットのどこ | 何が取れるか | 優先 |
|---|---|---|---|
| **Claude Code** — github.com/hesreallyhim/awesome-claude-code | `03_ClaudeCode/` 全体（commands 18 本・hooks 18 本・agents 5 本・`03_ClaudeCode/CLAUDE.md.template`） | **他人が書いたスラッシュコマンド・CLAUDE.md・hook・ワークフローの実例集**。キットは自作のみで育ってきたため、①同じ用途を他の人がどう書いているか ②キットに無い型 ③`04_Codex/AGENTS.md.template` との差 を初めて外部と比較できる | ★★★ |
| **Copilot Agents** — github.com/Code-and-Sorts/awesome-copilot-agents | `03_ClaudeCode/agents/` 5 本 | エージェント定義（目標・ループ・終了条件）の書き方の他流試合 | ★★ |
| **Gemini CLI** — github.com/Piebald-AI/awesome-gemini-cli | `04_Codex/` | Claude Code 以外のエージェントへの可搬性。`06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-4（強制層が Claude Code 専用）の他事例 | ★★ |
| **Generative AI** — github.com/steven2358/awesome-generative-ai | `skills/agent-eval/SKILL.md` | 評価・観測ツールの棚（キットは DeepEval / Langfuse で固定） | ★ |
| **ChatGPT** — github.com/sindresorhus/awesome-chatgpt | — | 直接は使わない。プロンプト資産の整理の仕方の参考 | ☆ |

## 2. QA・テスト（保守者の本業。キットの中核）

| リスト | キットのどこ | 何が取れるか | 優先 |
|---|---|---|---|
| **Falsehood** — github.com/kdeldycke/awesome-falsehood | `skills/qa-review-standards/references/personas.md`（16 ペルソナ）・`02_共通/ひな形/test/system_test_cases.csv` | **「プログラマが信じている誤り」の集大成**（名前・時刻・住所・メール・電話・通貨・ファイル名）。境界値と異常系の観点がそのままテスト設計に落ちる。キットの検証ペルソナに「壊れた入力を渡す人」はあるが、**渡す入力の具体リストが無い** | ★★★ |
| **Testing** — github.com/TheJambo/awesome-testing | `skills/test-strategy/SKILL.md`・`skills/dev-lifecycle/references/test-levels.md` | ISTQB・ISO 29119 で既に埋めた領域。**照合用**（`rules/absolute-rules.md` A-4 網羅性が求める「照合した外部基準」として使える） | ★★ |
| **Visual Regression Testing** — github.com/mojoaxel/awesome-regression-testing | `02_共通/ツール/ui-hash.py`・`skills/uiux_review/SKILL.md` | `.ui-verified` は「人が見た」ことを縛るが**見た目の差分は測っていない**。視覚回帰を入れると `rules/speed-harness.md` H-3 の2周上限が機械判定になる | ★★★ |
| **Playwright** — github.com/mxschmitt/awesome-playwright | `skills/e2e-cycle/SKILL.md`・`skills/test-automation/references/playwright_smoke.py` | 上の実装手段。visual comparison / trace viewer / a11y snapshot の利用状況は未確認（X-3） | ★★ |
| **Code Review** — github.com/joho/awesome-code-review | `03_ClaudeCode/agents/gate-agent.md`（3 役レビュー） | レビュー観点の外部基準。ペルソナの網羅性の裏取り | ★★ |
| **Empirical Software Engineering** — github.com/dspinellis/awesome-msr | `05_プロジェクト管理/構想.md` の価値判定基準・`06_保守者向け/学んだこと.md` | **証拠に基づくソフトウェア工学研究**。キットの「実測だけを書く」（A-5）を、体感でなく研究結果で裏付ける材料 | ★★ |
| **Audit Algorithms** — github.com/erwanlemerrer/awesome-audit-algorithms | `skills/agent-eval/SKILL.md`・`skills/qa-review-standards/SKILL.md` | **アルゴリズムの第三者監査**。保守者の第三者検証の役割そのもの。AI 成果物を外から検査する手法の棚 | ★★ |
| **Fuzzing** — github.com/cpuu/awesome-fuzzing | `02_共通/ツール/quality_harness.py` | 異常系の自動生成。Falsehood と対で使う | ★ |
| **QA Roadmap** — github.com/fityanos/awesome-quality-assurance-roadmap | — | QA キャリアの道筋。キットの Non-Goals（汎用化しない）に触れるが、**メンター層（§6）の素材にはなる** | ★ |
| k6 / JMeter / Gatling / Selenium / Appium / CodeRabbit | `skills/nfr-standards/SKILL.md` | 負荷試験はキットが扱っていない領域。必要になったときの入口 | ☆ |

## 3. デザイン・UI（`skills/design-system/` ・ `skills/uiux_review/` ・ `skills/personal-pwa/`）

| リスト | 何が取れるか | 優先 |
|---|---|---|
| **Design Principles** — github.com/robinstickel/awesome-design-principles | 判断の根拠になる原則集。`02_共通/ひな形/ADR-template.md` の「捨てた案と理由となる原則」欄（`06_保守者向け/保守者の傾向.md` #27）に入れる原則の出どころ | ★★★ |
| **Web Accessibility** — github.com/brunopulis/awesome-a11y | ECC の `accessibility` に依存している領域をキット側で持てる。`skills/uiux_review/references/viewpoints.md` の補強 | ★★★ |
| **Storybook** — github.com/lauthieb/awesome-storybook | `06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-3「デザインを散文でなく出荷物に」の次の一手。`02_共通/ひな形/components/` を実際に見られる形にする | ★★ |
| **Design systems** — github.com/klaufel/awesome-design-systems | `skills/design-system/SKILL.md` の他流試合。トークン設計の粒度の比較 | ★★ |
| **Progressive Web Apps** — github.com/TalAter/awesome-progressive-web-apps ／ **Service Workers** — github.com/TalAter/awesome-service-workers ／ **Offline-First** — github.com/pazguille/offline-first | `skills/personal-pwa/SKILL.md`（30 行と薄い）。オフライン前提の設計は `skills/nfr-standards/SKILL.md` の制約と直結 | ★★ |
| **PageSpeed Metrics** — github.com/csabapalfi/awesome-pagespeed-metrics ／ **Web Performance Budget** — github.com/pajaydev/awesome-web-performance-budget | `skills/nfr-standards/SKILL.md` の数値基準の出典。**指標名と閾値の根拠**（A-5 が要求する一次情報） | ★★ |
| **No-Login Web Apps** — github.com/aviaryan/awesome-no-login-web-apps | `skills/single-html-tool/SKILL.md` の実例集。ログイン無し・単一ファイルで完結する道具の先行事例 | ★★ |
| Material Design / Tailwind CSS / Web Typography / Icons / Colorful / Product Design / Web Design / Framer / Motion UI Design | `skills/design-system/references/` の各論。必要になった章だけ開く | ☆ |

## 4. 強制層・道具（`03_ClaudeCode/hooks/` ・ `02_共通/ツール/`）

| リスト | 何が取れるか | 優先 |
|---|---|---|
| **Static Analysis & Code Quality** — github.com/analysis-tools-dev/static-analysis | 検査系（`06_保守者向け/03_回帰テスト/check_docs.py`・`00_導入/03_点検/check_design.py`・`02_共通/ツール/trace-check.sh`）は**全て自作**。`06_保守者向け/学んだこと.md` の「正規表現だけの検査は定義と呼び出しを区別できない」は既成ツールなら踏まない欠陥 | ★★★ |
| **Git Hooks** — github.com/compscilauren/awesome-git-hooks | `06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-4 の結論「強制は git hook かスクリプトへ寄せる」の実装カタログ。現状の git hook は `02_共通/ツール/pre-commit` と `02_共通/ツール/pre-commit-ui-gate.sh` の 2 本 | ★★★ |
| **Prompt Injection** — github.com/FonduAI/awesome-prompt-injection | **キットの穴**。`hooks/instruction-guard.py` は保守者の指示を作業より優先させる hook であり、**外部入力（ECC 資産・Web 取得・Issue/PR 本文）が AI を乗っ取る経路には何も無い** | ★★★ |
| **Regex** — github.com/slevithan/awesome-regex | 検査スクリプトの正規表現の質。上の誤検出の直接の対策 | ★★ |
| **Shell** — github.com/alebcay/awesome-shell ／ **Command-Line Apps** — github.com/agarrharr/awesome-cli-apps | `00_導入/` の入口スクリプト群と `02_共通/ツール/` の書き方。`rules/speed-harness.md` H-2 の環境チートシートに入れる道具 | ★ |
| **SRE** — github.com/dastergon/awesome-sre ／ **Prometheus** | `02_共通/ひな形/lifecycle/09-operations.md`（保守運用工程）が薄い領域 | ★ |
| CI/CD — github.com/cicdops/awesome-ciandcd ／ GitHub Actions | `02_共通/ひな形/github/workflows/` の 4 本。**ただし `06_保守者向け/保守者の傾向.md` #4「自動処理を認めない」に抵触するため、雛形の中身の参考に留める** | ☆ |

## 5. 文書・命名（`INDEX.md` ・ `01_利用者向け資料/` ・ `02_共通/ひな形/`）

| リスト | 何が取れるか | 優先 |
|---|---|---|
| **Naming** — github.com/gruhn/awesome-naming | `06_保守者向け/保守者の傾向.md` #11（文言の規約）の裏付け。変数名・ファイル名・エラー文の命名指針 | ★★ |
| **Design and Development Guides** — github.com/NARKOZ/guides | 各社のスタイルガイド集。`02_共通/rules/` の書き方の他流試合 | ★★ |
| **Readme** — github.com/matiassingers/awesome-readme | `README.md` と `INDEX.md` の構造。エントリ書式の参考 | ★ |
| **Standards** — github.com/donBarbos/awesome-standards | `rules/absolute-rules.md` A-4（外部基準への照合）で名前を出す規格の索引 | ★ |
| Markdown / Scientific Writing / Read the Docs / Quarto | 文書生成の道具。`01_利用者向け資料/` は HTML 手書きなので、生成に寄せるかの判断材料 | ☆ |

## 6. メンター・パートナー層（保守者の役割: AI テックリード・課長代理・スクラムマスター）

キットは「作業をさせる仕組み」としてほぼ完成している。**保守者自身の判断を支える資産がキットに1つも無い**（`05_プロジェクト管理/構想.md` の Non-Goals にも入っていない＝未検討の領域）。ここが「パートナー・メンター」に最も近い。

| リスト | 何が取れるか | 優先 |
|---|---|---|
| **Engineering Strategy** — github.com/aleixmorgadas/awesome-engineering-strategy | 技術戦略の立て方と実行。`05_プロジェクト管理/ロードマップ.md` の優先順位付けの型（現状は保守者の勘と `06_保守者向け/01_内部仕様/11_目標運用モデル.md` の運用条件のみ） | ★★★ |
| **Wardley Maps** — github.com/wardley-maps-community/awesome-wardley-maps | **状況認識のための地図**。「どの資産に投資し、どれを退役させるか」を位置で判断する手法。キットの資産が増え続ける問題に効く | ★★★ |
| **Engineering Team Management** — github.com/kdeldycke/awesome-engineering-team-management | 開発者からマネジメントへの移行。課長代理の実務（1on1・評価・委譲）の材料 | ★★ |
| **OKR Methodology** — github.com/domenicosolazzo/awesome-okr | 目標設定。`05_プロジェクト管理/ロードマップ.md` のマイルストーンは作業単位で、**成果の目標が無い** | ★★ |
| **Product Management** — github.com/dend/awesome-product-management | 何を作らないかの判断。`02_共通/ひな形/lifecycle/00-rfd.md`（RFD）の前段 | ★★ |
| **Roadmaps** — github.com/liuchong/awesome-roadmaps | 技能の習得順路。メンターとしての「次に何を学ぶか」の提示 | ★ |
| **Empathy in Engineering** — github.com/KimberlyMunoz/empathy-in-engineering ／ **Mental Health** — github.com/dreamingechoes/awesome-mental-health | パートナーとしての関わり方。**キットの応答スタイルは「厳しく評価する・褒めない」（`06_保守者向け/保守者の傾向.md` #7）で固定されており、これを変えるかは保守者の決定事項** | ☆ |

## 7. 設計・アーキテクチャ（`skills/dev-lifecycle/`）

| リスト | 何が取れるか | 優先 |
|---|---|---|
| **Software Architecture** — github.com/simskij/awesome-software-architecture | `02_共通/ひな形/lifecycle/02-basic-design.md`・`02_共通/ひな形/ADR-template.md` の設計判断の型 | ★★ |
| **Domain-Driven Design** — github.com/heynickc/awesome-ddd ／ **Event-Driven Architecture** — github.com/lutzh/awesome-event-driven-architecture ／ **Microservices** | キットが扱っていない規模の設計。現状の対象（個人 PWA・単一 HTML・Streamlit）には過剰 | ☆ |

## 8. awesome 自身の維持機構（リンク集としてではなく、運用の型として）

`INDEX.md` と資産集合はリンク集と同じ問題（厳選・陳腐化・書式の揺れ）を抱える。awesome.md（マニフェスト）と pull_request_template.md から取れるもの。

| # | 機構 | キットの現状 | 移植案 |
|---|---|---|---|
| E-1 | **「収集ではなく厳選」**。"You should rather leave stuff out than include too much" / 未保守の項目は別ファイルへ隔離 | 追加の基準（構想の3基準）はあるが**退役の基準が無い** | `05_プロジェクト管理/構想.md` に退役基準を1節。判定は `/retro` の月次に載せる |
| E-2 | **✅/❌ の対句で規則を書く**（PR テンプレートは全項目に正例・反例） | `06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-2 が「Sonnet は決定表・禁止リストの形の方が従う」と自ら認定済みだが**対句の形になっていない** | 常時読み込み層は触らず、`02_共通/ひな形/work-order.md` と `skills/done-gate/SKILL.md` に ✅/❌ を1対ずつ |
| E-3 | **30 日の成熟待ち** | `skills/retro/SKILL.md` の還流に成熟ゲートが無く、1 回の作業の知見がそのまま規約になり得る | 「2 回以上再利用で実証されたものだけ昇格。1 回限りは `06_保守者向け/学んだこと.md` に留める」 |
| E-4 | **読了証明**（"comment with just the word `unicorn`"） | `rules/speed-harness.md` H-4 の委譲プロンプトに**読んだ証明が無い**（読み飛ばしを事後にしか検知できない） | 委譲先の最初の出力で終了条件を復唱させ、食い違ったら着手前に差し戻す |

## 9. 採用しないもの

Awesome バッジ・CC0・ToC 規約等の公開一覧の体裁（`05_プロジェクト管理/構想.md` Non-Goals）。相互レビュー義務（単独保守。同等の機能は `skills/qa-review-standards/references/personas.md` の多ペルソナ検証が果たしている）。ブロックチェーン・ゲーム・ハードウェア・言語別の各セクション（対象外）。

## 10. 未確認（`rules/absolute-rules.md` A-5）

| # | 未確認 | 確認方法 |
|---|---|---|
| X-1 | **各リンク先の中身は未取得**。本調査は readme.md の 1 行説明だけを読んだ | 採用を決めた項目だけ個別に取得する。優先は §1 の Claude Code、§2 の Falsehood、§4 の Static Analysis |
| X-2 | awesome-claude-code にキットと重複する資産がどれだけあるか | 開いて `03_ClaudeCode/commands/` 18 本・`03_ClaudeCode/hooks/` 18 本と突き合わせる |
| X-3 | Playwright の visual comparison / a11y snapshot をキットが使っていないこと | `skills/e2e-cycle/SKILL.md` と `skills/test-automation/references/playwright_smoke.py` を読む |
| X-4 | §6 の各リストが日本の組織文脈で使えるか（多くは英語圏の管理慣行） | 採用時に個別判断 |

## 本調査の誤り（記録）

初回（同日）の結論で「awesome は AI エージェント系を意図的に収録しておらず、本体の一覧から得られるものは少ない」と書いたが**誤り**。Miscellaneous 節に Claude Code・Gemini CLI・Copilot Agents・Generative AI・ChatGPT が収録されている。原因は grep のパターンに "Claude" を含めず、`^## ` の節名だけで AI 系の有無を判断したこと。**866 行を全部読む前に結論を書いた**（`rules/absolute-rules.md` A-4 網羅性・A-5 未検証を断定しない の両方に違反）。

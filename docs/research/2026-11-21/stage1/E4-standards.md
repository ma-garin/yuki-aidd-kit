# E4-standards 規格（ISO・ISTQB・QA4AI・NIST・OWASP）の引用の正確さと取り込み漏れ

- 対象: origin/main の worktree（research-20261121）。主に `03_ClaudeCode/skills/{qa-review-standards,nfr-standards,test-strategy,security-audit,uiux_review,agent-eval}`、`03_ClaudeCode/commands/qa-review.md`、`03_ClaudeCode/agents/*.md`、`02_共通/ひな形/test/*`、`02_共通/rules/evidence-citation.md`。`04_Codex/skills/` は同内容の複製（grep の件数が一致）で、同じ指摘が当たる。
- 調べた方法: `git grep -nE "25010|25023|29119|CT-AI|CT-GenAI|QA4AI|AI RMF|600-1|OWASP|LLM0[0-9]|Agentic"`（監査記録 CSV・docs/research を除き 375 行）→ 引用箇所を読む。規格の版は公式ページ（OWASP・NIST・ISTQB・GitHub）を WebFetch、取れないもの（iso.org は 403）は WebSearch の二次情報で確かめた。取得日はすべて 2026-11-21。
- 調べた件数/全件数: 規格 9 系統中 9 系統の版を確認（うち ISO 系 3 件は iso.org 本体が 403 で二次情報。QA4AI は版番号を確認できず）。キット内の引用は、grep で当たった 47 ファイル中、規格の版・項目名を述べている 17 ファイルを読んだ（残りは CHANGELOG・HTML 版・Codex 複製など同文の写し）。

## 規格の版（確認結果）

| 規格 | 現行の版 | 根拠 | 状態 |
|---|---|---|---|
| ISO/IEC 25010 | 2023（第 2 版。2011 を置換。9 特性。Usability→Interaction capability、Portability→Flexibility、Safety 追加） | ANSI/iTeh の 2023 版プレビュー、BIS 資料（WebSearch） | 主張（iso.org 403） |
| ISO/IEC 25023 | 2016 が現行。改訂版は DIS 段階（DIN の目標 2026-03） | iso.org/standard/89069 の検索結果、genorma "90.92 to be revised" | 主張・発行は未確認 |
| ISO/IEC/IEEE 29119 | -1:2022、-2/-3/-4:2021（一般知識。今回の検索では未確認） | — | 未確認 |
| ISO/IEC TS 42119-2 | 2025-11 発行（29119 を AI システムのテストへ適用） | iso.org/standard/84127 の検索結果 | 主張 |
| ISTQB CTFL | v4.0（2023-04-21）、v4.0.1 errata（2024-09-15） | istqb.org の CTFL v4.0.1 PDF（検索結果） | 主張 |
| ISTQB CT-AI | v2.0（2026-04-21 告知。生成 AI・LLM・red teaming を追加、ISO/IEC 25059 に整合） | https://istqb.org/istqb-releases-certified-tester-ai-testing-ct-ai-syllabus-version-2-0/ | 主張（公式ページを取得） |
| ISTQB CT-GenAI | v1.0（2025-06-10）。v1.1（2026-04-27 発効）は二次情報のみ | atsqa の v1.0 PDF（検索結果） | v1.1 は未確認 |
| QA4AI ガイドライン | 最新版の版番号・公開日を確認できず | qa4ai.jp を未取得 | 未確認 |
| NIST AI RMF | 1.0（2023-01）が現行。改訂作業中（版番号・草案なし） | nist.gov AI RMF ページの検索結果 | 主張 |
| NIST AI 600-1 | 2024-07-26 発行（2026-04-08 更新表示） | https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence | 主張（公式ページを取得） |
| OWASP LLM Top 10 | 2025 版（LLM01〜10 の名称はキットと一致）。2026 版の告知なし | https://genai.owasp.org/llm-top-10/ | 主張（公式ページを取得） |
| OWASP Agentic Top 10 | "for 2026"、2025-12-09 公開。ASI01〜10 の名称はキットと一致（一覧は二次情報） | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ | 公開日は主張、項目名は二次情報 |
| OWASP Top 10（Web） | 2025 版が公開（A01 Broken Access Control … A03 Software Supply Chain Failures、A10 Mishandling of Exceptional Conditions） | https://top10.owasp.org/2025 | 主張 |
| OWASP ASVS | 5.0.0（v5.0.0_release、5 月 30 日。年はページに無し。2025 と推定） | https://github.com/OWASP/ASVS/releases | 主張（年は未確認） |

## 発見

### E4-standards-01 qa-review-standards・/qa-review の 25010 が 2011 版の構成のまま（5 特性・「使用性」）
- 種別: 欠陥（版の古さ）
- 深刻度: High
- 根拠: `03_ClaudeCode/skills/qa-review-standards/SKILL.md:10-15`（「ISO/IEC 25010 スコアリング（5カテゴリ運用）」使用性・性能効率性・信頼性・セキュリティ・保守性。版の記載なし）、`03_ClaudeCode/commands/qa-review.md:11-16`（同じ 5 特性）、`SKILL.md:54` 報告形式 `category(25010)`。25010:2023 は 9 特性で Usability を Interaction capability に置換、Safety を追加（ANSI プレビュー等の検索結果）。キットの中心のレビュー基準が置換済みの特性名を使い、機能適合性・互換性・柔軟性・安全性を採点対象から外している。
- 状態: 実証（キットの記述）＋主張（2023 版の内容）
- 改善の方向: 版を「25010:2023」と明記し、9 特性を対象にしたうえで 5 特性に絞るなら絞る理由と対象外を書く。

### E4-standards-02 キット内で 25010 の版と特性名が 3 通りに割れている
- 種別: 矛盾
- 深刻度: High
- 根拠: `03_ClaudeCode/skills/uiux_review/references/viewpoints.md:14` は「ISO/IEC 25010:2023」で 80 観点に「対話性 - 包摂性」「柔軟性 - 設置性」「信頼性 - 無欠陥性」等の 2023 用語を付与（python で集計: 対話性 55 件・柔軟性 3 件など 22 種）。一方 `02_共通/ひな形/test/iso29119-test-completion-report.md:40-49` は版なしで 6 特性（「使用性」を含み、互換性・柔軟性・安全性なし）、qa-review-standards は 5 特性・「使用性」。uiux_review の指摘を qa-review の category に転記すると対応が取れない。
- 状態: 実証
- 改善の方向: 特性名の真実源を 1 か所（GLOSSARY か qa-review-standards）に決め、テンプレ・コマンド・観点表をそこへ揃える。

### E4-standards-03 security-audit の観点表が OWASP Top 10 2021／ASVS 4.0.3 のまま
- 種別: 欠陥（版の古さ）
- 深刻度: High
- 根拠: `03_ClaudeCode/skills/security-audit/SKILL.md:47`「OWASP Top 10（2021）と ASVS 4.0.3 の章で引いている」、`references/{node-web,python-web,streamlit,single-html-pwa}.md:1` 見出しも 2021／4.0.3、`node-web.md:9` が「A03 注入（ASVS V5.3）」。OWASP Top 10:2025 では A03 が Software Supply Chain Failures、Injection は A05、A10 Mishandling of Exceptional Conditions が新設（https://top10.owasp.org/2025）。ASVS は 5.0.0 が公開済みで章番号が変わっている（https://github.com/OWASP/ASVS/releases）。ID だけで引くと 2025 版の読者には別項目を指す。
- 状態: 実証（キット）＋主張（OWASP の現行版）
- 改善の方向: 2025／ASVS 5.0 へ ID を引き直すか、「2021 版で引く」と明記したうえで 2025 の新項目（A03 供給網・A10 例外処理）を観点に足す。

### E4-standards-04 「ISTQB severity 分類」として 4 段階の定義を ISTQB に帰属させている
- 種別: 欠陥（誤引用の疑い）
- 深刻度: Medium
- 根拠: `03_ClaudeCode/skills/qa-review-standards/SKILL.md:19-24`（Critical/High/Medium/Low とその定義を「ISTQB severity 分類」と表題）、`02_共通/ひな形/test/TESTING_STRATEGY.md:80`、`agent-eval/SKILL.md:50`「ISTQB severity連動」。ISTQB Glossary の severity は「欠陥が開発・運用に与える影響の度合い」という定義で、段階の名称・基準は定めていない（記憶による。glossary.istqb.org の取得は空応答で原文未確認）。段階の分類体系は IEEE 1044 が持つ。キット内に IEEE 1044 の言及は 0 件（`git grep -c "IEEE 1044"`）。
- 状態: 未確認（ISTQB 側の原文）
- 改善の方向: 「4 段階はキット独自の定義。severity の概念は ISTQB Glossary」と出所を分けて書く。

### E4-standards-05 qa-review-standards が自らの「原本で確認した条項だけ出す」規約に反し、テンプレが条項番号を出している
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `qa-review-standards/SKILL.md:44`「条項番号・章構成を出すのは原本で確認したものだけ」。一方 `02_共通/ひな形/test/iso29119-test-design-spec.md:20,41,49` に「29119-4 §5」「経験ベース技法（… 29119-4 §6）」「29119-2 §7」、`iso29119-test-plan.md:5,34` に節名。29119-4 の構成は 5 章が技法（5.2 仕様ベース・5.3 構造ベース・5.4 経験ベース）、6 章がカバレッジ測定と記憶しており、「経験ベース＝§6」は誤りの疑い。確認の記録はキット内に無い（grep で原本確認の記載を探して 0 件）。
- 状態: 未確認（原本未入手）
- 改善の方向: 条項番号を外して名称だけにするか、原本で確かめた記録（版・確認日）を添える。

### E4-standards-06 ISTQB の版が古い（CTFL v4.0 のみ、v4.0.1 errata を未反映）
- 種別: 欠陥（版の古さ）
- 深刻度: Low
- 根拠: `03_ClaudeCode/skills/test-strategy/SKILL.md:9`「ISTQB FL v4.0」、`02_共通/ひな形/test/TESTING_STRATEGY.md:3`「ISTQB Foundation Level Syllabus v4.0」。v4.0.1（errata）が 2024-09-15 に出ている（istqb.org の v4.0.1 PDF、検索結果）。章番号 4.2〜4.4 は v4.0.1 でも同じ（未確認だが errata の性質上変わらない見込み）。
- 状態: 主張
- 改善の方向: 「v4.0.1」と書く。

### E4-standards-07 AI システムの品質モデル ISO/IEC 25059:2023 と AI テストの規格（TS 42119-2:2025・TR 29119-11）が無い
- 種別: 欠落
- 深刻度: High
- 根拠: `git grep -c` で 25059=0、42119=0、29119-11=0、42001=0。キットは LLM・RAG・エージェントを扱う（`nfr-standards/SKILL.md:91`「LLM・エージェントを含む場合」、`agent-eval`）が、品質特性は 25010 のみ。CT-AI v2.0 は AI 品質特性を ISO/IEC 25059 に揃えたと告知（istqb.org 2026-04-21）。TS 42119-2 は 29119 を AI システムへ適用する要求を 2025-11 に規定（iso.org/standard/84127 の検索結果）。キットの 29119 テンプレに AI 固有のテスト（データ・モデル・非決定性）の枠が無い。
- 状態: 実証（キットに無いこと）＋主張（規格の内容）
- 改善の方向: nfr-standards の LLM 節と agent-eval に 25059 の AI 追加特性（機能適応性・ユーザー制御性・透明性・ロバスト性など。名称は原本で確認）を、29119 テンプレに 42119-2 への参照を足す。

### E4-standards-08 NIST AI RMF・AI 600-1 の取り込みが 0 件
- 種別: 欠落
- 深刻度: Medium
- 根拠: `git grep -c` で NIST=0、AI RMF=0、600-1=0。AI 600-1（2024-07-26、NIST 公式ページ）は生成 AI 固有リスク（作話・情報の完全性・有害バイアス・人と AI の構成・価値連鎖など。項目数・名称は今回原文未確認）と GOVERN/MAP/MEASURE/MANAGE の行動を示す。キットの `llm-agentic-top10.md` は OWASP（セキュリティ寄り）だけで、バイアス・作話の評価方針は agent-eval の Faithfulness に限られる（`agent-eval/SKILL.md:29`）。
- 状態: 実証（0 件）＋主張（600-1 の内容は記憶。未確認）
- 改善の方向: llm-agentic-top10 の隣に AI 600-1 のリスク区分とキットの対応表を 1 枚足す（OWASP と重なる行は相互参照）。

### E4-standards-09 ISTQB CT-AI v2.0／CT-GenAI の観点が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠: `git grep -c` で CT-AI=0、CT-GenAI=0。CT-AI v2.0 は生成 AI の探索的テスト・red teaming、メタモルフィックテスト・ドリフト・back-to-back を含む（istqb.org 2026-04-21）。キットの `test-strategy` は L1〜L4 とゲートだけで、非決定的な出力のテスト技法（メタモルフィック等）を挙げていない（`test-strategy/SKILL.md` を grep し該当語なし: 今回の grep 範囲で "メタモルフィック" 未検出は未実施のため未確認）。
- 状態: 実証（CT-AI 0 件）／技法の欠落は未確認
- 改善の方向: test-strategy に「AI を含む場合のテスト技法」節を足し CT-AI v2.0 の章に照らす。

### E4-standards-10 QA4AI は名前だけで、ガイドラインの軸が取り込まれていない
- 種別: 欠落
- 深刻度: Medium
- 根拠: QA4AI の出現は 3 件のみ（`03_ClaudeCode/hooks/reply_rules.py:14`「QA4AI の集計用」、`06_保守者向け/01_内部仕様/09_指摘事項.md:244`「QA4AIDD」、CHANGELOG）。ガイドラインの 5 軸（Data Integrity・Model Robustness・System Quality・Process Agility・Customer Expectation。記憶による）や生成系 WG の観点はキットに無い。最新版の版番号は今回確認できなかった。
- 状態: 実証（出現 3 件）／ガイドラインの最新版は未確認
- 改善の方向: qa4ai.jp で最新版を確かめ、agent-eval の評価観点に 5 軸を対応づける。

### E4-standards-11 llm-agentic-top10.md の「保守者が確かめてから確定」が未了のまま、記述が実体とずれている
- 種別: 欠陥
- 深刻度: Low
- 根拠: `03_ClaudeCode/skills/nfr-standards/references/llm-agentic-top10.md:9`「この表は外部アクセスなしで作った。版と項目名は保守者が公式ページで確かめてから確定する」。今回 LLM01〜10（2025）の名称は公式ページと一致、ASI01〜10 は二次情報と一致、Agentic 版の正式名は "for 2026"・2025-12-09 公開を確認。また LLM06 行の「5 エージェントの tools が全員 Bash・Write・Edit を持つ」は実体と違う: `grep -n '^tools:' 03_ClaudeCode/agents/*.md` で 6 体、`advisor.md:4` は Write・Edit を持たない。
- 状態: 実証
- 改善の方向: 確認済みの注記（確認日・URL）に置き換え、LLM06 行のエージェント数と tools を実体に合わせる。

### E4-standards-12 WCAG 2.1 を基準にしている（現行は 2.2）
- 種別: 欠陥（版の古さ）
- 深刻度: Low
- 根拠: `03_ClaudeCode/skills/nfr-standards/SKILL.md:40`「WCAG 2.1 AA準拠」、`qa-review-standards/SKILL.md:12`、`commands/qa-review.md:12`。`git grep -c "WCAG 2.2"`=0。WCAG 2.2 は 2023-10 に W3C 勧告（記憶。今回は未取得）で、フォーカスの非遮蔽・ターゲットサイズ等が追加。25010:2023 の包摂性と uiux_review の観点にも関わる。
- 状態: 実証（キット）＋未確認（2.2 の日付は今回未取得）
- 改善の方向: 2.2 AA に上げ、追加達成基準をデザイン検査（check-design 等）の観点に足す。

### E4-standards-13 25023 の引用は「概要」止まりで、改訂中であることが書かれていない
- 種別: 機会
- 深刻度: Low
- 根拠: `02_共通/rules/evidence-citation.md:29`「閾値は規格が決めない（ISO/IEC 25023 の概要）」。版の記載なし。同ファイルは「規格の引用には番号・版・発行年を付ける」と自ら書いている（同ファイル「書き方」節）。25023 は 2016 が現行で DIS 改訂中（検索結果）。
- 状態: 実証（版の欠落）
- 改善の方向: 「ISO/IEC 25023:2016（改訂中）」と書く。

### E4-standards-14 規格の版を一元管理する場所が無く、同じ古さが Codex 複製・HTML 版に写る
- 種別: 機会
- 深刻度: Low
- 根拠: 同文が `03_ClaudeCode/skills/*` と `04_Codex/skills/*` に重複（grep の行数が一致: 例 test-strategy 11/11、qa-review-standards 5/5、llm-agentic-top10 16/16）。利用者向け HTML（`01_利用者向け資料/02_操作マニュアル.html:1142`「ISO 25010とISTQBで見る」）にも版なしで写る。版を上げるとき漏れる構造。
- 状態: 実証
- 改善の方向: 規格名・版・確認日の一覧（reference 1 枚）を作り、skill からはそこを参照させる。

## 調べられなかったこと
- iso.org の 25010・25023・42119-2 の個別ページは 403。版・発行日は ANSI/iTeh/DIN/BSI と検索要約による二次情報。29119-1〜4 の版は今回の検索で出ず未確認。
- ISO/IEC 25059 の AI 追加特性の正確な名称（原本未入手）。
- ISTQB Glossary の severity の原文（glossary.istqb.org が空応答）。E4-standards-04 は記憶による。
- CT-GenAI v1.1 の発効（二次情報のみ）、QA4AI ガイドラインの最新版の版番号と日付（qa4ai.jp 未取得）、NIST AI 600-1 のリスク区分の数と名称（PDF 未取得）、WCAG 2.2 の勧告日（未取得）、ASVS 5.0.0 の公開年（ページに年なし）。
- OWASP Agentic Top 10 の ASI 名称は公式 PDF 未取得（二次情報で一致を確認）。
- 規格本文の有償原本はどれも読んでいない。

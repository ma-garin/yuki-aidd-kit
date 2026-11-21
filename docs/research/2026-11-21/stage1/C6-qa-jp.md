# C6-qa-jp 競合: QA 特化と日本語圏（段1・広域）

- 対象: QA・テスト特化の AI 開発キット／スキル集（英語圏）と日本語圏の類似キット。比較先はキット origin/main の worktree（`.claude/worktrees/research-20261121`）
- 調べた方法:
  - WebSearch 4 回（英語 QA スキル集・日本語 Zenn/Qiita・日本語設定集）、WebFetch 1 回（Zenn 記事）
  - 上位 4 件を `git clone --depth 1`（scratchpad/clones/ 配下）。読むだけで、スクリプト・ビルドは**一つも実行していない**
  - `gh api repos/<r>` でスター数・ライセンス・最終 push を取得（2026-11-21）
  - キットと競合に同じ grep 語（ペアワイズ・期待TC数・property-based・性能・ビジュアル回帰など）を当てて、ファイル数を突き合わせた
- 調べた件数／全件数: 候補 11 件（検索結果に出た QA スキル集 7・日本語記事/リポジトリ 4）のうち 5 件を読んだ（clone 4、記事 1）。全件数は母集団が不定のため不明

| リポジトリ | スター | ライセンス | 最終 push | SKILL.md 数 |
|---|---|---|---|---|
| petrkindlmann/qa-skills | 293 | MIT | 2026-11-16 | 50 |
| fugazi/test-automation-skills-agents | 269 | MIT | 2026-11-17 | 10 |
| jam0824/ai_test_process_skills（日本語） | 17 | なし | 2026-05-31 | 18 |
| kao273183/qa-claude-skill（ja README あり） | 9 | MIT＋商用の二重 | 2026-09-02 | 32 |
| ma-garin/yuki-aidd-kit（キット） | 0 | MIT | 2026-11-15 | — |

根拠: `gh api repos/<r> --jq '...stargazers_count...'` の出力と `find . -name SKILL.md | wc -l`。

## 差別化点（キットにあって競合に無いもの）

- **hook による機械的な強制**: clone した 4 件すべてで `hooks.json`／`settings.json` が 0 件（`find ... -name hooks.json -o -name settings.json | wc -l` → 4 件とも 0）。競合は手順の文書とプロンプトにとどまり、ゲートを止める仕組みを持たない。キットの README は hook で止めることを差別化の筆頭に置いている（README.md:3-12）
- **AI が書いたテストを信じる前の静的検査群**: `oracle-lint.py`（期待値の出どころ）・`test-weaken-check.py`（assert 削除や skip の追加）・`mutate-quick.py`・`passk.py`（02_共通/ツール/ 各ファイル冒頭の docstring）。競合で近いのは petr の `scripts/agent-result-gate.mjs` だけ。こちらはモデルの「passed」を証拠に数えず、ゲート自身がオラクルを実行する（同ファイル 30 行付近のコメント）。テストの弱体化を差分から拾うものは競合 4 件に見当たらなかった（未確認。grep 語は weaken/retries）
- **工程承認とハッシュ**（check-approval・phase-hash）と ISO/IEC/IEEE 29119 のひな形（02_共通/ひな形/test/iso29119-*.md の 4 本）。競合の ISTQB 対応は fugazi の `qa-manual-istqb` が最も厚いが、規格のひな形とハッシュで縛る承認は無い

## 発見

### C6-qa-jp-01 キット自身のスキルに挙動評価（evals）が無い
- 種別: 欠落
- 深刻度: High
- 根拠: petr はスキルごとに `evals/<skill>-evals.json` を持つ（例 `evals/risk-based-testing-evals.json`: `expected_patterns`／`anti_patterns`）。`scripts/run_evals.py` には static／baseline／live の 3 モードがあり、`scripts/judge_evals.py` は「yes には原文の逐語引用が必須。引用が見つからなければ unverified とし、合格に数えない」（同ファイル docstring）。キットで `grep -rnE "evals?\.json|expected_patterns|skill.*eval" 02_共通 03_ClaudeCode` → 1 件で、それも nfr-standards の文中の言及だけ。`skill-lint.py` が見るのは frontmatter の形（docstring）で、スキルを入れて出力が良くなったかではない。`agent-eval` は利用者のアプリ向け
- 状態: 実証（両方のファイルを読み、grep の件数を取った。petr の評価は実行していない）
- 改善の方向: 主要スキル（test-strategy・qa-review-standards・dev-lifecycle）に、スキル無し（baseline）とスキル有りを比べる評価ケースを置く

### C6-qa-jp-02 テスト設計に「期待 TC 数」の突合が無く、ケースの間引きを検出できない
- 種別: 欠落
- 深刻度: Medium
- 根拠: jam0824 `skills/create-test-design/SKILL.md:108-121` は設計 ID ごとに `期待TC数`・`分割方針`・`代表抽出理由` を必須とし、「代表値」「各」「など」は具体値が無ければブロッカーとする。`run-test-process/SKILL.md:97` は「実TC数 < 期待TC数 で理由が無ければ設計工程へ差し戻す」。キットは `grep -rnE "期待TC数|代表抽出|case yield"` → 0 件。`trace-check.sh` は ID がつながっているかを見るが、ケースの数が足りているかは見ない（未確認。仕様は読んでいない）
- 状態: 実証（grep）／jam の効果は主張
- 改善の方向: iso29119-test-design-spec に期待ケース数の列を足し、trace-check で実ケース数と突き合わせる

### C6-qa-jp-03 組み合わせ技法（ペアワイズ／PICT）の記述が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠: キットで `grep -rliE "pairwise|ペアワイズ|PICT|組み合わせテスト|直交表" 02_共通 03_ClaudeCode` → 0 件。技法の一覧は同値分割・境界値・デシジョンテーブル・状態遷移まで（03_ClaudeCode/skills/dev-lifecycle/references/test-levels.md:22-25）。競合は petr 5 ファイル・jam 3 ファイルがヒット（jam の分割方針に `組み合わせ展開` がある。create-test-design:116）。ISTQB CTFL 4.0 のブラックボックス技法は 4 種で、組み合わせテストは Advanced Test Analyst の範囲（規格・シラバスの記述で、本調査では再確認していない）
- 状態: 実証（grep）
- 改善の方向: test-levels.md に組み合わせテストを適用する条件（因子 3 つ以上）と道具を 1 節足す

### C6-qa-jp-04 テスト分析工程（テスト条件の抽出と質問票）が独立していない
- 種別: 欠落
- 深刻度: Medium
- 根拠: jam は テスト計画 → **テスト分析**（TA/TV の ID、`テスト分析_質問票.md`）→ 設計 → ケースを工程として分け、仕様が未確定な箇所は推測で埋めず質問票に残す（README.md「質問待ち、仕様未確定…は無理に埋めず質問票…に残します」、run-test-process/SKILL.md:81,110）。キットは `grep -rn "テスト分析\|テスト条件"` → iso29119-test-design-spec.md:49 の 1 件だけで、質問票は 0 件
- 状態: 実証（grep）
- 改善の方向: 設計仕様の前に、テスト条件の一覧と仕様への質問票をひな形として置く（人間の要件合意の入力になる）

### C6-qa-jp-05 配布経路と見つけやすさで大きく負けている
- 種別: 機会
- 深刻度: Medium
- 根拠: スター数はキット 0 に対し petr 293・fugazi 269（gh api）。petr は `npx skills add petrkindlmann/qa-skills` で Claude Code・Codex・Cursor・Gemini CLI・VS Code に入る（README.md:3-10）。fugazi は `.agent.md` と Copilot の instructions を持つ。キットは Claude Code プラグインと Codex だけ（`grep -rniE "Cursor|\.mdc|copilot-instructions"` で実質 0 件。ヒットしたのは CSS の `cursor:` だけ）
- 状態: 実証（gh api・grep）
- 改善の方向: Agent Skills 標準の形でスキルだけを切り出し、`npx skills add` で入る経路を用意する（hook は入らないと明記する）

### C6-qa-jp-06 README の差別化点に、テストを信じるための検査群が入っていない
- 種別: 機会
- 深刻度: Low
- 根拠: `grep -nE "oracle-lint|test-weaken|mutate-quick|passk" README.md README.en.md` → 0 件。README の「他の設定集に無い4点」は見積の校正・工程承認・デザイン検査・hook のログ（README.md:5-10）。テストの弱体化を拾う検査は、競合 4 件に同等品が見当たらない（上の差別化点の節）
- 状態: 実証（grep）
- 改善の方向: QA 特化の競合と比べたときの差（テストの弱体化・オラクル・変異検査）を README の比較に足す

### C6-qa-jp-07 プロパティベーステストを扱っていない
- 種別: 欠落
- 深刻度: Low
- 根拠: キットで `grep -rliE "property-based|hypothesis|fast-check|プロパティベース"` → 0 件。petr は 14 ファイル、kao は 14 ファイルがヒット（kao は `skills/property-based-test-gen` を持つ）
- 状態: 実証（grep）
- 改善の方向: test-automation に、境界値が書きにくい純粋関数へ Hypothesis／fast-check を使う指針を 1 節足す

### C6-qa-jp-08 負荷・性能テストの手順が無い
- 種別: 欠落
- 深刻度: Low
- 根拠: `grep -rliE "performance test|性能テスト|負荷テスト|k6|locust"` → 0 件。`Lighthouse|LCP|パフォーマンス` は nfr-standards・done-gate・07-system-test.md などにヒットし、Web の表示性能の目標値はある。petr は `performance-testing`、kao は `performance-test-gen` を持つ
- 状態: 実証（grep）
- 改善の方向: 対象が個人 PWA・単一 HTML 中心なら範囲外と明記し、API があるスタック（Streamlit/Python Web）向けに最小の負荷テスト手順だけ置く

### C6-qa-jp-09 ビジュアル回帰テストの記述が無い
- 種別: 欠落
- 深刻度: Low
- 根拠: `grep -rliE "visual regression|toHaveScreenshot|ビジュアル回帰"` → 0 件。`ui-hash.py` は UI ファイルのコンテンツハッシュで（docstring 2 行目）、画素の差分は見ない。petr は 11 ファイル、kao は 8 ファイルがヒット（`visual-regression-gen`）。キットは「並べて撮って比べる」を規約にしているが（speed-harness H-3）、手作業による比較
- 状態: 実証（grep）
- 改善の方向: check-screens／uiux_review の撮影に、基準画像との差分（Playwright の toHaveScreenshot）をつなぐ

### C6-qa-jp-10 探索的テストの「発見 → 仮説 → 確認」と次回への申し送りが無い
- 種別: 機会
- 深刻度: Low
- 根拠: Zenn「nascimento_qa」記事（https://zenn.dev/nascimento_qa/articles/916dd983e10add 、2026-05-07 公開、取得日 2026-11-21）の `qa-explore` は 23 の観点で探索し、同じ傾向の Finding が 2 件そろうと Hypothesis に昇格させて Probe で確かめる。セッションの終わりに申し送りを書く。キットの探索観点は Whittaker のツアー（qa-review-standards/SKILL.md:29）と atarimae-quality-audit の欠陥クラスの列挙で、仮説へ昇格させる規則は見当たらなかった（grep「仮説|Hypothesis」→ atarimae-quality-audit/SKILL.md に 0 件）。記事のリポジトリは公開されていない（記事に記載なし）。効果の数値も無い
- 状態: 主張（記事の記述）
- 改善の方向: atarimae-quality-audit に、同じ傾向の指摘 2 件で仮説に昇格させる規則と、次回への申し送りの 1 節を足す

### C6-qa-jp-11 日本語圏には、強制の仕組みを持つ QA キットの競合が見つからなかった
- 種別: 機会
- 深刻度: Low
- 根拠: 日本語の候補は jam0824（17 スター・ライセンス無し・Codex 向けで、Claude 向けは別に指示が要る。README 冒頭）、nascimento の記事（リポジトリ未公開）、Qiita の記事（プロンプト集の販売や体験談。https://qiita.com/aipapalog/items/25c03a629f807d35f5ca ・https://qiita.com/ktsubone/items/6df0a850e8a0a53c03af ）。kao は ja の README を持つが、本文（例 skills/test-master/SKILL.md）は繁体字中国語。キットで `grep -rniE "JSTQB"` → 0 件で、VSTeP は uiux_review/references/viewpoints.md:9 の 1 件だけ
- 状態: 主張（検索 3 回の範囲。網羅は未確認）
- 改善の方向: JSTQB の用語集・テスト観点（VSTeP など）との対応表を置き、日本語の QA 実務者に向けて差別化する

### C6-qa-jp-12 取り込み元のライセンスに制約がある
- 種別: 欠陥（取り込むときのリスク）
- 深刻度: Low
- 根拠: jam0824 は `license=null`（gh api）なので、再利用の許諾が無い。kao の LICENSE は「営利企業の社内ワークフローでの利用を含む商用利用は Commercial License が必要」（LICENSE 1-15 行）。petr と fugazi は MIT
- 状態: 実証（gh api・LICENSE を読んだ）
- 改善の方向: 発想（期待 TC 数・質問票）だけを参考にし、文面は複製しない。複製するなら MIT の 2 件に限り、出典を記録する

## 調べられなかったこと

- 競合のスクリプト（run_evals.py・agent-result-gate.mjs ほか）は実行していない。効果と動作は静的に読んだ範囲だけ
- sethdford/claude-skills（QA toolkit）・javalenciacai/qaskills・github/awesome-copilot の breakdown-test・PramodDutta/qaskills は検索で出たが、clone していない
- 日本語の Qiita/Zenn は検索 3 回の範囲だけ。GitHub の日本語リポジトリは網羅的に検索していない（GitHub の検索 API は使っていない）
- 競合の評価結果や効果の数値（バグ検出率など）は原データが無く、引用していない。petr の「6+ production sites」は README の主張で、確認していない
- キットの trace-check.sh がケース数を数えるかどうかは仕様を読んでいない（02 の補足）

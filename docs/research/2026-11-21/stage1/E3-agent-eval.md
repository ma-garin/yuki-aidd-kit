# E3-agent-eval 研究: エージェント評価（段1・広域）

- 対象: キットの `03_ClaudeCode/skills/agent-eval/`（SKILL.md 72 行・references 3 件）、`03_ClaudeCode/commands/eval.md`、`02_共通/rules/quality-decision.md`、`02_共通/ツール/passk.py`、`06_保守者向け/03_回帰テスト/skill_trigger_eval.py`・`test-agents.sh`・`skill-triggers/agent-eval.jsonl`。Codex 版（`04_Codex/skills/agent-eval/SKILL.md`）は生成物で、diff の差はヘッダ 2 行だけ（`diff` で確認）
- 調べた方法: `git ls-files | grep -iE 'agent-eval|quality-decision|eval'` で対象を特定 → 全文を読む → `git grep -nIiE 'pass@|pass\^|swe-bench|position bias|self-preference|複数回実行|非決定|judge|校正|contamina|汚染'` で関連箇所を横断 → 一次資料（arXiv 6 本・OpenAI 2 本・Anthropic 1 本）を WebFetch / WebSearch で取得（取得日 2026-11-21）
- 調べた件数/全件数: キット側 9/9 ファイル（上の対象一覧。eval に関係するファイルを grep で拾った全件）。外部資料 9 件（下の各発見に URL）。スクリプトは実行していない（静的に読んだだけ）

## 外部資料の要点（条件つき）

| 資料 | 種類 | 条件と数値 |
|---|---|---|
| Aleithan ほか「SWE-Bench+」arXiv:2410.06992（2024-10） | 研究 | SWE-agent+GPT-4 の成功パッチのうち解答漏れ 32.67%、テストが弱く通った疑い 31.08%。除外後の解決率 12.47%→3.97% |
| Liang ほか「The SWE-Bench Illusion」arXiv:2506.12286（2025-06、v4 2025-12） | 研究 | issue 文だけでバグのファイルパスを当てる正答率が SWE-bench Verified で最大 76%、SWE-bench 外のリポジトリで最大 53%（記憶の示唆。モデル名は概要に無い） |
| OpenAI「Why we no longer evaluate SWE-bench Verified」（2026-02-23） | 製品文書 | 汚染を理由に報告を停止。モデルがよく失敗する問題を監査した部分集合の 59.4% 以上で、正しい解を落とすテストの欠陥 |
| OpenAI「Separating signal from noise in coding evaluations」（2026-07-08） | 製品文書 | SWE-bench Pro 731 件のうち自動判定 200 件（27.4%）、人手 249 件（34.1%）が壊れている。SWE-bench Pro 推奨を撤回 |
| Zheng ほか「Judging LLM-as-a-Judge」arXiv:2306.05685（2023） | 研究 | 位置・冗長・自己強化の偏りを特定。GPT-4 judge と人の一致は 80% 超（人同士と同程度）。MT-Bench/Chatbot Arena の対話評価が対象 |
| Panickssery ほか arXiv:2404.13076（NeurIPS 2024） | 研究 | 自己認識の能力と自己選好の強さが線形に相関（GPT-3.5・Llama 2 の微調整実験）。要約のみ確認・本文未読 |
| Miller「Adding Error Bars to Evals」arXiv:2411.00640（2024-11） | 研究 | 推奨 5 つ: CLT の標準誤差を併記／まとまりのある問題はクラスタ標準誤差／問題ごとに複数回サンプリングして平均（温度を下げて分散を減らさない）／2 モデル比較は問題単位の差（paired）／事前に検出力分析 |
| Atil ほか arXiv:2408.04667（v5 2025-04） | 研究 | 決定的設定（temperature 0 等）の 5 モデル・8 タスク・10 回で出力が揺れる |
| Yao ほか「τ-bench」arXiv:2406.12045（2024-06） | 研究 | pass^k（k 回すべて成功）を提案。gpt-4o の retail で pass^8 < 25% |
| Anthropic「Demystifying evals for AI agents」（2026-01-09） | 製品文書 | pass@k と pass^k の定義、複数試行、決定的な grader 優先、LLM judge は専門家と校正、20〜50 件を実際の失敗から、正例と負例の両方、「専門家 2 人が独立に同じ判定」になる課題、参照解で解けることを示す、多試行で 0% は課題の故障を疑う、試行ごとに環境を隔離（前の試行の git 履歴を使った例）、capability と regression を分ける、トランスクリプトを読む |
| Chen ほか（Codex）arXiv:2107.03374（2021） | 研究 | 1 問 100 サンプルで 70.2% を解く。pass@k の不偏推定量は本文にあり、概要ページでは確認できず（未確認） |

## 発見

### E3-agent-eval-01 ／ judge の揺れを temperature=0 で抑える指示が一次資料と食い違う
- 種別: 欠陥
- 深刻度: High
- 根拠: `03_ClaudeCode/skills/agent-eval/SKILL.md:57`「temperature=0で安定化、必要なら複数回平均」。Miller arXiv:2411.00640 Sec.3 は「分散を減らすために温度を下げない。複数回サンプリングして平均する」。Atil arXiv:2408.04667 は temperature 0 等の決定的設定でも 10 回の実行で出力が揺れると報告
- 状態: 主張（文書間の突合。キット側で揺れを実測していない）
- 改善の方向: 「temperature=0 で安定化」を消し、judge も被評価側も複数回実行して平均と標準誤差を出す手順に置き換える

### E3-agent-eval-02 ／ 回帰ゲートに統計的な判定が無く、20〜50 件の点推定の低下で落とす
- 種別: 欠落
- 深刻度: High
- 根拠: `SKILL.md:47`「ベースライン比でスコア低下したらCIで落とす」、`SKILL.md:44`・`references/eval_dataset_schema.md:32` は 20〜50 件。標準誤差・信頼区間・paired 差・検出力の語は agent-eval 配下に無い（`git grep -nIiE 'judge|校正|...'` の結果に該当なし）。Miller の推奨 1・4・5
- 状態: 主張（50 件でどれだけ揺れるかは未実測）
- 改善の方向: スコア表に標準誤差を併記し、ベースラインとの比較は問題単位の paired 差で判定し、件数は検出したい差から検出力分析で決める

### E3-agent-eval-03 ／ 被評価エージェントの複数試行（pass^k）が agent-eval に無く、既存の passk.py とも結ばれていない
- 種別: 欠落
- 深刻度: High
- 根拠: agent-eval の複数回は judge の平均だけ（`SKILL.md:57`）。`git grep -nI passk` の参照先は `02_共通/ツール/passk.py` 本体・`test-oracle-tools.sh`・目録・ロードマップ・`export-project.sh` で、agent-eval・eval.md からは参照なし。quality-decision は「AI の判定を組み込んだ部分は複数回実行の対象」（`02_共通/rules/quality-decision.md:64`）と言うが実行手段への導線が無い。τ-bench の pass^8 < 25%（gpt-4o retail）、Anthropic 2026-01 の pass^k
- 状態: 実証（grep で参照の無さを確認）
- 改善の方向: agent-eval の運用フローに「各ケース k 回実行して pass@k / pass^k / 成功率」を入れ、quality-decision:64 から passk.py へ導線を張る

### E3-agent-eval-04 ／ LLM-as-judge の既知の偏りと対策が書かれていない
- 種別: 欠落
- 深刻度: High
- 根拠: agent-eval で judge の注意は「judge が違えばスコアがずれる」（`SKILL.md:56`）と「数件を目視突合して校正」（`SKILL.md:58`）だけ。位置・冗長・自己強化の偏り（Zheng arXiv:2306.05685）、自己選好（Panickssery arXiv:2404.13076）の語は無い（`git grep -nIiE 'position bias|self-preference'` で 0 件）。judge を GPT-4o 系に固定（`SKILL.md:16`）しているため、被評価システムも同系列なら自己選好が入る条件になる
- 状態: 主張（キットで偏りを測っていない）
- 改善の方向: 比較採点では順序を入れ替えて 2 回採点し、judge は被評価側と別系列にし、観点ごとに別 judge で採点する

### E3-agent-eval-05 ／ judge の校正が「数件の目視」で、一致の数え方と合格線が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠: `SKILL.md:58`。Anthropic 2026-01「LLM judges should be closely calibrated with human experts」「Unknown を返せる逃げ道」。Zheng は人同士の一致（80% 超）を比較の基準にしている
- 状態: 主張
- 改善の方向: 人手ラベル付きの校正セットを持ち、judge と人の一致率（または κ）を記録して閾値をベースラインから決める（evidence-citation の「閾値は自チームのベースラインから」に合わせる）

### E3-agent-eval-06 ／ 課題（データセット）の妥当性検査が無く、壊れた課題を見分けられない
- 種別: 欠落
- 深刻度: Medium
- 根拠: `references/eval_dataset_schema.md:5-38` のフィールドは id/input/expected/context/tags/source だけで、参照解・課題の曖昧さの確認・負例の割合の下限が無い。SWE-Bench+ で通ったパッチの 31.08% が弱いテスト、OpenAI 監査で 59.4% 以上が正しい解を落とすテスト、SWE-bench Pro は約 30% が壊れている。Anthropic「専門家 2 人が独立に同じ判定」「参照解で解けることを示す」「多試行で 0% は課題の故障を疑う」
- 状態: 主張
- 改善の方向: スキーマに参照解・2 人判定の一致記録を足し、多試行 0% のケースを課題の故障候補として先に点検する手順を入れる

### E3-agent-eval-07 ／ 公開ベンチマークの汚染・故障についての指針がキットに無い
- 種別: 欠落
- 深刻度: Medium
- 根拠: `git grep -nIiE 'contamina|汚染'`（skills・rules）の該当は Playwright のブラウザ汚染と prototype 汚染だけで、ベンチ汚染の記述は無い。SWE-bench 系はキット内で目録 CSV（`06_保守者向け/04_監査記録/EXTERNAL-REF-github-2026-09.csv:4225` 等）に名前があるだけ。外部: SWE-Bench+（12.47%→3.97%）、SWE-Bench Illusion（76% 対 53%）、OpenAI 2026-02 の報告停止と 2026-07 の Pro 推奨撤回
- 状態: 実証（grep で不在を確認）／外部数値は主張
- 改善の方向: model-routing・agent-eval に「公開ベンチの点数はモデル選定の根拠にしない。自前の課題（実際の失敗由来）で測る」と根拠つきで書く

### E3-agent-eval-08 ／ passk.py が試行間で作業環境を隔離しない
- 種別: 欠落
- 深刻度: Medium
- 根拠: `02_共通/ツール/passk.py:55-58` は同じ cwd で `subprocess.run(cmd)` を k 回呼ぶだけで、作業ツリー・キャッシュの初期化は無い。Anthropic 2026-01: 残ったファイル・キャッシュが相関した失敗や水増しを生む（前の試行の git 履歴を使った例）。決定的なテストの再実行では問題になりにくいが、エージェント実行を k 回回す用途では成立しない
- 状態: 実証（コードを読んで確認。実行はしていない）
- 改善の方向: エージェント試行に使う場合は試行ごとに worktree / 一時ディレクトリを作り直すオプションか注意書きを付ける

### E3-agent-eval-09 ／ スキル発火の評価が 1 回実行・少数ケースで、閾値の判定が粗い
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `06_保守者向け/03_回帰テスト/skill_trigger_eval.py:17,133` `--runs` 既定 1、合格線 `--min-hit 0.8`。`skill-triggers/agent-eval.jsonl` は 6 行で `"none"`（負例）は 1 件（`wc -l`・`grep -c '"none"'`）。正例 5 件だと 1 件外れただけで 0.8 の境界になり、1 回実行では揺れと区別できない。Atil（決定的設定でも揺れる）、Anthropic（正例と負例の両方、複数試行）、Miller（標準誤差）
- 状態: 実証（件数と既定値を確認。発火率は未実測）
- 改善の方向: 既定 runs を 3 以上にし、負例を増やし、発火率に標準誤差を添えて閾値をまたぐときだけ判定保留にする

### E3-agent-eval-10 ／ キット自身のエージェント（aidd-lead 等）に挙動の評価が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠: `06_保守者向け/03_回帰テスト/test-agents.sh:1-13` は `03_ClaudeCode/agents/*.md` を `grep -qF` で文字列検査するだけ。`git grep -lI 'claude -p'` で実際にモデルを呼ぶ評価は `skill_trigger_eval.py` だけ（他は資料・目録）。quality-decision:56-57 は L3・L4 で範囲と検証者を求めるが、委譲・差し戻しの挙動を多試行で測る仕組みが無い
- 状態: 実証（grep で確認）
- 改善の方向: 実際の失敗例から 20〜50 件の課題を作り、エージェントを k 回走らせて pass^k とトランスクリプトで見る回帰 eval を用意する

### E3-agent-eval-11 ／ capability eval と regression eval の区別が無い
- 種別: 欠落
- 深刻度: Low
- 根拠: `SKILL.md:43-48` は回帰ゲートだけ。Anthropic 2026-01: capability は低い合格率から登る山、regression はほぼ 100% を保つ。高合格率の capability を regression へ移す
- 状態: 主張
- 改善の方向: データセットに用途（capability / regression）を付け、合格線を別にする

### E3-agent-eval-12 ／ スコアだけで判断し、トランスクリプトを読む手順が無い
- 種別: 欠落
- 深刻度: Low
- 根拠: `SKILL.md:62-67` の出力はスコア表・回帰判定・構築手順。トレースは記録する（`SKILL.md:48`）が読む工程が無い。Anthropic「多くの試行のトランスクリプトと採点を読まないと grader が効いているか分からない」
- 状態: 主張
- 改善の方向: 回帰判定の出力に「落ちたケースのトランスクリプトを読み、エージェントの誤りか grader の誤りかを分類」を足す

### E3-agent-eval-13 ／ passk.py の pass@k が文献の定義（確率の推定量）と名前だけ一致する
- 種別: 矛盾
- 深刻度: Low
- 根拠: `02_共通/ツール/passk.py:4,71` は 1 コマンドについて「1 回でも合格」を 1.00/0.00 で出す。Chen 2021 の pass@k は n 回サンプルから問題ごとに確率を推定し課題集合で平均する量（不偏推定量の式は本文。今回は概要ページのみで未確認）。Anthropic も確率として定義。「pass@5: 1.00」を確率と読み違える余地がある
- 状態: 主張
- 改善の方向: docstring に「単一コマンドの指標で、文献の pass@k（課題集合での確率推定）とは別」と 1 行添えるか、課題集合を受け取る場合は不偏推定量で出す

### E3-agent-eval-14 ／ judge モデルの版を固定する指示が無い
- 種別: 欠落
- 深刻度: Low
- 根拠: `SKILL.md:16,56` は「GPT-4o 系」「ベースライン比較は同一 judge」とだけ書き、スナップショット名の固定・記録が無い。提供側の版更新で同名でもスコアがずれうる（未検証）
- 状態: 未確認（提供側の版更新がスコアに与える影響はキットで測っていない）
- 改善の方向: ベースラインに judge のモデル ID（スナップショット）と設定を記録し、変わったらベースラインを取り直す

## 調べられなかったこと

- Miller 論文の数式の詳細（HTML 版から推奨 5 項目だけ取得）。Chen 2021 の pass@k 不偏推定量の式は概要ページに無く、本文を開いていない
- Panickssery 2024 は検索の要約だけで本文未読。後続研究で自己選好が条件次第で消えるとする報告（2026 プレプリント）もあり、結論は割れている
- SWE-bench Illusion の 76%/53% のモデル別内訳（概要に無い）
- キットの eval 系スクリプトの実行結果（調査の制約で実行していない。skill_trigger_eval の発火率・passk.py の動作はすべて静的読み）
- DeepEval の G-Eval・Faithfulness 自体の人手一致率（製品側の公表値を探していない）
- OpenAI 2026-07 記事のモデル側の試行回数・分散（記事に記載なしと要約された）

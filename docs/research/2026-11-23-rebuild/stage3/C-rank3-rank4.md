# 段3 反証 C: 順位 3（偽の合格）・順位 4（導入で資産が消える・届かない）

- 対象コミット: 3ef90fd（origin/main）。作業ツリーは $ROOT（git worktree）
- 調べ方: 発見本文（stage1・stage2）を読み、3ef90fd の現物で根拠行を再確認。I2-tools-01・I2-tools-02・I8-install-01 は一時ディレクトリ／一時 HOME で単体実測。他は `git grep`・`git log`・ソース読み。回帰テスト・run-all.sh・CI は実行していない
- 11/21 以降の関連コミット（`git log --since=2026-11-21`）: 3 件のみ
  - 2114f37 docs: キット強化調査（docs/research/2026-11-21/ のみ変更）
  - 42f5ffc fix: statusline の進捗行を非表示（`03_ClaudeCode/hooks/statusline.py` 1 行のみ）
  - 3ef90fd 上記 PR のマージ
  - 9 件の根拠行に触れるコミットは無い。「既に直っている」で反証できた件は 0
- 維持すべき正しい部分（弱めない）: `run-all.sh` の合格判定（`RUN=FOUND` かつ `FAIL=0`）、`trace-check.sh` の ID 連鎖・版ハッシュ照合、C7・C8 の「判定不能は合格に数えない」（stage1 I2-tools.md:141）。下の欠陥は、この方針が test-metrics の基準行と trace-check の C1〜C6 の入口に及んでいないという範囲の話で、これらの仕組み自体を否定するものではない

## I2-tools-01
- 結果: 維持
- 根拠: `02_共通/ツール/test_metrics.py:480-482`（`m = CRITERIA_RE.search(thr)` → `if not m: continue`）は同一。CRITERIA_RE（:52）は ASCII 演算子と 6 つの指標名だけ。gate_code（:505-510）は残った評価だけで判定
- 実測: 一時ディレクトリに ST-001 pass・ST-002 fail と、基準 3 行（`progress >= 100`・`failed ≦ 0`・`合格率 95% 以上`、出典あり）を置き `test_metrics.py --gate` を実行 → 出力は「✓ 1. 消化」の 1 行のみ、「判定候補: **進める**」、`gate_exit=0`。行 2・3 は警告なしで消えた
- 反証の試み: 「別の仕組みで防がれている」を探したが、捨てた件数・警告の出力は無い。出典が空の行は dropped に数える実装があるので、書式不一致だけが漏れている（対照は stage2 の B 表で exit=1）
- 深刻度: High のまま。ただし前提は「人が基準を全角・日本語で書く」こと。雛形が機械可読の書式を案内しているかは未確認
- 偽の合格に当たるか: 当たる。fail 1 件・合格率 50% の入力に exit 0

## I2-tools-02
- 結果: 維持
- 根拠: `02_共通/ツール/trace-check.sh:75-80`（`FILES=$(find ... | sort)` を文字列で持ち、後段で引用符なし展開）は同一
- 実測: `d d/01_requirement.md`（REQ-F-001）と `d d/02 basic-design.md`（未定義の REQ-F-009 を参照）を置いて実行 → 「✅ NG=0（定義済み ID: 0 件）」、rc=0。定義 ID が 0 件と出るので注意深い人には気づける手がかりはある
- 反証の試み: 実運用のパスに空白があるか。キットの通常配置（`01_QAツール` 等）には無い。空白は利用者のプロジェクトのパス次第（例: iCloud の `Mobile Documents`、`My Project`）で、発生条件は限定的
- 深刻度: High から Medium に下げる余地あり（理由: 発生条件がパスの空白に限られ、「定義済み ID: 0 件」の表示が残る）。ただし不合格入力に NG=0・rc=0 を返す点は事実
- 偽の合格に当たるか: 当たる。未定義 ID 参照があるのに NG=0

## I3-tests-01
- 結果: 維持（ただし順位 3 の根本原因には当たらない）
- 根拠: stage1 I3-tests.md:22-74 の失敗は、`04_Codex/skills-manifest.json` と生成物の食い違い（design-system・uiux_review）と、check_docs.py の spec 同期 33 件。`git log --since=2026-11-21 -- 04_Codex 06_保守者向け/03_回帰テスト` は 0 件、`skills-manifest.json` の最終変更は 2026-11-14 以前。11/21 以降に直すコミットは無い
- 偽の合格に当たるか: 当たらない。これは検査が正しく FAIL を返している「本物の不合格」で、検査の偽合格ではない。問題は「赤のままマージされた」（`kit-ci.yml` が `workflow_dispatch` のみ）という運用で、順位 3（検査が偽の合格を返す）の根本原因に当たらない
- 今も赤か: 未実施（回帰テストは保守者の要求時のみの決まり）。HEAD の変更が statusline.py と docs のみなので、11/21 時点の赤が残っている見込みだが、推測であり未確認
- 深刻度: High のまま（別順位の問題として）

## R4-note-01
- 結果: 維持
- 根拠: `02_共通/ツール/test-weaken-check.py:6`、`:31-33`、`:59`（OK_RE）、`:178-193`。差分の ±3 行にこの差分で足された `weaken-ok: <8 字以上>` があれば許可。承認者の記録（approver）への接続は無い。ファイル削除も差分内のどこかに `weaken-ok: <ファイル名> <理由>` を足せば許可（:32）
- 反証の試み: 「前からあった weaken-ok は数えない」（:33）で将来の素通りは防がれているが、同じ差分で AI が書き足す経路は防がれていない。`done-gate/SKILL.md:15` も「近くに weaken-ok: <理由>」と案内している。実行はしていない（ソース確認）
- 深刻度: High のまま。ただし「全く検出しない」ではなく、検出したうえで自己申告で許可できる。assert 削除・skip 追加の検出自体は有効で、維持すべき
- 偽の合格に当たるか: 部分的に当たる。弱体化した差分に、AI が書いたコメントだけで合格を返せる。設計上の許可口なので、判定ロジックの誤りではなく承認統制の欠落

## E2-llm-testgen-01
- 結果: 維持（ただし「偽の合格」ではなく「網羅の欠落」）
- 根拠: `git grep -nIlE 'oracle-lint|mutate-quick|passk' -- 03_ClaudeCode 04_Codex 02_共通/rules 02_共通/ひな形 .claude-plugin .github` → 0 ファイル。参照は INDEX・CHANGELOG・構成品目目録・export-project.sh:17・`test-oracle-tools.sh`（回帰テスト）だけ。done-gate が呼ぶ検査は test-weaken-check のみ（`SKILL.md:15`）
- 反証の試み: export-project.sh:17 で配布はされるので「死蔵」ではない。ただしテスト方針・検証エージェントから呼ばれない
- 偽の合格に当たるか: 当たらない。呼ばれないので合格も不合格も返さない。検査が無い（網羅の欠落）であり、順位 3 の判定基準（不合格であるべき入力に合格を返す）に合わない
- 深刻度: High から Medium へ（理由: 誤った合格ではなく未使用の追加検査。ただし LLM テストの欠陥検出力を測る段が無い点は別の順位の問題として残る）

## I8-install-01
- 結果: 維持
- 根拠: `00_導入/01_インストール/install.sh:33-37`（`cp "$CLAUDE_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md.bak"`）・`:39-43`（AGENTS.md も同じ）。退避名は固定で、日時・連番なし。`export-project.sh:25-30` の `backup_if_exists` も固定名 `.bak`（`cp -r`）
- 実測（一時 HOME）: `.claude/CLAUDE.md`=ORIGINAL、`AGENTS.md`=ORIG_AGENTS を置き install.sh を 2 回実行 → run1 rc=0、run2 rc=0。`CLAUDE.md.bak` の先頭は `@AGENTS.md`、`AGENTS.md.bak` の先頭は `# AGENTS.md（共通規約…`（どちらもキットの雛形）。`grep -rlx -e ORIGINAL -e ORIG_AGENTS` は 0 件。退避ファイルは 2 つのみで世代なし
- 反証の試み: 1 回目には「手動マージ推奨」の警告が出る。2 回目にも同じ警告が出るが、退避の中身が既に雛形であることは示さない。利用者が 1 回目の直後に退避を移せば防げるが、キットの再実行（更新）は通常の操作
- 深刻度: High のまま（取り消せない。再現は 100%）

## D1-distribution-02
- 結果: 維持（I8-install-01 と同一の事象。stage1 の別 ID）
- 根拠・実測: 上記 I8-install-01 と同じ。install.sh:33-43 の固定名上書きを一時 HOME で 2 回実行して確認
- 深刻度: High のまま。I8-install-01 に統合して数えるのが妥当（重複計上すると順位 4 の件数が過大になる）

## S3-cc-skills-01
- 結果: 維持（件数は一致。深刻度は見直し）
- 根拠: `grep -lE '(0[0-6]_[^ /]+/|\.\./\.\./)' 03_ClaudeCode/skills/*/SKILL.md | wc -l` → 14（発見と同数）。`CLAUDE_SKILL_DIR`・`CLAUDE_PLUGIN_ROOT` を含む SKILL.md は 0 件。`design-system/SKILL.md:17,26,112` はキット直下のパスを参照
- 反証の試み（部分的に成立）: install.sh:63 は `02_共通/ひな形/tokens.css` を `~/.claude/templates/` へ、:90 は check_approval.py など 3 本を `~/.claude/scripts/` へコピーする。つまり一部の実体は導入先にあるが、SKILL.md が書くパスはキット直下の名前のままで、そこへは解決しない。`00_導入/03_点検/check-design.sh` を導入先へ置く行は、確認した範囲（install.sh の grep 結果）では見つからない（未確認）
- 深刻度: High から Medium へ（理由: 資産は消えないし参照が切れるだけ。AI が cwd にキットが無いと気づいて別の探し方をする余地があり、実害の有無は未測定）
- 順位 4 の基準（資産が消える・届かない）には「届かない」側で当たる

## S2-cc-plugins-01
- 結果: 維持（数値は更新）
- 根拠: `.claude-plugin/plugin.json:3` `"version": "8.7.0"`、`VERSION`=8.7.0。plugin.json の最終変更は 1d9f163（2026-11-10）。`git log --oneline 1d9f163..HEAD | wc -l` → 26（発見の 23 は 2114f37 の親時点。研究 PR・statusline 修正・マージの 3 件が増えた）。うち製品パス（03_ClaudeCode・02_共通・04_Codex・.claude-plugin）に触れるのは 14 件、docs・chore 系の題名が 7 件
- 反証の試み: 「23 コミットがすべて利用者に有意な変更」ではない。製品パスを触るものは 14 件で、全件が届かないのではなく届かない対象は半数強。また、グローバル規約は「バージョンを上げるのは明示的に頼まれたときだけ」と定めており、版固定は規約どおりの運用の結果でもある。版を上げない運用が欠陥か方針かは保守者の判断
- 更新挙動（版固定だと更新されない）は公式文書の引用に基づく主張で、今回は再取得していない（未確認）
- 深刻度: High から Medium へ（理由: 規約上の意図的な運用で、実害は plugin 利用者に限られる）

## 集計

| ID | 結果 | 深刻度 |
|---|---|---|
| I2-tools-01 | 維持 | High |
| I2-tools-02 | 維持 | Medium（見直し） |
| I3-tests-01 | 維持（順位 3 に非該当） | High |
| R4-note-01 | 維持 | High |
| E2-llm-testgen-01 | 維持（網羅の欠落） | Medium（見直し） |
| I8-install-01 | 維持 | High |
| D1-distribution-02 | 維持（I8 と同事象） | High |
| S3-cc-skills-01 | 維持 | Medium（見直し） |
| S2-cc-plugins-01 | 維持 | Medium（見直し） |

9 件すべてに結果を付けた。反証された件は 0。

## 未確認・未実施
- I3-tests-01: 3ef90fd で回帰テストが今も赤かは未実施（要求時のみの決まりのため）
- I2-tools-01: 雛形が機械可読の基準書式を人に案内しているか（人が全角で書く頻度）は未確認
- S3-cc-skills-01: `check-design.sh` など 00_導入 配下のスクリプトが導入先に置かれるかは、install.sh の一部（grep の範囲）だけ確認。全体は未確認
- S2-cc-plugins-01: 版固定時の更新挙動は公式文書の再取得をしていない。Claude Code 本体での再現も未実施
- R4-note-01: 実行はしていない（ソースの静的確認のみ）
- export-project.sh の 2 回実行による退避上書きは、ソース確認のみで実行していない
- 注: 作業中に `trace-check.sh` を cwd=$ROOT で実行したため、`trace-check-report.md` が出力される設計のスクリプトが $ROOT 直下に書いた可能性がある。`git status --short` には現れなかった（無視設定か別の場所の可能性。確認は未了）

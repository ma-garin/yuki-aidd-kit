# C1-superpowers 競合: obra/superpowers

- 対象: obra/superpowers（`git clone --depth 1`、HEAD `22f0b463` 2026-11-03）と yuki-aidd-kit（worktree research-20261121 = origin/main `7e80b79`）
- 調べた方法: clone の静的読解のみ（スクリプト・テストは実行していない）。kit 側は `git grep` / `ls` / `wc` / settings.json の hook 配線を python で列挙。WebSearch・WebFetch は未使用
- 調べた件数/全件数: superpowers の 236 ファイル中、hooks 全 4・SKILL.md 15 本中 7 本（using-superpowers / verification-before-completion / test-driven-development / executing-plans の scripts 2 本 / subagent-driven-development / writing-skills の testing 参照 / diagnosing-superpowers の cost-and-time）・docs/testing.md・positive-instruction 設計書・tests の 3 本を精読。約 25/236
- 取得日: 2026-11-21

## 比較表（同じ課題 3 つ）

| 課題 | superpowers | yuki-aidd-kit |
|---|---|---|
| 見積と中間報告 | 仕組みなし | hook で強制 |
| 完了前の検証 | 文章＋台帳スクリプト | DoD＋検査スクリプト |
| TDD を守らせる | Iron Law の文章 | 自前の規定なし |

補足（表の外）:
- 見積と中間報告: superpowers は見積の規定を持たない（`grep -rniE "estimat|timebox|status update|minutes" skills` で該当は待機時の規定だけ）。待機中だけ「5〜10 分の区切りで 1 行の状況報告」（skills/subagent-driven-development/SKILL.md:187-196）。kit は reply-language.py:259-352（見積と経過の乖離 1.5 倍／3 分の 1 の検出）・tool-timer.py・Stop/PreToolUse の停止ゲートで機械強制
- 完了前の検証: superpowers は「NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE」（verification-before-completion/SKILL.md:16-18）＋ `task-done` がテストの exit 0 のときだけ台帳に完了行を書く（executing-plans/scripts/task-done:42-54）。kit は done-gate（DoD 照合）・test-weaken-check.py・trace-check / check-approval / test-metrics・`.ui-verified`
- TDD: superpowers は「NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST / Write code before the test? Delete it.」（test-driven-development/SKILL.md:33-45）。kit は external-skills.json:604 で `tdd` を source=null で列挙するのみ。test-strategy は「tdd が発動した場合も…」と外部依存（03_ClaudeCode/skills/test-strategy/SKILL.md:3）

## 発見

### C1-superpowers-01 完了検証の手順を外部スキルに依存し、kit 単体では欠ける
- 種別: 欠落
- 深刻度: High
- 根拠: 03_ClaudeCode/skills/done-gate/SKILL.md:3 が「検証コマンドを実際に走らせて証拠を取る手順は verification-before-completion に従い」と書く。`git ls-files | grep -i verification-before` は 0 件。実体は 00_導入/01_インストール/external-skills.json:688-691 の `npx skills add obra/superpowers -g --skill verification-before-completion`（競合の外部スキル）。外部導入が無い環境では参照先が空
- 状態: 実証（git grep / git ls-files）
- 改善の方向: 証拠取得の手順（IDENTIFY→RUN→READ→VERIFY）を done-gate 本体か kit 内 reference に取り込み、外部依存を外す

### C1-superpowers-02 TDD を守らせる規定が kit 内に無い
- 種別: 欠落
- 深刻度: High
- 根拠: `git grep -iE "red.?green|テストファースト|test-first|\bTDD\b" -- 03_ClaudeCode 02_共通` の該当は test-strategy の description 1 件のみ。external-skills.json:604-607 の `tdd` は source/install とも null。superpowers は Iron Law・Verify RED 必須・「先に書いたコードは削除」（test-driven-development/SKILL.md:31-45, 113-115）
- 状態: 実証
- 改善の方向: 赤を見た証拠（失敗出力）を残す規定を test-automation に足し、test-weaken-check と組み合わせて「赤→緑」の記録を DoD 項目にする

### C1-superpowers-03 機械判定の停止ゲートに誤判定時の安全弁が無い（superpowers は hook で止めない設計）
- 種別: 欠陥
- 深刻度: High
- 根拠: CLAUDE.md（kit）「違反 1 回で停止ファイルが書かれ全ツールが deny。解除の環境変数は無い」。今回のワークフロー起動依頼の本文に「誤判定で停止」の記録依頼がある（利用者の記述）。reply-language.py のコメントに誤判定の履歴（例 :276「2026-10-10 に 11 回誤判定」、:333「偽の乖離」）、`git grep -c "誤判定|誤検知|偽の" 03_ClaudeCode/hooks` で 6 ファイル計 17 件。対して superpowers の hook は SessionStart 1 本のみで文脈注入だけ（hooks/hooks.json, hooks/session-start）。停止ゲート本体のコードは読めていない（権限拒否）
- 状態: 主張（kit 文書と利用者の記述。誤判定の頻度・ゲートの判定ロジックは未確認）
- 改善の方向: 停止ゲートに誤判定の回帰テスト集（過去の誤判定ケース）を持たせ、判定根拠をログに残して解除時に原因を特定できるようにする

### C1-superpowers-04 規律スキルの「圧力下で守るか」を測る評価が無い
- 種別: 機会
- 深刻度: Medium
- 根拠: superpowers は「スキル無しで失敗させる（RED）→スキルで遵守（GREEN）→抜け道を塞ぐ」を規定（skills/writing-skills/references/testing-skills-with-subagents.md:9-46）し、tests/systematic-debugging/pressure-scenarios/ に圧力シナリオ（例 test-pressure-1.md: 損失額・上司の催促・時間圧）を置く。docs/testing.md は実 CLI を駆動する evals（Quorum）を記述。kit は skill_trigger_eval.py（06_保守者向け/03_回帰テスト/skill_trigger_eval.py:6 `claude -p ... --max-turns 1`）で発火のみ測り、skill-triggers は 23/27 本。遵守の評価は `git grep -iE "pressure|rationaliz"` で kit 内 0 件
- 状態: 実証（kit 側の不在）／主張（superpowers の evals の効果。evals ディレクトリは clone に無く外部リポジトリ、未確認）
- 改善の方向: 見積・done-gate・A-12 など規律系だけ、時間圧つきシナリオで遵守率を測る評価を足す

### C1-superpowers-05 「言い訳表（Red Flags / Rationalization）」が kit のスキルに無い
- 種別: 機会
- 深刻度: Medium
- 根拠: superpowers は各規律スキルに「考え→現実」の表を置く（using-superpowers/SKILL.md:33-50、verification-before-completion/SKILL.md:50-72）。設計書 docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md:24-35 は「Recognition tables work」「Composition prohibitions backfire」を測定に基づき主張（opus、各 5 回、プログラム採点。例: 禁止文で再記述 4.4 件、無指示 3.6 件、手順文 3.0 件）。kit の 03_ClaudeCode/skills で `git grep -iE "rationaliz|Red Flags|言い訳"` は 0 件
- 状態: 主張（測定は n=5・単一モデル・superpowers 自身の実験。一般化は未確認）
- 改善の方向: done-gate・見積の規定に「よくある言い訳→現実」の短い表を足す。禁止文は手順文へ置換を検討

### C1-superpowers-06 テスト成功時だけ完了を記録する台帳スクリプト
- 種別: 機会
- 深刻度: Medium
- 根拠: executing-plans/scripts/task-done:42-54 はテストを実行し、exit≠0 なら「NOT recorded」で終了、成功時だけ `Task N: complete (commits a..b, tests: <cmd> → <最終行>)` を progress.md に追記。完了の主張とテスト出力・コミット範囲が 1 行で結びつく。kit の done-gate はチェックリストで、完了記録と実行結果を機械で結ぶ仕組みは CURRENT_STATE.md 手書き（done-gate/SKILL.md 共通項目）
- 状態: 主張（静的読解。実行していない）
- 改善の方向: 「テスト exit 0 のときだけ完了行を書く」小スクリプトを kit の作業記録（implement.md）に接続する

### C1-superpowers-07 差し戻し上限で止めた後の打ち手（モデル昇格・新規担当）が無い
- 種別: 機会
- 深刻度: Low
- 根拠: superpowers の fix-loop は 5 回上限、1〜3 回は同じ担当を再開、4〜5 回は新しい担当をより強いモデルで起動（subagent-driven-development/references/fix-loop.md:20-34）、5 回で breaker。kit は A-12 で 3 回目に止まり 5 項目報告（02_共通/rules/absolute-rules.md:20）。途中で担当・モデルを替える規定は model-routing の「Sonnet が 2 周で収束しない」だけ
- 状態: 主張
- 改善の方向: A-12 の 2 回目失敗時に「新しい担当＋上位モデル」を 1 回挟む選択肢を検討（上限は 3 のまま）

### C1-superpowers-08 SKILL.md の長さの回帰検査が無い
- 種別: 機会
- 深刻度: Low
- 根拠: superpowers の tests/skill-size/test-skill-size.sh:1-31 は圧縮後の再添付が 20,000 文字で切れる（同ファイルの記述、#2481 参照）として SKILL.md 20,000 バイト未満を検査。kit は現状 27 本とも 20,000 バイト未満（`wc -c` で OVER 0 件）だが、同等の検査は 06_保守者向け/03_回帰テスト で `git grep 20000` の該当なし
- 状態: 実証（kit 側の計測）／主張（20,000 文字で切れるという Claude Code の挙動は未確認）
- 改善の方向: test-skill-scan.sh に SKILL.md のバイト上限を 1 項目足す

### C1-superpowers-09 待ち中の「区切り報告」は kit とほぼ同等、根拠付きで一致
- 種別: 機会（kit の方が強い点の裏付け）
- 深刻度: Low
- 根拠: superpowers は委譲待ちを 5〜10 分区切り＋1 行の状況報告＋子の生存確認（subagent-driven-development/SKILL.md:187-196）。kit は見積×60÷5 秒の中間行と生存確認 stat -L（speed-harness H-0・H-4・A-8）で、間隔が見積に比例し短い。機械検査は kit のみ
- 状態: 主張
- 改善の方向: なし（kit が上位）。superpowers の「生きている子の一覧と未報告の催促」を A-8 の手順に 1 行足す程度

### C1-superpowers-10 判断の記録書式「Ruling: 決定 — 理由 — 誤りのコスト」
- 種別: 機会
- 深刻度: Low
- 根拠: subagent-driven-development/SKILL.md:20-31。止まる理由を 4 つ（取り消せない操作・セキュリティ・作業木の外の副作用・計画が破綻）に限定し、それ以外は判断して台帳に記録。kit の AGENTS.md「判断は自分で下して宣言」と方針は同じだが、記録書式（誤りのコスト欄）は無い
- 状態: 主張
- 改善の方向: CURRENT_STATE.md の雛形に「判断（決定／理由／外れたときの損）」欄を足す

## kit の方が強い点
- 見積・中間報告・実測の機械強制（hook 21 配線。settings.json を列挙: PreToolUse 8・Stop 2 ほか）。superpowers には見積の概念自体が無い（grep で確認）
- 工程（V 字）・追跡（trace-check）・人間承認（check-approval, approver 欄を AI が埋めない）。superpowers は brainstorming→plan→実行で、承認の機械判定は無い（`grep -rn approver` は未実施・未確認）
- テスト弱体化の検出（02_共通/ツール/test-weaken-check.py）と E2E の flaky 履歴（e2e-cycle/SKILL.md:90）
- 破壊操作・秘密ファイル・注入の PreToolUse/PostToolUse 防御（block-destructive / pre-read-guard / injection-guard）。superpowers の hook は SessionStart のみ

## 調べられなかったこと
- kit の停止ゲート hook 本体の判定ロジック（読み取りが権限で拒否された。誤判定の原因は未確認）
- superpowers の evals（Quorum / superpowers-evals）の実データ・遵守率（clone に evals/ が無く外部リポジトリ。未取得）
- superpowers の残り SKILL.md 8 本（brainstorming / writing-plans / systematic-debugging 本文 等）の精読
- 両者を同じタスクで実際に動かした比較（実行は禁止のため未実施）

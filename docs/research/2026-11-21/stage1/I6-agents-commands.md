# I6-agents-commands 内部実装: agents・commands（段1 広域）

- 対象: `03_ClaudeCode/agents/`（6 件: advisor / aidd-lead / build-agent / gate-agent / spec-agent / verify-agent）、`03_ClaudeCode/commands/`（25 件）、Codex 版の `04_Codex/skills/agent-*`（6 件。本文の一致だけ確認）、エージェントが呼ぶ判定スクリプト（`02_共通/ツール/check_approval.py`・`trace-check.sh`・`test_metrics.py`・`00_導入/03_点検/check-design.sh`）、配布スクリプト（`install.sh`・`init-lifecycle.sh`・`init-test-docs.sh`）、hook `block-phase.py`、回帰テスト `06_保守者向け/03_回帰テスト/test-agents.sh`、`.claude-plugin/plugin.json`
- 調べた方法: `find` で agents/commands を全件列挙し、agents 6 件を全文、commands は 25 件全件の frontmatter の有無を確認し、うち 14 件を全文で読んだ。判定スクリプトは該当箇所を読み、2 件は scratchpad の合成プロジェクトで実行して再現した（`check_approval.py`・`trace-check.sh`。キットのリポジトリには書いていない）。製品仕様は Claude Code 公式文書 1 件（https://code.claude.com/docs/en/sub-agents 、取得日 2026-11-21）を参照した
- 調べた件数/全件数: agents 6/6（全文）、commands 25/25（frontmatter）・14/25（全文: agent-ready / compact-work / doc-search / e2e-cycle / ecc-daily / eval / lifecycle / phase-review / qa-review / retro / rfd / security-audit / test-metrics（先頭のみ）/ trace。未読 11 件: app-scan / cancel-ralph / grill / implement / new-pwa / plan / quality-card / ralph / sdd-start / token-check / wait-what）、Codex 版の agent-* 6/6（本文の一致のみ）

---

### I6-agents-commands-01 aidd-lead の「工程 2〜7 は止まらない」が check-approval の工程順序検査とぶつかり、終了条件の状態を判定器が表せない
- 種別: 矛盾
- 深刻度: Critical
- 根拠:
  - `03_ClaudeCode/agents/aidd-lead.md:19-21` 工程 2〜7 は承認欄を空のまま進める。`:70` 終了条件は「`check-approval.sh` が『要件定義のみ承認済み・以降は AI 検証完了』の状態」
  - `02_共通/ツール/check_approval.py:299-309` `check_order()` は、直前の着手済み工程が「承認済み／条件付き承認」でなければ `工程順序` NG を出す。「AI 検証完了」に当たる状態は無い（`git grep -e "AI 検証完了"` で出たのは文書 3 件・agent 定義 2 件だけで、判定コードには無い）
  - 再現（scratchpad の合成プロジェクト。工程 2〜4 に着手し、phase-2.md は「判定: 未記入」）: `check_approval.py --root <合成>` の結果は `着手済み 3 工程 / 承認済み 0 工程 ❌ NG=5（未承認 3・工程順序 2）`。「第3工程 詳細設計 — 直前の第2工程 基本設計 が『未承認』のまま着手されています」
  - `gate-agent.md:22` が毎工程 `check-approval.sh --phase <n>` を回すため、工程 3 以降は必ず NG になり、差し戻しが収束しない（または無視される）
  - `.claude/phase-gate` を置いたプロジェクトでは `block-phase.py` が工程 3 以降の成果物への書き込みを止める（`block-phase.py:77-100`）
- 状態: 実証
- 改善の方向: 「AI 検証完了・承認待ち」を check_approval の正式な状態（例: `phase-<n>-ai.md` の差し戻し 0 件＋ハッシュ一致）として定義し、aidd-lead 経路の工程順序検査をその状態で通す。または aidd-lead の流れを判定器に合わせる

### I6-agents-commands-02 「工程 2〜7 すべてで trace-check NG=0」は工程 8 の UAT が採番されるまで達成できない
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - `aidd-lead.md:69`・`spec-agent.md:10,36` が工程ごとに `trace-check.sh` NG=0 を終了条件にしている
  - `02_共通/ツール/trace-check.sh:224-228` C5 は REQ-F に `UAT-xxx`、REQ-N に `ST-xxx` を必須とし、`-`（非該当）を認めない。工程を意識した判定は無い
  - 再現（scratchpad。REQ-F-001 と BD-001 だけを定義し、追跡表に BD-001 を割り当て、残りの列は `-`）: `NG=1 — カバー漏れ: REQ-F-001 — 受け入れテスト未割当（REQ-F は UAT 必須）`
- 状態: 実証
- 改善の方向: trace-check に「工程 n まで」の指定（例: `--upto <工程>`）を足して下流の列を検査から外し、agent の終了条件をその呼び方にする

### I6-agents-commands-03 agent が叩く `./scripts/check-approval.sh`・`./scripts/req-lint.py`・`./00_導入/03_点検/check-design.sh` が配布先に無い
- 種別: 欠落
- 深刻度: High
- 根拠:
  - `init-lifecycle.sh:102-110` が配布先の `scripts/` に置くのは `trace-check.sh` と `section_hash.py` だけ。`init-test-docs.sh:27` が置くのは test-metrics 系。`install.sh:88-91` は `check_approval.py`・`phase-hash.py`・`req-lint.py` を `~/.claude/scripts/` に置くが、`check-approval.sh` のラッパは置かない
  - `grep -rn "cp .*check-approval\|cp .*req-lint" 00_導入` で配布先 `scripts/` への複写は 0 件（`install.sh:90` の `~/.claude/scripts` だけ）
  - 参照している箇所: `aidd-lead.md:70`・`gate-agent.md:22`・`commands/lifecycle.md:158`・`commands/phase-review.md:188`（check-approval.sh）、`spec-agent.md:43`（req-lint.py）、`build-agent.md:28`（キットからの相対パスの check-design.sh）。`commands/rfd.md:249`・`lifecycle.md:162` の `./00_導入/02_プロジェクト配布/init-lifecycle.sh .` もキットの中でしか通らない
- 状態: 実証（配布スクリプトの読解と grep。配布先での実行失敗そのものは再現していない）
- 改善の方向: init-lifecycle で `check-approval.sh`＋`check_approval.py`＋`phase-hash.py`＋`req-lint.py` を同梱する。agent 側は `~/.claude/scripts/` の解決順を書く

### I6-agents-commands-04 approver の人間判定は禁止語の一覧だけで、AI が人名を書けば通る。承認記録への書き込みは hook が常に許可する
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - `check_approval.py:63-68,182-186` は AI 語（ai / claude / gpt / agent / エージェント 等）の禁止語一覧で判定している。実行結果は次のとおり。`approver_is_ai('aidd-lead')=False`、`'Sonnet'=False`、`'Opus'=False`、`'Fable'=False`、`'山田太郎'=False`、`'ma-garin'=False`、`'人工知能'=False`、`'ｇａｔｅ'=False`（`'gate-agent'`・`'Claude'`・`'AI'` は True）
  - `block-phase.py:77-78` は `docs/lifecycle/approvals/` への書き込みを「常に許可」する。gate-agent は Write/Edit を持つ（`gate-agent.md:4`）
  - 「AI は approver を埋めない」を担保しているのは文面（`aidd-lead.md:22`・`gate-agent.md:14`・`phase-review.md:205`）と、`test-agents.sh:48` の「approver という文字列がある」検査だけ
- 状態: 実証（禁止語の関数を実行して確認。agent に実際に書かせる再現はしていない）
- 改善の方向: 承認を本文の外の証拠（人間の端末での署名付きコミット、または `phase-<n>.md` 本体への書き込みを subagent・AI から拒む hook で `phase-<n>-ai.md` だけを許可）に結び付ける

### I6-agents-commands-05 lifecycle コマンドは「全 10 工程で人間の承認が必須」、aidd-lead は「人間は 2 点だけ」
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `commands/lifecycle.md:158`（`check-approval.sh --gate` が exit 0 以外なら着手しない）・`:176`（全 10 工程の出口で人間の承認が必須）に対し、`aidd-lead.md:12-21`、利用者グローバル CLAUDE.md「人間が入るのは要件定義の合意と受け入れ判定の 2 点だけ」。同じキットに 2 つの承認モデルがあり、どちらが優先かは書かれていない
- 状態: 実証（文面の照合）
- 改善の方向: 2 つのモード（逐次承認・一括承認）として phase-gates.md に定義し、コマンドと agent の両方がそれを参照する

### I6-agents-commands-06 tools 指定が越えない線より広い（gate-agent の Edit、advisor の Bash、spec-agent の無制限 Read）
- 種別: 過剰
- 深刻度: Medium
- 根拠:
  - `gate-agent.md:4` は `Write, Edit` を持つが、`:14` の許可範囲は `phase-<n>-ai.md` への追記だけ。成果物本体を書き換えられる
  - `advisor.md:4` は Bash を持ち、`:56` の「状態を変えるコマンドを実行しない」は文面だけ
  - `spec-agent.md:19` の「実装コードを読まない」に対し、Read/Grep/Glob に範囲の制限が無い
  - 公式文書には `disallowedTools`・`permissionMode`（`plan` 等）・サブエージェント単位の `hooks` がある（https://code.claude.com/docs/en/sub-agents 、2026-11-21）。キットの agent はどれも使っていない（6 件の frontmatter は name/description/tools/model だけ）
- 状態: 実証（frontmatter）／製品仕様は主張（公式文書）
- 改善の方向: advisor に `permissionMode: plan` を付けるか Bash を外す。gate-agent から Edit を外し、agent 単位の hook で書き込み先を `approvals/phase-*-ai.md` に限る

### I6-agents-commands-07 aidd-lead の委譲先を限定していない。上限の周回数も文面だけ
- 種別: 欠落
- 深刻度: Medium
- 根拠: `aidd-lead.md:4` `tools: ... Task`（無制限）。公式文書では `Agent(worker, researcher)` の形で起動できる型を限定できる。`Task` は 2.1.63 で `Agent` に改名され、別名として有効（同 URL）。「同一工程 2 周まで」（`aidd-lead.md:61`）・「上限 3 周」（`spec-agent.md:30`・`build-agent.md:29`）を機械で止めるもの（`maxTurns` 等）は無い（6 件とも frontmatter に無し）
- 状態: 実証（frontmatter）／製品仕様は主張
- 改善の方向: `tools: Agent(spec-agent, build-agent, verify-agent, gate-agent, advisor), ...` に絞り、各 agent に `maxTurns` を付ける

### I6-agents-commands-08 作成と判定の独立が崩れる経路がある（Codex 版は 1 人で演じる、verify-agent は自分で直して自分で残数を判定する）
- 種別: 矛盾
- 深刻度: Medium
- 根拠:
  - `gate-agent.md:42` 「成果物を書いた者がその工程のゲートを兼ねない」に対し、`04_Codex/skills/agent-aidd-lead/SKILL.md:6-8`「この役割を自分で演じる…自分で演じるか、その SKILL.md をサブエージェントに渡す」。Codex では統括・実装・ゲートが同じ文脈になりうる
  - `verify-agent.md:22-36` はテストの作成・実装の修整・Critical/High 残数の判定を 1 つの agent が行う（`:41` に自己レビューを禁じる記述はあるが、終了判定は自分で出す）
  - gate-agent は 3 役を 1 つの文脈で順に回す（`gate-agent.md:17-33`）。役どうしの独立は前提の 5 行と「前の役の出力を読む」だけ
- 状態: 実証（文面）。独立が崩れたことによる見落としの実害は未確認
- 改善の方向: Codex 版でゲート役は別のサブエージェントに渡すことを必須にする。verify-agent の残数判定は gate-agent の `test-metrics.sh --gate` だけを根拠にする

### I6-agents-commands-09 verify-agent の `git apply -R` 手順に適用し直す工程が無い
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `verify-agent.md:32`「修整の差分を `git apply -R <patch>` で逆適用し赤に戻ることを確認」。直後に再適用（`git apply <patch>`）して緑に戻すことを確かめる手順が無い。差分ファイルの作り方も書かれていない
- 状態: 実証（文面）。実行時の挙動は未確認
- 改善の方向: 「patch を保存 → 逆適用で赤 → 再適用で緑」の 3 段にし、最後の状態を `git diff --stat` で確かめる

### I6-agents-commands-10 phase gate の hook は Write/Edit/MultiEdit だけを見ており、lifecycle の agent は全員 Bash を持つ
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `03_ClaudeCode/hooks/settings.json` の PreToolUse の matcher は `Write|Edit|MultiEdit` で `block-phase.py`（json を読み込んで確認）。`block-phase.py:62` も同じ 3 種のツール名だけを判定する。spec / build / verify / gate の 4 agent は Bash を持つ（各 `:4`）。シェルのリダイレクトで工程の成果物を書けば検査を通らない
- 状態: 未確認（matcher とツール名の判定は実証。Bash で書いて止まらないことは再現していない）
- 改善の方向: Bash にも `docs/lifecycle/0[2-9]-*.md` への書き込みを検出する検査を足すか、commit 時に check-approval を走らせる git hook で受ける

### I6-agents-commands-11 aidd-lead がサブエージェントとして起動されると「人間を待つ」「前提 3 問の 1 往復」が成り立たない。main thread で動かす方法が書かれていない
- 種別: 欠落
- 深刻度: Medium
- 根拠: `aidd-lead.md:12-17,37-46` は人間と直接やりとりする前提で書かれている。公式文書には `claude --agent <name>` または settings の `"agent"` で main thread をその agent にする方法がある（同 URL）。`git grep -n -e "--agent"` を `01_利用者向け資料/04_運用モード.md` にかけても 0 件。同ファイルの `:10` は受け手を `aidd-lead` とするだけ
- 状態: 未確認（サブエージェントとして起動したときの挙動は試していない）
- 改善の方向: 利用者向け資料と aidd-lead の description に `claude --agent aidd-lead` を入口として明記する

### I6-agents-commands-12 test-agents.sh は文字列があるかを見るだけで、終了条件が達成できるかも配布先に道具があるかも検査しない
- 種別: 欠陥
- 深刻度: Low
- 根拠: `06_保守者向け/03_回帰テスト/test-agents.sh:13`（`has()` は `grep -qF`）、`:42-48`（"trace-check.sh"・"check-approval.sh"・"approver" という文字列の有無）、`:69`（Task がある）。01〜04 はこの検査を通ったまま残っている
- 状態: 実証
- 改善の方向: 合成プロジェクトで aidd-lead の流れ（工程 1 承認 → 工程 2〜4 を AI 検証完了）を作り、check-approval・trace-check の終了コードを assert する回帰テストを足す

### I6-agents-commands-13 commands が skill の基準を書き写しており、ずれる余地がある
- 種別: 過剰
- 深刻度: Low
- 根拠:
  - `commands/qa-review.md:11-16` の 5 カテゴリは `skills/qa-review-standards/SKILL.md:10-18` の写し
  - `commands/e2e-cycle.md` は使い方の表を全量持つ。同じ役目の外部スキル `e2e-cycle-help` もある（`00_導入/01_インストール/external-skills.json:124`）
  - 3 役レビューの手順が `skills/phase-approval/SKILL.md`・`commands/phase-review.md:191-197`・`agents/gate-agent.md:24-33` の 3 か所にある。gate-agent だけが「確信度 60 未満なら判定に入らない」を持つ（phase-review.md には無い。phase-approval 側は未確認）
- 状態: 実証（重複があること）。中身がずれているかは一部未確認
- 改善の方向: commands は skill への参照と引数の扱いだけにし、基準の本文は skill に一本化する

### I6-agents-commands-14 commands 25 件すべてに frontmatter（description・argument-hint・allowed-tools）が無い
- 種別: 欠落
- 深刻度: Low
- 根拠: `grep -c '^---' commands/*.md` は全件 0。`grep -rn "argument-hint\|allowed-tools" commands` も 0 件。読むだけの `agent-ready.md:78`（「対象は読むだけ。変更しない」）も、ツールを制限していない
- 状態: 実証
- 改善の方向: 全件に description と argument-hint を付ける。読み取り専用のコマンドには allowed-tools を付ける

### I6-agents-commands-15 プラグインで導入すると、agent の hooks・permissionMode による締め付けが効かない
- 種別: 機会
- 深刻度: Low
- 根拠: `.claude-plugin/plugin.json` が agents 6 件を配る。公式文書は「`hooks`・`permissionMode` は plugin subagents では無視される」と書いている（同 URL）。06・07 の改善を agent の frontmatter だけで行うと、install.sh 経路では効き、プラグイン経路では効かない
- 状態: 主張（公式文書）
- 改善の方向: 締め付けはグローバルの hook（agent の種類で分岐）で行い、frontmatter は補助にする

### I6-agents-commands-16 advisor の「呼び出し元より強いモデル」は `model: opus` 固定では保証されない
- 種別: 矛盾
- 深刻度: Low
- 根拠: `advisor.md:3`（呼び出し元より強いモデルで動かす）・`:5`（`model: opus`）。公式文書では `fable` やモデル ID も指定できる（同 URL）。main が Opus 以上のときは「より強い」にならない
- 状態: 主張
- 改善の方向: 「最上位のモデル」の指定方法を model-routing に寄せ、advisor はそれを参照する

---

## 調べられなかったこと
- commands のうち 11 件（app-scan / cancel-ralph / grill / implement / new-pwa / plan / quality-card / ralph / sdd-start / token-check / wait-what）は本文を読んでいない。frontmatter が無いことだけを確認した
- aidd-lead を実際に起動し、委譲・差し戻し・エスカレーションを end-to-end で回す試験はしていない（01〜04 は判定器の単体実行と文面の照合による）
- Bash による phase gate の迂回（10）と、サブエージェントとして起動したときの対話（11）は再現していない
- `skills/phase-approval/SKILL.md` の全文と、gate-agent との差分の詳しい比較はしていない
- 他社・OSS の agent 構成との比較（clone）はしていない

# S4-cc-subagents — Claude Code 仕様: subagents とキットの突合（段1・広域）

- 対象: キットの `03_ClaudeCode/agents/`（6 体）、委譲の規約 `02_共通/rules/model-routing.md`・`02_共通/rules/speed-harness.md` H-4、委譲に関わる hook（`03_ClaudeCode/hooks/settings.json`・`.claude-plugin/hooks.json`・`subagent-context.py`・`instruction-guard.py`・`constitution-gate.py`（コード本体のみ。`.claude/` 配下の状態ファイルは見ていない）・`tool-timer.py`・`block-explore.sh`）、`03_ClaudeCode/skills/phase-approval/SKILL.md`、`.claude-plugin/plugin.json`
- 調べた方法: 公式文書を WebFetch（取得日 2026-11-21）
  - https://code.claude.com/docs/en/sub-agents （全文 116,240 字を 0〜100,000 と 100,000〜末尾の 2 回で読んだ）
  - https://code.claude.com/docs/en/hooks （先頭 100,000 字のみ。SubagentStart/SubagentStop の節は読めていない）
  - https://code.claude.com/docs/en/costs
  - リポジトリは grep / sed / git grep origin/main で静的に読んだ。hook・スクリプトは実行していない
- 調べた件数/全件数: agents 6/6、委譲規約 2/2、hook 登録ファイル 2/2、hook スクリプト 6/31（委譲に関係するもののみ）、skills 1 本（phase-approval）
- 仕様の要点（以下の発見の前提。すべて sub-agents 文書からの引用で、状態は「主張」）
  - 既定で背景起動: "With nothing configured, a subagent that Claude spawns from your main conversation starts in the background."
  - 背景の道具の削減: 背景サブエージェントが保持する組み込み道具は "Read, Grep, Glob, LSP, Bash, PowerShell, Edit, Write, NotebookEdit, WebFetch, WebSearch, TodoWrite, Skill, ToolSearch, EnterWorktree, ExitWorktree, Monitor, TaskStop, SendMessage, Artifact, ListPlugins, ListSkills, SearchPlugins, SearchSkills"。"Don't rely on other built-in tools in a background subagent: Claude Code removes most of them, whether inherited or listed in the `tools` field."（`Agent` は一覧に無い）
  - 入れ子: "By default, a subagent can spawn subagents of its own, up to three layers below the main conversation."／Task は v2.1.63 で Agent に改名され、`Task(...)` は別名として有効
  - 前景は親を止める: "Foreground subagents block the main conversation until complete."／fork モード（v2.1.302 から既定 ON）では "Claude also can't wait for a subagent in interactive terminal, VS Code, or desktop sessions"
  - hook: 設定・プラグインの hook はサブエージェント内でも動き、PreToolUse/PostToolUse の入力に `agent_id`・`agent_type` が載る（hooks 文書）。frontmatter の `Stop` は `SubagentStop` に変換される
  - プラグイン配布: "plugin subagents don't support the `hooks`, `mcpServers`, or `permissionMode` frontmatter fields"
  - frontmatter に `maxTurns`・`isolation: worktree`・`effort`・`omitClaudeMd`・`disallowedTools`・`background`・`memory` 等がある
  - CLAUDE.md: サブエージェントは "every level of the CLAUDE.md hierarchy the main conversation loads, including `~/.claude/CLAUDE.md`" を読む（Explore/Plan は除く）
  - `SendMessage` での再開は agent teams を要さない

---

## S4-cc-subagents-01 aidd-lead をサブエージェントとして呼ぶと、背景起動で Task(Agent) 道具が外れ、担当エージェントを起動できない
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - `03_ClaudeCode/agents/aidd-lead.md:4` `tools: Read, Grep, Glob, Bash, Write, Edit, Task`、同 `:56-60` で spec/build/verify/gate-agent を起動する前提のループ
  - sub-agents 文書: 既定で背景起動、背景では保持一覧に `Agent` が無く "removes most of them, whether inherited or listed in the `tools` field"
  - キット内に `claude --agent` で aidd-lead を主スレッドにする手順が無い: `git grep -- "--agent "` はキット外 CSV の 2 件のみ（`06_保守者向け/04_監査記録/EXTERNAL-REF-github-2026-09.csv`）。README.md:112・INDEX.md:81 は「aidd-lead に投げるだけ」とだけ書く
- 状態: 主張（文書）。背景起動で実際に Agent が消えるかの再現はしていない
- 改善の方向: aidd-lead の入口を `claude --agent yuki-aidd-kit:aidd-lead`（主スレッド化）として利用者向け資料に明記するか、統括は主セッションが行う設計に改める

## S4-cc-subagents-02 aidd-lead の「人間へ（ここで待つ）」はサブエージェントの中では成立しない
- 種別: 矛盾
- 深刻度: High
- 根拠: `03_ClaudeCode/agents/aidd-lead.md:12-19,46,54,64`（工程 1・8 で人間を待つ、前提 3 問は 1 往復待つ）。sub-agents 文書: サブエージェントは結果を返して終わり、続きは `SendMessage` での再開（"Resumed subagents retain their full conversation history"）。背景では許可確認だけが主セッションに出る（"Background subagents surface every permission prompt in your main session"）。利用者と対話する道具は背景の保持一覧に無い
- 状態: 主張（文書）
- 改善の方向: 「待つ」を「結果を返して終了し、主セッションが人間の回答を SendMessage で渡して再開する」手順に書き換えるか、01 と同じく主スレッド化を前提にする

## S4-cc-subagents-03 憲法の「無報告を作らない」「委譲先が走行中のまま番を終えない」が委譲の仕様と両立しない
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - `CLAUDE.md` 憲法 2・3（委譲先の待ち時間も見積分数×60÷5 秒ごとに中間行、走行中のまま自分の番を終えない）、`02_共通/rules/speed-harness.md:6`（委譲先の待ちも同じ）
  - `03_ClaudeCode/hooks/constitution-gate.py:303-304` `if payload.get("agent_id"): return 0   # 委譲先の中。…親の次のツール呼び出しで判定される`
  - sub-agents 文書: 前景は "block the main conversation until complete"（待ちの間、親は本文もツール呼び出しも出せない）。fork モード既定 ON では対話セッションで親は待てない＝背景になる。キットは sleep ポーリングと自己ウェイクを禁止（speed-harness H-9、AGENTS.md 禁止事項）しているため、背景の完了を待つ合法な手段は「番を終えて通知で起きる」だけ
- 状態: 主張（文書）＋コード読み（hook の判定位置は実証: 上記行）
- 改善の方向: 規則を仕様上可能な形（前景 1 本は 10 分以内に分割、背景は番を終えて完了通知で再開してよい、等）に書き直し、hook の判定も同じ定義に合わせる

## S4-cc-subagents-04 phase-approval が「Agent への並列委譲はトークン約 7 倍」と書くが、7 倍は agent teams（plan モード）の数値で、model-routing の並列委譲の方針とも衝突する
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `03_ClaudeCode/skills/phase-approval/SKILL.md:25`。costs 文書 "Agent teams use approximately 7x more tokens than standard sessions when teammates run in plan mode"（サブエージェントの倍率ではない）。`06_保守者向け/02_設計判断の根拠/model-routing.md:18` は正しく agent teams の数値として引用。一方 `02_共通/rules/model-routing.md:13` は「2 単位以上は並列で委譲（上限 30 本）」を義務化
- 状態: 実証（両ファイルの記述を確認）＋主張（倍率は文書）
- 改善の方向: SKILL.md の根拠を「独立性を保つため順次」等の実際の理由に差し替え、7 倍の数値は agent teams 限定と明記する

## S4-cc-subagents-05 advisor の「読み取り専用」はプロンプトだけで、Bash を持つ。プラグイン配布では frontmatter の hooks/permissionMode も効かない
- 種別: 欠落
- 深刻度: Medium
- 根拠: `03_ClaudeCode/agents/advisor.md:4` `tools: Read, Grep, Glob, Bash`、同 `:56` 「状態を変えるコマンドを実行しない」。`.claude-plugin/plugin.json` は agents 6 体をプラグインとして配布。sub-agents 文書 "plugin subagents don't support the `hooks`, `mcpServers`, or `permissionMode` frontmatter fields"。advisor 用の agent_type 判定を持つ設定 hook は無い（`grep -n agent_type` は subagent-context.py の検証系判定のみ）
- 状態: 主張（文書）＋実証（ファイル内容）
- 改善の方向: 設定 hook 側で `agent_type` が advisor のときに書込み系 Bash を deny するか、Bash を外して読み取り専用の道具だけにする

## S4-cc-subagents-06 H-4 の「ツール回数上限」はプロンプト頼みで、frontmatter の maxTurns を使っていない
- 種別: 機会
- 深刻度: Medium
- 根拠: `02_共通/rules/speed-harness.md:24`（1 本ごとにツール回数上限、既定 20 回）。agents 6 体の frontmatter に `maxTurns` 無し（各ファイル frontmatter を表示して確認）。sub-agents 文書 `maxTurns`: "Maximum number of agentic turns before the subagent stops"、上限到達時は部分結果として返り再開できる
- 状態: 実証（frontmatter）＋主張（仕様）
- 改善の方向: spec/build/verify/gate-agent に maxTurns を設定し、H-4 の上限と単位（ターン≠ツール回数）の違いを規約に書く

## S4-cc-subagents-07 H-4 の「独立した段は worktree で並列」を手作業前提にしており、isolation: worktree を使っていない
- 種別: 機会
- 深刻度: Medium
- 根拠: `02_共通/rules/speed-harness.md:23` ①。`git grep isolation` はテスト用 Python の関数名 1 件のみ（`03_ClaudeCode/skills/test-automation/references/pytest_streamlit.py:35`）。sub-agents 文書 `isolation`: "Set to `worktree` to run the subagent in a temporary git worktree"
- 状態: 実証（grep）＋主張（仕様）
- 改善の方向: build-agent など同じファイルを触りうる並列担当に isolation: worktree を指定する案を検討する（後片付け・結合手順も併記）

## S4-cc-subagents-08 tool-timer.json は全セッション・全サブエージェント共有の 1 ファイルで、ロック無しの読み書き
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `03_ClaudeCode/hooks/tool-timer.py:35-37`（記録先は 1 ファイル）、`:59-63` `save()` は `write_text` のみ。`grep -c "fcntl\|flock\|os.replace\|session_id" tool-timer.py` → 0。hooks 文書: サブエージェントのツール呼び出しでも PreToolUse/PostToolUse が同じ hook を起動する。H-4 は最大 30 本の並列を指示
- 状態: 未確認（競合による取りこぼしは再現していない。ロックが無いことはコードで確認）
- 改善の方向: ロック付き・原子的な書き込みにし、セッション ID ごとにキーを分ける

## S4-cc-subagents-09 advisor は「呼び出し元より強いモデル」と書くが model: opus 固定で、主が Fable のときは逆転する
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `03_ClaudeCode/agents/advisor.md:3,5`（description「呼び出し元より強いモデルで動かす」、`model: opus`）。sub-agents 文書 `model` の値に `fable` がある。利用者の規約（`~/.claude/rules/common/core.md`「メインが Fable のとき」）は主が Fable の運用を想定
- 状態: 主張（文書）＋実証（ファイル内容）
- 改善の方向: 呼び出し時に model 引数で上書きする手順を advisor スキルに書くか、Fable 運用時の扱いを明記する

## S4-cc-subagents-10 サブエージェントは CLAUDE.md 全階層（憲法の見積行・長い規約）を読み込み、H-4 の短い返却と衝突し、固定費も増える
- 種別: 機会
- 深刻度: Medium
- 根拠: sub-agents 文書（CLAUDE.md 全階層を読む、`omitClaudeMd: true` で外せる）。本調査のサブエージェント自身の初期文脈に `~/.claude/CLAUDE.md`・AGENTS.md・rules・プロジェクト CLAUDE.md が載っていた（自分の文脈で確認）。speed-harness H-4 は 1 本 57k〜90k トークンを固定費として計上（`02_共通/rules/speed-harness.md:24`）。agents 6 体に `omitClaudeMd` 無し
- 状態: 実証（この起動で CLAUDE.md が載っていたこと）／削減量は未計測
- 改善の方向: 規約を SubagentStart 注入と agent 本文に寄せた担当には omitClaudeMd を試し、`/usage` の内訳で前後を測る

## S4-cc-subagents-11 サブエージェントの終了時の検査が無い（Stop 系 hook は主の番だけ、SubagentStop 未登録）
- 種別: 欠落
- 深刻度: Low
- 根拠: 両 hook 登録ファイルに SubagentStop が無い（python で全イベントを列挙して確認）。返却 10 行以内・approver を埋めない等は SubagentStart の注入だけ（`subagent-context.py:24-32`）。hooks 文書: SubagentStop は exit 2 で停止を阻止でき、`last_assistant_message` を受け取れる
- 状態: 実証（登録内容）＋主張（仕様）
- 改善の方向: SubagentStop で返却の長さ・approver 欄の書込みを検査する hook を検討する

## S4-cc-subagents-12 H-4 の生存確認「stat -L <output>（output はリンク）」が文書に無い前提
- 種別: 矛盾
- 深刻度: Low
- 根拠: `02_共通/rules/speed-harness.md:22`。sub-agents 文書は記録の場所を `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl` とだけ書き、output がリンクだとは書かない
- 状態: 未確認（実物のリンク構造は調べていない）
- 改善の方向: 生存確認の対象を文書にある transcript パス、または TaskStop/Monitor 等の公式手段に揃える

## S4-cc-subagents-13 再開（SendMessage）の手順がキットの規約に無い
- 種別: 欠落
- 深刻度: Low
- 根拠: `grep -rn SendMessage 02_共通 03_ClaudeCode/skills` → 0 件。`02_共通/rules/model-routing.md:13` は「Agent teams は使わない」とだけ書く。sub-agents 文書 "`SendMessage` doesn't require agent teams to be enabled"。利用者のグローバル AGENTS.md は「既存の担当は新規起動より再開を優先」と書くが、キットの規約には無い
- 状態: 実証（grep）＋主張（仕様）
- 改善の方向: H-4 に「差し戻しは新規起動でなく SendMessage で再開」を追加し、aidd-lead のループ（c. 差し戻し）にも反映する

## S4-cc-subagents-14 利用者規約が「hook が記録」と書く subagent-budget・context-size-guard はキットに含まれない
- 種別: 欠落
- 深刻度: Low
- 根拠: `git grep -n "subagent-budget\|context-size-guard" origin/main` → 0 件。`ls ~/.claude/hooks` には `subagent-budget.py`・`context-size-guard.py` がある。キットの hook 登録 2 ファイルにも無い
- 状態: 実証
- 改善の方向: キットに取り込むか、利用者規約側で「キット外・手元のみ」と明記する

## S4-cc-subagents-15 プラグインでは担当名が `yuki-aidd-kit:spec-agent` 形式になるが、aidd-lead は素の名前で呼ぶ
- 種別: 矛盾
- 深刻度: Low
- 根拠: sub-agents 文書（プラグインの agent は scoped name で登録される）。`03_ClaudeCode/agents/aidd-lead.md:57-60` は `spec-agent` 等の素の名前。`install.sh:73` は `~/.claude/agents/` にも同じ 6 体を写すため、両方入れると同名が 2 系統になる
- 状態: 未確認（素の名前で解決されるかは試していない）
- 改善の方向: 導入方法を 1 つに絞るか、aidd-lead 本文に scoped name を併記する

## S4-cc-subagents-16 effort を担当ごとに指定していない
- 種別: 機会
- 深刻度: Low
- 根拠: `02_共通/rules/model-routing.md:12`（定型・整形・要約は medium まで下げてよい）。agents 6 体に `effort` 無し。sub-agents 文書 `effort`: low〜max
- 状態: 実証（frontmatter）＋主張（仕様）
- 改善の方向: 定型の担当（例: gate-agent の機械判定部分）に effort を指定し、予実で効果を測る

## S4-cc-subagents-17 実装モード（.claude/mode）の探索ブロックは委譲先にも効き、Explore 系の担当が Read/Grep/Glob を使えなくなる
- 種別: 矛盾
- 深刻度: Low
- 根拠: `03_ClaudeCode/hooks/block-explore.sh:14-15,32`（agent_id を見ない）。hooks 文書: 設定の hook はサブエージェントのツール呼び出しでも動く
- 状態: 未確認（意図した仕様かは記述が無い。実行していない）
- 改善の方向: 委譲先を対象にするか否かを規約に明記し、外すなら agent_id で分岐する

## 仕様と合っていた点（欠陥ではない。参考）
- SubagentStart で規約を注入する設計（`subagent-context.py`）は、hooks 文書の「SubagentStart の通知はサブエージェント自身の transcript に入る」と一致。本調査の起動で `[subagent-context]` の注入が届いていた（実証）
- instruction-guard / constitution-gate が `agent_id` で委譲先を対象外にする判定は、hooks 文書の「サブエージェント内のツールイベントに agent_id が載る」と一致
- aidd-lead の `Task` は Agent の別名として有効、入れ子の深さ（主→aidd-lead→担当で 2 層）も既定上限 3 層の内（ただし 01 の背景起動の問題が先に当たる）

## 調べられなかったこと
- hooks 文書の SubagentStart / SubagentStop の入力・出力スキーマ（取得したのは先頭 100,000 字のみ）。`Stop`（設定側）がサブエージェント終了時に発火しないことは明示文が見つからず未確認
- 背景サブエージェントで Agent 道具が実際に消えるか、素の名前で plugin agent が解決されるかの実機再現（実行していない）
- tool-timer.json の競合の実測、omitClaudeMd による削減量の実測
- `effort` を省いたときサブエージェントが親の effort を継ぐかの規定（文書で見つけていない）

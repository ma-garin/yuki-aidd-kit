# C5-codex-agentsmd — 競合: Codex・AGENTS.md 標準

- 対象: キットの `04_Codex/`（AGENTS.md.template・README・hooks/・estimate-guard/）と、導入先の `~/.codex/`（AGENTS.md・hooks.json・rules/default.rules・config.toml の [features]）を、AGENTS.md 標準と Codex 公式文書に照らして突き合わせた
- 調べた方法: リポジトリは grep・sed・diff・`git grep origin/main`・`git log` で読んだ。導入先は ls・cat・grep で読んだ（auth 系は開いていない）。外部は WebFetch で 4 ページ（取得日 2026-11-21）。`codex --version` は `codex-cli 0.171.0`。正規表現 1 本だけ `python3 -I -c` で再現した（キットのスクリプトは実行していない）
- 調べた件数/全件数: `04_Codex/` 直下と hooks/・estimate-guard/・statusline/ のスキル以外のファイル 15 件中 9 件を読んだ（statusline 6 件は未読）。`04_Codex/skills/` 約 60 件は `規約のみ` の grep だけ。外部文書は 4/4 件（agents.md、Codex hooks、Codex rules、Codex AGENTS.md）

外部の出典（取得日 2026-11-21。どれも製品文書・標準のページで、研究ではない）
- S1 https://agents.md — 標準。必須の項目は無い。「最も近い AGENTS.md が優先、チャットの指示がすべてに優先」
- S2 https://learn.chatgpt.com/docs/hooks.md（developers.openai.com/codex/hooks.md からの 308 転送先）
- S3 https://learn.chatgpt.com/docs/agent-configuration/rules.md（同じく転送先）
- S4 https://learn.chatgpt.com/docs/agent-configuration/agents-md（同じく転送先）

---

## C5-codex-agentsmd-01 キットの estimate_guard が、規約で決めた見積書式「見積：N分（HH:MM）」を見積として認めない
- 種別: 欠陥
- 深刻度: High
- 根拠: `04_Codex/estimate-guard/estimate_guard.py:10` が `^見積[:：]\s*[0-9０-９]+(?:[.．][0-9０-９]+)?\s*分\s*$`（括弧を認めない）。その正規表現を `python3 -I -c` で試すと `'見積：5分'` は True、`'見積：5分（16:50）'` は False。規約 `04_Codex/AGENTS.md.template:6` は「見積：x分（HH:MM）」を求めている。導入先の `~/.codex/aidd-hooks/estimate_guard.py:10` は `分(?:[（(][^\n）)]*[）)])?\s*$` に直してあるが、キットのファイルは 2026-10-18（d2b2abf）のまま。キットから入れ直すと、規約どおりに見積を書いてもコード編集がすべて deny される
- 状態: 実証
- 改善の方向: 導入先で直した正規表現をキットに戻し、括弧付きの書式を test_estimate_guard.py に足す

## C5-codex-agentsmd-02 Codex の 3 項目を、規約は「規約のみ」と書き、04_Codex の README は「hook で止める」と書いている
- 種別: 矛盾
- 深刻度: High
- 根拠: `04_Codex/AGENTS.md.template:78`「Codex に同等の仕組みは無い」、:82-84 ではゲート・再探索・破壊操作の 3 行がどれも「規約のみ」。一方で `04_Codex/hooks/README.md:3` は「規約のみとしていた 3 項目を Codex CLI の hook で止める」、`04_Codex/README.md:14` も同じ書き方。導入先の `~/.claude/AGENTS.md`（Codex は `~/.codex/AGENTS.md -> ../.claude/AGENTS.md` からこれを読む）も「規約のみ」の表を載せている
- 状態: 実証
- 改善の方向: 状態を「hook あり（配線と /hooks の信頼が条件）／配線していなければ規約のみ」の 1 本にそろえ、配線されているかの確かめ方を書く

## C5-codex-agentsmd-03 導入先の ~/.codex/hooks.json に PreToolUse が無く、破壊操作・ゲート・再探索・見積の deny は実際には配線されていない
- 種別: 欠落
- 深刻度: High
- 根拠: `cat ~/.codex/hooks.json` の中身は UserPromptSubmit（prompt-priority・clock-guard・context_guard）と SubagentStart だけ。キットの `04_Codex/hooks/hooks.json.template` にある PreToolUse の 4 本（block-destructive・block-gates・block-ci・block-explore）と estimate-guard の PreToolUse がどれも入っていない。`~/.codex/aidd-hooks/` には `estimate_guard.py.before-no-block-20261108-1145` と `clock_stop.py.before-no-block-20261108-1145` があり、11-08 に deny を外したように見える（理由は未確認）。キットには配線の状態を確かめる検査が見当たらない（`04_Codex/hooks/README.md` の検証は unittest だけ）
- 状態: 実証（配線が無いこと）／未確認（外した理由）
- 改善の方向: 導入先の hooks.json に何が入っているかを出す点検コマンドをキットに用意し、規約の表はその結果に合わせる

## C5-codex-agentsmd-04 Codex の `prefix_rule(decision="forbidden")` が公式に文書化されたので、hook の信頼に頼らず破壊操作を機械で止められる
- 種別: 機会
- 深刻度: High
- 根拠: S3 は「`forbidden`: blocks the request without prompting」「most restrictive wins: forbidden > prompt > allow」と書き、`~/.codex/rules/*.rules` と、信頼済みのときだけ読む `<repo>/.codex/rules/`、試し方の `codex execpolicy check --rules`、管理者が強制する `requirements.toml` を説明している。キットの `CHANGELOG.md:120` は「Codex 側の `prefix_rule` 配線は仕様が公式文書で確認できず見送り」としている。見送った理由はもう成り立たない。限界（S3）: 分割して判定するのは `&&`・`||`・`;`・`|` だけでつないだ直線的なコマンドに限られ、リダイレクト・置換・変数・ワイルドカードを含むとコマンド全体を 1 件として判定する。機能は「experimental」。full-access／承認なしのモードで forbidden が効くかは文書に書かれていない
- 状態: 主張（製品文書）。実機での deny は未確認
- 改善の方向: `git reset --hard`・`push --force`・`add -A`・`rm -rf`・`clean -fd`・`stash drop` の forbidden 規則を雛形にし、`codex execpolicy check` で試す手順を付ける

## C5-codex-agentsmd-05 導入先の default.rules は allow が 322 件、forbidden が 0 件で、`rm -rf` の allow も含む
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `grep -o 'decision *= *"[a-z]*"' ~/.codex/rules/default.rules | sort | uniq -c` の結果は `322 decision="allow"`。`rm -rf` の allow は :19・:123・:195 にある。S3 によると allow は「runs outside the sandbox without prompting」。S3 の説明では、TUI で許可した操作がこのファイルに書き足されていく
- 状態: 実証（件数）／主張（allow はサンドボックスの外で動く）
- 改善の方向: 01_導入の点検で allow の棚卸しと forbidden の有無を出し、`rm -rf` 系の allow は消すか範囲を絞る

## C5-codex-agentsmd-06 hooks/README の Codex 仕様は 0.163.0 で止まっていて、今の文書と食い違う（allow と updatedInput は使えるようになった）
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `04_Codex/hooks/README.md:17,22` は「確認元: Codex 0.163.0」「PreToolUse は allow・ask・updatedInput を受け付けない」。S2 は「`permissionDecision: "allow"` with `updatedInput` is supported」（Bash と apply_patch では文字列の `command` が要る）と書き、ask は今も使えない。導入先は `codex-cli 0.171.0`。README:38 は updatedInput を使うという理由で `filter-output.py` を「移植不可」に分類している
- 状態: 主張（製品文書）。0.171.0 の実機では未確認
- 改善の方向: 仕様欄を今の版で取り直し、C 区分（移植不可）の判定を見直す

## C5-codex-agentsmd-07 PreToolUse は今は apply_patch と MCP も拾うが、アダプタは apply_patch を通さないので、書き込み系の hook を移植できていない
- 種別: 機会
- 深刻度: Medium
- 根拠: S2「Intercepts shell commands (matched as Bash), unified exec (exec_command), apply_patch, MCP tools…」「Doesn't cover hosted tools such as WebSearch」。`04_Codex/hooks/codex_hook_adapter.py:37` の `WRITE_TOOLS = {'apply_patch', ...}` と :56 `if short in WRITE_TOOLS ...: return None` は、書き込みをシェルとして扱わずに素通りさせる。README:37 は `pre-write-check.sh`・`block-phase.py`・`pre-read-guard.py`・`injection-guard.py` を「Write / Edit / Read ツール前提」として移植不可にしている
- 状態: 主張（製品文書）＋実証（アダプタのコード）
- 改善の方向: apply_patch の `command`（パッチ本文）から対象のパスを取り出して、Write/Edit の形に直して渡す変換を足せるか調べる

## C5-codex-agentsmd-08 Stop hook の `decision:"block"` は続きの指示として差し戻せるので、完了の計測行を機械で催促できる
- 種別: 機会
- 深刻度: Medium
- 根拠: S2「`decision: "block"` doesn't reject the turn. Instead, Codex continues, using the reason as a new continuation prompt」。キット側は `04_Codex/skills/work-metering/SKILL.md:51`「末尾行の強制 … 規約のみ」、`04_Codex/AGENTS.md.template:13`「発言送信を機械で止めるhookとは呼ばない」、:45「Codex は hook が無いので自分で出す」
- 状態: 主張（製品文書）
- 改善の方向: Claude 側の reply-language.py に当たる Stop 検査を Codex 用に作れるか、transcript の形式が安定していないこと（estimate-guard/README:13）も含めて評価する

## C5-codex-agentsmd-09 Codex の AGENTS.md には合計 32 KiB の上限があり、グローバルだけで 22,422 バイトを使っている。キットはこの上限に触れていない
- 種別: 欠落
- 深刻度: Medium
- 根拠: S4「stops adding files once the combined size reaches `project_doc_max_bytes`, which defaults to 32 KiB」、さらにグローバル（`~/.codex`）は「first non-empty file」1 件だけを読む。`wc -c ~/.claude/AGENTS.md` は 22422、`04_Codex/AGENTS.md.template` は 17042。プロジェクト側の AGENTS.md に使えるのは残りのおよそ 10.3 KB で、超えた分は読み込まれない（S4 の説明による。手元での再現はしていない）。`git grep project_doc_max_bytes origin/main -- 04_Codex 02_共通 00_導入` は 0 件。`~/.codex/config.toml` にも設定は無い（grep で 0 件）
- 状態: 実証（サイズ）／主張（読み込まれないこと）
- 改善の方向: グローバルの AGENTS.md に予算（例: 16 KiB 以下）を決めて検査するか、`project_doc_max_bytes` の設定を導入手順に入れる

## C5-codex-agentsmd-10 AGENTS.md.template が導入先のグローバル AGENTS.md より遅れている（3 節足りない）
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `diff 04_Codex/AGENTS.md.template ~/.claude/AGENTS.md` では、導入先にだけある行が 32 行あった。その中に節が 3 つ：「速く届ける進め方（2026-11-14）」「2026-10-25 事故の再発防止」「見積・途中報告の実行ゲート（2026-10-25）」。キットから新しい環境へ入れると、この 3 節の規律が抜ける
- 状態: 実証
- 改善の方向: どちらを真実源にするか決め、同期を検査する（例: install/点検で diff を出す）

## C5-codex-agentsmd-11 導入先の Codex hook は、キットに無い部品（clock-guard・context_guard・clock_stop）を呼んでいる
- 種別: 矛盾
- 深刻度: Low
- 根拠: `~/.codex/hooks.json` は `~/.claude/hooks/clock-guard.py` と `~/.codex/aidd-hooks/context_guard.py` を呼んでいる。`~/.codex/aidd-hooks/clock_stop.py` もある。`git grep -n "context_guard.py\|clock-guard" origin/main -- 04_Codex 03_ClaudeCode/hooks` は 0 件
- 状態: 実証
- 改善の方向: 導入先で足した部品をキットに戻すか、導入先の手直しとして記録する

## C5-codex-agentsmd-12 AGENTS.md.template の「下の 2 つ」と、表にある「規約のみ」3 行が合わない
- 種別: 矛盾
- 深刻度: Low
- 根拠: `04_Codex/AGENTS.md.template:78`「下の 2 つは規約として自分で守る」に対し、:82-84 の「規約のみ」は 3 行ある
- 状態: 実証
- 改善の方向: 02 の書き直しと一緒に、数を書かない文にする

## C5-codex-agentsmd-13 `.env` を読まない規約は、Codex でも PreToolUse（exec_command）でシェルからの読み取りを deny できる
- 種別: 機会
- 深刻度: Low
- 根拠: `04_Codex/AGENTS.md.template:109`「Codex は規約のみ」。S2 によると PreToolUse は exec_command と shell を拾う。アダプタにはすでに読み取り系コマンドの対応表 `READ_BINS`（`codex_hook_adapter.py:38-42`）があり、cat/grep などを Read/Grep として原本へ渡す仕組みがある（いまは `--explore` のときだけ使う）。S2 は hook について「a useful guardrail, not a complete enforcement boundary」とも書いている
- 状態: 主張（製品文書）＋実証（アダプタのコード）
- 改善の方向: `pre-read-guard.py` を explore と同じ変換で配線できるか調べる。すり抜け（python -c 等）は限界として書く

## C5-codex-agentsmd-14 このリポジトリの直下に AGENTS.md が無く、Codex でキットを触るとプロジェクトの指示が届かない
- 種別: 欠落
- 深刻度: Low
- 根拠: `wc -c AGENTS.md`（worktree の直下）は「No such file」。CLAUDE.md はあるが、Codex は読まない（S4 で探すのは AGENTS.override.md、AGENTS.md、fallback 名だけ）。S1 はリポジトリ直下に置くことを勧めている
- 状態: 実証
- 改善の方向: CLAUDE.md の憲法・入口を AGENTS.md に移して CLAUDE.md から import するか、`project_doc_fallback_filenames` で CLAUDE.md を読ませる

## 参考（発見ではない事実）
- S2: hook はプロジェクトの `.codex/hooks.json`（信頼済みの層だけ）、ユーザーの `$CODEX_HOME/hooks.json`、システムの `/etc/codex/hooks.json` から読む。既定で有効（`[features] hooks=false` で切る。`codex_hooks` は非推奨の別名）。管理されていない hook は信頼するまで動かない。中身が変わると、ハッシュが変わって信頼し直すまで skip される。既定の timeout は 600 秒
- S2: クラウド側で動かす hook では、PreToolUse のエラー・時間切れ・壊れた応答があるとツールがそのまま動きうる。ローカルの command hook が時間切れになったときの扱いは文書に書かれていない
- 他社の主張（未確認・引用しない）: destructive_command_guard の文書によると、Windows の unified_exec 経路では PreToolUse がシェル呼び出しを拾わない

## 調べられなかったこと
- Codex 0.171.0 の実機で deny が発火するか（PreToolUse hook・prefix_rule forbidden のどちらも、実行していない）
- full-access／承認なしのモードで forbidden が効くか（S3 に記述が無い）
- 11-08 に導入先で PreToolUse の deny を外した理由（バックアップの名前以外の証拠が無い）
- `04_Codex/statusline/` の 6 件と `04_Codex/skills/` 約 60 件の中身（`規約のみ` の grep だけ）
- `git grep` でヒットした `06_保守者向け/01_内部仕様/10_…` と `04_監査記録/EXTERNAL-REF-…` は、パスが日本語の 8 進表記のため本文を読んでいない

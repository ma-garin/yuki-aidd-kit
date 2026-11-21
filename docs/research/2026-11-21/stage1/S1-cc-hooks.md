# S1-cc-hooks: Claude Code の hooks 仕様とキットの突合（段1・広域）

- 対象: hooks の配線ファイル（`03_ClaudeCode/hooks/settings.json`＝配布形、`.claude-plugin/hooks.json`＝プラグイン、`.claude/settings.json`＝キット開発用）、利用者の実環境 `~/.claude/settings.json`（hooks 欄だけ）、`03_ClaudeCode/hooks/` の hook 本体、`00_導入/01_インストール/install.sh`
- 照合した仕様: https://code.claude.com/docs/en/hooks （取得 2026-11-21。全 294,429 字を offset 0 / 100000 / 200000 の 3 回で読んだ）
- ローカル版: `claude --version` → `2.1.330 (Claude Code)`
- 調べた方法: 3 つの配線ファイルを python で「イベント・matcher・コマンド・timeout」に展開して比べた／hook 本体を出力欄（permissionDecision・decision・additionalContext・systemMessage・updatedInput・exit 2）で grep した／7 本を精読（filter-output・pre-read-guard・pre-compact・tool-timer・instruction-guard・reply-language・ralph-stop の該当箇所）／tool-timer は scratchpad で再現実験（`AIDD_TOOL_TIME` で記録先を差し替えた。リポジトリは変更していない）
- 調べた件数/全件数: 配線ファイル 4/4、hook 本体の出力欄 grep 30/31、精読 7/31。`constitution-gate.py` は委譲の制約（名前が constitution で始まるファイルを開かない）に従い本体を読んでいない（配線の行だけ見た）

## 発見

### S1-cc-hooks-01 導入スクリプトが既存の settings.json に guard を配線せず、実環境で主要 guard が動いていない
- 種別: 欠陥（規約の記述とも矛盾）
- 深刻度: High
- 根拠: `00_導入/01_インストール/install.sh:77-86` は hook 本体を `~/.claude/hooks/` へコピーするが、`settings.json` が既にあると「手動でマージしてください」と出すだけ。自動で入れるのは `install_guard.py` の「指示優先の 3 hook」だけ。実環境 `~/.claude/settings.json` の hooks を展開した結果: tool-timer・block-ci・prompt-priority と、キット外の git-guard 等だけ。`grep -c block-destructive ~/.claude/settings.json` → `0`。プラグイン（`installed_plugins.json`）にも yuki-aidd-kit は無い。キット開発用の `.claude/settings.json` にも block-destructive・pre-write-check（秘密値）・block-gates・block-explore・filter-output・block-phase は無い。一方 `AGENTS.md` は「Claude Code では `block-destructive.py` が deny する」「hook が deny」と書いている
- 状態: 実証（配線ファイルの展開と grep）
- 改善の方向: install 時に配布形の hooks 欄を既存 settings.json へ冪等にマージする（install_guard の対象を全 guard に広げる）。合わせて「配線されている guard の一覧」を出す点検コマンドを用意する

### S1-cc-hooks-02 filter-output.py と pre-read-guard.py が `permissionDecision: "allow"` を返し、権限確認を飛ばしている
- 種別: 欠陥（セキュリティ）
- 深刻度: High
- 根拠: `03_ClaudeCode/hooks/filter-output.py:105-106`（`"permissionDecision": "allow"` と `updatedInput`）、`pre-read-guard.py:216-217`（同じ形）。仕様（hooks ページ）: updatedInput は「`"allow"` と組むと自動承認、`"ask"` と組むと書き換えた入力を利用者に見せる」。書き換えの対象は pytest・npm/yarn/pnpm install・pip install・docker build・cargo build・`make` 単体・git log・git diff（filter-output.py:27-37）。これらが allow リストに無くても確認なしで実行される。deny ルールと ask ルールは仕様上なお評価され、他の hook の deny は勝つ（deny > defer > ask > allow）。ただし 01 のとおり、実環境では block-destructive・block-deps の配線が欠けている場合がある
- 状態: 主張（仕様の記述とコードを照合した。挙動は再現していない）
- 改善の方向: permissionDecision を返さず updatedInput だけを返す（通常の権限判定に任せる）か、仕様が認める範囲で `ask` にする

### S1-cc-hooks-03 「hook の例外・時間切れは deny」という規約と、仕様・配線が食い違っている
- 種別: 矛盾
- 深刻度: High
- 根拠: `CLAUDE.md:10`「hook の例外・時間切れは deny（素通りは合格ではない）」。仕様: PreToolUse で時間切れになった hook は既定ではブロックしない（`onFailure: "block"` を付けたときだけブロック）。終了コードが 0・2 以外ならブロックしない（exit 1 は `onFailure: "block"` が無ければ非ブロック）。`grep -rn '"onFailure"' --include=*.json .` → 0 件。`.claude/settings.json` の全コマンドは `[ -f "$f" ] && exec python3 "$f" ... || exit 0` で、本体が無ければ黙って通す（_comment に意図を記載）。`block-gates.py:29`・`block-ci.py:46` は JSON を読めなければ `return 0` で通す。block-destructive.py:540 と secret_patterns.py:936 は自分で例外を捕まえて deny している（この 2 つは規約どおり）
- 状態: 実証（配線は grep で確認）／仕様は主張
- 改善の方向: 止めたい guard（constitution・block-destructive・pre-write-check）に `onFailure: "block"` を付ける。規約の文言を「どの hook が閉じる側に倒れるか」の一覧に直す

### S1-cc-hooks-04 Claude に伝えるつもりの文を systemMessage に入れている（仕様上は利用者向けの表示）
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `filter-output.py:16`「必ず systemMessage で『絞った・全量の取り方』を Claude に伝える」と `:108`。`pre-read-guard.py:219-223`（先頭 300 行に絞った旨と offset の案内を systemMessage だけに入れている。additionalContext に入るのは読み直しの警告があるときだけ）。`block-deps.py:172`。仕様: `systemMessage` は「利用者に表示する警告」。Claude の文脈に入るのは `additionalContext`（system reminder で包まれる）
- 状態: 主張（仕様とコードの照合）
- 改善の方向: Claude に知らせる文は `hookSpecificOutput.additionalContext` に移し、systemMessage は利用者向けだけに使う

### S1-cc-hooks-05 pre-compact.py が PreCompact に使えない additionalContext で指示を返している
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `pre-compact.py:27-29` が `{"hookSpecificOutput":{"hookEventName":"PreCompact","additionalContext":...}}` を出す。仕様: additionalContext を受け付けるイベントは SessionStart・SubagentStart・UserPromptSubmit・UserPromptExpansion・PreToolUse・PostToolUse・PostToolUseFailure・PostToolBatch・Stop・SubagentStop・PostModelSwitch で、PreCompact は入っていない。PreCompact は「exit 0 でブロックしないとき、stdout を要約の指示として使う」。終了 0 の stdout が JSON 1 個なら JSON として解釈する
- 状態: 未確認（圧縮を実際に走らせて要約への反映を見ていない）
- 改善の方向: 指示文を JSON に包まず、プレーンテキストで stdout に出す

### S1-cc-hooks-06 Write 系の matcher に NotebookEdit が無く、MultiEdit は今の版に存在しない
- 種別: 欠陥
- 深刻度: Medium
- 根拠: 配線の matcher は `Write|Edit|MultiEdit`（pre-write-check.sh・block-phase.py・post-write-html.sh）と `Bash|Write|Edit`（block-deps.py）。仕様: 英数字と `|` だけの matcher は完全一致のリストになる。この版のセッションには NotebookEdit ツールがある（deferred tool 一覧で確認）。仕様の PreToolUse ツール名一覧と、この版のツール一覧のどちらにも MultiEdit は無い。`block-phase.py:62`・`observe.py:44,97` もツール名を固定で持っている。秘密値の検査と工程承認の検査は、NotebookEdit で書けば通らない
- 状態: 実証（matcher の文字列と仕様の照合規則で確認。NotebookEdit を実際に通してはいない）
- 改善の方向: matcher に NotebookEdit を加え、MultiEdit を外すか、残すなら版の互換と明記する

### S1-cc-hooks-07 tool-timer が PostToolUse の来ない呼び出しで inflight を残し、以後のツール時間を数えなくなる
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `tool-timer.py:124-144`。区間を閉じるのは inflight が空になったときだけ。仕様では PostToolUse は成功時だけ発火し、失敗時は PostToolUseFailure になる。他の hook の deny で止まった呼び出しにも PostToolUse は来ない（tool-timer pre は並列で先に記録済み）。再現（scratchpad、`AIDD_TOOL_TIME` で記録先を差し替え）: A pre/post → total 0.0444。F pre だけ（失敗を模擬）→ B・C を pre/post しても `total 0.0444` のまま、`inflight ['F']`、count だけ 3 に増える。`report` の既定行は壁時計（`since` から）なので影響しないが、`--full` のツール時間と session_sec は過小になる。`observe.py:20` も失敗を記録しないと自ら書いている
- 状態: 実証（再現した）
- 改善の方向: PostToolUseFailure にも post を配線する（必要なら PostToolBatch で残った inflight を掃除する）

### S1-cc-hooks-08 グローバルとプロジェクトで同じ hook を別の文字列で二重に配線し、重複排除が効かない
- 種別: 過剰
- 深刻度: Medium
- 根拠: 仕様:「同一のハンドラを複数の設定ファイルに書くと 1 回だけ実行する。プラグイン・スキルのものは別に数える」。このリポジトリでは `~/.claude/settings.json` の `python3 ~/.claude/hooks/tool-timer.py pre|post|reset` と `python3 ~/.claude/hooks/prompt-priority.py` に加えて、`.claude/settings.json` の `sh -c 'f="$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/..."'` も走る。文字列が違うので両方実行される。`cmp` の結果、`~/.claude/hooks/prompt-priority.py` と `statusline.py` はリポジトリ版と中身が違う。このため prompt-priority が別々の文脈を 2 回注入し、tool-timer は 2 つの記録先（`~/.claude/tool-time.json` と `03_ClaudeCode/tool-time.json`）に分かれる。plugin 版を入れると 3 重になる
- 状態: 実証（配線と cmp）／二重実行は仕様からの主張
- 改善の方向: 1 つの層にだけ配線し、コマンドの文字列をそろえる。古いグローバルのコピーを検出する点検を用意する

### S1-cc-hooks-09 .claude/settings.json の _comment に書かれた block-protected.py の配線が実在しない
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `.claude/settings.json` の `_comment`「2026-09-24（B-19）: block-protected.py を Write 系と Bash に配線」。`ls 03_ClaudeCode/hooks/block-protected.py` → No such file。hooks 欄にも無い。`git grep -l block-protected origin/main` → settings.json・CHANGELOG・06_保守者向け の文書だけ。CLAUDE.md の「`.claude/settings*.json` は AI が当てない」を機械で守る仕組みが存在しない
- 状態: 実証
- 改善の方向: 文書を実態に合わせるか、ConfigChange イベント（下の 15）で設定変更を止める仕組みを作る

### S1-cc-hooks-10 timeout 未指定の hook が 4 本あり、既定の 600 秒になる
- 種別: 欠落
- 深刻度: Low
- 根拠: pre-write-check.sh・block-explore.sh・post-write-html.sh・session-summary.sh は配布形・plugin とも timeout を書いていない（展開結果の `{}`）。仕様: command の既定は 600 秒。PreToolUse で時間切れになっても既定ではブロックしない（03）
- 状態: 主張
- 改善の方向: 5〜10 秒を明記し、止める側の hook には onFailure も付ける

### S1-cc-hooks-11 instruction-guard の冒頭説明と実装・規約が食い違う
- 種別: 矛盾
- 深刻度: Low
- 根拠: `instruction-guard.py:4-7`「deny をやめ additionalContext に変えた。以下の deny は通知と読み替える」。一方 `:278-282` は見積が無いと毎回 deny する（2026-11-07 に追加）。AGENTS.md は「instruction-guard.py が止める」と書いている
- 状態: 実証（コードを読んだ）
- 改善の方向: docstring を「見積は deny、それ以外は通知」に直す

### S1-cc-hooks-12 injection-guard の matcher が正規表現として解釈され、部分一致になる
- 種別: 欠陥
- 深刻度: Low
- 根拠: matcher `WebFetch|WebSearch|mcp__.*|Read` は `.` と `*` を含む。仕様では、英数字・`_`・`-`・空白・`,`・`|` 以外の文字を含むと、アンカー無しの JS 正規表現（`RegExp.test`）として扱う。そのため `Read` は名前に Read を含むすべてのツールに当たる。範囲が広がる方向なので、検査漏れにはならない
- 状態: 主張
- 改善の方向: `^(WebFetch|WebSearch|Read)$|^mcp__` のようにアンカーを付ける

### S1-cc-hooks-13 filter-output の前提「PostToolUse は出力を書き換えられない」が今の仕様では古い
- 種別: 機会
- 深刻度: Medium
- 根拠: `filter-output.py:5`。仕様: PostToolUse の `hookSpecificOutput.updatedToolOutput` は Claude が見る出力を置き換える（組み込みツールは出力の形が合わないと無視する。MCP は検証しない）。入力には `duration_ms` もある
- 状態: 主張
- 改善の方向: コマンドの書き換えと allow（02）をやめ、PostToolUse で出力を絞る方式を検討する（形の互換は要検証）

### S1-cc-hooks-14 Stop 入力の background_tasks で「委譲先が走行中のまま番を終えない」を機械判定できる
- 種別: 機会
- 深刻度: Medium
- 根拠: 仕様: Stop の入力に `background_tasks` と `session_crons` があり、「完了」と「バックグラウンド待ち」を区別できる。`last_assistant_message` は transcript より確実（transcript は Stop 時点で最終メッセージを含む保証が無い）。CLAUDE.md の憲法 3 は「委譲先が走行中…のまま自分の番を終えない」。reply-language.py は last_assistant_message を使っているが、background_tasks の参照は grep で 0 件
- 状態: 主張
- 改善の方向: Stop hook で background_tasks が空でないとき、待ちの報告を求める判定を足す

### S1-cc-hooks-15 使っていない有用なイベント・項目
- 種別: 機会
- 深刻度: Low
- 根拠: 仕様のイベント一覧と配線の照合（配線にあるのは PreToolUse・PostToolUse・UserPromptSubmit・SubagentStart・PreCompact・SessionStart・InstructionsLoaded・Stop の 8 種）。`grep -rn 'PostToolUseFailure|PermissionDenied|PostToolBatch|StopFailure|SessionEnd|ConfigChange|SubagentStop|PostCompact'` → observe.py の説明文 1 件だけ
  - PostToolUseFailure: 07 の修正と、失敗の観測
  - ConfigChange: 設定ファイルの変更をブロックできる（policy_settings を除く）。UserPromptSubmit で取っている config-snapshot の置き換え、09 の代わり
  - SubagentStop: H-4 の「返答は完了＋パスに限る」を機械で検査し、block で差し戻す
  - SessionEnd: 終了処理（session-summary.sh は Stop で毎ターン走っている）。予算は 1.5 秒（per-hook timeout を上げると最大 60 秒）
  - PostCompact: `compact_summary` を記録し、要約の質を点検する
  - StopFailure・PermissionDenied・UserPromptExpansion・PostToolBatch
  - ハンドラ項目 `if`（権限ルール書式。例 `Bash(git *)`）: Bash の hook 6 本は毎回 python を起動している。`if` で対象を絞れる
  - `args`（シェルを通さない exec 形）、`CLAUDE_ENV_FILE`（SessionStart で環境変数を渡す）
- 状態: 主張
- 改善の方向: 07・09・14 に関わる PostToolUseFailure・ConfigChange・SubagentStop から優先して検討する

### S1-cc-hooks-16 Stop hook の連続継続は 8 回で打ち切られ、ralph-stop の上限 20 と合わない場合がある
- 種別: 矛盾
- 深刻度: Low
- 根拠: 仕様: Stop hook が 8 回続けて継続させると、次の block は無視されてターンが終わる（ツールを呼ぶと数え直す。`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` で変更可）。`ralph-stop.py:15` は max を 1〜20 に丸め、stop_hook_active でも回す
- 状態: 主張
- 改善の方向: 上限が 8 を超えるときは環境変数の設定を案内するか、上限を 8 以下にそろえる

### 仕様と合っている点（参考）
- PreToolUse の出力はすべて `hookSpecificOutput.permissionDecision` を使っている。廃止された top-level の `decision: approve/block` は使っていない（grep で確認）
- Stop の `decision: "block"`、`stop_hook_active` によるループ防止（reply-language.py:417）、`last_assistant_message` の優先（reply-language.py:421、ralph-stop.py:51）は仕様どおり
- UserPromptSubmit の timeout 5 秒は、仕様の上限 30 秒以内
- SubagentStart・SessionStart・UserPromptSubmit の additionalContext は仕様の対象イベント
- `suppressOutput`（仕様では効果なし）は使っていない

## 調べられなかったこと
- `constitution-gate.py` の本体（委譲の制約で開いていない）。配線（timeout 5〜10・onFailure 無し）だけ確認した。03 の時間切れの扱いはこの hook にも当てはまる
- 05（PreCompact の JSON 出力が要約に効くか）と 02（allow で確認が出なくなること）は実機で再現していない。`claude -p` の起動は、利用者のグローバル hook が走るため避けた
- 仕様に書かれていないこと: 複数の hook が updatedInput を返したときの合成規則、matcher の大文字・小文字の扱い
- hook 本体 31 本のうち、精読したのは 7 本。他の本数は出力欄の grep だけで、判定ロジックの正しさは見ていない
- MultiEdit が廃止された版の公式な changelog（WebSearch していない）

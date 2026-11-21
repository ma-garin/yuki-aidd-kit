# I1-hooks 内部実装（hooks）調査

- 対象: `03_ClaudeCode/hooks/` 全 31 ファイル（約 6,039 行）＋ `settings.json` の配線
- 調べた方法:
  1. 全ファイルを通読して、目的・発火・判定・fail-open/closed を表にした。
  2. 手作りの transcript と JSON ペイロードを `python3` で各 hook に流した。実験は scratchpad 内の `mkdtemp` で行い、`CLAUDE_PROJECT_DIR`・`TMPDIR`・`HOME` などの環境変数をそちらへ逃がした。スクリプトは `scratchpad/exp/cg.py`・`bat.py`・`cases.json`。
  3. 本日のセッションの transcript（`9b343f84…jsonl`）で起きた見積欠落の停止を、`constitution-gate.py` の `scan()` と `evaluate()` に再生させた。
  4. 性能は hook ごとに 5 回実行し、中央値と最大値を測った。
  5. 回避は 34 パターンを実際に流して確かめた。
- 調べた件数/全件数: 31/31 ファイル（＋settings.json）。実行で確かめたのは 22 hook。

## hook 一覧（要約）

| hook | 発火 | 失敗時 | 実行時間の中央値 |
|---|---|---|---|
| constitution-gate | Pre 全ツール／Stop | closed | 58ms／56ms |
| instruction-guard | Pre | open | 45ms |
| block-destructive | Pre Bash | closed | 43ms |
| block-deps | Pre Bash/Write/Edit | closed | 46ms |
| block-ci / block-gates | Pre Bash | open | 36／31ms |
| filter-output | Pre Bash | open | 32ms |
| pre-read-guard | Pre Read 系 | 秘密は closed | 42ms |
| block-explore.sh | Pre Read 系 | mode があるときだけ | 7ms |
| pre-write-check.sh | Pre Write 系 | closed | 59ms |
| block-phase | Pre Write 系 | open（opt-in） | 40ms |
| tool-timer / observe | Pre/Post | open | 33〜68ms |
| injection-guard | Post Web/MCP/Read | open（警告だけ） | 77ms |
| reply-language | Stop | open | 98ms |
| ralph-stop / session-summary | Stop | open | 67ms／未計測 |
| prompt-priority / context-guard / config-snapshot | UserPromptSubmit | open | 87／36ms／未計測 |
| session-context / subagent-context / pre-compact / log-instructions | Session 系 | open | 33〜44ms |
| progress / statusline / secret_patterns | 補助（hook ではない） | — | — |

- Bash 1 回あたり、PreToolUse の 8 本の合計は約 324ms。直列で走るか並列で走るかは未確認。
- 単体で 100ms を超えた hook は無かった（最大 129ms、prompt-priority）。性能が問題になる兆候は無い。

## 発見

### I1-hooks-01 本日 16:14 の見積欠落による停止は、transcript の書き込みの遅れが原因の誤判定（推定）
- 種別: 欠陥／深刻度: Critical／状態: 主張（再生実験で強く裏付け）
- 根拠:
  - 本セッションの transcript を時系列で見た。
    - 見積の行 `見積：150分（18:44）` を含む assistant エントリは 47 行目（07:14:47Z）にある。
    - その後の Bash の tool_use（07:14:49Z）に対し、54 行目で `[constitution-gate] 憲法違反（見積欠落）` が出た。`hook-decisions.log` には `2026-11-21T16:14:51 stop 見積欠落` が残っている。
  - 同じ transcript を `scan()` と `evaluate()` に再生した。
    - 見積のエントリを含めると「許可」になる。
    - 見積のエントリを除くと「見積欠落」になる。
  - したがって、hook が実際に読んだ時点で、見積を含むエントリはまだファイルに書かれていなかったことになる。待ち時間は既定の 1 秒（L306、`AIDD_TRANSCRIPT_FLUSH_SEC`）で、これでは足りなかった。
  - `<pasted_content>` は原因ではない。その指示は `instruction_of()` で 977 字のまま human の指示として扱われ、coding=True と判定されていた。
- 改善の方向: 見積が見当たらないときは即停止にしない。
  - まず deny（停止ファイルは書かない）にとどめ、次の呼び出しで再確認する。
  - 停止は同じターンで 2 回続けて欠落したときに限る。

### I1-hooks-02 ターンの途中に届いた queued メッセージで、見積済みでも見積欠落の停止になる
- 種別: 欠陥／深刻度: High／状態: 実証（実験 D）
- 根拠:
  - 見積の行を出した後に、queue-operation の enqueue「あと README も直して」が届く transcript を作った。
  - 次の Bash で、`constitution-gate pre` が見積欠落の stop を返した。
  - queued メッセージが新しいターンとして扱われ、その区間に見積が無いと判定される。
- 改善の方向: queued の追加指示は直前のターンに合流させる。または、その区間では見積の再提示を求めるだけの deny にとどめ、停止にはしない。

### I1-hooks-03 見積の書式の判定が 2 つの hook で食い違い、太字の見積で停止する
- 種別: 矛盾／深刻度: High／状態: 実証（実験 E）
- 根拠:
  - 2 つの hook の判定条件。
    - `constitution-gate.py` L37 の `EST_RE`: 行頭の `【?見積[:：]` が必要。時刻は不要。
    - `instruction-guard.py` L43 の `ESTIMATE_RE`: 行頭でなくてよい。`（HH:MM）` が必要。
  - 実験の結果。
    - `**見積：5分（16:40）**` は instruction-guard を通るが、constitution-gate では見積欠落の stop になった。
    - 時刻の無い `見積：5分` は逆に、constitution-gate を通り、instruction-guard で deny される。
- 改善の方向: 見積を検出する正規表現を `secret_patterns` 相当の共通モジュールに 1 つだけ置き、2 つの hook はそれを import する。Markdown の装飾は剥がしてから照合する。

### I1-hooks-04 CODING_RE が質問や否定文でも発火する
- 種別: 欠陥／深刻度: High／状態: 実証（実験 G・本日の実例）
- 根拠:
  - `constitution-gate.py` L34 の `CODING_RE` は「hook」「実装」「やって」「進めて」や拡張子にも当たる。
  - 実験 G: 質問「この hook は何をしている？」で、見積欠落の stop になった。
  - 本日の実例: 「実装はしない」の「実装」に当たり、coding=True になった（再生で確認）。
  - A-2 は質問・調査を見積の対象外としており、これと矛盾する。
- 改善の方向: 疑問文と否定（「しない」「不要」）を除外する。停止の判定は「Write/Edit/Bash の書き込み系ツールを使ったとき」に寄せ、語彙で推定しない。

### I1-hooks-05 `<pasted_content>` だけのターンが見えず、指示を取り違える
- 種別: 欠陥／深刻度: Medium／状態: 実証（実験 A・B・C・実データ）
- 根拠:
  - `instruction_of()`（L106-122）は、`TAG_BLOCK_RE.sub("", raw).strip() or None` で、タグのブロックを丸ごと消す。
    - 本物のペーストでは、閉じタグが `</pasted_content id="…">` の形になる。実データ 3 件で確かめた。この形だと `TAG_BLOCK_RE` の `</\1>` が一致しないので、ブロックは消えずに残る（実データでは 977 字・651 字がそのまま残った）。
    - 実験で `</pasted_content>` という閉じタグを使うと消えた。
  - 消えたときに起きること（実験 C）。
    - ターンは前の指示「ありがとう」に戻る。
    - constitution-gate は coding を見落として許可する（取り締まり不足）。
    - instruction-guard は「指示「ありがとう」への応答に見積が無い」と、取り違えた指示を名指しして deny する。
  - 疑われていた「ペーストで見積欠落」は、A・B の形では再現しなかった。
  - 実データ `eeab3fc4` の 9 行目では、ペースト本文の中に `[constitution-gate]` があった。そのため、constitution-gate はメッセージ全体を機械の文と判定して指示を捨てた（instruction_of=None）。instruction-guard は 2706 字の指示として扱った。
- 改善の方向:
  - ペーストのタグは中身を残す。
  - 機械の文かどうかは、メッセージ全体ではなく行頭の接頭辞だけで判定する。

### I1-hooks-06 MACHINE_MARKERS が 2 つの hook で違う
- 種別: 矛盾／深刻度: Medium／状態: 実証（実験 F）
- 根拠:
  - instruction-guard の `MACHINE_MARKERS` には `[constitution-gate]` が無い。
  - 「直して\n[constitution-gate] …」という入力で、2 つの hook の扱いが分かれた。
    - constitution-gate は指示を無視して許可した。
    - instruction-guard は未応答として通知した。
  - 利用者が hook のメッセージを貼って「直して」と書くと、その指示は constitution-gate から見えなくなる。
- 改善の方向: マーカーは共通モジュールに置き、行頭の一致に限る。

### I1-hooks-07 instruction-guard が純粋な質問にも見積を要求し、到達しないコードがある
- 種別: 矛盾／深刻度: Medium／状態: 実証（実験 H）
- 根拠:
  - `judge()`（L173-208）は、指示がコーディングを含むかを判定しないまま `estimate` の deny を出す。
  - 「今日の天気は？」でも deny された。A-2 の対象外の規定と矛盾する。
  - L289-291 の `kind=="estimate"` の通知の分岐は、L278 で先に deny されるため到達しない。
- 改善の方向: constitution-gate と同じ coding の判定を通してから、見積を要求する。

### I1-hooks-08 Bash ガードは `bash -c` と、利用者用の逃がし口の文字列で回避できる
- 種別: 欠陥／深刻度: Medium／状態: 実証（34 パターンを実行）
- 根拠:
  - 次のコマンドがすべて pass した。
    - `bash -c 'pytest -q'`、`(pytest -q)`、`uv run pytest -q`
    - `echo GATES_REQUESTED=1 >/dev/null; pytest -q`
    - `echo CI_REQUESTED=1; gh run watch 1`、`bash -c 'gh run watch 1'`
    - `bash -c 'pip install requests'`
  - 逃がし口は「利用者が要求したときだけ」という前提なのに、コマンド文字列のどこかに含まれていれば通るので、AI が自分で付けられる。
  - 規約では、AIDD_DEPS_OK は AI が付けても通らない（`AIDD_DEPS_OK=1 pip …` は DENY）。それなのに理由文は AI に付けて再試行するよう案内しており、誤誘導になっている。
- 改善の方向:
  - 逃がし口は環境変数か、利用者の発言（UserPromptSubmit で記録したもの）で判定する。
  - `bash -c`・サブシェル・`uv run`・`npx` を展開してから照合する。block-destructive が使っている secret_patterns の展開処理を共通で使う。

### I1-hooks-09 block-destructive が規約で禁止している操作を通す
- 種別: 欠落／深刻度: Medium／状態: 実証
- 根拠:
  - 次のコマンドが pass した。
    - `rm -r build`
    - `git stash`
    - `git reset HEAD~1`
    - `git switch -f main`
    - `git worktree remove --force`
    - `truncate -s 0 src/app.py`
    - `: > src/app.py`
    - `perl -e 'unlink …'`
    - `g=git; $g reset --hard`
    - `git commit -am x`
  - AGENTS.md の禁止事項は `git stash`・`git reset` を禁じ、`rm -rf` の代わりに `mv` を使うよう定めている。
  - `git add -A`・`--all`・`.`、`find -delete`、`cat .e''nv` は DENY された（正しく働いた）。
- 改善の方向: 禁止の一覧を AGENTS.md の禁止事項と 1 対 1 で突き合わせて足す。変数や perl など構文解析の限界は docstring に列挙し、テストで固定する。

### I1-hooks-10 block-explore / block-phase は Bash を経由すると回避できる
- 種別: 欠落／深刻度: Medium／状態: 主張（コードを読んだ結果）
- 根拠:
  - block-explore.sh の対象は Read・Grep・Glob だけ。実装モードでも `cat`・`grep` を Bash で打つと通る。
  - block-phase の対象は Write・Edit・MultiEdit だけ。heredoc やリダイレクトでの書き込みは見ない。
  - 本セッションの auto mode の指示自体が、cat や sed での読み書きを勧めている。
- 改善の方向: Bash の PreToolUse で、読み取り・書き込みのコマンドを同じ規則で判定する。

### I1-hooks-11 constitution の状態ファイルがプロジェクト単位で、セッションをまたいで共有される
- 種別: 欠陥／深刻度: Medium／状態: 主張（コードを読んだ結果。実行では未確認）
- 根拠:
  - 状態ファイルのパスはプロジェクトのルートから決まり、session_id を含まない。
  - `turn is None` のときは前の状態を引き継ぐ。
  - 同じリポジトリで並行するセッションが、互いの turn や est を上書きしうる。worktree をまたぐ場合も同じ。
  - 停止ファイルが 1 つなので、1 つのセッションの違反で全セッションが止まる。
- 改善の方向: 状態ファイルを session_id ごとに分ける。停止の範囲を明示する。

### I1-hooks-12 shell hook 3 本に timeout が無い
- 種別: 欠落／深刻度: Low／状態: 実証（settings.json を読んだ）
- 根拠: settings.json で、pre-write-check.sh・block-explore.sh・post-write-html.sh に `timeout` が設定されていない。
- 改善の方向: ほかの hook と同じく 10〜25 秒を明示する。

### I1-hooks-13 tail の読み取り量が hook ごとに違う
- 種別: 矛盾／深刻度: Low／状態: 実証（コードを読んだ）
- 根拠: constitution-gate は transcript の末尾 2048KB を読み、instruction-guard は 512KB を読む。長いターンでは、2 つの hook が別の「最後の指示」を見る可能性がある。
- 改善の方向: 読み取りの処理を共通化する。

### I1-hooks-14 progress.py に例外処理が無い
- 種別: 欠陥／深刻度: Low／状態: 主張（コードを読んだ）
- 根拠:
  - `int(sys.argv[3])` を保護せずに呼んでいる。
  - step の処理で、`json.loads` を try で囲んでいない。
  - Bash に連結して使う前提なので、ここで失敗すると、連結した本来のコマンドの終了コードを汚す。
- 改善の方向: 例外を握って exit 0 にし、標準エラーに 1 行出す。

### I1-hooks-15 constitution-gate の改ざん検査の回避経路が、docstring に既知として並んでいる
- 種別: 欠落／深刻度: Low／状態: 主張（docstring L9-13）
- 根拠:
  - 回避経路として、glob、変数、eval、`rsync --delete` などが自ら列挙されている。
  - SAFE_READ の許可リストに `git commit` と `git add` が含まれている。
- 改善の方向: 停止ファイルを利用者専有の場所に置き、AI のプロセスから書けなくする。

## 性能

- 22 hook すべてで中央値は 7〜98ms、最大でも 129ms（prompt-priority）。
- Bash 1 回あたりの PreToolUse の合計は約 324ms。
- 遅さに関する問題は見つからなかった。

## 調べられなかったこと

- 停止ファイルと状態ファイルの実物。指示に従い、読んでいない。
  - このため 01 の「書き込みの遅れ」は、transcript の再生による推定である。hook が読んだ時点のファイル内容そのものは未確認。
- Claude Code が同じイベントの hook を並列で実行するか、直列で実行するか。未確認。
- session-summary.sh・config-snapshot.py・statusline・post-write-html.sh の実行時間。未計測。
- 複数セッションでの状態ファイルの競合（11）は実行で再現していない。
- WebSearch は使っていない（0/6）。外部の Claude Code 仕様、たとえば transcript の flush のタイミングは未確認。

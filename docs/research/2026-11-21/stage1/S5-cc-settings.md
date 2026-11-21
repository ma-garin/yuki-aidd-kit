# S5-cc-settings — Claude Code 仕様: settings・クラウド実行（段1 広域）

- 対象: キットが配る settings 雛形 7 点と、`CLAUDE.md` の「hook が入っていない環境」節
  - `.claude/settings.json`（キット自身の開発用）／`03_ClaudeCode/hooks/settings.json`（`~/.claude` 向け雛形）／`02_共通/ひな形/settings.sandbox.json`／`.claude-plugin/plugin.json`・`hooks.json`・`marketplace.json`／`00_導入/02_プロジェクト配布/export-project.sh` が書き出す `.claude/settings.json`（ヒアドキュメント）
  - `CLAUDE.md:8-15`（強制の仕組み・hook 未導入環境）
- 調べた方法
  - 公式文書（取得日 2026-11-21）: https://code.claude.com/docs/en/settings ・ /hooks ・ /claude-code-on-the-web ・ /cloud-environments ・ /settings-reference（索引部のみ）・ /env-vars ・ /model-config
  - 動いているバイナリ: `claude --version` → `2.1.330 (Claude Code)`、実体 `/opt/homebrew/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe`。キー名の出現数を `grep -c -a`、スキーマ断片を Python の mmap で静的に抽出（実行時検証ではない）
  - 実験: `python3 <存在しないファイル>` の終了コード、`sh -c '[ -f ] && exec … || exit 0'` の終了コード、`claude --settings <file> doctor`（検出力なし、後述）
  - `git grep` による存在確認（`docs/research` は除外）
- 調べた件数/全件数: 設定ファイル 7/7、CLAUDE.md の該当節 1/1、キー・フィールド 20/20（下表）

## 確認済みのキー（動いているバイナリで実在を確認）

| キー | バイナリ | 型・値の確認 |
|---|---|---|
| effortLevel | 実在 40 件 | `F(["low","medium","high","xhigh"]).optional().catch(void 0)`。"high" は有効 |
| autoCompactWindow | 実在 76 件 | 最上位キーは整数（→ -04） |
| bashOutputMaxChars | 実在 4 件 | 正の整数、4000〜128000 に丸め。12000 は有効 |
| statusLine.padding | 実在 | `c({type:v("command"),command:n(),padding:E().optional(),…})` |
| hooks[].statusMessage | 実在 103 件 | 文書 /hooks に「Custom spinner message」 |
| InstructionsLoaded（イベント） | 実在 | イベント名の列挙に含まれる |
| sandbox.allowUnsandboxedCommands / filesystem.denyRead / network.allowedDomains | 実在 17/42/36 件 | 文書の索引に同名あり |
| env.CLAUDE_CODE_GOAL_CHECKIN_MINUTES | 実在 3 件 | 文書 /env-vars:「Set `0` to turn check-ins off」 |
| onFailure（hook フィールド） | 実在 81 件 | キットでは未使用（→ -03） |
| disableAllHooks / allowManagedHooksOnly / CLAUDE_PLUGIN_ROOT / CLAUDE_CODE_REMOTE | 実在 | — |

実在しないキーはなかった。ただし「実在するが値の形が不正」が 1 件（-04）。値の形を確かめられなかったものが 1 件（-09）。

---

## 発見

### S5-cc-settings-01 ／ CLAUDE.md の前提「クラウドセッション＝hook 未導入」が公式文書と食い違う
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - `CLAUDE.md:12-14`: 「hook が入っていない環境（クラウドセッション等）… 最初の応答で『hook 未導入。憲法を手動で履行する』と宣言するまでツールを使わない」
  - https://code.claude.com/docs/en/cloud-environments 「What carries over from your setup」: 「Your repo's `.claude/settings.json` hooks and permission rules | Yes, in a session with one repository」。同じページで、プロジェクトのスレッドでは読まない（「It starts without … `.claude/settings.json` hooks and permission rules」）、複数リポジトリのセッションでも読まない（「a session with several repositories doesn't load hooks from any repository's `.claude/settings.json`」）
  - キット自身の `.claude/settings.json` は `$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/constitution-gate.py` を PreToolUse の先頭に配線している。cloud-environments の Installed tools には「Python 3.x」がある。つまりリポジトリ 1 つのクラウドセッションでは憲法ゲートが動く見込みが高い（実機では未確認）
  - `git grep -l CLAUDE_CODE_REMOTE` → 0 件。キットはクラウドかどうか、どのセッション種別かを判定していない
- 状態: 主張（文書）＋実証（grep）。クラウド実機で hook が動くかは未確認
- 改善の方向: 「クラウド」で一括りにせず 3 種に分ける（リポジトリ 1 つ＝リポジトリの hook が動く／複数リポジトリ・プロジェクトのスレッド＝動かない／ユーザー設定の hook＝どれでも動かない）。そのうえで、宣言の要否を `CLAUDE_CODE_REMOTE` と hook の実際の発火で判定する

### S5-cc-settings-02 ／ クラウドで hook を入れる手順として書かれた `/plugin` が、クラウドでは使えない
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - `CLAUDE.md:15`: 「導入: `/plugin marketplace add ma-garin/yuki-aidd-kit` → `/plugin install …`（hooks が入る）」。`06_保守者向け/02_設計判断の根拠/constitution-gate.md:40`: 「plugin 導入で塞ぐ」
  - https://code.claude.com/docs/en/claude-code-on-the-web 「Manage context」: 「Commands that only run in the terminal interface, such as `/plugin` or `/resume`, aren't available.」
  - https://code.claude.com/docs/en/cloud-environments: 「Plugins and marketplaces declared in your repo's `.claude/settings.json` | No | A cloud session doesn't install the plugins a repository turns on under `enabledPlugins`…」「Plugins enabled only in your user settings | No」
  - https://code.claude.com/docs/en/settings 「Settings in cloud sessions」: 複数リポジトリのセッションでも、`enabledPlugins` で宣言した plugin は「still don't load in a cloud session」
- 状態: 主張（文書）
- 改善の方向: クラウドで hook を効かせる経路は「リポジトリの `.claude/settings.json` に `$CLAUDE_PROJECT_DIR` 相対で配線する」1 本だと明記する。plugin 経路はローカル専用と書き分け、ADR の対策欄も直す

### S5-cc-settings-03 ／ 「hook の例外・時間切れは deny」が配線と Claude Code の仕様の両方で成り立たない
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - `CLAUDE.md:10`: 「hook の例外・時間切れは deny（素通りは合格ではない）」
  - https://code.claude.com/docs/en/hooks: 「On `PreToolUse`, a timed-out … hook doesn't block the tool call, except for hooks whose failure blocks the action… don't count on a stalled hook to act as a gate.」「Non-blocking error: your hook exits with any other code, or fails in some other way, such as not starting…」。失敗で止めるには `"onFailure": "block"`（v2.1.295 以降）が要る
  - `git grep -n onFailure` → 0 件。`onFailure` はバイナリ 2.1.330 に 81 件あり、使える
  - `.claude/settings.json:12` の配線 `sh -c 'f=…constitution-gate.py; [ -f "$f" ] && exec python3 "$f" pre || exit 0'` は、スクリプトが無ければ exit 0（素通り）になる。実験 `sh -c 'f="/nonexistent_zz.py"; [ -f "$f" ] && exec python3 "$f" pre || exit 0'` → `guarded exit=0`。同じファイルの `_comment` に「実体が無ければ無言で飛ばす」とあり、設計として fail-open になっている
  - 時間切れまでの猶予: plugin `hooks.json` の constitution-gate は timeout=5、`.claude/settings.json` は 10。時間切れになると素通りする
  - スクリプト内部の例外は deny で正しく処理している: `03_ClaudeCode/hooks/constitution-gate.py:352-371`（`except Exception` → `fail(...)`）
- 状態: 実証（終了コードの実験・grep）＋主張（文書の時間切れ挙動）
- 改善の方向: 憲法ゲートの配線に `"onFailure": "block"` を付ける。CLAUDE.md の文言は「スクリプト内部の例外は deny。時間切れ・起動失敗は onFailure で止める」に直す

### S5-cc-settings-04 ／ `autoCompactWindow: "200k"` は設定キーとして無効で、警告なしに捨てられる
- 種別: 欠陥
- 深刻度: Medium
- 根拠:
  - 雛形: `03_ClaudeCode/hooks/settings.json` と `00_導入/02_プロジェクト配布/export-project.sh:57` が `"autoCompactWindow": "200k"`。利用者向け資料（`01_利用者向け資料/note/…導入ガイド.md:384` ほか）、`03_ClaudeCode/commands/token-check.md:27`、`install.sh:80` も "200k" と案内している
  - バイナリ 2.1.330 の最上位キーのスキーマ: `autoCompactWindow:()=>Xr()…`、`Xr=()=>E().int().min(uF).optional().catch(void 0)`。整数だけを受け、文字列は `.catch(void 0)` で未設定に落ちる（静的に読んだ結果。実行時の挙動ではない）
  - https://code.claude.com/docs/en/model-config 「Set the auto-compact window」: 設定キーの例は `"autoCompactWindow": 200000`。`500k` のような接尾辞の形は「The command and the flag accept…」とあり、`/autocompact` と `--autocompact` だけが受ける。環境変数 `CLAUDE_CODE_AUTO_COMPACT_WINDOW` は v2.1.304 以降で `200k` を受ける（/env-vars）
  - 利用者の実際の `~/.claude/settings.json:194` は `"autoCompactWindow": 200000`（整数）で、雛形と食い違っている
  - `00_導入/03_点検/token_audit.py:28` はキーの有無しか見ないので、"200k" でも合格になる
- 状態: 実証（バイナリの静的抽出と文書の一致）。実行時に無視されることは未確認（`claude --settings s.json doctor` は "abc" を渡しても何も出さず、検出に使えなかった）
- 改善の方向: 雛形と資料を `200000` に統一し、token_audit で値の型（整数で 100000 以上）も検査する

### S5-cc-settings-05 ／ export-project.sh が書く `.claude/settings.json` に憲法ゲートが無い
- 種別: 欠落
- 深刻度: Medium
- 根拠: `grep -c constitution export-project.sh` → 0、`grep -c block-deps` → 0。一方、plugin の `hooks.json` と `03_ClaudeCode/hooks/settings.json` は、どちらも PreToolUse の先頭が `constitution-gate.py pre`、Stop に `constitution-gate.py stop` がある
- 状態: 実証（grep）
- 改善の方向: 配る経路 3 つ（plugin・ユーザー雛形・プロジェクト書き出し）の hook 一覧を 1 か所から生成するか、差分検査を回帰テストに入れる。クラウドでリポジトリの hook しか動かないこと（-01）を考えると、ゲートが要る経路は書き出し側である

### S5-cc-settings-06 ／ plugin とユーザー設定（install.sh）の両方を入れると、同じ hook が 2 回動く
- 種別: 欠陥
- 深刻度: Medium
- 根拠:
  - https://code.claude.com/docs/en/hooks: 「If you define the same handler in more than one settings file, it runs once. A plugin's or skill's copy of the same handler stays separate.」「matching hooks run in parallel」
  - plugin（`python3 "${CLAUDE_PLUGIN_ROOT}"/…/tool-timer.py pre`）とユーザー雛形（`python3 ~/.claude/hooks/tool-timer.py pre`）は同じ 29 本をコマンド文字列だけ変えて持つ。plugin の分は重複を除かれない。キット自身のリポジトリの `.claude/settings.json` も `sh -c '…'` 形式で文字列が違うので、ユーザー設定と重ねると重複は除かれない
  - `install.sh` で plugin 併用時の注意を探したが見つからない（`grep -n -i -E "plugin|二重|重複|両方"` → 該当は rules の重複スキップ 1 行だけ）
  - 並行に 2 回動くことで tool-timer の計測と constitution-gate の状態ファイルが競合するかは未確認
- 状態: 主張（文書）＋実証（文字列の比較・grep）。競合の影響は未確認
- 改善の方向: 導入経路は排他にする（plugin を入れたら install.sh の hook を外す）と明記し、hook 側でも同じイベントの二重起動を検知する

### S5-cc-settings-07 ／ hook のスクリプトが見つからないと python3 が exit 2 を返し、全ツールが「ブロック」扱いで止まる
- 種別: 欠陥
- 深刻度: Medium
- 根拠:
  - 実験: `python3 /nonexistent_zz.py` → `exit=2`。hook の仕様では exit 2 はブロックを意味する（/hooks「Blocking error: your hook exits 2」）
  - `export-project.sh:63-125` は `python3 .claude/hooks/x.py` と相対パスで書いている。スクリプト自身のコメントに「プロジェクトスコープ hooks はプロジェクトルートを作業ディレクトリとして実行される。環境によって異なる場合は要検証」とある。公式文書の例は `$CLAUDE_PROJECT_DIR` で書いている（/cloud-environments のインストール例:「`$CLAUDE_PROJECT_DIR` resolves to the repository root, so the hook finds the script regardless of the session's working directory」）
  - ユーザー雛形の `python3 ~/.claude/hooks/x.py` も、ファイルを配らずに settings だけ写すと同じことが起きる
  - 結果は経路で逆になる: `.claude/settings.json` の `[ -f ] || exit 0` は素通りし（-03）、こちらは全部止まる
- 状態: 実証（終了コード）。作業ディレクトリが変わったときに Claude Code 上で実際に止まるかは未確認
- 改善の方向: 書き出し側を `"$CLAUDE_PROJECT_DIR"/.claude/hooks/…` に揃える。ファイルが無いときの扱いは、意図に合わせて onFailure で明示する

### S5-cc-settings-08 ／ settings.sandbox.json の allow がキットの禁止事項と矛盾する
- 種別: 矛盾
- 深刻度: Low
- 根拠: `02_共通/ひな形/settings.sandbox.json` の permissions.allow に `Bash(git add *)`（`git add -A` も通る）、`Bash(git checkout *)`（`git checkout -- <file>` も通る。deny は `Bash(git checkout -- .)` 1 つだけ）、`Bash(npm install)` がある。AGENTS.md は `add -A`・`checkout --` を禁じ、H-4 は「担当に npm install をさせない」としている。`block-deps.py` も依存の追加を止めている
- 状態: 実証（ファイルの内容）。hook と permission のどちらが先に効くかは、この段では調べていない
- 改善の方向: allow を禁止事項と照らして絞る（`git add -A`・`git checkout --` を deny に入れる、`npm install` を allow から外す）

### S5-cc-settings-09 ／ settings.sandbox.json のオブジェクト内の `"// …"` キーが受け付けられるか確かめていない
- 種別: 欠陥（の疑い）
- 深刻度: Low
- 根拠: `sandbox` の中に `"// filesystem"`・`"// network"`、`permissions` の中に `"// allow"` などがある。/settings には「Settings Warning: only individual entries fail, such as a malformed permission rule or an unknown hook event name. Claude Code skips those values」「Settings Error: … a value the schema rejects」とある。sandbox と permissions のスキーマが未知のキーを拒むかは特定できなかった。`claude --settings … doctor` は不正な値でも何も出さず、確かめる手段にならなかった
- 状態: 未確認
- 改善の方向: 対話セッションで実際に読み込ませて Settings Warning/Error が出るか確かめる。出るなら説明用のキーを外へ出す（JSON の外の README に書く）

### S5-cc-settings-10 ／ token-check.md が、設定キーがあるときは無視される環境変数を案内している
- 種別: 矛盾
- 深刻度: Low
- 根拠: `03_ClaudeCode/commands/token-check.md:27` は `BASH_MAX_OUTPUT_LENGTH=12000` と書くが、雛形は `bashOutputMaxChars: 12000` を使っている。/env-vars:「If you set the `bashOutputMaxChars` setting, Claude Code ignores this variable.」。バイナリにも同じ優先の処理がある（`GW(){let e=k(vt().bashOutputMaxChars);if(e!==void 0)return e;return bGn("BASH_MAX_OUTPUT_LENGTH",…)}`）
- 状態: 実証（バイナリと文書の一致）
- 改善の方向: 文書の表記を `bashOutputMaxChars=12000` に揃える

### S5-cc-settings-11 ／ クラウドでは `~/.claude` の規約（AGENTS.md・rules）が載らないのに、それを補う手順が無い
- 種別: 機会
- 深刻度: Low
- 根拠: /cloud-environments:「Your user `~/.claude/CLAUDE.md` | No」「`~/.claude/skills/`, `agents/`, `commands/` | No」。補う方法として「add a setup script that writes `~/.claude/CLAUDE.md`」が示されている。キットの CLAUDE.md の hook 未導入節は hook だけを扱い、規約本体（A-1〜A-14 は `~/.claude/rules` にある）が無くなることには触れていない
- 状態: 主張（文書）
- 改善の方向: クラウド環境のセットアップスクリプトの雛形（`~/.claude/CLAUDE.md` と rules を書き出す）を配る経路として検討する

## 調べられなかったこと
- クラウド実機（claude.ai/code）でリポジトリの `.claude/settings.json` の hook が本当に発火するか、python3 の版、`CLAUDE_CODE_REMOTE` の値。いずれも未確認（文書による主張だけ）
- `autoCompactWindow: "200k"` が実行時に捨てられることの再現。`claude doctor --settings` に検出力がなかった。対話起動の `/status`・`/context` での確認はしていない
- sandbox と permissions のオブジェクトが未知キーを受け付けるか（-09）
- settings-reference の各キーの本文。ページが 46 万字あり、取得できたのは索引部分だけ。型はバイナリの静的抽出で補った
- plugin とユーザー設定の二重起動で状態ファイルが実際に競合するか（-06）
- 複数リポジトリのセッションと、自前でホストする環境の細かい規則（/self-hosted-environments-configuration は未読）

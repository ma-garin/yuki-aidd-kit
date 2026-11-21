# I8-install 内部実装: 導入スクリプト（段1・広域）

- 対象: `00_導入/`（01_インストール 6・02_プロジェクト配布 5・03_点検 9 = 20 ファイル）と `.claude-plugin/`（marketplace.json・plugin.json・hooks.json = 3 ファイル）。worktree: research-20261121（origin/main 7e80b79、VERSION 8.7.0）
- 調べた方法:
  - 静的読解: install.sh・install-guard.sh・install_guard.py・sync-agent-rules.py・plugin.json・marketplace.json・init-project.sh・export-project.sh・install-git-hooks.sh（本体）・verify.sh（冒頭と実行結果）・init-lifecycle.sh / init-test-docs.sh（上書き方針を grep）・token-audit.sh・check-screens.sh・doctor.py（docstring）
  - 機械比較: hooks.json と `03_ClaudeCode/hooks/settings.json` の hook 集合、export-project.sh の埋め込み settings と settings.json の hook 集合（python で集合差）
  - 実行（すべて scratchpad 内の一時 HOME・一時ディレクトリ。実環境の ~/.claude は触っていない）: install.sh を一時 HOME で 3 回、verify.sh、python3 を PATH から外した install.sh、空白入り・`#` 入りパス、init-project.sh、export-project.sh 2 回、install-git-hooks.sh を worktree と core.hooksPath 付きリポジトリで、相対パス hook をサブディレクトリから起動
  - 製品文書: https://code.claude.com/docs/en/hooks （取得日 2026-11-21、先頭 100,000 字のみ）
- 調べた件数/全件数: 16/23 ファイル（中身まで読んだ・実行した）。未読 7 件は末尾「調べられなかったこと」

---

## I8-install-01 install.sh を 2 回実行すると利用者の元の CLAUDE.md / AGENTS.md が失われる
- 種別: 欠陥
- 深刻度: High
- 根拠: install.sh:33-37・39-43 は既存を毎回 `cp X X.bak` で固定名に退避してから上書きする。一時 HOME に `CLAUDE.md=ORIGINAL`・`AGENTS.md=ORIG_AGENTS` を置いて 2 回実行 → 2 回目の後 `CLAUDE.md.bak` の先頭は `@AGENTS.md`（キットの版）、`AGENTS.md.bak` はキットの AGENTS.md。ORIGINAL はどこにも残らない。export-project.sh:25-30 の `backup_if_exists` も同じ固定名 `.bak`（CLAUDE.md・AGENTS.md・.claude/settings.json）
- 状態: 実証
- 改善の方向: 退避名に時刻を付ける（sync-agent-rules.py:22 と同じ方式）か、退避済み・内容同一なら退避しない

## I8-install-02 既存 settings.json がある利用者には安全系 hook の大半が配線されない
- 種別: 欠陥
- 深刻度: High
- 根拠: install.sh:79-83 は settings.json が既存なら「手動でマージしてください」と出すだけ。自動 merge は install_guard.py:23-32 の 4 ファイル（tool-timer×3 イベント・instruction-guard・prompt-priority・reply-language）だけ。一時 HOME（既存 settings.json あり）で実行後の hooks は `Stop 2 / PreToolUse 2 / PostToolUse 1 / UserPromptSubmit 2` 件で、block-destructive・pre-read-guard（秘密ファイルの読み取り deny）・injection-guard・block-deps・filter-output などは未配線。hook ファイル自体は ~/.claude/hooks/ に置かれる
- 状態: 実証
- 改善の方向: install_guard.py の merge 対象を settings.json の全 hook に広げる（冪等の仕組みは既にある）か、未配線を NG として出す

## I8-install-03 verify.sh は hook の配線を見ず、未配線でも OK=106 / NG=0 を返す
- 種別: 欠陥
- 深刻度: High
- 根拠: 02 の状態の一時 HOME で `HOME=… verify.sh` → `結果: OK=106 / NG=0`、rc=0。verify.sh:21-23 の `check` はファイルの存在（`-e`）だけを見る
- 状態: 実証
- 改善の方向: `03_ClaudeCode/hooks/settings.json` の command 集合と導入先 settings の command 集合の差を NG にする

## I8-install-04 export-project.sh の hook が相対パスで、サブディレクトリで起動すると python hook は exit 2、bash hook は exit 127
- 種別: 欠陥
- 深刻度: High
- 根拠: export-project.sh:60-127 の command は全部 `python3 .claude/hooks/…` / `bash .claude/hooks/…`。同ファイル:49-50 に「要検証」とある。製品文書は「Handlers run in the current directory」で、パスには `${CLAUDE_PROJECT_DIR}` を使うよう示している（hooks 文書）。配布先の `src/` から起動すると `python3 .claude/hooks/block-destructive.py` → `can't open file … rc=2`、`bash .claude/hooks/pre-write-check.sh` → `No such file or directory rc=127`。文書上 exit 2 はブロック扱いなので python 系は全ツールを止め、bash 系はブロックしない（素通り）。exit 2 の扱いは文書による（主張）、終了コードは実証
- 状態: 実証（終了コード）／主張（Claude Code 側の扱い）
- 改善の方向: `"${CLAUDE_PROJECT_DIR}"/.claude/hooks/…` に揃える（hooks.json は既に `${CLAUDE_PLUGIN_ROOT}` を使っている）

## I8-install-05 install-git-hooks.sh が worktree と core.hooksPath では効かないのに成功と表示する
- 種別: 欠陥
- 深刻度: High
- 根拠: install-git-hooks.sh:25-27 は `git rev-parse --git-dir` の下に `hooks/pre-commit` を書く。`git worktree` の中では `.git/worktrees/<名>/hooks/` になり、git はそこを使わない（`git rev-parse --git-path hooks` は `<repo>/.git/hooks`）。常に exit 1 の scripts/pre-commit を置いた検証で、worktree の commit は rc=0（hook 不発）、core.hooksPath=.husky のリポジトリも rc=0。対照（hooksPath なしの本体）は `SECRETSCAN` を出して rc=1。`grep -rnE 'hooksPath|git-common-dir|git-path' 00_導入` は 0 件。キット自身が worktree で研究・開発している
- 状態: 実証
- 改善の方向: `git rev-parse --git-path hooks` で場所を決め、core.hooksPath が設定済みなら NG で止める

## I8-install-06 export-project.sh の埋め込み settings が settings.json から乖離している
- 種別: 矛盾
- 深刻度: Medium
- 根拠: export-project.sh:54-133 はヒアドキュメントで settings を手書きしている。集合差（python）で settings.json にあって export に無いもの: `block-deps.py`（PreToolUse・Bash|Write|Edit）、`config-snapshot.py snapshot`（SessionStart・UserPromptSubmit）、憲法ゲート（PreToolUse・Stop）。export にだけあるものは 0。block-deps は新規依存追加を人の承認待ちにする hook（block-deps.py:2-12）で、配布先では効かない。憲法ゲートを配布先から外すのが意図かは未確認
- 状態: 実証
- 改善の方向: 埋め込みをやめ、settings.json から `~/.claude/hooks/` を `"${CLAUDE_PROJECT_DIR}"/.claude/hooks/` に置換して生成する（除外は明示リストにする）

## I8-install-07 init-project.sh が既存ディレクトリのファイルを黙って上書きする
- 種別: 欠陥
- 深刻度: Medium
- 根拠: init-project.sh:15-97 は `cat >` / `echo >` で .gitignore・CLAUDE.md・spec.md・plan.md・tasks.md・app.py 等を無条件に書く。既存の `spec.md=MY SPEC`・`.gitignore=secret.txt`・`CLAUDE.md=MINE` があるディレクトリで実行 → 3 つともキットの雛形に置き換わり、退避なし・rc=0。init-lifecycle.sh:11・40-43 と init-test-docs.sh:18-19 は既存をスキップしており方針が揃っていない。あわせて種別 `weird` も rc=0 で受け付ける（case に既定節なし、:64-92）。名前に `"` を含むと docs/manifest.json が JSON として壊れる（`JSONDecodeError: Expecting ',' delimiter`）
- 状態: 実証
- 改善の方向: 既存はスキップして報告（init-lifecycle と同じ方式）、種別を検証、名前は JSON エスケープする

## I8-install-08 export-project.sh を再実行しても scripts/ のゲートは古いまま残る
- 種別: 欠陥
- 深刻度: Medium
- 根拠: export-project.sh:165-179 は scripts/ の 26 本を「既存ならスキップ」する。skills・hooks・settings は上書きされるので、キットを更新して再配布すると hook は新しく、pre-commit・check_approval.py 等は古いという混在になる。回帰テストも「再実行は全件スキップ（↷ が 15）」を期待している（06_保守者向け/03_回帰テスト/test-install.sh:428）。版の差を知らせる仕組みは無い（KIT_VERSION は .claude/ にだけ刻む）
- 状態: 実証（コードとテストの期待値から）
- 改善の方向: キット配布物と内容が違うときは差分を報告するか、版付きで上書き＋退避する

## I8-install-09 アンインストール手段が無い（git hook 以外）
- 種別: 欠落
- 深刻度: Medium
- 根拠: `grep -rniE 'uninstall|アンインストール'` の該当は install-git-hooks.sh の `--uninstall` とその文書・テストだけ。install.sh は ~/.claude に skills 27・commands 25・agents 6・hooks 30・rules 10・scripts 3・templates・docs、~/.agents/skills に 71、~/.codex/AGENTS.md のリンクを置くが、外す手順もマニフェストも無い。install_guard.py が settings.json に入れた配線を外す手段も無い
- 状態: 実証
- 改善の方向: 導入時に配置したパス一覧を書き出し、それに基づく削除（退避）スクリプトを用意する

## I8-install-10 python3 が無いと静的検査を素通りし、CLAUDE.md を上書きした後で途中終了する
- 種別: 欠陥
- 深刻度: Medium
- 根拠: python3 を外した PATH で一時 HOME に実行 → `skill-scan が判定不能… UNKNOWN として導入を続ける`（install.sh:27-28）、CLAUDE.md と AGENTS.md を上書きし、:44 の `python3: command not found` で rc=127 で終了。残ったのは agents/commands/hooks/rules/skills の空ディレクトリと上書き済み CLAUDE.md。事前の依存確認が無い（doctor.py は別コマンド）
- 状態: 実証
- 改善の方向: 冒頭で python3（3.9+）・git の有無を確かめてから何も書かない段階で止める

## I8-install-11 同名スキルの手直しは退避なしで消え、削除された資産の残骸は残る
- 種別: 欠陥
- 深刻度: Medium
- 根拠: install.sh:47・58 は `cp -r skills/* ~/.claude/skills/`。一時 HOME で `done-gate/SKILL.md` に `MY CUSTOM` を足し、`done-gate/old-removed.md` を置いて再実行 → `MY CUSTOM` は 0 件（上書き）、`old-removed.md` は残る。`done-gate.bak` は無い。commands・agents・hooks も同じ `cp`
- 状態: 実証
- 改善の方向: 配置前に内容差を検出して退避し、前回の配置一覧（09 のマニフェスト）に無い残骸を報告する

## I8-install-12 plugin 経由と install.sh 経由で入る資産が食い違う
- 種別: 矛盾
- 深刻度: Medium
- 根拠: plugin.json:16-31 で入るのは skills・commands・agents 6・hooks（hooks.json）・outputStyles。hooks.json と settings.json の hook 集合は一致（集合差 0）。plugin で入らないもの: CLAUDE.md / AGENTS.md、rules 10、statusLine と settings の 3 キー・env、~/.claude/scripts（block-phase.py:47 のフォールバック先）、templates、docs、Codex スキル、KIT_VERSION。逆に install.sh と export-project.sh は `03_ClaudeCode/output-styles/`（quick.md・structured-report.md）を配らない（両スクリプトと verify.sh を `output-styles|outputStyle` で grep して 0 件）。README.md:15-24 は plugin を「skills・commands・agents・hooks が入る」と書くが、output-styles には触れていない
- 状態: 実証
- 改善の方向: 方式ごとに入る資産の表を 1 つ作って README と verify.sh の判定元にし、output-styles を install.sh にも入れる

## I8-install-13 plugin と install.sh を両方入れると hook が二重に動く
- 種別: 欠陥
- 深刻度: Medium
- 根拠: hooks 文書「If you define the same handler in more than one settings file, it runs once. A plugin's or skill's copy of the same handler stays separate.」と「When a plugin is enabled, its hooks merge with your user and project hooks.」。command の文字列も違う（`${CLAUDE_PLUGIN_ROOT}/03_ClaudeCode/hooks/…` と `~/.claude/hooks/…`）ので重複除去されない。tool-timer の pre/post が二重に記録されると実測が倍になる恐れがある。verify.sh を `plugin|CLAUDE_PLUGIN|二重|重複` で grep しても、二重導入の検出は 0 件
- 状態: 主張（文書）。二重実行の実機確認は未確認
- 改善の方向: verify.sh で plugin の有効化と settings 側の配線が両方あれば WARN を出し、README に「どちらか一方」を明記する

## I8-install-14 グローバル導入では design-system スキルが参照する templates/ui が入らない
- 種別: 欠落
- 深刻度: Medium
- 根拠: design-system/SKILL.md:3 は `templates/ui/components.css`・`templates/ui/layout.css` を真実源に挙げる。install.sh:62-66 は tokens.css と components/ の 4 ファイルだけを配る。一時 HOME の `~/.claude/templates` は 5 ファイルで ui/ は無い。キットには `02_共通/ひな形/ui/` に 7 ファイルある。export-project.sh:160 はひな形を丸ごと配るので、グローバル導入だけが欠ける
- 状態: 実証
- 改善の方向: install.sh でも `ひな形/ui/` を配るか、スキルの参照をグローバルで解決できるパスにする

## I8-install-15 macOS 既定の bash 3.2 と UTF-8 ロケールで `$VAR）` が化ける
- 種別: 欠陥
- 深刻度: Low
- 根拠: `LC_ALL=en_US.UTF-8 /bin/bash -c 'X=5; echo "exit $X）"'` → `exit ��`（C ロケールでは `exit 5）`）。bash 3.2.57 は全角括弧のバイトを変数名の一部として読む。該当箇所: install.sh:28、verify.sh:217・398（いずれも判定不能時の終了コード表示で、表示が失われる）。python3 なしの実行で `exit ��` を実際に確認した
- 状態: 実証
- 改善の方向: `${VAR}` に統一し、grep で `\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7F]` を検査に加える

## I8-install-16 キットのパスに `#` を含むと install.sh が何も入れずに終わる（空白・日本語は通る）
- 種別: 欠陥
- 深刻度: Low
- 根拠: install.sh:19 の `sed "s#$KIT_DIR/##"`。`kit with space#1` へのリンク経由で実行 → `sed: … bad flag in substitute command: '#'`、rc=1（set -e）。`kit with space` と空白入り HOME `home 4` では rc=0、hook（`python3 ~/.claude/hooks/tool-timer.py pre`）も rc=0、export-project.sh も空白入りの対象で rc=0。日本語（`04_AI開発基盤`・`00_導入`）は既定の環境で通っている
- 状態: 実証
- 改善の方向: sed の置換をやめ、python 側で相対化するか `${var#prefix}` を使う

## I8-install-17 文言とコメントの食い違い（hook の本数・配置先）
- 種別: 矛盾
- 深刻度: Low
- 根拠: install.sh:85 と install_guard.py:2 は「指示優先の 3 hook」だが、GUARDS は 4 ファイル（install_guard.py:23-32。install.sh:15 は「4 本」）。install-guard.sh:2 も「3 hook」。init-project.sh:79 は「01_利用者向け資料/ に配置」と出すが、実際は docs/ に書く（:66-78）。install.sh:121 の Codex 案内は sync-agent-rules.py の結果ではなく固定文
- 状態: 実証（grep・読解）
- 改善の方向: 本数は GUARDS から出力し、メッセージは実際の書き込み先から組み立てる

## I8-install-18 Windows（Codex 環境）ではシンボリックリンク作成で途中終了しうる
- 種別: 欠陥
- 深刻度: Low
- 根拠: install.sh:44 → sync-agent-rules.py:26 の `symlink_to` は失敗すると例外を再送出し、set -e で止まる。この時点で CLAUDE.md と AGENTS.md は上書き済み。doctor.py:3-4 は「Codex（Windows・git/bash 無し）」を想定しているが、install.sh は bash 前提。macOS では `date -I`・`sed -i.bak` を含め rc=0（実証）。Linux（GNU coreutils）では未実行
- 状態: 未確認（Windows・Linux で実行していない）
- 改善の方向: リンク失敗時はコピーに縮退し、対応 OS を README に書く

## I8-install-19 回帰テストに「再実行で元の内容が残るか」の検査が無い
- 種別: 欠落
- 深刻度: Low
- 根拠: test-install.sh:41 は 1 回目の `.bak` の内容だけ、:391-395 は再実行で `.bak` が「ある」ことだけを確かめる。01 の消失は検出されない。:152-169 の install-guard の冪等テストは配線数だけを見る
- 状態: 実証（テストの読解）
- 改善の方向: 2 回実行した後に元の内容が残っているかを expect_grep で確かめる

## I8-install-20 block-phase.py は plugin だけの導入だと判定スクリプトを見つけられない
- 種別: 欠落
- 深刻度: Low
- 根拠: block-phase.py:28・43-48 の探索先は `<project>/scripts`・`<project>/.claude/scripts`・`~/.claude/scripts` で、`${CLAUDE_PLUGIN_ROOT}/02_共通/ツール` は探さない。plugin だけを入れた利用者が `.claude/phase-gate` を置くと、Write/Edit はすべて deny になる（:84-91 のメッセージで export-project.sh を案内する）。安全側に倒れるが、plugin 単独では工程ゲートが使えない
- 状態: 主張（コード読解。plugin 環境で実行していない）
- 改善の方向: `CLAUDE_PLUGIN_ROOT` が定義されていれば同梱のツールを候補に加える

---

## 調べられなかったこと
- 未読 7 件: `external-skills.json`・`check_design.py`・`check_screens.py`・`token_audit.py` 本体・`token_report.py`・`check-design.sh`・`audit-app-workspace.sh`（check-design.sh / token-audit.sh / check-screens.sh は薄いラッパであることだけ確認）
- plugin を実際に `/plugin install` した環境での挙動（hook の二重実行、output-styles の読み込み、`${CLAUDE_PLUGIN_ROOT}` に日本語パスが入ったときの動き）。未確認
- Linux・Windows（Git Bash / WSL）での install.sh・export-project.sh の実行。未確認
- verify.sh の後半（設定の監査・文脈ファイルの点検）は、正常系の 1 回だけ実行した。NG 系の誤検知・見逃しは調べていない
- hooks 文書は 294,429 字のうち先頭 100,000 字だけ読んだ。exit 2 のブロック扱いは別節の記述で、今回は確認していない
- 他の AI 開発キットの導入スクリプトとの比較（clone・WebSearch は使っていない）

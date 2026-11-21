# I8-install 段2（深掘り）: 導入スクリプト

- 入力: `docs/research/2026-11-21/stage1/I8-install.md`（High 5 件・Medium 9 件・Low 6 件）
- 選定: High のうち影響の大きい順に 3 件
  1. I8-install-02（安全系 hook が配線されない。秘密ファイルの読み取り・破壊操作の deny が効かない）
  2. I8-install-01（再実行で利用者の元の CLAUDE.md / AGENTS.md が失われる。取り返しがつかない）
  3. I8-install-04（配布先のサブディレクトリから起動すると python hook が exit 2 で全ツールを止める）
  - 選ばなかった High: 03（verify.sh が配線を見ない）は 02 の検出漏れにあたるため、02 の再現の中で一緒に測った。05（git hook の worktree 問題）は 4 件目になるので段2では扱わない
- 実行環境: scratchpad の一時 HOME・一時ディレクトリ `S=/private/tmp/claude-501/-Users-fujimagariyuki-dev-active-04-AI-----yuki-aidd-kit/9b343f84-5f7a-427d-9432-30aedf317802/scratchpad/i8s2.ZDCl`。実環境の ~/.claude は触っていない。worktree は research-20261121（7e80b79 基準）
- 実行日時: 2026-11-21 16:50 以降（Asia/Tokyo）

再現コマンドはすべてリポジトリの worktree ルートで実行する。`S` は `mktemp -d` で作る一時ディレクトリに読み替える。

---

## I8-install-02 既存 settings.json がある利用者には安全系 hook の大半が配線されない
- 深刻度: High
- 再現手順:
  ```bash
  K=$PWD; S=$(mktemp -d); mkdir -p $S/h2/.claude
  printf '{"model":"x"}\n' > $S/h2/.claude/settings.json
  HOME=$S/h2 bash 00_導入/01_インストール/install.sh > $S/run2.log 2>&1; echo rc=$?
  grep -E 'settings.json が既存|配線' $S/run2.log
  python3 - "$S/h2/.claude/settings.json" "$K/03_ClaudeCode/hooks/settings.json" <<'EOF'
  import json,sys,re
  def cmds(p):
      d=json.load(open(p)); s=set()
      for es in d.get("hooks",{}).values():
          for e in es:
              for h in e.get("hooks",[]):
                  m=re.search(r'([\w.-]+\.(?:py|sh))',h.get("command",""))
                  if m: s.add(m.group(1))
      return d,s
  d1,a=cmds(sys.argv[1]); _,b=cmds(sys.argv[2])
  print({k:len(v) for k,v in d1["hooks"].items()}, sorted(a), len(b), len(b-a))
  EOF
  HOME=$S/h2 bash 00_導入/01_インストール/verify.sh > $S/verify.log 2>&1; echo rc=$?; grep 'OK=' $S/verify.log
  ```
- 実測結果:
  - install.sh は rc=0。表示は「⚠ settings.json が既存。hooks / statusLine と…を手動でマージしてください」と「✅ settings.json に配線: tool-timer.py ×3, instruction-guard.py, prompt-priority.py, reply-language.py」
  - 導入後の hooks: `PreToolUse 2 / PostToolUse 1 / UserPromptSubmit 2 / Stop 1`。配線されたのは 4 種（instruction-guard・prompt-priority・reply-language・tool-timer）
  - キットの settings.json にある hook は 25 種。そのうち **21 種が未配線**。未配線のうち安全系: `block-ci.py, block-deps.py, block-destructive.py, block-gates.py, filter-output.py, injection-guard.py, pre-read-guard.py`
  - hook の本体は置かれている（`$S/h2/.claude/hooks/block-destructive.py`・`pre-read-guard.py` は存在する）。置いただけで動かない
  - 同じ状態で verify.sh を流すと rc=0、`結果: OK=107 / NG=0`・「✅ 全て正常」（段1 は OK=106。件数の差は段1 と段2 の HEAD の違いと推定。未確認）。配線の欠けは検出されない（I8-install-03 も同時に再現）
  - 原因の場所: install.sh:79-83（既存なら手動マージの案内だけ）、install_guard.py:23-32（GUARDS は 6 エントリ・4 ファイルに限られる）
  - 段1 との差: 段1 は Stop 2 件、段2 は Stop 1 件。結論（安全系が未配線）は変わらない
- 判定: **再現**

## I8-install-01 install.sh を 2 回実行すると利用者の元の CLAUDE.md / AGENTS.md が失われる
- 深刻度: High
- 再現手順:
  ```bash
  S=$(mktemp -d); mkdir -p $S/h1/.claude
  printf 'ORIGINAL\n' > $S/h1/.claude/CLAUDE.md; printf 'ORIG_AGENTS\n' > $S/h1/.claude/AGENTS.md
  for i in 1 2; do HOME=$S/h1 bash 00_導入/01_インストール/install.sh > $S/run1_$i.log 2>&1; echo run$i rc=$?; done
  head -1 $S/h1/.claude/CLAUDE.md.bak; head -1 $S/h1/.claude/AGENTS.md.bak
  grep -rlx -e ORIGINAL -e ORIG_AGENTS $S/h1 | wc -l
  ```
- 実測結果:
  - 2 回とも rc=0
  - 2 回目の後、`CLAUDE.md.bak` の先頭は `@AGENTS.md`（キットの CLAUDE.md.template）。`AGENTS.md.bak` の先頭は `# AGENTS.md（共通規約。…）`（キットの AGENTS.md.template）
  - `ORIGINAL` / `ORIG_AGENTS` だけの行を持つファイルは一時 HOME 全体で **0 件**。利用者の元の内容は消えた
  - `.claude/` 直下の退避は `CLAUDE.md.bak`・`AGENTS.md.bak` の 2 つだけで、世代は残らない
  - 原因の場所: install.sh:33-37・39-43（`cp X X.bak` に固定名で上書き）。export-project.sh:25-30 の `backup_if_exists` も固定名 `.bak`（静的に確認。export を 2 回流す再現は段2 では実行していない）
- 判定: **再現**

## I8-install-04 export-project.sh の hook が相対パスで、サブディレクトリから起動すると python hook は exit 2・bash hook は exit 127
- 深刻度: High
- 再現手順:
  ```bash
  K=$PWD; S=$(mktemp -d); T=$S/proj; mkdir -p $T/src; git -C $T init -q
  bash 00_導入/02_プロジェクト配布/export-project.sh $T > $S/export.log 2>&1; echo export rc=$?
  python3 -c "import json,re;d=json.load(open('$T/.claude/settings.json'));c=[h['command'] for es in d['hooks'].values() for e in es for h in e['hooks']];print(len(c),sum(bool(re.match(r'(python3|bash) \.claude/',x)) for x in c),sum('CLAUDE_PROJECT_DIR' in x for x in c))"
  J='{"session_id":"t","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"ls"}}'
  cd $T;     echo "$J" | python3 .claude/hooks/block-destructive.py; echo root_py=$?
  cd $T;     echo "$J" | bash .claude/hooks/pre-write-check.sh;      echo root_sh=$?
  cd $T/src; echo "$J" | python3 .claude/hooks/block-destructive.py; echo src_py=$?
  cd $T/src; echo "$J" | bash .claude/hooks/pre-write-check.sh;      echo src_sh=$?
  cd $T/src; echo "$J" | python3 "$T"/.claude/hooks/block-destructive.py; echo src_abs=$?
  ```
- 実測結果:
  - export rc=0。配布先 settings.json の hook command は 24 本で、**24 本すべてが相対パス**（`python3 .claude/…` / `bash .claude/…`）、`CLAUDE_PROJECT_DIR` を使うものは 0 本
  - プロジェクトルートから起動: python rc=0、bash rc=0（正常）
  - `src/` から起動: python は `can't open file '…/proj/src/.claude/hooks/block-destructive.py': [Errno 2]` で **rc=2**、bash は `bash: .claude/hooks/pre-write-check.sh: No such file or directory` で **rc=127**
  - 対照: 同じ `src/` から絶対パスで起動すると rc=0（相対パスだけが原因）
  - 製品文書（https://code.claude.com/docs/en/hooks 、2026-11-21 再取得、先頭 100,000 字のみ読んだ）:
    - 「Handlers run in the current directory with Claude Code's environment.」
    - 「`${CLAUDE_PROJECT_DIR}`: the project root where the session started.」「In shell form, wrap each placeholder in double quotes.」
    - exit 2 は「Blocking error … Claude Code stops the action」、PreToolUse では「Blocks the tool call.」
    - 127 などその他は「Non-blocking error … The action goes ahead」
  - 以上から、セッションの現在ディレクトリが `src/` になったとき、PreToolUse の python hook（block-destructive・instruction-guard・pre-read-guard ほか）は exit 2 で**全ツール呼び出しを止める**。bash hook（pre-write-check・block-explore）は exit 127 で**検査なしで通る**。「全部止まる」と「検査が消える」が同時に起きる
  - 終了コードは実測。Claude Code が実際にどう扱うかは文書からの推論で、Claude Code 本体で動かす再現は未実行（未確認）
  - 原因の場所: export-project.sh:49-50 の「要検証」というコメントのとおり、`.claude/hooks/…` の相対パスを前提にしている（60-127 行）
- 判定: **再現**（終了コード）／Claude Code 本体での挙動は **未実行**

---

## 集計

| ID | 深刻度 | 判定 |
|---|---|---|
| I8-install-02 | High | 再現 |
| I8-install-01 | High | 再現 |
| I8-install-04 | High | 再現（本体挙動は未実行） |

- 02 を再現したとき、I8-install-03（verify.sh が NG=0 を返す）も同時に再現した
- 予備の段2 には I8-install-05（worktree / core.hooksPath で git hook が効かない）を推す

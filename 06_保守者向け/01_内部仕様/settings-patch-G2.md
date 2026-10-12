# settings-patch-G2 — キット自身の `.claude/settings.json` に当てる配線（保守者が当てる）

G2（文脈とループの hook）で足した配線のうち、キット自身の開発セッション用 `.claude/settings.json` の分。
この設定はエージェントが書き換えない（block-protected・`AIDD_ALLOW_CONFIG_EDIT=1` の運用）ので、保守者が手で当てる。
配布形の 2 経路（`03_ClaudeCode/hooks/settings.json`・`export-project.sh` のヒアドキュメント）は配線済み。
回帰テストは `06_保守者向け/03_回帰テスト/test-hooks.sh` の `[G2 の配線（settings.json・export-project.sh）]`。

## 足すもの

既存の書き方（実体が無ければ無言で飛ばす `sh -c` ラッパー）にそろえる。

### 1. PostToolUse — 観測（observe.py）

`"PostToolUse"` の先頭の要素（matcher 無し・tool-timer.py post）の `"hooks"` 配列の末尾に足す。

```json
{
  "type": "command",
  "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/observe.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
  "timeout": 5
}
```

### 2. Stop — 完了ループ（ralph-stop.py）

`"Stop"` の要素（reply-language.py）の `"hooks"` 配列の末尾に足す。`.claude/ralph.json` が無ければ何もしない。

```json
{
  "type": "command",
  "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/ralph-stop.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
  "timeout": 5
}
```

### 3. SessionStart — 再注入（session-context.py。B-29 の残と同じ。未適用なら一緒に当てる）

`"hooks"` の直下に足す（キーが無ければ新設）。G2 で直近の変更（observations.jsonl）も一緒に戻すようになった。

```json
"SessionStart": [
  {
    "matcher": "compact|resume",
    "hooks": [
      {
        "type": "command",
        "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/session-context.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
        "timeout": 5
      }
    ]
  }
]
```

### 4. （任意）PreToolUse — 読み直しの警告（pre-read-guard.py）

キット自身には pre-read-guard.py が配線されていない。読み直しの警告も効かせるなら `"PreToolUse"` に足す。
秘密ファイル・生成物の deny と大きいファイルの切り詰めも一緒に効くようになる（キットの開発で困る読み方は無い想定）。

```json
{
  "matcher": "Read|Grep|Glob",
  "hooks": [
    {
      "type": "command",
      "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/pre-read-guard.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
      "timeout": 5,
      "statusMessage": "読む価値とサイズを確認中"
    }
  ]
}
```

## 当てた後の確かめ方

1. `python3 -c "import json;json.load(open('.claude/settings.json'))"` が通る（JSON として妥当）
2. 何かファイルを 1 つ読んで、`.claude/observations.jsonl` に 1 行増える（中身は残らず、行数の要約だけ）
3. `/ralph` を使わない限り Stop の挙動は変わらない（`.claude/ralph.json` が無ければ ralph-stop.py は何もしない）

## 作業ファイル（コミットしない。`.gitignore` 済み）

| ファイル | 書く hook | 中身 |
|---|---|---|
| `.claude/observations.jsonl` | observe.py | 1 ツール 1 行の観測（時刻・ツール・パス・op・要約 60 字）。256KB 超で直近 1000 行に切り詰め |
| `.claude/read-seen.json` | pre-read-guard.py | 今のセッションで読んだファイルと mtime・回数（300 件まで。別セッションの記録は捨てる） |
| `.claude/ralph.json` | /ralph（作成）・ralph-stop.py（更新・削除） | 完了ループの状態 {prompt, iteration, max, done_phrase, session_id} |

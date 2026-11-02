# settings 配線の差分: config-snapshot.py / block-deps.py

AI はこの差分を `settings*.json` に当てない（この kit の規律）。**適用は保守者が行う。**
`03_ClaudeCode/hooks/settings.json`（配布元）と、導入先の `.claude/settings.json` の両方とも保守者が手で足す。

## 1. 足す配線（JSON の断片）

既存の `hooks` の各イベント配列の末尾に、次の要素を追加する（既存の要素は変えない）。

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command",
        "command": "python3 ~/.claude/hooks/config-snapshot.py snapshot" } ] }
    ],
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command",
        "command": "python3 ~/.claude/hooks/config-snapshot.py snapshot" } ] }
    ],
    "PreToolUse": [
      { "matcher": "Bash|Write|Edit",
        "hooks": [ { "type": "command",
          "command": "python3 ~/.claude/hooks/block-deps.py" } ] }
    ]
  }
}
```

- コマンドのパス表記は、既存の配線（`block-destructive.py` 等）と同じ書き方に揃える。
- `.claude/ai-config-log.jsonl` は導入先の記録。`.gitignore` に入れるか、検収の「構成の記録」として残すかを保守者が決める。

## 2. 動作

| hook | 契機 | 出力 |
|---|---|---|
| config-snapshot.py snapshot | SessionStart・UserPromptSubmit | 前回と差があるときだけ追記し、additionalContext に「AI の構成が変わった: <項目>」。初回・無変化は無出力。失敗しても止めない |
| config-snapshot.py report [N] | 手動（検収） | 直近 N 件の変更履歴の表 |
| block-deps.py | PreToolUse（Bash/Write/Edit） | 新規依存の追加を deny。承認後 `AIDD_DEPS_OK=1` で通し override を記録。初出名は WARN。読めない入力は deny |

## 3. 確認

```bash
bash 06_保守者向け/03_回帰テスト/test-config-deps.sh   # 最終行 結果: PASS=n / FAIL=0
```

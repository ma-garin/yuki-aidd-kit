# Codex hooks（AIDD の hook を Codex CLI で効かせる）

共通規約で「Codex では機械が止めない」としていた 3 項目（ゲートの無断実行・破壊操作・実装モード中の再探索）を、
Codex CLI の hook で止める。原本は `03_ClaudeCode/hooks/` のまま複製せず、`codex_hook_adapter.py` が入出力だけ変換する。

## 導入

```bash
./04_Codex/hooks/install.sh
```

- 既存の `~/.codex/hooks.json` を `hooks.json.bak-<日時>` に退避し、既存定義を残してマージする（再実行しても重複しない）
- 原本は `~/.claude/hooks`（無ければこのリポジトリの `03_ClaudeCode/hooks`）を参照する
- 導入後は Codex を再起動し、`/hooks` で確認・信頼する。信頼前に効いているとは扱わない
- 検証: `python3 -m unittest discover -s 04_Codex/hooks -p 'test_codex_hook_adapter.py'`

## Codex hook の仕様（確認元: Codex 0.163.0 バイナリ同梱の JSON スキーマ）

- イベント: PreToolUse / PostToolUse / PermissionRequest / UserPromptSubmit / SessionStart / SessionEnd / SubagentStart / SubagentStop / PreCompact / PostCompact / Stop
- PreToolUse の stdin: `session_id`・`turn_id`・`tool_use_id`・`transcript_path`・`cwd`・`hook_event_name`・`model`・`permission_mode`・`tool_name`・`tool_input`
- deny: `hookSpecificOutput.permissionDecision: "deny"` と空でない `permissionDecisionReason`
- PreToolUse は `allow`・`ask`・`updatedInput` を受け付けない。アダプタは原本の `ask` を deny に変える（安全側）
- hooks.json の書式は Claude Code と同じ（`hooks.<イベント>[].matcher / hooks[].type=command / command / timeout`）。出典は既存の `04_Codex/estimate-guard/`

## 分類（原本 27 ファイル。`settings.json` は配線表のため対象外）

| 区分 | 件数 | 原本 |
|---|---|---|
| そのまま動く | 2 | 下記 A |
| 差分を吸収して動く | 4 | 下記 B |
| Claude 専用・移植不可 | 21 | 下記 C |

- A（出力形式が同じ。passthrough で実行）: `prompt-priority.py`（UserPromptSubmit）・`subagent-context.py`（SubagentStart）
- B（pretool アダプタ。シェル系ツールを `Bash` + `command` に直す）: `block-destructive.py`・`block-gates.py`・`block-ci.py`・`block-explore.sh`（`--explore`。読取系コマンドを Read / Grep / Glob として渡す）
- C の理由:
  - Claude の transcript 形式を読む: `instruction-guard.py`・`reply-language.py`・`ralph-stop.py`・`context-guard.py`
  - Write / Edit / Read ツール前提。Codex は `apply_patch` とシェルで扱う: `pre-write-check.sh`・`block-phase.py`・`post-write-html.sh`・`pre-read-guard.py`・`injection-guard.py`
  - `updatedInput` で書き換える。Codex は非対応: `filter-output.py`
  - Codex に無いイベント・機能: `log-instructions.py`（InstructionsLoaded）・`statusline.py`・`statusline.sh`
  - `~/.claude/` の計測・観測・要約に書く: `tool-timer.py`・`observe.py`・`session-context.py`・`session-summary.sh`・`pre-compact.py`
  - hook ではない部品: `progress.py`・`secret_patterns.py`

## 未確認

- Codex のシェル系ツールの `tool_name` の実値。アダプタは `Bash`・`shell`・`exec_command` 等と、`command`/`cmd` を持つ入力をすべてシェルとして扱う。`AIDD_CODEX_HOOK_LOG=<ファイル>` で実値を記録できる
- 実機での deny の発火。2026-10-18 は `codex exec` が利用上限で止まり、hooks.json の読み込みエラーが出ないことまでしか確認していない
- 信頼前の hook が `codex exec` で実行されるか
- `pre-compact.py` は PreCompact の出力スキーマに `additionalContext` があるか未確認のため配線していない

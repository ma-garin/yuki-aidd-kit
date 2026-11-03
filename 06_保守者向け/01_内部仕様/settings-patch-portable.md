# settings-patch-portable — `.claude/settings.json`（W4 手元 clone）を真実源 hooks.json に揃える差分

- 対象: このリポジトリの `.claude/settings.json`（W4）。AI は当てない（CLAUDE.md・制約）。**保守者が `AIDD_ALLOW_CONFIG_EDIT=1` で起動して当てる**
- 生成: `python3 00_導入/01_インストール/gen-wiring.py --target local`（標準出力のみ。ファイルは書かない）
- 現状: `gen-wiring.py --check` は rc=0（W1・W2 一致・W4 は欠落 12 件を WARN 表示）。`--check --strict` は rc=1。下の差分を当てると `--strict` も rc=0 になる
- 欠落していた hook: block-ci・block-destructive・block-gates・filter-output・block-explore・pre-write-check・block-phase・post-write-html・pre-compact・log-instructions・session-summary・context-guard
- 順序: constitution-gate pre が PreToolUse の先頭（`02_設計判断の根拠/constitution-gate.md` の規定）。hook の timeout は hooks.json の値（constitution-gate は 5 秒）に揃う
- `_comment`・`env` は保持する

## 当て方（番号順）
1. 下の diff を `/tmp/w4.diff` に保存する
2. `patch -p1 --dry-run < /tmp/w4.diff` で当たることを確かめる
3. `patch -p1 < /tmp/w4.diff`
4. `python3 00_導入/01_インストール/gen-wiring.py --check --strict; echo rc=$?` が rc=0
5. 代替: `python3 00_導入/01_インストール/gen-wiring.py --target local > .claude/settings.json`（diff と同じ結果）

## 差分（unified diff）

```diff
--- a/.claude/settings.json
+++ b/.claude/settings.json
@@ -10,7 +10,7 @@
           {
             "type": "command",
             "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/constitution-gate.py\"; [ -f \"$f\" ] && exec python3 \"$f\" pre || exit 0'",
-            "timeout": 10
+            "timeout": 5
           }
         ]
       },
@@ -27,6 +27,16 @@
         "hooks": [
           {
             "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/block-ci.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "timeout": 5,
+            "statusMessage": "自己ウェイク・CI 待ちでないか確認中"
+          }
+        ]
+      },
+      {
+        "hooks": [
+          {
+            "type": "command",
             "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/instruction-guard.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
             "timeout": 5,
             "statusMessage": "保守者の指示に応答済みか確認中"
@@ -34,6 +44,21 @@
         ]
       },
       {
+        "matcher": "Write|Edit|MultiEdit",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/pre-write-check.sh\"; [ -f \"$f\" ] && exec bash \"$f\" || exit 0'"
+          },
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/block-phase.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "timeout": 25,
+            "statusMessage": "前工程の承認を確認中"
+          }
+        ]
+      },
+      {
         "matcher": "Read|Grep|Glob",
         "hooks": [
           {
@@ -41,6 +66,33 @@
             "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/pre-read-guard.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
             "timeout": 5,
             "statusMessage": "読む価値とサイズを確認中"
+          },
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/block-explore.sh\"; [ -f \"$f\" ] && exec bash \"$f\" || exit 0'"
+          }
+        ]
+      },
+      {
+        "matcher": "Bash",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/block-destructive.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "timeout": 5,
+            "statusMessage": "取り返しのつかない操作でないか確認中"
+          },
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/block-gates.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "timeout": 10,
+            "statusMessage": "ゲート実行の要否を確認中"
+          },
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/filter-output.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "timeout": 5,
+            "statusMessage": "冗長な出力を絞る書き換えを確認中"
           }
         ]
       },
@@ -55,48 +107,69 @@
         ]
       }
     ],
-    "PostToolUse": [
+    "UserPromptSubmit": [
       {
         "hooks": [
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/tool-timer.py\"; [ -f \"$f\" ] && exec python3 \"$f\" post || exit 0'",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/tool-timer.py\"; [ -f \"$f\" ] && exec python3 \"$f\" reset || exit 0'",
+            "timeout": 5
+          }
+        ]
+      },
+      {
+        "hooks": [
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/prompt-priority.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
             "timeout": 5
           },
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/observe.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/context-guard.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
             "timeout": 5
           }
         ]
       },
       {
-        "matcher": "WebFetch|WebSearch|mcp__.*|Read",
         "hooks": [
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/injection-guard.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
-            "timeout": 5,
-            "statusMessage": "取得内容に埋め込まれた指示を確認中"
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/config-snapshot.py\"; [ -f \"$f\" ] && exec python3 \"$f\" snapshot || exit 0'",
+            "timeout": 5
           }
         ]
       }
     ],
-    "UserPromptSubmit": [
+    "SubagentStart": [
       {
         "hooks": [
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/tool-timer.py\"; [ -f \"$f\" ] && exec python3 \"$f\" reset || exit 0'",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/subagent-context.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
             "timeout": 5
           }
         ]
-      },
+      }
+    ],
+    "PreCompact": [
       {
         "hooks": [
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/prompt-priority.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/pre-compact.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "timeout": 5
+          }
+        ]
+      }
+    ],
+    "SessionStart": [
+      {
+        "matcher": "compact|resume",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/session-context.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
             "timeout": 5
           }
         ]
@@ -111,49 +184,59 @@
         ]
       }
     ],
-    "SubagentStart": [
+    "InstructionsLoaded": [
       {
         "hooks": [
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/subagent-context.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/log-instructions.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
             "timeout": 5
           }
         ]
       }
     ],
-    "Stop": [
+    "PostToolUse": [
       {
         "hooks": [
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/reply-language.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/tool-timer.py\"; [ -f \"$f\" ] && exec python3 \"$f\" post || exit 0'",
             "timeout": 5
           },
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/ralph-stop.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/observe.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
             "timeout": 5
           }
         ]
       },
       {
+        "matcher": "Write|Edit|MultiEdit",
         "hooks": [
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/constitution-gate.py\"; [ -f \"$f\" ] && exec python3 \"$f\" stop || exit 0'",
-            "timeout": 10
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/post-write-html.sh\"; [ -f \"$f\" ] && exec bash \"$f\" || exit 0'"
+          }
+        ]
+      },
+      {
+        "matcher": "WebFetch|WebSearch|mcp__.*|Read",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/injection-guard.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "timeout": 5,
+            "statusMessage": "取得内容に埋め込まれた指示を確認中"
           }
         ]
       }
     ],
-    "SessionStart": [
+    "Stop": [
       {
-        "matcher": "compact|resume",
         "hooks": [
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/session-context.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/constitution-gate.py\"; [ -f \"$f\" ] && exec python3 \"$f\" stop || exit 0'",
             "timeout": 5
           }
         ]
@@ -162,7 +245,16 @@
         "hooks": [
           {
             "type": "command",
-            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/config-snapshot.py\"; [ -f \"$f\" ] && exec python3 \"$f\" snapshot || exit 0'",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/reply-language.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
+            "timeout": 5
+          },
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/session-summary.sh\"; [ -f \"$f\" ] && exec bash \"$f\" || exit 0'"
+          },
+          {
+            "type": "command",
+            "command": "sh -c 'f=\"$CLAUDE_PROJECT_DIR/03_ClaudeCode/hooks/ralph-stop.py\"; [ -f \"$f\" ] && exec python3 \"$f\" || exit 0'",
             "timeout": 5
           }
         ]
```

# コーディング前の見積ガード

Codex 0.163.0 の UserPromptSubmit / PreToolUse を使う。
現在の依頼以降の assistant commentary に独立行 `見積：N分` がない場合、コード編集と判定不能な実行を拒否する。
文書・設定ファイルだけの明確な編集と、既知の読取専用コマンドは対象外。

`hooks.json.example` の絶対パスを実体へ置換して `~/.codex/hooks.json` に既存定義とマージする。
クライアントを再起動し、`/hooks` で review / trust する。信頼前に強制確認済みとは扱わない。
無害な編集への拒否を実際に確認してから有効と報告する。

transcript は末尾 256 KiB のみ読む。最新 user 境界が取得できない場合、コード編集を拒否する。
対応形式は rollout JSONL の response_item/message role/channel/content と event_msg/user_message。
秘密名・解決後の秘密パスは開かない。transcript の形式は非安定なので、Codex 更新時に再検証する。
Hosted tools、一部の特殊ツール、既存 write_stdin は完全な強制範囲ではない。
文書・設定の拡張子で例外を判断するため、それらに埋め込まれた実行コードの意味検査は行わない。

仕様：[公式 Hooks](https://learn.chatgpt.com/docs/hooks)。
PreToolUse は `permissionDecision: deny` を返す。`continue: false` は利用しない。
検証：`python3 -m unittest discover -s 04_Codex/estimate-guard -p 'test_estimate_guard.py'`。

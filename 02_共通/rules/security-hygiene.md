---
paths:
  - "**/*.{py,js,ts,tsx,jsx,sh}"
---
# 秘密情報の取り扱い（実装側の規約）

- 秘密を書き出すファイル（設定・トークン・キャッシュ）は権限 `0600` で作る。作ってから `chmod` ではなく作成時に指定する
- エラー出力・ログに URL を出すときは、`user:pass@` やクエリのトークンを伏せてから出す
- 診断コマンド（doctor・health check）は副作用のある認証確認をしない。ログイン試行・トークン更新・課金 API を呼ばず、読み取りだけで判定する

（参照: Agent-Reach config.py, utils/text.py。`.env` と鍵を読まない規則は `absolute-rules.md` の常時行）

# Node Web（Express・Fastify・Next.js 等）の監査観点（OWASP Top 10 2021 ／ ASVS 4.0.3）

対象: Node の Web アプリ・API・SSR。E2E（Playwright）の設定もここで見る。
使い方: 該当しそうな 3〜5 行だけを選ぶ。「キットの対策」は効いているかを確かめ、「未対応」は手で読んで file:line を残す。

| 項目 | キットの対策（hook・検査・規約） | 未対応（手で見る） |
|---|---|---|
| A01 アクセス制御（ASVS V4.1・V4.2） | なし | ルートごとの認可ミドルウェアの付け忘れ、ID を受ける所で持ち主を確かめているか（IDOR）、Next.js の API Route・Server Action の認可 |
| A03 注入（ASVS V5.3） | `security-scan.sh`（semgrep のローカル規則か簡易シグネチャ: 子プロセスの exec 系・innerHTML・dangerouslySetInnerHTML・document.write） | クエリの組み立て（ORM の raw・テンプレート文字列）、NoSQL の演算子注入（`$where`・`$ne` を含む JSON）、パスの結合 |
| A03 表示（ASVS V5.3.3） | 同上（dangerouslySetInnerHTML） | Markdown・リッチテキストの描画でサニタイズしているか（DOMPurify 等） |
| A08 完全性・プロトタイプ汚染（ASVS V5.1.5・V10.3） | なし | 入力の JSON を深い merge に入れていないか（`__proto__`・constructor）。postinstall スクリプトを持つ依存 |
| A06 古い部品（ASVS V14.2） | `security-scan.sh`（npm audit・osv-scanner・trivy） | lockfile をコミットしているか、`npm ci` で入れているか。走査器が未導入なら未検査 |
| A02 機密（ASVS V6・V8） | `pre-write-check.sh`・`pre-commit`・gitleaks（秘密値）、`pre-read-guard.py` | クライアントへ出る環境変数（NEXT_PUBLIC_ 等）に秘密が無いか、ソースマップの公開 |
| A07 認証・セッション（ASVS V2・V3） | なし | JWT の検証（alg・期限・署名鍵）、Cookie の Secure・HttpOnly・SameSite、ログアウトで失効するか |
| A05 設定（ASVS V14.4） | なし | helmet 等のヘッダ（CSP・HSTS・X-Content-Type-Options）、CORS の origin を `*` にしていないか、本番のスタックトレース表示 |
| A04 設計（ASVS V11.1） | なし | レート制限、アップロードの大きさ、長い正規表現（ReDoS） |
| A09 記録（ASVS V7） | なし | 認証の失敗の記録、ログにトークン・個人情報を書いていないか |
| A10 SSRF（ASVS V12.6.1） | なし | 利用者の URL を fetch・axios で取る所（画像の取り込み・Webhook）。社内アドレスを拒否するか |
| E2E の設定 | `e2e-cycle`（テストは手元のブラウザで回す） | Playwright の storageState・テスト用アカウントの資格情報をリポジトリに置いていないか |

## 手で確かめる順（目安 30 分）

1. ルート・API の一覧 → 認可の有無を表にする（A01）
2. 入力が DB・シェル・HTML に入る所を grep（A03）
3. package.json の scripts・依存の postinstall・lockfile（A06・A08）
4. ヘッダ・CORS・Cookie の設定（A05・A07）

## 報告の例

| ID | 項目 | 重大度 | file:line | 根拠 | 直し方の案 |
|---|---|---|---|---|---|
| SA-1 | A03 / V5.3.3 | High | src/components/Comment.tsx:22 | 投稿本文を dangerouslySetInnerHTML にそのまま渡している | テキストとして描画する。Markdown が要るならサニタイザを通す |

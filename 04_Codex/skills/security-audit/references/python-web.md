# Python Web（Flask・FastAPI・Django）の監査観点（OWASP Top 10 2021 ／ ASVS 4.0.3）

対象: Python の Web アプリ・API。Streamlit は `streamlit.md` を使う。
使い方: 該当しそうな 3〜5 行だけを選ぶ。「キットの対策」は効いているかを確かめ、「未対応」は手で読んで file:line を残す。

| 項目 | キットの対策（hook・検査・規約） | 未対応（手で見る） |
|---|---|---|
| A01 アクセス制御（ASVS V4.1・V4.2） | なし | 各ルートの認可（デコレータ・Depends・permission_classes）の付け忘れ。ID を URL で受ける所で持ち主を確かめているか（IDOR） |
| A03 注入（ASVS V5.3.4・V5.3.8） | `security-scan.sh`（bandit か簡易シグネチャ: shell=True・os.system・pickle.loads・yaml.load） | raw SQL・`text()`・`extra()` に入力を連結していないか。テンプレートの自動エスケープを切っていないか（`|safe`・Markup） |
| A07 認証・セッション（ASVS V2・V3） | なし | パスワードのハッシュ（bcrypt・argon2）、セッションの失効、Cookie の Secure・HttpOnly・SameSite |
| A02 暗号・機密（ASVS V6・V8・V9） | `pre-write-check.sh`・`pre-commit`・`security-scan.sh` の gitleaks（秘密値）、`pre-read-guard.py` | SECRET_KEY・DB の接続文字列の置き場、HTTPS の強制、個人情報の暗号化の要否 |
| A05 設定（ASVS V14.1・V14.3） | なし | DEBUG=True のまま出さないか、ALLOWED_HOSTS・CORS の許可範囲、エラー画面に内部情報を出さないか |
| A06 古い部品（ASVS V14.2） | `security-scan.sh`（pip-audit・osv-scanner・trivy） | 走査器が未導入なら未検査。版の固定（lock・hash 付き requirements） |
| A08 完全性（ASVS V10.3・V1.14） | なし | pickle・yaml.load で外から来たデータを読んでいないか。更新・デプロイの手順で署名・ハッシュを確かめるか |
| A04 設計（ASVS V11.1） | なし | レート制限（ログイン・パスワード再設定・高コストな API）、処理の順序を飛ばせないか |
| A09 記録（ASVS V7.1・V7.2） | なし | 認証の失敗・権限エラーの記録、ログに秘密・トークンを書いていないか |
| A10 SSRF（ASVS V12.6.1） | なし | 利用者の URL を requests 等で取りに行く所。社内アドレス・メタデータ（169.254.169.254）を拒否するか |
| CSRF（ASVS V4.2.2） | なし | フォーム・Cookie 認証の API に CSRF 対策（Django の CsrfViewMiddleware・Flask-WTF 等）があるか |

## 手で確かめる順（目安 30 分）

1. ルートの一覧を出す（`flask routes`・FastAPI の openapi・Django の urls）→ 認可の有無を表にする（A01）
2. 入力が SQL・シェル・テンプレートに入る所を grep（A03）
3. 設定ファイル（settings・config）の DEBUG・CORS・Cookie（A05・A07）
4. 外へ取りに行く所（A10）と、外から来たデータを復元する所（A08）

## 報告の例

| ID | 項目 | 重大度 | file:line | 根拠 | 直し方の案 |
|---|---|---|---|---|---|
| SA-1 | A01 / V4.2.1 | High | app/routes/orders.py:57 | 注文 ID だけで取得し、持ち主を確かめていない | ログイン中の利用者 ID を条件に足す。他人の ID で 404 になるテストを先に書く |

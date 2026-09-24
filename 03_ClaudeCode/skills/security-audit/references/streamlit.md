# Streamlit アプリの監査観点（OWASP Top 10 2021 ／ ASVS 4.0.3）

対象: Streamlit の業務アプリ（business_agent 系・RAG・マルチテナント）。`skills/streamlit-rag-app/SKILL.md` の構成が前提。
使い方: 該当しそうな 3〜5 行だけを選ぶ。「キットの対策」は効いているかを確かめ、「未対応」は手で読んで file:line を残す。

| 項目 | キットの対策（hook・検査・規約） | 未対応（手で見る） |
|---|---|---|
| A01 アクセス制御・テナント越境（ASVS V4.1・V4.2） | `nfr-standards`（テナント ID を全クエリの第一キーにする・越境の単体テスト）、`done-gate`（越境しないことを確認） | テナント ID を session_state から取る箇所と、クエリに渡る箇所を全部たどる。URL の query_params で他テナントを指せないか |
| A07 認証（ASVS V2・V3） | なし | ログインの仕組み（st.login・リバースプロキシ・自前）と、未ログインで画面を開いたときの動き。session_state を認証の証拠にしていないか |
| A03 注入（ASVS V5.3.4・V5.3.8） | `security-scan.sh`（bandit か簡易シグネチャ: shell=True・os.system・pickle.loads・yaml.load） | SQL を f-string で組んでいないか（プレースホルダを使う）。ファイル名・パスを入力から作っていないか |
| A03 表示（ASVS V5.3.3） | なし | `st.markdown(..., unsafe_allow_html=True)`・`st.components.v1.html` に入力や LLM の出力を渡していないか |
| A02 機密データ（ASVS V6・V8） | `nfr-standards`・`done-gate`（キーは .env から・.env を .gitignore へ）、`pre-read-guard.py`（AI が秘密ファイルを読まない）、`pre-commit`（コミット前の秘密値） | secrets.toml・.env の置き場所と権限。画面・ログ・例外表示に秘密が出ないか |
| A06 古い部品（ASVS V14.2） | `security-scan.sh`（pip-audit・osv-scanner・trivy） | 走査器が未導入なら未検査。requirements の版を固定しているか |
| A04 設計・資源の上限（ASVS V11・V12.1） | なし | アップロードの大きさ・種類の制限、LLM 呼び出しの回数・トークンの上限（利用者ごと） |
| A05 設定（ASVS V14.3） | なし | `.streamlit/config.toml` の server.enableXsrfProtection・enableCORS を無効にしていないか。デバッグ表示（st.exception で内部情報）を出していないか |
| A09 記録（ASVS V7.1） | なし | 誰がいつ何を見たか・変えたかの記録。ログに秘密と個人情報を書いていないか |
| A10 SSRF（ASVS V12.6） | なし | 利用者の URL を取得する機能（RAG の取り込み等）が社内アドレスへ届かないか |
| LLM・RAG | `skills/nfr-standards/references/llm-agentic-top10.md`、`streamlit-rag-app`（LLM 呼び出しはラッパーに集約） | 取り込み文書の注入・出力の扱い・ツール権限は LLM の点検表で見る |

## 手で確かめる順（目安 20 分）

1. テナントの流れ（A01）: tenant_id を grep して、取り出し → クエリの経路を表にする
2. 画面への出力（A03 表示）: unsafe_allow_html と components.html の呼び出しを全部見る
3. 秘密の置き場（A02）: 読み込み箇所・例外表示・ログ出力
4. 依存（A06）: security-scan の未検査の有無

## 報告の例

| ID | 項目 | 重大度 | file:line | 根拠 | 直し方の案 |
|---|---|---|---|---|---|
| SA-1 | A01 / V4.2.1 | Critical | modules/search.py:88 | tenant_id を条件に入れずに文書を検索している | ラッパーでテナント条件を必須にし、越境の単体テストを足す |

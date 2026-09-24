# 単一 HTML・PWA の監査観点（OWASP Top 10 2021 ／ ASVS 4.0.3）

対象: HTML 1 枚で完結するツール、GitHub Pages に置く PWA（Service Worker・localStorage）。サーバは無い前提。
使い方: 該当しそうな 3〜5 行だけを選ぶ。「キットの対策」は効いているかを確かめ、「未対応」は手で読んで file:line を残す。

| 項目 | キットの対策（hook・検査・規約） | 未対応（手で見る） |
|---|---|---|
| A03 注入・XSS（ASVS V5.3） | `security-scan.sh` の簡易シグネチャ（innerHTML への代入・document.write）、`nfr-standards`（textContent を使う） | 利用者の入力・読み込んだ JSON・URL の値が DOM に入る経路を全部たどる。テンプレート文字列で HTML を組み立てていないか |
| A02 機密データ（ASVS V6・V8） | `pre-write-check.sh`・`pre-commit` が既知形式の秘密値の書き込みとコミットを止める、`done-gate`（API キーを埋め込まない） | localStorage に置く値（API キー・個人情報）の範囲と消し方。エクスポートした JSON に秘密が混ざらないか |
| A05 設定の誤り（ASVS V14.4） | なし | CSP（meta の Content-Security-Policy）の有無と中身、`target="_blank"` に rel="noopener"、iframe に入れられてよいか |
| A06 古い部品（ASVS V14.2） | `check_design.py` D04 が外部 CDN の読み込みを NG にする（同梱が既定） | 同梱したライブラリの版と既知脆弱性（走査器が拾えない手置きの .js）。版をファイル名かコメントに残す |
| A08 完全性（ASVS V10.3・V14.2.3） | D04（外部 CDN を読まない） | やむなく CDN を使うなら integrity（SRI）と crossorigin。Service Worker が古いキャッシュを返し続けないか（版の文字列を上げる運用） |
| A01 アクセス制御（ASVS V4） | なし（サーバが無い） | 「隠しボタン」「管理モード」をクライアント側の判定だけで守っていないか。守れないものは置かない |
| A04 設計（ASVS V1・V11） | `nfr-standards` の PWA・単一 HTML の NFR | インポート機能が不正な JSON（巨大・型違い・__proto__ を含む）を受けたときの動き。上書き前の確認 |
| A09 記録（ASVS V7） | なし | console に秘密・個人情報を出していないか（配布前に console.log を見直す） |
| A10 SSRF 相当 | なし | 利用者が入れた URL を fetch する機能があるなら、送り先を固定・許可リストにする |
| LLM API を直接呼ぶ | `injection-guard.py`（開発時に取り込んだ内容の注入の文を警告） | 利用者の API キーを他の送り先へ送っていないか。LLM の出力を HTML として描画していないか（`skills/nfr-standards/references/llm-agentic-top10.md`） |

## 手で確かめる順（目安 15 分）

1. 入力 → DOM の経路（A03）: `innerHTML`・`insertAdjacentHTML`・`outerHTML` を検索して、入る値の出所をたどる
2. 保存する値（A02）: localStorage・IndexedDB に書くキーの一覧を作り、秘密と個人情報に印を付ける
3. 読み込むもの（A06・A08）: `<script src>`・`<link href>`・`import` の送り先を一覧にする
4. 配布前（A05・A09）: CSP の有無、console 出力、エクスポートの中身

## 報告の例

| ID | 項目 | 重大度 | file:line | 根拠 | 直し方の案 |
|---|---|---|---|---|---|
| SA-1 | A03 / V5.3.3 | High | index.html:412 | 検索語をそのまま innerHTML に入れている | textContent にする。HTML が要るなら許可リストで組む |

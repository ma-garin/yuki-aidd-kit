---
name: security-audit
description: キットで作るアプリ（単一HTML・PWA／Streamlit／Python Web／Node Web）のセキュリティ監査を、走査器の結果とスタック別の OWASP 観点表で行うスキル。「セキュリティ監査」「脆弱性」「OWASP」「リリース前のセキュリティ確認」と明示に依頼された時と /security-audit で使う。範囲を決め、security-scan.sh を流し、未検査を一覧にし、該当スタックの references だけを読んで手動の観点を足し、file:line の根拠付きで security-report.md に追記する。使わない場面は、通常のコードレビュー（qa-review-standards）と設計・NFR の相談（nfr-standards）。ecc-daily-router からは自動で振らない。
---

# セキュリティ監査（security-audit）

走査器で機械的に取れるもの（依存の既知脆弱性・危険なコードの形・秘密の混入）は走査器に任せ、取れないもの
（認可・セッション・入力の流れ・LLM の出力の扱い）はスタック別の観点表で人が見る。
**指摘は file:line の根拠付き。根拠を示せない指摘は出さない**（`qa-review-standards` の evidence-only）。

## 手順

### 1. 範囲を決める（最初に保守者へ示す）

| 範囲 | 対象 | 使う時 |
|---|---|---|
| quick | 今回変えたファイルと、依存定義（requirements・package.json）の変更 | 小さな修正の確認 |
| diff | ブランチの差分（main との差） | PR の前 |
| full | リポジトリ全体 | マイルストーン・リリースの前 |

範囲の外は「見ていない」と報告に書く（見ていない所を合格に数えない）。

### 2. 機械の走査を流す

- `./scripts/security-scan.sh <対象ディレクトリ>`（キット内では `02_共通/ツール/security-scan.sh`）
- exit 0 = 指摘なし、1 = 中以上の指摘あり、2 = 判定不能（走査器が無い・解析失敗）。**2 を「指摘なし」と言わない**
- 許容済みの既知の指摘がある場合だけ `--baseline <ファイル>` を付ける。規律は `done-gate`（件数は減る方向だけ・理由と期限・期限切れは NG）
- 全件は `security-report.md`。会話には出さない

### 3. 未検査を先に一覧にする

- `security-report.md` の「未検査」節（未導入・対象なし・解析失敗）をそのまま会話に出す
- 未検査の分野は手順 4 の観点表で手で見るか、「未確認」として報告に残す
- 走査器の導入（pip install 等）はしない。導入は利用者が決める

### 4. スタックの観点を足す（必要な references だけを読む）

| スタック | 見分け方 | 読むもの |
|---|---|---|
| 単一 HTML・PWA | HTML 1 枚で完結・Service Worker・localStorage | `references/single-html-pwa.md` |
| Streamlit | `streamlit` を import・`st.` の画面 | `references/streamlit.md` |
| Python Web | Flask・FastAPI・Django | `references/python-web.md` |
| Node Web | package.json に express・fastify・next 等 | `references/node-web.md` |
| LLM・エージェントを含む | LLM API の呼び出し・RAG・ツール呼び出し | `skills/nfr-standards/references/llm-agentic-top10.md` |

- 表は OWASP Top 10（2021）と ASVS 4.0.3 の章で引いている。**該当しそうな 3〜5 行だけ**を選んで見る（全部は読まない）
- 「キットの対策」列は、その対策がこのプロジェクトで本当に効いているか（hook の配線・検査を実際に流したか）を確かめる
- 「未対応」列は手で読む。読んだ場所を file:line で残す

### 5. 判定して記録する

指摘の形式（重大度順に並べる）:

| ID | 項目（OWASP・ASVS） | 重大度 | file:line | 根拠（何がどう危ないか） | 直し方の案 |
|---|---|---|---|---|---|

- 重大度は Critical / High / Medium / Low（`qa-review-standards` の定義）
- `security-report.md` の末尾に `## 手動監査（YYYY-MM-DD・範囲）` の節を足して書く。走査の表は書き換えない
- 会話には要旨だけを 10 行以内（重大度順の先頭・未検査の一覧・次の一手）

## 越えない線

- AI は直し方を提案するまで。指摘の抑制（ignore の注記・除外設定・基準線への追加）は保守者が決める
- 秘密値を会話・報告に貼らない（file:line と型の名前だけ）
- 実環境への攻撃・侵入の試験はしない。静的な読みと手元のテストまで
- 外部サービスへコードや報告を送らない

## 外部の security-review（ECC）との使い分け

- ECC の `security-review`: 日常の差分で、`ecc-daily-router` が DAILY に上げたときに使う
- 本スキル: **明示の依頼（/security-audit・「セキュリティ監査」）だけ**。走査器の結果と観点表で報告書を残す。自動では振らない

## 外部スキル・MCP・プラグインを取り込むとき

アプリの監査ではなく、導入物の検査は `python3 02_共通/ツール/skill-scan.py <パス>`（実行せずに読むだけ）。
DANGEROUS は入れない。CAUTION・UNKNOWN は中身を確かめてから入れる。導入済みの設定の点検は `00_導入/01_インストール/verify.sh` の「設定の監査」。

## 適用範囲と引き継ぎ

**使わない場面**: 通常のコードレビュー（`qa-review-standards`）、設計の相談・NFR を決める時（`nfr-standards`）、日常の差分の確認（ECC の security-review）。`ecc-daily-router` からは自動で振らない。
**次に渡す先**: 直す作業は `test-automation`（再発を捕まえるテストを先に書く）、完了の判定は `done-gate`、LLM・エージェントの観点は `nfr-standards` の点検表。

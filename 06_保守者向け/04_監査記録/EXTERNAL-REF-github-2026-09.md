# EXTERNAL-REF — GitHub 公開リポジトリの全件走査（2026-09-23）

キットをレベルアップできる、または参考になる GitHub 公開リポジトリを全件列挙し、判定した記録。全件の一覧は同じフォルダの EXTERNAL-REF-github-2026-09.csv（UTF-8 BOM 付き）。

## 件数（3 区分）

| 区分 | 件数 | 意味 |
|---|--:|---|
| 列挙 | 21,045 | 収集元から機械的に集め、重複を除いたリポ |
| 説明文判定 | 11,360 | リポ名と説明文で判定（LLM。250 件ずつ、共通の判定規則） |
| 精読 | 265 | README か clone で中身を読んで判定（前回の 8 領域調査） |
| 未判定 | 9,420 | Web 検索で増えた分。5 時間の利用上限に達するため判定を次回へ回した（うち弱点キーワード該当 4,753 件） |

## 判定の内訳

| 判定 | 精読 | 説明文判定 | 計 |
|---|--:|--:|--:|
| 有益 | 75 | 0 | 75 |
| 有益候補 | 0 | 931 | 931 |
| 要確認 | 0 | 300 | 300 |
| 参考 | 125 | 1,380 | 1,505 |
| 無益 | 65 | 8,749 | 8,814 |
| 未判定 | - | - | 9,420 |

判定の基準: 有益（精読）／有益候補（説明文）＝キットの資産に取り込める具体的な仕組みがある。参考＝考え方は使えるが直接の取り込み先は無い。無益＝寄与しない（理由コード付き）。要確認＝説明が乏しいが領域内の可能性がある。

## 取り込み先（有益・有益候補の資産タグ、上位）

| タグ | 件数 |
|---|--:|
| skills | 464 |
| hooks | 218 |
| security | 200 |
| agents | 131 |
| context | 128 |
| token | 123 |
| design | 91 |
| retro | 69 |
| codex | 55 |
| commands | 51 |
| docs-check | 35 |
| lifecycle | 31 |
| trace | 31 |
| install | 25 |
| adr | 21 |
| skill | 15 |
| test-metrics | 13 |
| test-docs | 13 |
| agent-eval | 7 |
| build_codex_skills.py | 6 |

## 無益・参考の理由コード

| コード | 件数 |
|---|--:|
| GENERIC | 2,906 |
| OOS-DOMAIN | 2,302 |
| OOS-SAAS | 2,120 |
| OOS-STACK | 1,748 |
| SAMPLE | 612 |
| THIN | 573 |
| DUP | 476 |
| PLATFORM | 409 |
| PAID | 395 |
| LIST | 298 |
| DEAD | 158 |
| SEC-RISK | 71 |

## 収集元

| 収集元 | 件数（重複込み） |
|---|--:|
| lists | 11,416 |
| search-context | 4,848 |
| search-qatest | 3,708 |
| search-harness | 2,366 |
| search-crossagent | 2,023 |
| search-specdriven | 1,095 |
| search-review | 597 |
| search-evalobs | 498 |
| search-uipwa | 325 |
| search-japanese | 306 |
| search-guard | 287 |
| prior-deep | 265 |
| prior-unverified | 92 |

## 方法

1. **リスト**: awesome リスト・MCP レジストリ 45 件（awesome-claude-code 系、スキル集、awesome-mcp-servers 3 種、modelcontextprotocol/servers、docker/mcp-registry、テスト自動化・LLMOps・LLM 評価・設計システム・PWA・Streamlit・a11y・コードレビュー・静的解析・アーキテクチャ・ADR 等）を clone し、GitHub URL を全件抽出（11,416 件）
2. **検索**: 10 領域の検索担当（英語・日本語）。WebSearch、raw.githubusercontent.com の README 群、GitHub topic ページ、npm・PyPI・crates.io の検索
3. **説明文判定**: リスト分 11,360 件を 250 件ずつ判定。共通の判定規則（キットの資産・制約・既知の弱点・理由コード）を固定して全担当に渡した
4. **取りこぼし見直し**: 11 バッチで独立の担当が落選行を見直し、59 件を有益候補・要確認に引き上げた（CSV の「取りこぼし見直し」列）。残り 35 バッチは利用上限のため未実施

## 欠けているもの（次回の作業）

- 未判定 9,420 件の判定（弱点キーワード該当 4,753 件を優先）
- 取りこぼし見直しの残り（キーワードで絞った落選行 777 件）
- 有益候補 931 件・要確認 300 件の精読
- Web 検索はセッション全体の上限（200 回）に達した。Zenn・Qiita・note・dev.to・Medium はプロキシで遮断され、日本語記事にだけ載るリポは取りこぼしている可能性が高い
- ★ 数・最終更新は GitHub API が 403 のため取得できず、精読分だけ clone のコミット日を記録した
- npm 検索由来の行には関係の薄いリポが混ざる（判定で無益に落ちる想定）

## CSV の列

リポジトリ / URL / 説明（200 字まで）/ 収集元 / 判定 / 理由コード / 取り込み先 / メモ（取り込み案・判定理由）/ 確認レベル（精読・説明文・未判定）/ 取りこぼし見直し / ★・最終更新（精読のみ）

---
name: skill-guide
description: "やりたいことから、キットのどのスキル・コマンドを使えばよいかを案内するルーター。人が呼び出す専用（「どのスキルを使えばいい？」「何から始めればいい？」「skill-guide」）。自動では発火しない。"
---
<!-- 生成物: 04_Codex/build_codex_skills.py が 03_ClaudeCode/・02_共通/rules/ から生成する。直接編集しない -->
# スキル案内（skill-guide）

覚えていなくてよい。やりたいことを言えば、使うものを 1〜2 個に絞って答える。

**案内する前に、推薦するスキル（コマンド）の SKILL.md（commands/*.md）を開いて確認する。** 下の表は目次であり、内容の保証ではない。

## 答え方

1. 利用者の目的を 1 文で言い換える
2. 下の表から該当を選び、**使うもの・理由・最初の一言（そのまま打てるコマンド）**を示す
3. 迷う場合は閉じた質問を 1 つだけ返す（選択肢＋推奨）。複数の質問を並べない

## 目的 → スキル・コマンド

### 作り始める

| やりたいこと | 使うもの |
|---|---|
| 何を作るか整理したい・要件を詰めたい | `/grill` → `/rfd` |
| 提案（RFD）を起票したい | `/rfd` |
| 仕様駆動（SDD）で進めたい | `/sdd-start`（`sdd-ecc-workflow`） |
| 工程（RFD〜保守運用）を順に進めたい | `/lifecycle`（`dev-lifecycle`） |
| 方針を固めたい（調べてから決める） | `/plan` |
| 実装に入りたい | `/implement` |
| 個人用 PWA を作る | `/new-pwa`（`personal-pwa`） |
| 単一 HTML のツールを作る | `single-html-tool` |
| Streamlit + RAG の業務アプリを作る | `streamlit-rag-app` |
| 画面の見た目をそろえたい | `design-system` |

### 確かめる・直す

| やりたいこと | 使うもの |
|---|---|
| テスト方針（L1〜L4）を決めたい | `test-strategy` |
| テストコードを書いて流したい | `test-automation` |
| 画面を通しで検査し、不具合を直したい | `/e2e-cycle`（`e2e-cycle`） |
| 画面の UI/UX を全状態でレビューしたい | `uiux_review` |
| 品質レビュー（ISO 25010・ISTQB） | `/qa-review`（`qa-review-standards`） |
| 当たり前品質の漏れを探したい | `atarimae-quality-audit` |
| 非機能要件を書きたい | `nfr-standards` |
| セキュリティを点検したい | `/security-audit`（`security-audit`） |
| トレーサビリティを確認したい | `/trace` |
| テストの進捗・品質を数字で見たい | `/test-metrics` |
| エージェントシステムを eval したい | `/eval`（`agent-eval`） |
| 「完了」と言ってよいか確認したい | `done-gate` |
| 工程の出口で承認前レビューをしたい | `/phase-review`（`phase-approval`） |
| 自分のプロジェクトが AI 開発しやすいか採点したい | `/agent-ready` |

### 調べる・相談する

| やりたいこと | 使うもの |
|---|---|
| 技術ドキュメント・OSS コードを検索したい | `/doc-search`（`code-doc-search`） |
| AI 関連の最新動向を調べたい（読み取り専用） | `ai-trend-research` |
| 大きな判断の前・詰まったとき・完了前に別モデルへ相談したい | `advisor` |
| 直前の説明が分からなかった | `/wait-what` |

### 回す・引き継ぐ・改善する

| やりたいこと | 使うもの |
|---|---|
| 別セッション・Codex に引き継ぎたい | `handoff` |
| トークンを節約したい・出力が長い | `/compact-work`（`context-compression`）、`/token-check` |
| appワークスペースを棚卸ししたい | `/app-scan` |
| 手元の ECC 資産から使うものを選びたい | `/ecc-daily`（`ecc-daily-router`） |
| 振り返って、次に活かす修正先を決めたい | `/retro`（`retro`） |

## 見つからないとき

表に無い依頼は、無理に当てはめず「該当するものは無い」と答え、近いものを 1 つだけ挙げる。表が実物とずれていたら（スキルの追加・削除）、保守者に伝える。

## 適用範囲と引き継ぎ

**使わない場面**: 目的がすでに明確で、使うスキルが決まっているとき。モデルが自動で呼ぶことはしない（人が呼んだときだけ動く）。
**次に渡す先**: 案内した先のスキル・コマンドへ。

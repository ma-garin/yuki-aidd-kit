# AIDD Kit — INDEX

AI 駆動開発を高速・高品質にするための統合キット。Claude Code / Codex / claude.ai / ECC 横断。
**このファイルが全資産の入口。まずここを読み、必要なファイルだけを開く**（参照コスト＝およその行数）。

## 2層の読み方

| 層 | 基準 | 読むタイミング |
|---|---|---|
| **DAILY** | どのプロジェクトでも進め方を制御する横断資産 | セッション開始時・作業の節目に該当スキルを読む |
| **LIBRARY** | 特定のプロジェクト種別・場面でだけ効く資産 | タグが今の作業に一致した時だけ開く |

## クイックスタート

```bash
cd <YOUR_WORKSPACE>/yuki-aidd-kit
./scripts/install.sh && ./scripts/verify.sh   # 導入と確認
./scripts/init-project.sh my-app pwa          # 新規プロジェクト（pwa | html | streamlit）
./scripts/audit-app-workspace.sh <APP_WORKSPACE>  # アプリ群の棚卸し
open docs/yuki-aidd-kit-manual.html           # HTML版の取り扱い説明書
```

## DAILY スキル（進め方の制御）

| スキル | 1行要約 | タグ | コスト |
|---|---|---|---|
| `context-compression` | 出力の3層要約・grep/glob優先・決定論的作業のスクリプト化でトークンを推論に温存 | #token #process | 56行 |
| `ecc-daily-router` | プロジェクトに合うECC資産をDAILY/LIBRARYに分類（真実源は ECC-ASSET-MAP） | #ecc #routing | 57行 |
| `sdd-ecc-workflow` | 仕様駆動開発の10ステップ。spec/plan/tasks生成と役割分離 | #sdd #process | 53行 |
| `qa-review-standards` | ISO 25010・ISTQB severity・Whittakerツアーをレビューに注入。evidence-only | #qa #review | 43行 |
| `test-automation` | Playwright/pytestで「動いた」をテスト実行判定に置き換える | #qa #test | 49行 |
| `done-gate` | 完了宣言前のDefinition of Doneチェック | #qa #process | 43行 |
| `retro` | AIDDの進め方の学びを lessons.md に蓄積しキットへ還流 | #process #improve | 38行 |

## LIBRARY スキル（種別・場面で選ぶ）

| スキル | 1行要約 | タグ | コスト |
|---|---|---|---|
| `design-system` | AIDDツール群のカラー・タイポ・レイアウトの具体値（CSS変数の真実源） | #ui #design | 183行 |
| `nfr-standards` | PWA/単一HTML/Streamlit別の非機能要件デフォルト値 | #nfr #spec | 89行 |
| `agent-eval` | LLM/RAG/エージェント出力の品質をデータセット＋スコアラーで回帰評価 | #ai #eval | 67行 |
| `code-doc-search` | 技術ドキュメント検索のクエリ最適化 | #search #docs | 55行 |
| `single-html-tool` | 単一HTMLツール（社内配布・PoC）の開発規約 | #html #tool | 36行 |
| `personal-pwa` | GitHub Pages PWA・localStorage・折りたたみ端末対応の開発規約 | #pwa #mobile | 30行 |
| `streamlit-rag-app` | Streamlit+RAG業務アプリ（特定プロジェクト前提）の開発規約 | #streamlit #rag | 30行 |

## スラッシュコマンド（呼んだ時だけコストが発生）

| コマンド | 1行要約 | タグ | コスト |
|---|---|---|---|
| `/compact-work` | context-compression 規約で作業（3層要約・スクリプト化） | #token | 13行 |
| `/ecc-daily` | プロジェクトに合うECC資産の分類を実行 | #ecc | 26行 |
| `/app-scan` | アプリワークスペースの軽量棚卸し | #ecc #scan | 20行 |
| `/sdd-start` | SDDのspec/plan/tasks/CLAUDE.mdを一気に生成 | #sdd | 28行 |
| `/new-pwa` | 新規個人PWAのspec〜スキャフォールド生成 | #pwa | 27行 |
| `/qa-review` | ISO/ISTQB準拠のレビュー実行 | #qa | 28行 |
| `/eval` | AIシステムのeval実行（スコアラー選定〜回帰判定） | #ai #eval | 20行 |
| `/doc-search` | 技術ドキュメント特化検索 | #search | 14行 |
| `/retro` | レトロ実行と lessons.md 追記 | #improve | 17行 |
| `/token-check` | トークン使用量の確認と最適化提案 | #token | 23行 |

## ECC 連携

ECC 資産のプロジェクト別 DAILY/LIBRARY 対応は **`docs/ECC-ASSET-MAP.md`（147行）が唯一の真実源**。ここには複製しない。

## docs/（キット自体の文書）

| ファイル | 1行要約 | コスト |
|---|---|---|
| `docs/Roadmap.md` | キット開発の作業台帳。**開発を継続するモデルはまずこれ** | 65行 |
| `docs/Vision.md` | キットの目的・到達点・Non-Goals | 45行 |
| `docs/PRD.md` | FR/NFR（Claude Code と他エージェント双方で動作、が最重要NFR） | 65行 |
| `docs/ECC-ASSET-MAP.md` | ECCプロジェクト別対応表（真実源） | 148行 |
| `docs/AUDIT-2026-07.md` | 2026-07 資産監査の記録と適用済み修正 | 120行 |
| `docs/OPERATING-MODE.md` | 日常の標準作業モード | 75行 |
| `docs/PROJECT-FIT-REPORT.md` | 実プロジェクト群への適合レポート | — |
| `docs/yuki-aidd-kit-manual.html` | 初心者向けHTML取説（読み物。デザイン適用除外ジャンル） | 923行 |

templates/: `design-system.md`（視覚的指示書）/ `CURRENT_STATE.md` / `ADR-template.md` / `lessons.md`

## 運用原則

- 全量導入より、対象プロジェクトに合う DAILY だけを読む。LIBRARY は削除せず必要時に検索・参照
- ファイルを読む前に grep/glob で絞る（`context-compression` 参照）
- UI変更はスクリーンショットかE2Eで確認する
- AI出力品質は `agent-eval`、コード動作は `test-automation`、完了判定は `done-gate` で分ける
- セッション終了時は `CURRENT_STATE.md` と `lessons.md` を更新する

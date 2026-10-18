# 作業から原本を選ぶ

一覧は原文の代用ではない。選んだスキルの本文と今回必要な参照資料を読む。
導入済みならプロジェクトの `.agents/skills/<名前>/SKILL.md`、グローバルの `~/.agents/skills/<名前>/SKILL.md` または `~/.codex/skills/<名前>/SKILL.md` を確認する。kit 内なら `04_Codex/skills/<名前>/SKILL.md` を使う。

| 作業 | 入口 |
|---|---|
| 工程分割・長期保守 | dev-lifecycle |
| 個人アプリ・PoC | sdd-ecc-workflow |
| UI実装 | design-system |
| UI実機検証 | uiux_review |
| 非機能要件 | nfr-standards |
| テスト方針 | test-strategy |
| テストコード | test-automation |
| E2E修整 | e2e-cycle |
| レビュー | qa-review-standards |
| 全面品質監査 | atarimae-quality-audit |
| セキュリティ監査 | security-audit |
| AI出力評価 | agent-eval |
| 工程出口 | phase-approval |
| 完了判定 | done-gate |
| 技術資料検索 | code-doc-search |
| ECC資産選択 | ecc-daily-router |
| 全件集計・圧縮 | context-compression |
| 単一HTML | single-html-tool |
| PWA | personal-pwa |
| Streamlit・RAG | streamlit-rag-app |
| 作業計測 | work-metering |
| 引き継ぎ | handoff |
| 振り返り | retro |
| HTML作業報告 | work-report-html |
| 開発しやすさ評価 | agent-ready |
| AI動向調査 | ai-trend-research |
| 別視点の助言 | advisor |
| スキル案内 | skill-guide |

コマンドは全件 `03_ClaudeCode/commands/` にある。Codex では `$cmd-<コマンド名>` として生成され、引数はユーザーが続けた文章として読む。
新規スキル・コマンドを追加したらこの表だけに依存せず、台帳と生成物を確認する。
`security-audit` は明示依頼時に選ぶ。通常開発を無断の全面監査へ広げない。

成果物を丸ごと作る依頼は、`03_ClaudeCode/agents/aidd-lead.md` の目的と分担を参考に、
仕様→設計→実装→検証→工程出口の責務を Codex の実在機能で実行する。
詳細設計・実装・検証・ゲートの原文は同ディレクトリの `spec-agent.md`、`build-agent.md`、`verify-agent.md`、`gate-agent.md`。
人間承認の要否は適用 AGENTS と `dev-lifecycle` を優先し、既存資料の「返事がなければ進む」で承認を捏造しない。

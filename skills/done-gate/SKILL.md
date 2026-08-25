---
name: done-gate
description: タスクや機能を「完了」と判定する前の最終チェックを行うスキル。「完成」「できた」「終わった」「リリースしていい？」「これで完了」という発言があった時、またはタスクをクローズしようとする時は必ずこのスキルを使い、完了基準を満たしているか検証すること。スクラムのDefinition of Doneに相当する。
---

# 完了ゲート（Definition of Done）

「動いた」と「完了」は別物。クローズ前に以下を機械的に確認する。満たさない項目があれば完了と判定しない。

## 全種別共通
- [ ] spec.md の対象FRの検証基準を全て満たす（evidence提示可能）
- [ ] qa-review-standardsの観点で自己レビュー済み（Critical/High残ゼロ）
- [ ] **テストがpassする**（test-automationスキル。「動作確認した」は人力でなくテスト実行で判定）
- [ ] 秘密情報がコードに混入していない（grep確認）
- [ ] CURRENT_STATE.md を更新した
- [ ] implement.md に作業記録を追記した
- [ ] コミット済み（Conventional Commits形式）
- [ ] `quality/feature_contracts.yml` があるプロジェクトでは `python3 scripts/quality_harness.py` が PASS（新機能は契約を追加済み）

## 変更タイプ別（`skills/test-strategy`。詳細は `templates/test/DEFINITION_OF_DONE.md`）
- [ ] **Type B（HTML/JS/CSS を触った）**: L3 E2E 全 PASS で `.ui-verified` が更新済み、ブラウザで実操作（1920×1080 と 1366×768）、コンソールエラーなし、`uiux_review` で全状態を確認。**pytest PASS だけで完了としない**
- [ ] Type A（バックエンド）: L1/L2 全 PASS + 構文チェック + code-reviewer で HIGH 以上ゼロ
- [ ] Type C（文書）: 内部リンク有効、関連文書を同時更新
- [ ] ゲートを実行しなかった項目（日常コミットは H-7 で未実行が既定）は「未実行」と明記した。マイルストーンならフルゲートを実行し `docs/quality/evidence/` に保存した

## 工程ライフサイクル（dev-lifecycle）を使っている場合の追加項目
- [ ] 対象工程の**出口基準**を満たす（`skills/dev-lifecycle/references/phase-gates.md`。未達は次工程で埋めず差し戻す）
- [ ] `./scripts/trace-check.sh docs/lifecycle` が NG=0（要件が設計・実装・テストへ紐づいている）
- [ ] 成果物に未確定の `TBD` が残っていない
- [ ] 人間の承認が必要な3点（RFD の決定 / 要件定義の確定 / UAT 合格）を取得済み

## AI/LLMを含む場合の追加項目
- [ ] **agent-evalのスコアがベースライン以上**（プロンプト/モデル/ロジックを変更した場合は必須）
- [ ] Faithfulness等の必須ゲートを満たす（RAGの場合）

## PWA追加項目
- [ ] 折りたたみ端末カバー画面（360px）で主要機能が動く
- [ ] localStorageのexport/import が動作する
- [ ] Service Workerのキャッシュバージョンを更新した
- [ ] オフラインで全機能が動く
- [ ] Lighthouse Performance 80点以上（可能なら）

## 単一HTMLツール追加項目
- [ ] ブラウザでダブルクリックして動作確認した
- [ ] CSS/JS外部分割していない（単一ファイル維持）
- [ ] APIキーがハードコードされていない
- [ ] エクスポート機能（Jira CSV / Markdown等）が動く

## Streamlitアプリ追加項目
- [ ] 対象モジュールのみ変更した（他モジュールに副作用なし）
- [ ] マルチテナント: テナント越境が起きないことを確認
- [ ] LLM呼び出しがラッパー経由に統一されている
- [ ] .env が .gitignore に入っている

## 出力
未達項目があれば「未完了。残りN項目」とリスト表示する。全達成時のみ「完了基準を満たしている」と判定する。安易に「完成」と言わない。

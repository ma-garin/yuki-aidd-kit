---
paths:
  - "**/*.{py,js,ts,tsx,jsx,html,css,vue,svelte}"
---
# Functional Integrity Rule（機能完全性）

実装・レビュー・UX 評価・戦略レビューのいずれも、**実際の実行経路を検証するまで「完了」と言わない。**

必須の検証経路: `UI → API → backend route → service/core → output → persistence → error handling → user-visible evidence`

完了の根拠として**扱わない**: UI がある／ボタンがある／**テストが通った**／ペルソナ・戦略をレビューした／使えそうに見える／コードがきれい

Critical / High リスクの機能で必ず確認する: happy path／failure path／timeout・cancellation／auth・login wall／robots・制限の扱い／partial result・recovery／ログまたは証跡／ユーザーに見えるエラー・状態表示

- ゲート（テスト・verify-ui 等）の実行はユーザーが明示的に要求した時だけ（`rules/speed-harness.md` H-7）。要求が無ければ未実行の項目をすべて `未実行` / `未検証` と明記して提出し、1つでも未検証があれば `未確認` と書いて完了として提示しない
- 実行経路の存在は人の注意力でなく機械で検証する: `quality/feature_contracts.yml`（機能ごとの UI/route/core・出力・永続化・failure_modes・required_tests）を `scripts/quality_harness.py` が検査する（`skills/test-strategy/references/feature-contracts.md`）
- 開発プロセス上の失敗には名前のある RCA 枠組み（5 Whys / Fishbone / FMEA / CAPA / DoD 更新）を使う。枠組み名を持たない場当たりの原因分析は禁止

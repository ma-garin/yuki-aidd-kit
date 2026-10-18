---
name: rules-functional-integrity
description: "Functional Integrity Rule（機能完全性）。Claude Code のrules（規約） `functional-integrity` の Codex 版"
---
<!-- 生成物: 04_Codex/build_codex_skills.py が 03_ClaudeCode/・02_共通/rules/ から生成する。直接編集しない -->
Claude Code のrules（規約） `functional-integrity` の Codex 版。対象ファイルの範囲（Claude Code の paths）: `**/*.{py,js,ts,tsx,jsx,html,css,vue,svelte}`。該当するファイルを扱うときに従う。Claude Code 専用の hook・コマンドは、Codex で対応機能を確認できた場合だけ適用する。

# Functional Integrity Rule（機能完全性）

実装・レビュー・UX 評価・戦略レビューのいずれも、**実際の実行経路を検証するまで「完了」と言わない。**

必須の検証経路: `UI → API → backend route → service/core → output → persistence → error handling → user-visible evidence`

完了の根拠として**扱わない**: UI がある／ボタンがある／**テストが通った**／ペルソナ・戦略をレビューした／使えそうに見える／コードがきれい

Critical / High リスクの機能で必ず確認する: happy path／failure path／timeout・cancellation／auth・login wall／robots・制限の扱い／partial result・recovery／ログまたは証跡／ユーザーに見えるエラー・状態表示

- **入口をすべて踏む**: 1 つの機能に入口が複数ある（画面・API・CLI・設定・ショートカット・文書）なら、直した入口と「該当なし」と判断した入口を一覧で報告する。試した 1 経路だけ直して他を漏らさない。**足したら戻す手段も作る**（追加に対する削除・取り消し・無効化。片道の操作はバグ）（参照: t3code AGENTS.md "Hit every surface"）
- ゲート（テスト・verify-ui 等）の実行はユーザーが明示的に要求した時だけ（`rules/speed-harness.md` H-7）。要求が無ければ未実行の項目をすべて `未実行` / `未検証` と明記して提出し、1つでも未検証があれば `未確認` と書いて完了として提示しない
- 実行経路の存在は人の注意力でなく機械で検証する: `quality/feature_contracts.yml`（機能ごとの UI/route/core・出力・永続化・failure_modes・required_tests）を `scripts/quality_harness.py` が検査する（`skills/test-strategy/references/feature-contracts.md`）
- 開発プロセス上の失敗には名前のある RCA 枠組み（5 Whys / Fishbone / FMEA / CAPA / DoD 更新）を使う。枠組み名を持たない場当たりの原因分析は禁止
- **実物で確かめる**: 代理指標（行数・カバレッジ・モックの緑・「型が通った」）を完了の根拠にしない。動かしたい実物を動かして出力を見る。確認手順は**再実行できる検証スクリプト**として渡す（口頭の手順だけで終えない）（参照: plugins/pstack principle-prove-it-works）
- **根拠の出所**（挙動が曖昧なまま実装・断定するとき）: 実測も一次資料も無い挙動を事実として書かない。推測で埋めて通さない（参照: AnyPS5 CONTRIBUTING / docs/dev/HW_ORACLE.md）

# Functional Integrity Rule（機能完全性）

実装・レビュー・UX 評価・ペルソナ評価・戦略レビューのいずれも、**実際の実行経路を検証するまで「完了」と言わない。**

必須の検証経路:

```text
UI → API → backend route → service/core → output → persistence → error handling → user-visible evidence
```

次は完了の根拠として**扱わない**:

- UI がある / ボタンがある
- テストが通った
- ペルソナ・戦略をレビューした
- 使えそうに見える / コードがきれい

Critical / High リスクの機能では、次を必ず確認する:

- happy path
- failure path
- timeout / cancellation
- auth / login wall
- robots / 制限の扱い
- partial result / recovery
- ログまたは証跡
- ユーザーに見えるエラー・状態表示

ゲート（テスト・verify-ui 等）の実行は**ユーザーが明示的に要求した時だけ**（`rules/speed-harness.md` H-7）。
要求がない時は、未実行の項目をすべて `未実行` / `未検証` と明記して提出する:

```bash
<プロジェクトのゲートコマンド>   # ユーザー要求時のみ
```

1 つでも未検証の項目があれば `未確認` と書き、完了として提示しない。

開発プロセス上の失敗が起きたときは、名前のある RCA 枠組みを使う（5 Whys / Fishbone / FMEA / CAPA / DoD 更新）。
枠組み名を持たない場当たりの原因分析は禁止する。

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
- **データは正しく入っている（が、利用者の入口から到達できない）**

## 到達性（Reachability）

**利用者の入口から到達できて初めて完了。**「見えないものは存在しない。」

- 成果物は、**依頼者が普段使う画面から順にたどって到達できるか**を実際に操作して確かめる。
  API を叩けば取れる・DB には入っている、は完了の根拠にならない
- **既存レコードへ機械的に相乗りさせない。**`.first()` や「とりあえず先頭に紐付ける」は、
  データとしては成立していても利用者の導線からは消える
- 機能を追加したら、**その入口（メニュー項目・リンク・ボタン）も同時に用意されているか**を数える。
  認証系なら「ログアウト導線」「プロフィール編集」まで含めて 1 セット

実損害: 428 件を正しく取り込んだリポジトリ連携を `.first()` で既存案件へ機械的に紐付け、
利用者の案件選択画面から到達不能にした。認証スキャフォールドでログアウト導線の欠落を 2 回指摘された。

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

実行経路の存在は人の注意力でなく機械で検証する: `quality/feature_contracts.yml`（機能ごとの UI/route/core・出力・永続化・failure_modes・required_tests）を `scripts/quality_harness.py` が検査する（`skills/test-strategy/references/feature-contracts.md`）。

開発プロセス上の失敗が起きたときは、名前のある RCA 枠組みを使う（5 Whys / Fishbone / FMEA / CAPA / DoD 更新）。
枠組み名を持たない場当たりの原因分析は禁止する。

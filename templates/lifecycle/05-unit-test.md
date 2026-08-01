# 単体テスト仕様・結果 — <プロジェクト名>

> 検証対象: `03-detailed-design.md` の `DD-xxx`（V字の対応）。
> **テストケースは実装コードでなく DD を入力にして作る**（実装の写しにすると欠陥を検出できない）。
> 実装・実行方法は `skills/test-automation`、技法の詳細は `skills/dev-lifecycle/references/test-levels.md`。

**日付**: YYYY-MM-DD ／ **実行環境**: ／ **フレームワーク**: pytest / vitest / その他

## テストケース

| ID | 対象 DD | 区分 | 観点 | 入力 | 期待結果 | テストコード | 結果 |
|---|---|---|---|---|---|---|---|
| UT-001 | DD-001 | 正常系 |  |  |  | `tests/test_x.py::test_a` | pass / fail / 未実施 |
| UT-002 | DD-001 | 異常系 | 入力不正 |  |  |  |  |
| UT-003 | DD-001 | 境界値 | 上限+1 |  |  |  |  |

- 区分は **正常系 / 異常系 / 境界値** の3つ。各 `DD` に3区分すべてを1件以上作る
- 技法: 同値分割・境界値分析・分岐網羅・デシジョンテーブル
- 外部依存（LLM API・ネットワーク・時刻・乱数）はモック化する

## 実行結果（evidence）

```text
<!-- 例: pytest tests/ -v の出力サマリ。pass/fail 件数まで貼る -->
```

- 実行コマンド: 
- 合計: pass ___ / fail ___ / skip ___

## 検出した欠陥

| DEF-ID | 対象 UT | 対象 DD | severity | 内容 | evidence | 対応 |
|---|---|---|---|---|---|---|
| DEF-0xx |  |  | Critical / High / Medium / Low |  |  | 修正済 / 未対応 |

## 出口確認

- [ ] 全 `DD-xxx` に1件以上の `UT-xxx` がある（`./scripts/trace-check.sh` NG=0）
- [ ] 正常系・異常系・境界値の3区分がそろっている
- [ ] Critical / High の欠陥が残ゼロ
- [ ] 実装に合わせて期待値を緩めていない

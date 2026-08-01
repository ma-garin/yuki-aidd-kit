---
name: 欠陥（DEF）
about: テスト工程で検出した不具合を ISTQB severity 付きで記録する
title: "[DEF-000] "
labels: defect
---

<!-- 規約: skills/qa-review-standards/SKILL.md（severity / evidence-only）
     evidence の無い指摘は起票しない -->

## 事象

<!-- 何が起きたか。1〜2行 -->

## 検出工程・対象 ID

- 検出工程: 単体テスト / 結合テスト / システムテスト / 受け入れテスト / 運用
- 対象テストケース: UT-xxx / IT-xxx / ST-xxx / UAT-xxx
- 対象要件・設計: REQ-F-xxx / REQ-N-xxx / DD-xxx

## severity（ISTQB）

- [ ] Critical — データ損失・セキュリティ侵害・主要機能停止
- [ ] High — 主要ユースケースの阻害、回避策が困難
- [ ] Medium — 回避策あり、限定的影響
- [ ] Low — 軽微なUI不整合・改善提案レベル

<!-- severity と priority を混同しない。priority はビジネス判断として別途決める -->

## 再現手順

1.
2.
3.

- 期待結果:
- 実結果:

## evidence

<!-- ログ・スクリーンショット・出力ファイルのパス。ここが空なら起票しない -->

## 環境

- 実行環境 / ブラウザ / 端末幅 / データ条件:

## 対応

- [ ] 修正する（対象工程へ差し戻す）
- [ ] 次リリースへ送る
- [ ] 受容する（`docs/lifecycle/09-operations.md` の既知の制約へ引き継ぐ）

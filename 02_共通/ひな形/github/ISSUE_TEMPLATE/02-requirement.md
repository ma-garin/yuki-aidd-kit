---
name: 要件（REQ）
about: 1つの機能要件／非機能要件を工程に載せる
title: "[REQ-F-000] "
labels: requirement
---

<!-- 規約: skills/dev-lifecycle/SKILL.md
     受入基準は UAT の手順にそのまま書き換えられる粒度で書く -->

## 要件

<!-- 1要件1文。「AかつB」は2つの Issue に分ける -->

## 種別・優先度

- 種別: 機能要件（REQ-F） / 非機能要件（REQ-N）
- 非機能の場合の品質特性（ISO/IEC 25010）: 性能効率性 / 使用性 / 信頼性 / セキュリティ / 保守性
- 優先度（MoSCoW）: Must / Should / Could / Won't

## 受入基準（観測可能な合格条件）

<!-- ×「使いやすい」 ○「3タップ以内で保存でき、リロード後もデータが残る」
     非機能は測定条件つきで書く（例: 3G相当(1.6Mbps)で初回操作可能まで3秒以内） -->

- [ ]
- [ ]

## 由来

- RFD: RFD-xxx

## 工程の進捗

- [ ] 基本設計（BD-xxx）
- [ ] 詳細設計（DD-xxx）
- [ ] 実装（T-xxx）
- [ ] 単体テスト（UT-xxx）
- [ ] 結合テスト（IT-xxx）
- [ ] システムテスト（ST-xxx｜REQ-N は必須）
- [ ] 受け入れテスト（UAT-xxx｜REQ-F は必須）
- [ ] `docs/lifecycle/traceability-matrix.md` を更新した

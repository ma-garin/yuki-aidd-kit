---
name: ecc-daily-router
description: 各プロジェクトに対して、ECCのskills/rules/agentsをDAILYとLIBRARYに分類して使うためのルーティングスキル。QA document generator、UX audit tool、React finance PWA、QA portal、QA repository research tool、PWA、Playwright、Python、React、Django、E2E、QAレビュー、ECC活用への言及があればこのスキルを使う。
---

# ECC Daily Router

ECC を全部読むのではなく、対象プロジェクトに合う資産だけを選ぶ。

## 基本方針

- DAILY: そのプロジェクトで毎回使う
- LIBRARY: 必要時だけ検索・参照する
- OFF: 現状の文脈では使わない

## 最初に見る証拠

1. `AGENTS.md` / `CLAUDE.md`
2. `README.md`
3. `package.json`, `pyproject.toml`, `requirements.txt`
4. `tests/`, `test/`, `playwright.config.*`
5. 変更対象ファイルの近傍

大きいファイル全文や `node_modules`, `venv`, `dist`, `output`, `test-results` は読まない。

## Project Presets

プロジェクト別のプリセット（ECC DAILY / LIBRARY / 併用 Kit skills）の真実源は、キットリポジトリの **`docs/ECC-ASSET-MAP.md`** の Project Mapping。このスキルには複製しない（二重管理で乖離した実績があるため）。

1. `docs/ECC-ASSET-MAP.md` の Project Mapping から対象プロジェクトの項を読む
2. 該当プロジェクトが無い場合は、「最初に見る証拠」で技術スタックを確認して MAP の DAILY / LIBRARY 表から選び、MAP への追記案を出す

## 出力フォーマット

```text
STACK
- 確認した manifest / docs / test surface

DAILY
- ECC資産: 根拠
- Kit資産: 根拠

LIBRARY
- 必要時だけ使う資産

NEXT
- 最小の次アクション
- 実行が重い場合の確認事項
```

## 注意

- `ecc plan` や install を実行する前に、まず分類だけを出す
- full install は原則避ける
- UI/E2E/ブラウザ実行は必要性を説明してから
- セキュリティ・秘密情報・localStorage・外部URL取得が絡む時は `security-review` を DAILY に昇格する


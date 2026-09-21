---
name: cmd-ecc-daily
description: "/ecc-daily — プロジェクトに合う ECC 資産を選ぶ"
---
<!-- 生成物: 04_Codex/build_codex_skills.py が 03_ClaudeCode/ から生成する。直接編集しない -->
コマンド `/ecc-daily` の Codex 版。引数は、呼び出し時にユーザーが続けて書いた文を `$ARGUMENTS` として読む。

# /ecc-daily — プロジェクトに合う ECC 資産を選ぶ

引数: `$ARGUMENTS`（対象プロジェクト名またはパス）

## 実行内容

`ecc-daily-router` スキルを使い、対象プロジェクトに合う ECC 資産を DAILY / LIBRARY に分類する。

1. 対象プロジェクトを特定する
2. `AGENTS.md`, `README.md`, manifest を最小限読む
3. 技術スタックを確認する
4. ECC の DAILY / LIBRARY を出す
5. Kit 側で併用するスキルも出す
6. install や E2E 実行が必要な場合は、実行前に確認事項を明記する

出力は以下の順にする。

```text
STACK
DAILY
LIBRARY
NEXT
```

引数がない場合は、現在の作業ディレクトリを対象にする。


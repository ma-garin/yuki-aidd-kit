# /app-scan — appワークスペースの軽量棚卸し

引数: `$ARGUMENTS`（省略時は現在の作業ディレクトリ）

## 実行内容

対象ワークスペースを重く読まずに棚卸しする。

1. `node_modules`, `.git`, `venv`, `.venv`, `dist`, `build`, `coverage`, `test-results`, `output` を除外する
2. ファイル拡張子、manifest、主要READMEだけ確認する
3. ECC DAILY候補を更新する
4. 新しく増えた技術スタックがあれば `01_利用者向け資料/ECC-ASSET-MAP.md` の更新案を出す

必要なら以下を使う。

```bash
<YOUR_WORKSPACE>/yuki-aidd-kit/00_導入/audit-app-workspace.sh <APP_WORKSPACE>
```

広範囲の全文読み込みはしない。

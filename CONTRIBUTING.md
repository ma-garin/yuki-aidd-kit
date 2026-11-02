# Contributing

## ブランチ

- `main` へ直接コミットしない。`feat/<名前>`・`fix/<名前>` のブランチを切り、PR で取り込む

## 提出前に通すもの

```bash
bash 06_保守者向け/03_回帰テスト/test-hooks.sh
bash 06_保守者向け/03_回帰テスト/check-docs.sh
```

- どちらも失敗0であること
- hook・ツールを足したら `test-hooks.sh` 等にケースを追加する

## CI

- `.github/workflows/kit-ci.yml` は手動起動のみ（`workflow_dispatch`。保守者決定 2026-09-17）
- PR で自動実行はされないため、上記をローカルで実行して結果を PR に貼る

## 設定ファイル

- `.claude/settings*.json` は PR で変更しない。必要な変更は差分案を PR 本文に書き、保守者が当てる

## CHANGELOG

- 変更は `CHANGELOG.md` の「## 未リリース」に1項目で追記する（版番号は保守者がリリース時に付ける）

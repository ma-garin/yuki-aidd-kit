# Operating Mode

AIDD Kit を使う時の標準作業モードです。

## 1. まずプロジェクト種別を決める

| 種別 | 代表例 | 常用スキル |
|---|---|---|
| QA Web crawler / report | QA document generator | `python-patterns`, `e2e-testing`, `qa-review-standards` |
| UX audit tool | UX_Auto_Reviewer | `browser-qa`, `accessibility`, `design-system` |
| React / Vite PWA | React finance PWA, investment hypothesis PWA | `react-patterns`, `vite-patterns`, `personal-pwa` |
| QA research / scoring | QA repository research tool | `deep-research`, `eval-harness`, `agent-eval` |
| Django portal | QA portal | `django-patterns`, `python-testing`, `security-review` |
| Single HTML tool | demo / PoC | `single-html-tool`, `qa-review-standards` |

## 2. 読む範囲を絞る

キット資産は `INDEX.md` の DAILY／LIBRARY 分類とタグで選ぶ。対象プロジェクト側で最初に読むのは原則この順。

1. `AGENTS.md` / `CLAUDE.md`
2. `README.md`
3. `package.json` / `pyproject.toml` / `requirements.txt`
4. 変更対象に近いファイル
5. テストファイル

`node_modules`, `venv`, `.pytest_cache`, `dist`, `test-results`, `output` は通常読まない。

## 3. ECC の使い方

DAILY:

- 毎回の判断・実装・検証で使う
- プロジェクトの主要技術に一致している
- トークンを使っても回収できる

LIBRARY:

- 必要時だけ参照する
- 現在のプロジェクトでは日常利用しない
- 削除ではなく検索対象に残す

## 4. 実装ループ

着手前に `目的:` `見積:` `検証:` の3行を出す（`rules/speed-harness.md` H-1）。所要時間 ≒ 往復回数 × 12秒。

```text
調査（grep/glob で絞る。依存先・呼び出し元は読む）
→ 方針提示
→ 合意
→ 編集を全ファイル分まとめて行う（1修正→1確認を回さない）
→ 軽量テスト（ゲートの実行はユーザー要求時のみ。未実行は「未実行」と明記）
→ UI なら再起動 1 回 → 全画面・全状態のスクショを連続で取り、まとめて読む（上限 2 周。`uiux_review`）
→ done-gate
→ CURRENT_STATE / lessons 更新
```

UI変更では、ブラウザまたはスクリーンショット確認を省略しない。「作った」を「効いている」と報告しない。

## 5. 完了判定

「動いた」では完了にしない。実行経路（UI→API→backend→出力→永続化→エラー処理→ユーザーに見える証跡）を確認するまで「完了」と言わない（`rules/functional-integrity.md`）。

- ロジック変更: unit / pytest / vitest
- UI変更: smoke / Playwright / screenshot
- AI出力変更: eval / golden dataset
- セキュリティ境界: security-review
- 仕様変更: docs / CURRENT_STATE 更新

## 6. クレジット節約

- 大きなファイルを全文取得しない
- まず `rg --files` と短い `rg`
- 2分を超えそうなら方針確認。見積を出したら `date` で実測し、見込み・実績・差異を報告する（`rules/absolute-rules.md` A-2）
- 1分超の作業は `progress.py start/step/done` をコマンドに連結し、ステータスラインに経過を出す
- `npm ci`, Playwright, ブラウザ実行、外部配信確認は必要性を説明してから
- full ECC ではなく `ecc-daily-router` で選ぶ
- 長い調査・集計は `context-compression`（3層要約・スクリプト化）で出力を絞る


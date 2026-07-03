# AIDD Kit

AI 駆動開発を、QA・E2E・仕様駆動・個人PWA・ローカル業務ツールに最適化するための個人用キットです。

**全資産の入口は `INDEX.md`**（DAILY／LIBRARY の2層＋タグ＋参照コスト）。エージェントにも人間にも、まず INDEX.md から読むことを推奨します。キット自体の目的・要求・開発継続手順は `docs/Vision.md`・`docs/PRD.md`・`docs/Roadmap.md` にあります。

## Ver.5.0 での主な更新（2026-07）

- `context-compression` スキルと `/compact-work` コマンドを追加（3層要約・grep/glob優先・決定論的作業のスクリプト化）
- 全資産を監査し修正を適用（`docs/AUDIT-2026-07.md`）。特に **hooks が入力を受け取れず無言で機能停止していた不具合を修復**し、`scripts/test-hooks.sh` で回帰テスト化
- キット自体の自己文書化: `docs/Vision.md` / `docs/PRD.md` / `docs/Roadmap.md`（前提知識ゼロのモデルが開発を継続できる作業台帳）
- `templates/design-system.md`: コード無しで見た目を再現するための視覚的指示書（Webアプリ／HTMLスライド／管理画面）
- `INDEX.md` を2層＋タグ＋参照コストで再構成。ECC 対応表の真実源を `docs/ECC-ASSET-MAP.md` に一本化
- `verify.sh` のチェックリストをリポジトリ実体からの自動導出に変更（資産追加時の更新不要）

## 導入

```bash
cd <YOUR_WORKSPACE>/yuki-aidd-kit
./scripts/install.sh     # ~/.claude へ配置
./scripts/verify.sh      # 配置確認（リストは自動導出）
./scripts/test-hooks.sh  # hooks の回帰テスト（8ケース）
```

Codex 等の他エージェントで使う場合は `AGENTS.md.template` を各エージェントのグローバル設定にコピーします。claude.ai の Projects で使う場合は `claude-projects-setup.md` を参照。

## 取り扱い説明書

初心者向けの HTML 版ガイドを同梱しています。ブラウザで開くと、サイドメニュー付きでキットの使い方、ECC との関係、プロジェクト別の使い分けを確認できます。

```bash
open docs/yuki-aidd-kit-manual.html
```

## 推奨する使い方

普段の開発では、まずこの順で使います。

1. `INDEX.md` を読み、今の作業タグに合う DAILY／LIBRARY だけ開く
2. `ecc-daily-router` で対象プロジェクトに合う ECC 資産を選ぶ
3. 仕様や大きめの変更は `sdd-ecc-workflow` で spec / plan / tasks に分ける
4. 長い調査・集計は `context-compression`（または `/compact-work`）で3層要約＋スクリプト化する
5. 実装後は `test-automation` と ECC の `verification-loop` を使う
6. UI / UX / QA 観点は `qa-review-standards` と ECC の `browser-qa` / `accessibility` を併用する
7. 完了前に `done-gate` を通す
8. つまずきや改善は `retro` で `lessons.md` に蓄積する

## ECC との連携

ECC（外部キット）の資産は全部読まず、プロジェクトごとに DAILY／LIBRARY に絞って使います。**プロジェクト別の対応表の真実源は `docs/ECC-ASSET-MAP.md`**（ここには複製しません）。分類の実行は `ecc-daily-router` スキルまたは `/ecc-daily` コマンドで行います。

アプリ群の棚卸しを更新する場合:

```bash
./scripts/audit-app-workspace.sh <APP_WORKSPACE>
```

## キット構成

```text
yuki-aidd-kit/
├── README.md                 # この文書（入口の案内）
├── INDEX.md                  # 全資産の索引（DAILY/LIBRARY・タグ・参照コスト）
├── AGENTS.md.template        # 他エージェント用グローバル設定
├── CLAUDE.md.template        # Claude Code 用グローバル設定
├── claude-projects-setup.md  # claude.ai Projects のセットアップ
├── docs/
│   ├── Vision.md / PRD.md / Roadmap.md   # キット自体の目的・要求・作業台帳
│   ├── ECC-ASSET-MAP.md                  # ECC 対応表（真実源）
│   ├── AUDIT-2026-07.md                  # 資産監査の記録
│   ├── OPERATING-MODE.md                 # 標準作業モード
│   ├── PROJECT-FIT-REPORT.md             # 実プロジェクト適合レポート
│   └── yuki-aidd-kit-manual.html         # HTML 取説
├── skills/                   # 14スキル（各 SKILL.md、一部 references/ 付き）
├── claude-code/
│   ├── commands/             # 10スラッシュコマンド
│   └── hooks/                # 3 hooks + settings.json
├── scripts/
│   ├── install.sh / verify.sh / test-hooks.sh
│   ├── init-project.sh / audit-app-workspace.sh / pre-commit
├── templates/
│   ├── design-system.md      # 視覚的指示書
│   └── CURRENT_STATE.md / ADR-template.md / lessons.md
└── github-actions/           # 配布用サンプル（deploy / secret-scan）
```

## 今後の開発時の合言葉

- 「このプロジェクトに合うECCだけ選んで」 → `ecc-daily-router`
- 「仕様から進めたい」 → `sdd-ecc-workflow`
- 「トークンを節約して進めて」 → `/compact-work`（`context-compression`）
- 「UI/UXを見て」 → `qa-review-standards` + ECC `browser-qa`
- 「E2E/動作確認」 → `test-automation` + ECC `e2e-testing`
- 「完成判定」 → `done-gate` + ECC `verification-loop`
- 「キット自体を直したい」 → `docs/Roadmap.md` の作業ルールに従う

# AIDD Kit

AI 駆動開発を、QA・E2E・仕様駆動・個人PWA・ローカル業務ツールに最適化するための個人用キットです。

**全資産の入口は `INDEX.md`**（DAILY／LIBRARY の2層＋タグ＋参照コスト）。エージェントにも人間にも、まず INDEX.md から読むことを推奨します。キット自体の目的・要求・開発継続手順は `docs/Vision.md`・`docs/PRD.md`・`docs/Roadmap.md` にあります。

## Ver.6.1 での主な更新（2026-08-25）— 速度ハーネス・機能完全性・UI/UX 実機レビュー

2026-08 に実プロジェクト（WebSpec2Doc / UX_Auto_Reviewer / my_forward）で育った運用を、キットへ還流しました。

- **`rules/`（新設・常時読み込み）**: `absolute-rules.md`（A-1〜A-10）/ `speed-harness.md`（往復×12秒の見積・環境チートシート・バッチ検証・委譲の型・見積の既定値・進捗の逐次提示）/ `functional-integrity.md`（実行経路を検証するまで完了と言わない）
- **`skills/uiux_review`**: 画面を実際に開いて全状態を確認し、「作った」を「効いている」と報告しない手順（観点表 `references/viewpoints.md` 付き）
- **hooks 3本追加**: `block-gates.py`（pytest / make test / lint をユーザー要求時以外 deny）/ `progress.py` + `statusline.py`（進行中タスクの経過・見積・残りをステータスラインに表示）
- **`templates/settings.sandbox.json`**: sandbox・denyRead・network allowlist・permissions deny の雛形
- `CLAUDE.md.template` / `AGENTS.md.template` を「速度最優先」「必須プロセス」「完了条件」で改訂。「指定外ファイルは読まない」「セッション分割を提案」は廃止（AUDIT-2026-07 C-02 / X-4）
- `install.sh` / `export-project.sh` / `verify.sh` / `test-hooks.sh` が rules と `.py` hooks を扱うよう更新（hooks 回帰テスト 19 ケース）

## Ver.6.0 での主な更新（2026-08）— 開発工程ライフサイクル

RFD から保守運用までの10工程を AI に実行させる層を追加しました。既存の軽量 SDD（spec/plan/tasks）はそのまま残り、**工程分割が必要な案件だけ**がこの層を使います（使い分けの判断表は `skills/dev-lifecycle/SKILL.md` の冒頭）。

```text
RFD → 要件定義 → 基本設計 → 詳細設計 → 実装 → 単体テスト → 結合テスト → システムテスト → 受け入れテスト → 保守運用
      └── V字の対応: 要件↔受け入れ / 基本設計↔システム・結合 / 詳細設計↔単体 ──┘
```

- `skills/dev-lifecycle`: 10工程の成果物・ID 体系・工程ゲート（入口/出口基準）・役割・他スキルへの委譲を規定。詳細は references（`phase-gates.md` / `traceability.md` / `test-levels.md`）
- `templates/lifecycle/`: 工程成果物の雛形11本。`./scripts/init-lifecycle.sh <対象>` で配置（既存ファイルは上書きしない）
- **`scripts/trace-check.sh`**: 要件が設計・実装・テストへ紐づいているかを目視でなく機械検証する。重複定義／未定義参照／所有ファイル違反／追跡表未記載／カバー漏れ／孤立テストの6種別を検出し、NG>0 で exit 1（CI でそのまま落とせる）
- コマンド `/rfd`・`/lifecycle <工程名>`・`/trace` を追加
- GitHub 連携: Issue テンプレート（RFD・要件・欠陥）、関係 ID 欄付き PR テンプレート、PR で trace-check を回す `lifecycle-check.yml`
- 回帰テスト `scripts/test-trace-check.sh`（15ケース）。**配布する雛形が最初から NG=0 で始まること**もテスト対象

```bash
./scripts/init-lifecycle.sh <対象プロジェクト> --github   # 工程文書＋GitHub テンプレート一式
./scripts/trace-check.sh docs/lifecycle                   # 追跡の機械検証（NG=0 で合格）
```

## Ver.5.0 での主な更新（2026-07）

- `context-compression` スキルと `/compact-work` コマンドを追加（3層要約・grep/glob優先・決定論的作業のスクリプト化）
- 全資産を監査し修正を適用（`docs/AUDIT-2026-07.md`）。特に **hooks が入力を受け取れず無言で機能停止していた不具合を修復**し、`scripts/test-hooks.sh` で回帰テスト化
- キット自体の自己文書化: `docs/Vision.md` / `docs/PRD.md` / `docs/Roadmap.md`（前提知識ゼロのモデルが開発を継続できる作業台帳）
- `templates/design-system.md`: コード無しで見た目を再現するための視覚的指示書（Webアプリ／HTMLスライド／管理画面）
- `INDEX.md` を2層＋タグ＋参照コストで再構成。ECC 対応表の真実源を `docs/ECC-ASSET-MAP.md` に一本化
- `verify.sh` のチェックリストをリポジトリ実体からの自動導出に変更（資産追加時の更新不要）

## 導入（2つの方式。併用が前提）

**① グローバル導入** — 自分のPC1台で複数プロジェクトを横断する日常運用向け。

```bash
cd <YOUR_WORKSPACE>/yuki-aidd-kit
./scripts/install.sh     # ~/.claude へ配置
./scripts/verify.sh      # 配置確認（リストは自動導出）
./scripts/test-hooks.sh  # hooks の回帰テスト（11ケース）
```

**② プロジェクト配布** — Codex・リモート/エフェメラルな Claude Code 環境・teammate の clone 先など、`~/.claude` へのグローバル導入が効かない/望ましくない環境向け。対象プロジェクト直下に `.claude/` と `AGENTS.md`・`CLAUDE.md` を書き出し、そのプロジェクトの git にコミットして持ち運ぶ。

```bash
./scripts/export-project.sh <対象プロジェクトのパス>
cd <対象プロジェクトのパス> && git add .claude AGENTS.md CLAUDE.md && git commit -m "chore: add AIDD Kit"
```

Codex ローカル利用のみで済む場合は `AGENTS.md.template` を `~/.codex/AGENTS.md` にコピーする方法もあります。claude.ai の Projects で使う場合は `claude-projects-setup.md` を参照。

## 取り扱い説明書

初心者向けの HTML 版ガイドを同梱しています。ブラウザで開くと、サイドメニュー付きでキットの使い方、ECC との関係、プロジェクト別の使い分けを確認できます。

```bash
open docs/yuki-aidd-kit-manual.html
```

## 推奨する使い方

普段の開発では、まずこの順で使います。

1. `INDEX.md` を読み、今の作業タグに合う DAILY／LIBRARY だけ開く
2. `ecc-daily-router` で対象プロジェクトに合う ECC 資産を選ぶ
3. 進め方を決める: 工程分割が要る案件（納品・引き継ぎ・要件合意・保守運用）は `dev-lifecycle`、個人PWA/単一HTML/PoC は軽量な `sdd-ecc-workflow` で spec / plan / tasks に分ける
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
├── rules/                    # 常時読み込みの規律 3本（absolute-rules / speed-harness / functional-integrity）
├── skills/                   # 17スキル（各 SKILL.md、一部 references/ 付き）
│   ├── dev-lifecycle/        # 工程ライフサイクル（+ phase-gates / traceability / test-levels）
│   └── uiux_review/          # UI/UX 実機レビュー（+ references/viewpoints.md）
├── claude-code/
│   ├── commands/             # 15スラッシュコマンド
│   └── hooks/                # 7 hooks（sh 4 + py 3）+ settings.json（statusLine 含む）
├── scripts/
│   ├── install.sh / verify.sh / test-hooks.sh   # グローバル導入
│   ├── export-project.sh                        # プロジェクト配布
│   ├── init-lifecycle.sh / trace-check.sh / test-trace-check.sh  # 工程ライフサイクル
│   ├── init-project.sh / audit-app-workspace.sh / pre-commit
├── templates/
│   ├── design-system.md      # 視覚的指示書
│   ├── settings.sandbox.json # sandbox / denyRead / network allowlist / permissions の雛形
│   ├── lifecycle/            # 工程成果物の雛形11本（RFD〜保守運用＋追跡表）
│   ├── github/               # Issue（RFD/要件/欠陥）・PR テンプレート
│   └── CURRENT_STATE.md / ADR-template.md / lessons.md / implement-profile.md
└── github-actions/           # 配布用サンプル（deploy / secret-scan / lifecycle-check）
```

## 今後の開発時の合言葉

- 「このプロジェクトに合うECCだけ選んで」 → `ecc-daily-router`
- 「要件定義から順番に、工程を分けて進めたい」 → `dev-lifecycle`（`/rfd` → `/lifecycle <工程名>`）
- 「要件がテストまで漏れなく落ちているか確認して」 → `/trace`（`scripts/trace-check.sh`）
- 「仕様から進めたい」 → `sdd-ecc-workflow`
- 「トークンを節約して進めて」 → `/compact-work`（`context-compression`）
- 「UI/UXを見て」 → `qa-review-standards` + ECC `browser-qa`
- 「E2E/動作確認」 → `test-automation` + ECC `e2e-testing`
- 「完成判定」 → `done-gate` + ECC `verification-loop`
- 「キット自体を直したい」 → `docs/Roadmap.md` の作業ルールに従う

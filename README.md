# AIDD Kit

AI 駆動開発を、QA・E2E・仕様駆動・個人PWA・ローカル業務ツールに最適化するための個人用キットです。

**全資産の入口は `INDEX.md`**（DAILY／LIBRARY の2層＋タグ＋参照コスト）。エージェントにも人間にも、まず INDEX.md から読むことを推奨します。キット自体の目的・要求・開発継続手順は `docs/Vision.md`・`docs/PRD.md`・`docs/Roadmap.md` にあります。

## Ver.6.4 での主な更新（2026-09-09）— A-0 土台・実行と停止・実損害からの還流

143 件の作業メモリと各プロジェクトの `CLAUDE.md` / `AGENTS.md` を横断して、**キットに未反映だった実運用の知見**を取り込みました。追加した規律はすべて実際の損害の記録に紐づいています。

- **`rules/a0-foundations.md`（新設）**: A-1〜A-10 より先に効く土台。指示が最優先（指摘には修正結果だけ返し、反省・経緯を書かない）／「できませんでした」の前に別経路を試す（Bash・Write・Edit × 新規・既存編集の 2 軸）／調査の最初は `git fetch origin`、否定の結論は `git grep <語> origin/main` で確かめる／指示は字義通りに解釈し範囲を広げない／相手が今答えられない情報は仮置きして進める
- **`rules/execution-safety.md`（新設）**: バックグラウンド実行（`&`）と `sleep` ポーリングの禁止（常駐サーバの起動のみ例外）／1タスクの範囲と**マージまでの完遂**（プッシュ後に「マージしますか」と聞かない）／自分が起動した一時プロセス・タブの片付け（本体サーバは止めない）／スコープは合意・実装手順は即決
- **`rules/functional-integrity.md` に「到達性」を追加**: **利用者の入口から到達できて初めて完了**。DB に入っている・API では取れる、は根拠にならない。既存レコードへ `.first()` で機械的に相乗りさせない（実損害: 428 件を正しく取り込んだ連携が案件選択画面から到達不能になった）
- **`rules/absolute-rules.md` A-4 に grep の落とし穴を追加**: 網羅性の照合で `| head` を使わない。先に `grep -c` で件数を出す（実損害: 15 箇所あるものを「3 箇所のみ」と誤断定し、空の作業ブランチを 2 本切った）
- **`rules/speed-harness.md` H-4 に検証委譲の細則**: 検証は必ず別のサブエージェントへ委譲し、**指摘が無くなるまで往復する**（実損害: 1 往復で打ち切り、引数評価順のバグがテスト 516 件を通過した）
- **`skills/test-strategy` に characterization test**: 「挙動を変えない」変更は着手前に現在の入出力を固定するテストを書く。**行カバレッジでは意味の変化を検出できない**。規約違反が大量に出たら個別修正でなく適用範囲を実測で見直す
- **`skills/design-system` に着手ゲート**: UI は実装前にデザインの承認を取る（部分改修＝HTML 案 1 本／刷新＝思想の異なる 5 案 → 操作可能プロトタイプ → 契約書）。実装 → 見せる → 作り直しが最大の速度低下要因
- **`skills/uiux_review` に通しテストと共通導線**: 状態を 1 つずつ見るだけでなく、着地から完了まで通しで操作する。システム切替・ユーザーメニュー・ログアウトが全画面から到達できるかを契約書に明記する
- **`CLAUDE.md.template` / `AGENTS.md.template`**: 応答スタイルを PREP 法・区切り線（`─`）・相槌禁止まで具体化。両テンプレートに「本節は `rules/` の要約。矛盾したら `rules/` を正とする」を明記し、片方だけ更新されるドリフトを防止
- README の Ver.6.2 以前の履歴を `docs/CHANGELOG.md` へ分離（README を 183 行 → 125 行に圧縮）

## Ver.6.3 での主な更新（2026-08-25）— デザイン: トークン実物・画面の作り方・フレームワーク別適用

- **`templates/tokens.css`**: デザイントークンの実物（ライト＋ダーク、`prefers-color-scheme` と `data-theme` 両対応、reduced-motion、タップ最小 44px）。WebSpec2Doc の `on-primary` / `surface-3` / `border-strong` / severity `-border` / `motion-*`、UX_Auto_Reviewer の本文幅 68ch を統合
- **`design-system` に「画面の作り方」を追加**: 直値禁止のトークン運用（色 105 種・角丸 11 種・文字 21 段階を整理した実績から）、骨格（globalbar / sidebar / topbar / content）、**操作には必ず結果を返す**（成功＝消えるトースト／失敗＝消えない＋次の行動／処理中／0 件／危険操作の確認、`textContent` で入れる）、アイコン（同梱・CDN 禁止・慣用の形）、文言規約（ボタンは動作名、見出しに動詞を入れない、「（任意）」を付けない）
- **`skills/design-system/references/frameworks.md`**: 単一 HTML / React+Vite（Tailwind は CSS 変数参照で登録）/ Streamlit（`config.toml` + `ui/theme.py` 集約）/ Flask・Django 別の当て方と、ECC `frontend-patterns`・`frontend-design`・`ckm:design`・`uiux_review` との分担表
- `templates/design-system.md` の再現チェックリストに直値・フィードバック・文言・アイコンの項目を追加
- **`templates/components/`**: `feedback.js`（トースト／消えない失敗＋次の行動／処理中／空状態／確認ダイアログ。自己完結）、`icons.js`（Material Symbols 同梱）、`demo.html`（ライト／ダークの実機確認ページ。Playwright で確認済み）
- `github-actions/test-gates.yml` を Python / Node 両対応（ファイルの有無で自動判定）


## 過去バージョンの更新履歴

Ver.6.2 以前の更新内容は `docs/CHANGELOG.md` にあります。

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
│   ├── CHANGELOG.md                      # Ver.6.2 以前の更新履歴
│   ├── ECC-ASSET-MAP.md                  # ECC 対応表（真実源）
│   ├── AUDIT-2026-07.md                  # 資産監査の記録
│   ├── OPERATING-MODE.md                 # 標準作業モード
│   ├── PROJECT-FIT-REPORT.md             # 実プロジェクト適合レポート
│   └── yuki-aidd-kit-manual.html         # HTML 取説
├── rules/                    # 常時読み込みの規律 5本（a0-foundations / absolute-rules / execution-safety / speed-harness / functional-integrity）
├── skills/                   # 19スキル（各 SKILL.md、一部 references/ 付き）
│   ├── dev-lifecycle/        # 工程ライフサイクル（+ phase-gates / traceability / test-levels）
│   ├── test-strategy/        # テスト活動の設計（+ feature-contracts / ui-verified-gate）
│   ├── e2e-cycle/            # 段階停止型 E2E ワークフロー
│   └── uiux_review/          # UI/UX 実機レビュー（+ references/viewpoints.md）
├── claude-code/
│   ├── commands/             # 16スラッシュコマンド
│   └── hooks/                # 7 hooks（sh 4 + py 3）+ settings.json（statusLine 含む）
├── scripts/
│   ├── install.sh / verify.sh / test-hooks.sh   # グローバル導入
│   ├── export-project.sh                        # プロジェクト配布
│   ├── init-lifecycle.sh / trace-check.sh / test-trace-check.sh  # 工程ライフサイクル
│   ├── init-test-docs.sh / quality_harness.py / test-quality-harness.sh  # テスト活動
│   ├── ui-hash.py / pre-commit-ui-gate.sh          # UI 検証マーカー
│   ├── init-project.sh / audit-app-workspace.sh / pre-commit
├── templates/
│   ├── design-system.md      # 視覚的指示書
│   ├── tokens.css            # デザイントークンの実物（ライト＋ダーク）
│   ├── settings.sandbox.json # sandbox / denyRead / network allowlist / permissions の雛形
│   ├── lifecycle/            # 工程成果物の雛形11本（RFD〜保守運用＋追跡表）
│   ├── test/                 # テスト戦略・DoD・29119 文書・テストケース CSV・機能契約の雛形8本
│   ├── github/               # Issue（RFD/要件/欠陥）・PR テンプレート
│   └── CURRENT_STATE.md / ADR-template.md / lessons.md / implement-profile.md
└── github-actions/           # 配布用サンプル（deploy / secret-scan / lifecycle-check / test-gates）
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

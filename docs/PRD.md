# PRD — yuki-aidd-kit

このキット自体を1つのプロダクトとして定義する要求文書。形式はキット自身の spec テンプレート（`skills/sdd-ecc-workflow/references/templates.md`）に従う。上位文書: `docs/Vision.md`、実行計画: `docs/Roadmap.md`。

## 目的（1〜2文）

AI エージェントに開発規約・品質基準・作業手順を供給する個人用キットを維持・進化させる。導入は `scripts/install.sh`、健全性確認は `scripts/verify.sh` で完結すること。

## ユーザーと利用シーン

| ユーザー | シーン |
|---|---|
| 保守者（人間） | キットの導入・更新・レトロ反映。QA エンジニア。ISTQB/ISO 用語は説明不要 |
| Claude Code | `~/.claude/` 配下のスキル・コマンド・hooks として読み込み、日常開発で発火 |
| 他エージェント（Codex 等） | `AGENTS.md.template` とスキル本文を文書として読み込み、同じ規約で動作 |
| ゼロコンテキストのモデル | `INDEX.md` → `docs/Roadmap.md` を読んでキット自体の開発を継続 |

## スコープ / 対象外

- スコープ: `skills/`・`commands/`・`hooks/`・`scripts/`・`templates/`・`docs/`・`INDEX.md`・`*.template`
- 対象外: ECC 本体（外部参照のみ）、実プロジェクトのコード、CI/CD 基盤（`templates/github/workflows/` は配布用サンプル）

## 機能要求（FR）

- **FR-01 スキル供給**: `skills/<name>/SKILL.md`（frontmatter: name / description 必須）形式でスキルを提供する
  - 検証基準: 全スキルが frontmatter を持ち、`./scripts/verify.sh` の対象リストに含まれ OK になる
- **FR-02 コマンド供給**: `commands/<name>.md` 形式で、対応スキルを呼び出すスラッシュコマンドを提供する
  - 検証基準: 各コマンドが「引数」「実行内容」を持ち、参照先スキルが実在する
- **FR-03 hooks 供給**: 書き込み前チェック・HTML 保存後チェック・セッション終了時リマインド・実装モードの探索ブロック・ゲート実行の要求時限定（`block-gates.py`）・進捗表示（`progress.py` / `statusline.py`）の7 hook と、それらを配線した `settings.json` を提供する
  - 検証基準: stdin に Claude Code hooks 形式の JSON を渡すと期待出力を返す（`./scripts/test-hooks.sh` 19 ケース。`docs/AUDIT-2026-07.md` A-01 の再発防止）
- **FR-03a ルール供給**: `rules/<name>.md` 形式で規律を提供する。`paths:` frontmatter の無いもの（`absolute-rules` / `speed-harness` / `model-routing`）は毎セッション、`paths:` 付き（`functional-integrity`）は該当ファイルを触ったときだけ読み込まれる。根拠・原文は `docs/rules-rationale/`（自動ロードされない場所）に置く。`install.sh` は `~/.claude/rules/aidd-kit/` へ、`export-project.sh` は `.claude/rules/` へ配置する
  - 検証基準: `verify.sh` が rules の配置を OK/NG で報告する。同名ファイルが利用者の `~/.claude/rules` 配下に既にある場合は上書きせずスキップする
- **FR-04 導入・検証スクリプト**: `install.sh` が `~/.claude/` へ配置し、`verify.sh` が全資産の配置を OK/NG で報告し、NG>0 で exit 1 を返す
  - 検証基準: クリーン環境で install → verify が NG=0・exit 0 で完了する（`./scripts/test-install.sh` が HOME 差し替えで検証）
- **FR-04a プロジェクト配布**: `export-project.sh <target>` が対象プロジェクト直下に `.claude/`（skills・commands・hooks・rules・settings.json・INDEX.md 一式）と `AGENTS.md`・`CLAUDE.md` を生成し、install なしで Codex・エフェメラルな Claude Code 環境でも動作する形にする
  - 検証基準: 生成物を対象プロジェクトの git にコミットするだけで、そのプロジェクトを開いた別セッションでスキル・コマンド・hooks が発火する。既存ファイルがある場合は `.bak` に退避してから上書きする
- **FR-05 検索構造**: `INDEX.md` が DAILY／LIBRARY の2層で全資産への導線を提供する
  - 検証基準: 全スキル・コマンドが INDEX.md に1行要約＋参照コスト付きで掲載されている
- **FR-06 ECC ルーティング**: プロジェクトに応じた ECC 資産の絞り込みを提供する。真実源は `docs/ECC-ASSET-MAP.md` のみ（複製禁止）
  - 検証基準: プリセット情報が MAP 以外に重複して存在しない
- **FR-07 自己文書化**: キット自体の開発が `docs/Vision.md`・`docs/PRD.md`・`docs/Roadmap.md` で継続可能である
  - 検証基準: Roadmap の未完了項目に対象ファイル・完了条件・検証手順が明記されている
- **FR-08 開発工程ライフサイクル**: RFD →要件定義→基本設計→詳細設計→実装→単体/結合/システム/受け入れテスト→保守運用の10工程を、成果物雛形（`templates/lifecycle/`）・入口出口基準（`skills/dev-lifecycle/references/phase-gates.md`）・ID 体系の3点で提供する
  - 検証基準: `./scripts/init-lifecycle.sh <対象>` が11ファイルを配置し、`./scripts/trace-check.sh` が NG=0 を返す（`./scripts/test-trace-check.sh` で回帰テスト）
- **FR-09 テスト活動の設計と機械ゲート**: テストレベル L1〜L4・ゲート基準・ゲートの実行タイミング・変更タイプ別 DoD を `skills/test-strategy` で規定し、ISO/IEC/IEEE 29119-3 文書（計画・設計仕様・完了報告・インシデント）とシステムテストケース CSV・機能契約の雛形を `templates/test/` で提供する
  - 検証基準: `./scripts/init-test-docs.sh <対象>` が雛形とゲートスクリプトを配置し、配置直後に `python3 scripts/quality_harness.py` が PASS する（`./scripts/test-quality-harness.sh` で回帰テスト）
- **FR-09a 機能契約ハーネス**: 機能ごとの UI/route/core・出力・永続化・failure_modes・required_tests を契約として記述し、実行経路の無い implemented・高リスク機能の失敗系テスト欠落・契約未登録モジュール・未実装マーカーをスクリプトで検出する（NG>0 で exit 1）
- **FR-09b UI 検証マーカー**: E2E 合格時に git hash + UI hash + 時刻を `.ui-verified` に記録し、pre-commit で未検証・期限切れ・検証後変更の UI コミットを止める。刷新期間は `.rebuild-mode` で明示的に免除する
- **FR-10 デザイントークンの実物と画面の作り方**: 値の唯一の真実源を `templates/tokens.css`（ライト＋ダーク）とし、部品 `templates/ui/components.css`・骨格 `templates/ui/layout.css`・フレームワーク別の出荷物（`tailwind.config.js` / `streamlit-config.toml` / `streamlit_theme.py` / `templates/ui/README.md` の1枚表）を配布する。`skills/design-system` は直値禁止・骨格・操作フィードバック・アイコン・文言の**規律**だけを持つ（≦ 200 行）
  - 検証基準: `tokens.css` の変数名が SKILL.md と一致し、`templates/design-system.md` の再現チェックリストで直値・フィードバック・文言・アイコンが確認できる
- **FR-11 版の刻印**: `VERSION` を真実源とし、`install.sh` / `export-project.sh` が導入先に `KIT_VERSION`（版・commit・日付）を書く。配布先がどの版のキットから出たかを判別できる
  - 検証基準: `./scripts/test-install.sh` が KIT_VERSION の3フィールドと VERSION との一致を assert する
- **FR-12 キット自身の回帰テストと文書整合**: 入口スクリプト（`test-install.sh`）・git ゲート（`test-git-gates.sh`）・文書整合（`check-docs.sh`）を回帰テスト化し、`.github/workflows/kit-ci.yml` から**保守者が手動起動したときだけ**実行する（自動実行はしない。ゲートは要求時のみ、の規律と同じ）
  - 検証基準: `./scripts/check-docs.sh` が NG=0（INDEX 参照コスト・掲載漏れ・ケース数・参照切れ・frontmatter・spec/01 同期）。常時読込 rules ≦ 100 行と SKILL ≦ 200 行は移行作業中 WARN、完了後 NG
- **FR-13 デザイン検査**: `scripts/check-design.sh` が CSS/HTML/JS の直値（色・余白・角丸・文字サイズ）・未定義トークン・外部 CDN・`alert()`・`tokens.css` 未読込を機械判定する（NG>0 で exit 1）。キットの出荷物自身が NG=0 で通ることを回帰テストに含める。配布先では対象パスを引数で渡す
  - 検証基準: `templates/design-system.md` 再現チェックリストの「機械」項目が全て `check-design.sh` で判定される
- **FR-14 工程承認ゲート**: 各工程の出口に**人間の承認**を置き、その承認を**承認時の成果物の版に縛る**。承認後に成果物が変われば承認は自動失効する。`scripts/check-approval.sh` が記録の有無・必須欄・版の一致・未解消の差し戻し・未確認事項・承認者が人間か・工程順序を機械判定する
  - 検証基準: 終了コードが 0（合格）／1（未承認・失効・工程順序違反）／2（判定不能）の3値で、**判定不能を合格に数えない**。`.claude/phase-gate` があるプロジェクトでは `block-phase.py` が未承認工程の下流成果物への書き込みを deny する。配布雛形（`init-lifecycle.sh` 直後）が NG=0 で通ることを回帰テストに含める
  - 境界: 機械が判定するのは「承認記録の形式的な健全性と版の一致」まで。**その設計が本当に要件を満たすかは人間しか判定できない**。AI は承認しない（`/phase-review` は指摘の申し送りまで）
- **FR-15 トークン節約の機械化**: 節約策を散文でなく hook・設定・検査で強制する。出力の絞り込み（`filter-output.py`）・読む価値の無いファイルの deny と大ファイルの切り詰め（`pre-read-guard.py`）・会話の寿命の警告（`context-guard.py`）・圧縮指示（`pre-compact.py`）・`effortLevel` `autoCompactWindow` `BASH_MAX_OUTPUT_LENGTH` の既定
  - 検証基準: `scripts/token-audit.sh` が配線漏れを NG（exit 1）で検出する。絞ったときは必ず `systemMessage` で全量の取り方を伝える（黙って削らない）。逃がし口は `FULL_OUTPUT=1` と `offset`/`limit` の明示だけで、恒久バイパスは作らない。常時読み込みは rules ≦ 100 行・CLAUDE+AGENTS ≦ 200 行を `check-docs.sh` が検査する
- **FR-17 指示優先の強制**: 保守者の発言（作業の途中で届いたものを含む）に日本語で応答するまで hook が全ツールを止める（`instruction-guard.py`）。最後の応答の言語は `reply-language.py` が見る。バイパス無し
- **FR-16 テスト工程のメトリクス**: 工程文書 05〜08 のテスト表・欠陥表と `system_test_cases.csv` を真実源に、`scripts/test-metrics.sh` が消化率・合格率・欠陥密度・Critical/High 未解決・滞留・偏り・完了予測（根拠付き）を出す。集計値を文書に手書きしない
  - 検証基準: 結果欄が語彙外の行は分母に含め、1 件でもあれば `--gate` は 2（判定できない）。欠陥表が無ければ密度・未解決は「算出できない」（0 ではない）。基準は `TESTING_STRATEGY.md` §7 の表（しきい値＋出典。出典が空の行は読まない）。`--into` が完了報告書 §2 と基準評価を置き換え、GO/NO-GO は人が書く。配布雛形が status で exit 0 になることを回帰テストに含める
- **FR-08a トレーサビリティの機械検証**: 要件が設計・実装・テストへ紐づいているかを目視でなくスクリプトで判定する
  - 検証基準: 重複定義・未定義参照・所有ファイル違反・追跡表未記載・カバー漏れ・孤立テストの6種別を検出し、NG>0 で exit 1 する（CI から `templates/github/workflows/lifecycle-check.yml` で実行できる）

## 非機能要求（ISO/IEC 25010）

- **互換性（最重要）**: **Claude Code と他エージェント（Codex 等）の双方で動作すること。** 共通規約の本体は `AGENTS.md`（Codex が直接読む）一本とし、`CLAUDE.md` は `@AGENTS.md` の import ＋ Claude Code でしか効かないものだけを持つ（二重管理をしない）。スキル・コマンド本文は特定ツールの内部名に依存せず、固有機能に言及する場合は「汎用表現（Claude Code では X）」の併記形式を守る。加えて、**グローバル導入（`install.sh`）とプロジェクト配布（`export-project.sh`）のどちらでも同一の振る舞いになること**（Vision.md「配置の2層」参照）
- **使用性**: 新しいセッションが `AGENTS.md` の「読む範囲」表から 1 ファイル以内の参照で作業開始できる（INDEX.md は表に無いときの第2段）。**毎セッション自動読み込みの `rules/`（`paths` 無し）は合計 ≦ 100 行**（`check-docs.sh` が NG で止める）。**1スキル ≦ 200行、1コマンド ≦ 40行**（`check-docs.sh` が NG で止める）
- **性能効率性（トークン）**: 毎回読む層（DAILY）の合計を小さく保つ。詳細は references/・docs/ に逃がし、必要時のみ読む
- **保守性**: 同一情報の真実源は1箇所（デザイン値は design-system、ECC 対応は ECC-ASSET-MAP）。重複を作る変更は監査（AUDIT）で検出・却下する
- **信頼性**: verify.sh が資産の欠落を検出する。hooks は入力不正時に無害終了（exit 0）する
- **セキュリティ**: 秘密情報・実在の個人情報・内部ホスト名をキットに含めない。個人環境依存値はプレースホルダ（`<APP_WORKSPACE>` / `<YOUR_WORKSPACE>` / `<GITHUB_OWNER>`）で表現する

## 制約

- 実在しないファイル・ECC 資産への参照を新規に作らない
- ECC 資産の実在はこのリポジトリからは検証不能（外部キット）。参照追加時は ECC-ASSET-MAP 経由に限定する
- コミットは Conventional Commits。1コミット＝1論理変更。各変更は `./scripts/verify.sh` 通過後にコミットする
- 日本語で記述する（コード・コマンド例を除く）

## 検証方針

evidence-only。各 FR の検証基準に対し、実行結果（verify.sh 出力・hook の実出力等）を提示できる場合のみ「満たしている」と判定する。品質判定の詳細規約は `skills/qa-review-standards/SKILL.md`、完了判定は `skills/done-gate/SKILL.md` に従う。

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

- スコープ: `skills/`・`claude-code/`（commands, hooks）・`scripts/`・`templates/`・`docs/`・`INDEX.md`・`*.template`
- 対象外: ECC 本体（外部参照のみ）、実プロジェクトのコード、CI/CD 基盤（`github-actions/` は配布用サンプル）

## 機能要求（FR）

- **FR-01 スキル供給**: `skills/<name>/SKILL.md`（frontmatter: name / description 必須）形式でスキルを提供する
  - 検証基準: 全スキルが frontmatter を持ち、`./scripts/verify.sh` の対象リストに含まれ OK になる
- **FR-02 コマンド供給**: `claude-code/commands/<name>.md` 形式で、対応スキルを呼び出すスラッシュコマンドを提供する
  - 検証基準: 各コマンドが「引数」「実行内容」を持ち、参照先スキルが実在する
- **FR-03 hooks 供給**: 書き込み前チェック・HTML 保存後チェック・セッション終了時リマインドの3 hook を提供する
  - 検証基準: stdin に Claude Code hooks 形式の JSON（`tool_input.file_path`）を渡すと期待メッセージを出力する（`docs/AUDIT-2026-07.md` A-01 の再発防止）
- **FR-04 導入・検証スクリプト**: `install.sh` が `~/.claude/` へ配置し、`verify.sh` が全資産の配置を OK/NG で報告する
  - 検証基準: クリーン環境で install → verify が NG=0 で完了する
- **FR-05 検索構造**: `INDEX.md` が DAILY／LIBRARY の2層で全資産への導線を提供する
  - 検証基準: 全スキル・コマンドが INDEX.md に1行要約＋参照コスト付きで掲載されている
- **FR-06 ECC ルーティング**: プロジェクトに応じた ECC 資産の絞り込みを提供する。真実源は `docs/ECC-ASSET-MAP.md` のみ（複製禁止）
  - 検証基準: プリセット情報が MAP 以外に重複して存在しない
- **FR-07 自己文書化**: キット自体の開発が `docs/Vision.md`・`docs/PRD.md`・`docs/Roadmap.md` で継続可能である
  - 検証基準: Roadmap の未完了項目に対象ファイル・完了条件・検証手順が明記されている

## 非機能要求（ISO/IEC 25010）

- **互換性（最重要）**: **Claude Code と他エージェント（Codex 等）の双方で動作すること。** スキル・コマンド本文は特定ツールの内部名に依存せず、固有機能に言及する場合は「汎用表現（Claude Code では X）」の併記形式を守る
- **使用性**: 新しいセッションが INDEX.md から 2 ファイル以内の参照で作業開始できる。1スキル ≦ 200行、1コマンド ≦ 40行を目安とする
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

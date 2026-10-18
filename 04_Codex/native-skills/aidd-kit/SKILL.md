---
name: aidd-kit
description: yuki-aidd-kit を Codex で使って開発・改善する際に、工程、専門スキル、共通規約、検証ツールを選び、原本を参照して作業を進める。
---

# Codex で yuki-aidd-kit を使う

このスキルは kit の統合入口。専門スキルの基準や原文を短縮版で置き換えない。
全資産へのアクセスは保ち、今回の判断に必要な原文だけをコンテキストへ取り込む。

## 原本を特定する

kit 内では `INDEX.md` と `02_共通/` と `04_Codex/` がある階層をルートにする。
導入先では同梱済みの `.agents/skills/`、`.claude/rules/`、`.claude/templates/`、`scripts/` を使う。
保守資料や未配布資産が必要なら kit の checkout を特定する。存在しなければ未確認と記録する。
`scripts/kit_catalog.py --root <kit> inventory --output <台帳.json>` は Git 管理対象と未追跡の非 ignored ファイルを全件列挙し、非秘密ファイルを全文機械読込する。
秘密情報・外部リンク・読取エラーは状態を記録し、読込済みに数えない。`inventory --include-ignored` なら ignored も列挙する。依存・キャッシュは内容を開かず記録し、Git 内部は対象外と明示する。
機械読込・意味の精読・実行検証を分けて記録する。ハッシュ取得を精読や検証の根拠にしない。

## 進め方を決める

1. ユーザーの目的と終了条件、既存の変更、対象範囲を確かめる。小変更に新しい工程文書を強制しない。
2. [routing.md](references/routing.md) から該当するスキルを選び、その `SKILL.md` を読む。詳細はそのスキルの references へ進む。
3. 共通規約は実際に適用される AGENTS と rules を読む。`paths` が付く規約は今回の変更対象に照合する。
4. 大きい独立作業は依存と編集ファイルを分け、利用可能・許可された委譲機能で並列化する。共有ファイルと Git 操作は本線で直列に扱う。
5. 実装・検証・反映まで依頼範囲を進める。要件の人間承認と受け入れ判定を AI で代行しない。

## Codex に適用する

- Claude の Task、専用モデル、hook、slash command を機械的に実行しない。[codex-runtime.md](references/codex-runtime.md) で対応を確認する。
- 既存スキルとその references は原文のまま利用する。存在しない道具や CLI をあるものとして報告しない。
- コーディング時だけ `work-metering` で予実を記録する。文書・設定だけなら計測表示を出さない。
- テスト・lint の日常ゲートはユーザー要求時に実行する。必要な変更の検証は実施し、未実行のゲートは区別する。CI・定期実行は勝手に作成・起動しない。
- コミット前に Git hook の実配線を確認する。安全検査を `--no-verify` で迂回しない。
- 完了前に `done-gate` と該当する品質観点で証拠を確認する。UI 変更なら `uiux_review` の全状態と実行経路を実機で確認する。

## 全件参照とトークン節約

原文を削って節約しない。台帳→全文検索→該当原文の順で取り込む。
`kit_catalog.py --root <kit> search <語>` は総一致件数と表示件数を区別する。
`kit_catalog.py --root <kit> read <相対パス>` は全文、`--start` と `--end` は行範囲を読む。
全文を求められた対象は最後の行まで読む。範囲読込を全文精読済みと記録しない。
詳細ログはファイルに保存し、結果・根拠・未検証項目を会話に返す。
同じ内容を複数スキルへ転記しない。原本変更後は台帳のハッシュと生成器の `--check` で古い参照を確認する。

## kit 自体の保守

全ディレクトリの責務は [source-map.md](references/source-map.md) を参照する。
共通スキルの真実源は `03_ClaudeCode/skills/`、コマンドは `03_ClaudeCode/commands/`。
Codex 固有スキルは `04_Codex/native-skills/` を編集する。`04_Codex/skills/` を直接編集しない。
`python3 04_Codex/build_codex_skills.py` で生成し、`--check` で原本・生成物・manifest の一致を確認する。
導入は既存 install/export が生成スキルを配る。個人環境へ追加する場合は対象スキルだけを配置し、既存の同名スキルを無断上書きしない。

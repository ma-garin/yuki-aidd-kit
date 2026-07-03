# Roadmap — yuki-aidd-kit

このファイルは、前提知識ゼロのモデル（Opus 4.8 等）がキット開発を継続するための作業台帳。チェックボックスを上から順に消化する。

## 作業ルール（毎回ここから）

1. まず `INDEX.md` を読み、次に本ファイルの未完了項目（先頭の `[ ]`）だけを見る。他ファイルは各項目の「対象」に書かれたものだけ開く
2. 上位文書: 目的は `docs/Vision.md`、要求と非機能制約は `docs/PRD.md`。迷ったら PRD の非機能要求（特に「Claude Code と他エージェント双方で動作」）に反しないか確認する
3. 1項目完了ごとに: `./scripts/install.sh` → `./scripts/verify.sh` が NG=0 → 完了条件を確認 → チェックを付け本ファイルを更新 → Conventional Commits で個別コミット
4. 禁止: 実在しないファイル・ECC 資産への参照の新規作成／真実源の重複（デザイン値は `skills/design-system`、ECC 対応は `docs/ECC-ASSET-MAP.md`）／承認なしの大規模リファクタ
5. 設計判断に迷ったら選択肢を提示して保守者の確認を取る（勝手に決めない）

## M1: コンテキスト圧縮（完了 2026-07）

- [x] `skills/context-compression/SKILL.md` 新設（3層要約規約／grep・glob 優先／決定論的作業のスクリプト化）
- [x] `claude-code/commands/compact-work.md` 追加（スキル呼び出し）
- [x] `scripts/verify.sh` の確認リストに両者を追加

## M2: 資産監査と修正（完了 2026-07）

- [x] 全資産（skills 14 / commands 10 / hooks 4）の監査表を `docs/AUDIT-2026-07.md` に出力
- [x] 承認済み修正の適用（hooks の stdin JSON 化＝A-01、端末幅 360×820 統一＝A-02、ECC プリセットの MAP 一本化＝A-03、ほか A-05〜A-09。詳細は AUDIT の適用記録）

## M3: 自己文書化（完了 2026-07）

- [x] `docs/Vision.md` / `docs/PRD.md` / `docs/Roadmap.md`（本ファイル）を新設

## M4: デザインシステム指示書（完了 2026-07）

- [x] `templates/design-system.md` を新設する
  - 対象: `templates/design-system.md`（新規）。参照してよいもの: `skills/design-system/SKILL.md`（トークンの真実源）、`docs/yuki-aidd-kit-manual.html`（既存スタイルの実例）
  - 内容: 基準トークン（primary `#1976D2`、Noto Sans JP + JetBrains Mono、MD3 light）を前提に、①Web アプリ ②HTML スライド ③管理画面 の3パターンを、コード無しでも他モデルが再現できる「視覚的指示書」（配置・比率・余白・階層・状態の言葉による指定）で記述する
  - 制約: `skills/design-system/SKILL.md` の CSS 変数値と矛盾させない（値の再定義はせず参照する。AUDIT の D-02 を悪化させない）。`docs/yuki-aidd-kit-manual.html` の見た目とも矛盾しないこと
  - 完了条件: 3パターンそれぞれに「レイアウト構造」「タイポグラフィ階層」「色の役割」「余白・密度」「状態表現（hover/選択/エラー）」の指定があり、具体値は design-system スキルへの参照で解決できる
  - 検証: `./scripts/verify.sh` NG=0（このファイル自体は verify 対象外なので、目視で完了条件を確認して記録する）

## M5: 検索構造の再設計

- [ ] `INDEX.md` を DAILY／LIBRARY の2層＋タグで再構成する
  - 対象: `INDEX.md`。参照: 全 `skills/*/SKILL.md` の frontmatter と `claude-code/commands/*.md` の1行目、各ファイルの行数（`wc -l`）
  - 内容: 各スキル・コマンドに「1行要約」「タグ（例: #qa #pwa #token #eval）」「参照コスト（読むべき行数目安）」を付与。ECC 連携表は `docs/ECC-ASSET-MAP.md` への参照1行に置換する（AUDIT の A-04 解消）
  - 完了条件: 全14スキル・10コマンドが掲載され、DAILY/LIBRARY の判定基準が冒頭に明記されている
- [ ] `CLAUDE.md.template` に導線を追記する
  - 対象: `CLAUDE.md.template`。内容: 「まず `INDEX.md` を読み、必要ファイルのみ開く」動線をトークン規律セクションに追加
  - 完了条件: install 後の `~/.claude/CLAUDE.md` を読んだエージェントが、最初に INDEX.md へ誘導される記述になっている
- [ ] 両変更後に `./scripts/install.sh` → `./scripts/verify.sh` NG=0 → コミット

## M6: バックログ（優先度順・未着手）

- [ ] hooks の回帰テストをスクリプト化する
  - 対象: `scripts/test-hooks.sh`（新規）。stdin JSON を3 hook に流し、期待出力（秘密ファイル警告／CSS・JS 警告／HTML レポート）を assert する。M2 A-01 の再発防止を自動化する（現状は手動確認のみ）
  - 完了条件: `./scripts/test-hooks.sh` が exit 0 で PASS/FAIL を表示し、README か INDEX.md から辿れる
- [ ] `verify.sh` のリスト自動生成化を検討する
  - 課題: スキル追加のたびに verify.sh のハードコードリストを手で更新している。`skills/` 実体からリストを導出する案と、意図的な台帳として現状維持する案がある — **保守者に選択肢を提示して確認**
- [ ] retro 運用の実績を反映する
  - 対象: `templates/lessons.md` の運用実績を見て、`skills/retro/SKILL.md` の「キットへのフィードバック」手順を実測に合わせて更新する。lessons.md にエントリが溜まってから着手（前提条件）
- [ ] streamlit-rag-app スキルの前提明記
  - 対象: `skills/streamlit-rag-app/SKILL.md`。「VeriRAG 基盤」「16モジュール構成」が特定プロジェクト前提であることを冒頭に1行明記する（AUDIT 監査表の備考対応。Low）

## 完了の定義（全マイルストーン共通）

`skills/done-gate/SKILL.md` の全種別共通チェックに加え、本キット固有の条件: ①verify.sh NG=0 ②真実源の重複を新設していない ③本ファイルのチェック状態を更新済み。

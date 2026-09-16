# 10 — 作り込みバックログ

`docs/Roadmap.md` の作業ルールに合わせ、各項目に **対象 / 内容 / 完了条件 / 検証** を持たせる。
採用して着手が決まったら **Roadmap のマイルストーンへ昇格させ、ここからは消す**。

優先度は `spec/09-findings.md` の severity と根本原因の順序から決めた。
**F-07 → F-09 を先に潰さないと、F-01〜F-03 は手で直しても再発する。**

---

## 優先度1（先にやる。他の項目の前提になる）

### B-01 — キット自身の CI と文書整合チェック ★★

**対応 finding**: F-07（High）/ F-09（Medium）/ F-01・F-02・F-03（再発防止）

- **対象**:
  - `scripts/check-docs.sh`（新規）
  - `.github/workflows/kit-ci.yml`（新規。**キット自身用**。配布用サンプルの `github-actions/` とは別物であることをファイル冒頭に明記する）
  - 併せて `scripts/verify.sh`（B-02 と同時が望ましい）
- **内容**:
  - `check-docs.sh` が**リポジトリ実体から導出した値**と文書の記載を突合する。検査項目:
    1. `INDEX.md` の参照コスト（行数）が実測と一致するか
    2. `INDEX.md` に全スキル・全コマンド・全 rules・全 hooks が掲載されているか
    3. 回帰テストのケース数の記載（`README.md` / `INDEX.md` / `manual.html`）が実測と一致するか
    4. キット内相対パス参照の切れ（ECC 外部と対象プロジェクト側の生成パスは既知の除外リストで無視）
    5. SKILL.md の frontmatter `name` とディレクトリ名の一致
    6. PRD の「1スキル ≦ 200行 / 1コマンド ≦ 40行」超過の検出（**超過は WARN。現状 `design-system` があるため即 NG にしない**）
  - 出力は `context-compression` の3層（結論 NG 件数 → 種別ごとの件数 → 全件は `check-docs-report.md`）。既存2スクリプトと出力形式を揃える
  - `kit-ci.yml` は PR / push(main) / dispatch で `test-hooks.sh` `test-trace-check.sh` `test-quality-harness.sh` `check-docs.sh` を実行。**`GATES_REQUESTED=1` を付ける**（H-7 と `block-gates.py` の思想に合わせる）。レポートは artifact と `$GITHUB_STEP_SUMMARY` へ
- **完了条件**:
  - `check-docs.sh` が現状のリポジトリに対して F-01・F-02・F-03 を**検出できる**（先に失敗することを確認してから直す＝赤→緑）
  - 直したあと NG=0 で exit 0
  - `scripts/test-check-docs.sh`（回帰テスト）を作り、**正常ケースと各検査の NG ケースを両方**通す（既存2スクリプトの作法に合わせる）
  - `.github/workflows/kit-ci.yml` が PR で 4 ジョブすべて green
- **検証**: `bash scripts/check-docs.sh`（NG=0）／`bash scripts/test-check-docs.sh`（PASS 全件）／PR 上の Actions が green
- **見積**: 自分 8〜12 往復（≒25分）＋検証1周

### B-02 — `verify.sh` を終了コードで判定できるようにする

**対応 finding**: F-06（Low）

- **対象**: `scripts/verify.sh`
- **内容**: 末尾に `[ "$NG" -eq 0 ] && exit 0 || exit 1` を追加する。既存の出力は変えない
- **完了条件**: NG=0 で `echo $?` が 0、欠落を作った状態で 1。Roadmap の「完了の定義 ①verify.sh NG=0」が機械判定可能になる
- **検証**: `~/.claude` を汚さないため、`HOME` を一時ディレクトリに差し替えて `install.sh` → `verify.sh` を実行し 0、ファイルを1つ消して 1 を確認
- **見積**: 自分 2 往復（≒5分）

---

## 優先度2（B-01 の成果物で自動化してから直す）

### B-03 — 陳腐化した数値の一括是正

**対応 finding**: F-01 / F-02 / F-03

- **対象**: `README.md:82` / `INDEX.md:18, 45, 46, 48, 51, 59, 73, 112, 135, 137, 140, 142` / `docs/yuki-aidd-kit-manual.html:792-793`
- **内容**: `check-docs.sh` が出した差分どおりに修正。**`docs/Roadmap.md:52` は当時の事実の記録なので触らない**
- **完了条件**: `check-docs.sh` NG=0
- **検証**: 同上
- **見積**: 自分 2 往復（≒5分。B-01 完了後）

---

## 優先度3（構造の改善）

### B-04 — `design-system/SKILL.md` の分割

**対応 finding**: F-04（Medium）

- **対象**: `skills/design-system/SKILL.md`（465行）→ SKILL.md ＋ `references/` 2本
- **内容**（案）:
  | 移す先 | 内容 |
  |---|---|
  | `references/tokens.md` | カラーパレット / ダークテーマ / タイポ / スペーシング・形状 / フォント読み込み方針 |
  | `references/components.md` | レイアウトパターン / コンポーネント11種 / レスポンシブ |
  | `SKILL.md`（残す） | description・どれをいつ使うかの索引・**「画面の作り方」の規律**（直値禁止・骨格・操作フィードバック・アイコン・文言）・実物へのポインタ |
- **注意**: `templates/tokens.css` は「真実源 = SKILL.md」とヘッダに書いている。**分割後は参照先を `references/tokens.md` に更新する**。`templates/design-system.md` / `frameworks.md` / `single-html-tool` / `new-pwa` からの参照も追随させる
- **完了条件**: SKILL.md ≦ 200行／`tokens.css` の全変数名が新しい真実源と一致／`check-docs.sh` の参照切れ検査 NG=0／`INDEX.md` の参照コスト更新
- **検証**: `grep -o '\-\-[a-z0-9-]*' templates/tokens.css | sort -u` と新 references の変数定義を突合し差分ゼロ
- **見積**: 自分 6 往復（≒15分）＋検証1周
- **要確認**: 分割の粒度（2分割か3分割か）は保守者の好みが出るため、着手前に案を出して確認を取る（Roadmap 作業ルール⑤）

### B-05 — 自己改善ループを起動する

**対応 finding**: F-05（Medium）／Roadmap M6 の前提条件

- **対象**: `templates/lessons.md`（またはキット用の `docs/lessons.md` を新設するか要判断）／`rules/speed-harness.md` の実測記録欄／`skills/retro/SKILL.md`
- **内容**:
  1. **`templates/lessons.md` は「配布する雛形」なので実エントリを書く場所ではない**。キット自身の知見は `docs/lessons.md`（新設）に書く、という分離をまず決める
  2. 本セッション（全ファイル読解と `spec/` 新設）を最初のエントリにする。Keep / Problem / Try を実測ベースで
  3. `rules/speed-harness.md` の実測記録欄に、H-1 の見積と実績の差異を追記する
  4. エントリが3件以上溜まった時点で Roadmap M6「retro 運用の実績を反映する」に着手
- **完了条件**: `docs/lessons.md` にエントリ1件以上／`retro` の「キットへのフィードバック」手順が実測に合っているか確認できる状態
- **検証**: `/retro` を実行して、出力が `docs/lessons.md` の形式にそのまま追記できることを確認
- **見積**: 自分 3 往復（≒8分）
- **要確認**: `templates/lessons.md`（配布用）と `docs/lessons.md`（キット用）の分離をするか

### B-06 — 配布層の `/implement` 非対称を解消する

**対応 finding**: F-08（Low）／PRD 非機能「どちらの配置でも同一の振る舞い」

- **対象**: `scripts/export-project.sh:47-82`（settings.json のヒアドキュメント）／`CLAUDE.md.template`
- **選択肢**（**保守者の決定が必要**）:
  | 案 | 内容 | 利点 | 欠点 |
  |---|---|---|---|
  | A | 配線を含めて生成（既定 ON） | PRD の互換性 NFR を満たす。利用者が意識不要 | 配布先に `.claude/mode` が無ければ素通りするだけなので実害は小さいが、hook が1つ増える |
  | B | 配布先 `CLAUDE.md` に「配布層では要追記」を1行足す | 変更が最小 | 非対称は残る |
  | C | 現状維持で `spec/` にだけ記録 | 変更ゼロ | 利用者は気づけない |
- **推奨**: A（`block-explore.sh` はモード未設定時は無条件 exit 0 で、回帰テストでも確認済み。副作用が無い）
- **完了条件**: 選んだ案を適用し、`export-project.sh` の出力メッセージも整合させる
- **検証**: 一時ディレクトリへ export し、`.claude/settings.json` の配線と `.claude/mode` の有無で Read がブロック／許可されることを実測
- **見積**: 自分 3 往復（≒8分）

---

## 優先度4（着手条件が揃ってから）

### B-07 — `manual.html` の図解（Roadmap M13 の未完）

**対応 finding**: F-10

- **対象**: `docs/yuki-aidd-kit-manual.html`
- **内容**: テストレベル L1〜L4 と「テストが通った ≠ 完了」の図解。既存の `.flow-h` / `.flow-v` CSS が使える（外部依存を増やさない）
- **完了条件**: 単一 HTML のまま（外部 CSS/JS 依存なし）／狭幅（`max-width: 920px` 未満）でも崩れない／`uiux_review` の全状態確認ではなく読み物なので**ライト表示とモバイル幅の2状態で実機確認**
- **検証**: ブラウザで開いて目視＋Playwright でモバイル幅のスクショ
- **見積**: 自分 4 往復（≒10分）

### B-08 — `spec/` の自動同期（B-01 の発展）

- **対象**: `scripts/check-docs.sh`
- **内容**: `spec/01-inventory.md` の行数と実測の突合を検査項目に追加する。`spec/` が本体から乖離するのを機械で止める
- **完了条件**: `spec/01-inventory.md` の行数が1件でもズレたら NG を出す
- **検証**: 意図的に1件ズラして NG=1 を確認
- **見積**: 自分 2 往復（≒5分）
- **前提**: B-01 完了

---

## 保留・要判断（着手前に保守者の確認が必要なもの）

| # | 論点 | 選択肢 |
|---|---|---|
| Q-1 | B-04 の分割粒度 | 2分割（tokens / components）か 3分割か、そもそも分割せず PRD の目安を「LIBRARY 層は 500行まで」に緩めるか |
| Q-2 | B-05 の `lessons.md` 分離 | `docs/lessons.md` 新設 か `templates/lessons.md` に直書き か |
| Q-3 | B-06 の案 A/B/C | 推奨は A |
| Q-4 | `spec/` のコミット単位 | 本体変更と同一コミットに含める（推奨・乖離しない）か、`docs:` で分けるか |

**Roadmap 作業ルール⑤「設計判断に迷ったら選択肢を提示して保守者の確認を取る（勝手に決めない）」に従う。**

---

## 採用しなかった案（理由つきで残す。再提案を防ぐ）

| 案 | 却下理由 |
|---|---|
| `spec/` に設計値（トークン・ゲート基準）を写して一元化する | 真実源の重複を新設することになり、Roadmap 作業ルール④の禁止事項に該当。AUDIT D-01 で「二重管理は必ず乖離する」実績がある |
| INDEX の参照コストを手で直して終わりにする | F-09（検査の仕組みが無い）が根本原因なので必ず再発する |
| `github-actions/` の既存 yml をキット自身にも流用する | 配布用サンプルは対象プロジェクトの構成（`quality/feature_contracts.yml` 等）を前提にしており、キット自身には存在しない。別ファイルにする |

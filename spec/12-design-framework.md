# 12 — デザインシステム／デザインフレームワークの現状と作り込み計画

**保守者の要求（2026-09-17）**: 「デザインシステム・デザインフレームワークをちゃんと作り込んで入れておきたい」
**制約**: `spec/11-target-operating-model.md`（Pro ＋ Sonnet ＋ Codex 併用）

---

## 1. 現状の棚卸し（実測 2026-09-17）

### 出荷されている実物

| ファイル | 行 | 中身 |
|---|---|---|
| `templates/tokens.css` | 107 | **トークン定義54行 ＋ 基本適用5ルール**（body / code / tap-min / reduced-motion / color-scheme）。ライト＋ダーク両対応 |
| `templates/components/feedback.js` | 282 | トースト・失敗（消えない）・処理中・空状態・確認ダイアログ。CSS を自己注入。自己完結 |
| `templates/components/icons.js` | 152 | Material Symbols 48種を同梱。`data-icon` 自動置換。旧名エイリアス15件 |
| `templates/components/demo.html` | 113 | 部品の実機確認ページ。`ui/components.css` を読み込む形（DS-1 で置換） |
| `templates/components/demo-shell.html` | 71 | 骨格の実機確認ページ（DS-2 で追加） |
| `templates/ui/components.css` | 175 | **部品 CSS の実物**（DS-1。2026-09-17 出荷） |
| `templates/ui/layout.css` | 99 | **骨格 CSS の実物**（DS-2。2026-09-17 出荷） |

### 散文としてしか存在しないもの

`skills/design-system/SKILL.md`（465行・推定 8,187トークン）の中に:

- **CSS コードブロック17個 / セレクタ約47行**
- 該当するのは: 永続サイドバー shell / 旧2ペイン / カードグリッド / バッジ / スコアカード / 情報ツールチップ / 列フィルタ / ページネーション / トグル / セグメント / モーダル / 通知ポップオーバー / 空状態 / フォームエラー / レスポンシブ

`skills/design-system/references/frameworks.md`（47行）が記述しているが**何も出荷していないもの**:

- React + Vite の `tokens.css` 配置と Tailwind `theme.extend` の CSS 変数参照登録
- Streamlit の `.streamlit/config.toml` `[theme]` と `ui/theme.py` `ui/components.py`
- Flask / Django の `static/tokens.css` とパーシャル構成
- 検証手順（直値の残数を grep で数える）→ **スクリプト化されていない**

### 問題の構造

```text
今:  SKILL.md（465行の散文）→ モデルが毎回 CSS を書き起こす → ブレる・高い
     tokens.css（値だけ）   → 部品は毎回ゼロから
```

Opus ＋ Max なら成立する。**Sonnet ＋ Pro では二重に損**:
①465行を読ませるコスト ②書き起こしのたびに実装がブレる（`uiux_review` が繰り返し検出している「同じ役割のものが同じに見えない」の再生産）。

さらに `templates/design-system.md` の再現チェックリストは
「CSS に直値（`#xxxxxx` / `Npx`）が残っていない」を要求しているのに、**それを判定する手段が無い**。

---

## 2. 方針

> **散文を減らし、出荷物を増やす。モデルには「書かせる」のでなく「貼らせる／読み込ませる」。**

これは `spec/11` の D-3 の直接の帰結であり、デザインの一貫性とトークン削減が同じ方向を向いている。

| | 今 | 目標 |
|---|---|---|
| 値 | `tokens.css`（出荷済み） | 維持 |
| 部品の CSS | SKILL.md の散文 | **`templates/ui/components.css` として出荷** |
| 画面の骨格 | SKILL.md の散文 | **`templates/ui/layout.css` として出荷** |
| 振る舞い | `feedback.js` / `icons.js`（出荷済み） | 維持＋不足分を追加 |
| FW 別の当て方 | `frameworks.md` の散文 | **各 FW の設定ファイル実物を出荷** |
| 検証 | チェックリスト（人力） | **`scripts/check-design.sh` で機械判定** |
| SKILL.md の役割 | 値＋部品＋規律の全部（465行） | **「どれをいつ使うか」の索引＋規律に絞る（≦200行）** |

**真実源は動かさない。** 値の真実源は `skills/design-system`（またはその references）のままで、
`templates/ui/*.css` はその「実物」という関係を `tokens.css` と同じ書式のヘッダコメントで明示する。

---

## 3. 作るもの

### DS-1. `templates/ui/components.css`（新規）— **実装済み 2026-09-17**

SKILL.md の CSS コードブロック17個を、**トークン参照だけで書かれた1ファイル**に起こす。

対象部品（SKILL.md の記述をそのまま実体化）:

| 群 | セレクタ |
|---|---|
| バッジ | `.badge` / `.badge-{critical,high,medium,low,info,new}` |
| ボタン | `.btn` / `.btn--primary` / `.btn--ghost` / `.btn--danger` |
| カード | `.card` / `.card-grid` / `.score-card` |
| 表 | `table` / `th` / `td.num` / `.pagebar` / `.pager` / `.pagesize` |
| 入力 | `.input` / `.input.err` / `.field-err-text` / `.banner-err` |
| 情報 | `.info-ic` / `.info-ic .tooltip` / `.info-ic.edge-left`（画面端はみ出し対策を含む） |
| 選択 | `.toggle` / `.seg` |
| 重ね | `.modal-backdrop` / `.modal` / `.modal.sm` / `.modal-{head,body,foot}` / `.notif-pop` / `.notif-item.unread` |
| 列操作 | `.col-filter-btn` / `.col-pop` |

- **`feedback.js` が自己注入している CSS と重複させない**。トースト・空状態・確認ダイアログは `feedback.js` の責務のまま
- 直値を書かない（`tokens.css` の `var(--*)` のみ）。例外はコメントで理由を書く
- **完了条件**: `demo.html` が `components.css` を読み込む形に変わり、`check-design.sh` の直値検査が 0

### DS-2. `templates/ui/layout.css`（新規）— **実装済み 2026-09-17**（クラス名は `.shell` でなく `.app`。`demo-shell.html` で確認）

骨格（`spec/03-skills.md` と SKILL.md が言う globalbar / sidebar / topbar / content）を実体化。

- `.shell` / `.sidebar` / `.sidebar.collapsed`（72px・ラベル `display:none`）/ `.maincol` / `.app-globalbar` / `.app-topbar` / `.app-content`
- サイドバーは画面最上部から独立（ヘッダーをサイドバーの上に横断させない）
- 本文と別スクロール、`--text-measure` の適用
- 360px / 1366×768 のブレークポイント
- **完了条件**: 管理画面パターンの骨格が `layout.css` ＋ `components.css` だけで組めること（`demo.html` に shell の例を追加して確認）

### DS-3. フレームワーク別の出荷物 — **実装済み 2026-09-17**（`streamlit_theme.py` は `badge` `empty_state` に加え `kpi` `callout` も持つ）

`frameworks.md` が文章で説明しているものを、**コピーして置くだけのファイル**にする。

| 追加するもの | 内容 |
|---|---|
| `templates/ui/tailwind.config.js` | `theme.extend.{colors,spacing,borderRadius,boxShadow}` を `var(--color-*)` 参照で登録した実物。既定パレット（`blue-500` 等）を使わせない |
| `templates/ui/streamlit-config.toml` | `[theme]` に `primaryColor` 他をトークンと同じ値で。ライト／ダークのコメント付き |
| `templates/ui/streamlit_theme.py` | `st.markdown('<style>…</style>')` を1箇所に集約する雛形＋`badge()` / `empty_state()` |
| `templates/ui/README.md` | **どのファイルをどのフレームワークでどこに置くか**の1枚表（`frameworks.md` の散文を置換） |

- **完了条件**: `frameworks.md` が「値の説明」でなく「出荷物への導線＋分担表」に縮む

### DS-4. `scripts/check-design.sh`（新規）— **実装済み 2026-09-17**（`check_design.py` 236行 ＋ `test-check-design.sh` 36ケース。実装時の判定範囲は `spec/05-scripts.md`「デザイン検査」が正）

`templates/design-system.md` の再現チェックリストのうち**機械判定できるものを実行する**。

| 検査 | 内容 |
|---|---|
| 直値 | `#xxxxxx` / `Npx` / `rgb(` が `tokens.css` 以外の CSS/JS に残っていないか（許可コメント `/* token-exempt: 理由 */` のある行は除外） |
| 未定義トークン | `var(--x)` で参照されているのに `tokens.css` に定義が無いもの |
| 未使用トークン | 定義されているが誰も参照していないもの（WARN） |
| 外部 CDN | `fonts.googleapis.com` / アイコン CDN の読み込み（オフライン要件のあるプロジェクトでは NG） |
| `alert(` / `confirm(` | ブラウザ標準ダイアログの直接使用（`feedback.js` を使うべき） |
| tokens.css 読込 | `.html` が `tokens.css` を読み込んでいるか（`<link>` か `<style>` 内の定義）。タップ領域の `min-height` は `tokens.css` 側の適用ルールで担保 |

- 出力は3層（結論 NG 件数 → 種別ごと → 全件は `check-design-report.md`）。既存の `trace-check.sh` / `quality_harness.py` と同じ作法
- NG>0 で exit 1
- **回帰テスト `ci/test-check-design.sh`** を付ける。**出荷している `demo.html` と `components.css` 自身が NG=0 で通ること**を必ずテストに入れる（雛形が NG を出すと利用者が検査を無視する、という既存2スクリプトと同じ理由）

### DS-5. `skills/design-system/SKILL.md` の縮小（≦200行）— **実装済み 2026-09-17: 473 → 115 行**

実装時の決定（計画からの変更）: `references/tokens.md` に hex を**複製しない**。値の唯一の真実源は `templates/tokens.css`（`check-design.sh` が読む実ファイル）とし、tokens.md は役割と理由だけを持つ。SKILL.md と tokens.css の二重管理（乖離の温床）を廃止した。`templates/design-system.md` / `templates/ui/*` / `frameworks.md` / `templates/lifecycle/02-basic-design.md` のポインタも tokens.css に向け直した。7項目は grep で references に残っていることを確認済み。

`spec/09-findings.md` F-04（PRD の「1スキル ≦ 200行」違反）と同時に解決する。

| 移す先 | 内容 |
|---|---|
| `references/tokens.md` | 値の一覧と決めの理由（ダークの作り方・フォント方針） |
| `references/components.md` | 部品ごとの**使い分けと落とし穴**（CSS 本体は `components.css` へ行くので、ここは「いつどれを使うか」と実装時の注意） |
| `SKILL.md` に残す | description ／ どれをいつ使うかの索引 ／ **「画面の作り方」の規律**（直値禁止・骨格・操作には必ず結果を返す・アイコン・文言）／ 出荷物へのポインタ ／ 検証手順 |

**移設で失ってはいけない実務知**（すべて実際の不具合から来ている。references に必ず残す）:

- 情報ツールチップの `transform: translateX(-50%)` が画面端で切れる → `.edge-left`
- 常時表示のツールチップが下の行のクリックを妨げた → ホバー時のみ表示
- 破壊的操作の確認は対象名を**動的に**埋める（「〇〇を削除しますか」と一般化しない）
- 空状態は「フィルタ0件」と「新規ユーザー」で文言とボタンを変える
- フォームエラーはバナー＋フィールド直下の2段構え。警告色（High/橙）と混同しない
- ダーク背景に淡色を重ねると濁る → `rgba(色,.18〜.20)`
- `disabled` は値が送信されないので二重送信対策に使えない → `aria-busy` ＋「処理中…」

### DS-6. `templates/design-system.md` の更新 — **実装済み 2026-09-17**（再現チェックリストを表に変え、機械5項目（直値・未定義トークン・CDN・alert()・tokens.css 読込）と目視9項目に分けた）

再現チェックリストの各項目に、**それが機械判定されるかどうか**を付ける（`check-design.sh` で見る／目視のみ）。
人が見るべき項目と機械が見る項目を分ける。

---

## 4. Sonnet ／ Codex での使われ方（設計の受け入れ条件）

この作り込みが成功したかは、**移行後に次が成り立つか**で判定する。

| # | 受け入れ条件 |
|---|---|
| A-1 | 「管理画面を作って」に対し、Sonnet が `tokens.css` + `layout.css` + `components.css` を**読み込む指示を書くだけ**で骨格が出る（CSS を書き起こさない） |
| A-2 | Codex でも同じ3ファイルを置くだけで同じ見た目になる（`templates/ui/README.md` の1枚表で足りる） |
| A-3 | `check-design.sh` が直値の混入を検出して止める |
| A-4 | `design-system` スキルの発火時コストが現在の推定 8,187 トークンから**半分以下**になる |

A-4 は `spec/11` の U-2 と同じく **`/context` での実測**で確認する（推定のままにしない）。

実装状況（2026-09-17）: DS-1〜DS-6 すべて実装済み。A-1 / A-2 / A-3 は出荷物とテストで満たした（`demo-shell.html` が読み込み指示だけで骨格を出す／`templates/ui/README.md` の1枚表／`check-design.sh` が直値を NG にする）。A-4 は保守者の `/context` 実測待ち。

---

## 5. 範囲外（やらないこと）

| 項目 | 理由 |
|---|---|
| 新しいブランド・ロゴ・三層トークン設計 | `frameworks.md` の分担表どおり `ckm:design` 等の領分。既存 AIDD ツール群には使わない |
| CSS フレームワーク（Bootstrap 等）の採用 | 単一 HTML ツールの「外部依存なし」制約と衝突する |
| コンポーネントの JS フレームワーク化（Web Components 等） | 単一 HTML・React・Streamlit・Django を横断する必要があり、CSS ＋ 素の JS が最小公倍数 |
| `docs/yuki-aidd-kit-manual.html` へのデザイン適用 | `templates/design-system.md` が「読み物は適用除外」と明示的に宣言済み（意図的な別ジャンル） |

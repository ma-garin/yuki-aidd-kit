# 他社デザインシステムとの比較（Carbon・SmartHR UI・デジタル庁）

作成日 2026-11-15。目的は、現行フレームワークの値を 3 つの公開デザインシステムと並べ、取り入れる候補を出すこと。
現行値の出所は `tokens.md`・`principles.md`・`02_共通/ひな形/tokens.css`。

## 出典と取得状況

| 略称 | タイトル・URL | 取得日 |
|---|---|---|
| Carbon 表 | Data table style https://carbondesignsystem.com/components/data-table/style/ | 2026-11-15 |
| Carbon 書体 | Typography overview https://carbondesignsystem.com/elements/typography/overview/ | 2026-11-15 |
| Carbon 色 | Color overview https://carbondesignsystem.com/elements/color/overview/ | 2026-11-15 |
| Carbon 通知 | Notification pattern https://carbondesignsystem.com/patterns/notification-pattern/ | 2026-11-15 |
| Carbon フォーム | Forms pattern https://carbondesignsystem.com/patterns/forms-pattern/ | 2026-11-15 |
| SmartHR トークン | デザイントークン https://smarthr.design/products/design-tokens/ | 2026-11-15 |
| SmartHR 表 | Table https://smarthr.design/products/components/table/ | 2026-11-15 |
| DADS 書体 | タイポグラフィ https://design.digital.go.jp/dads/foundations/typography/ | 2026-11-15 |
| DADS 色 | カラー https://design.digital.go.jp/dads/foundations/color/ | 2026-11-15 |
| DADS 入力 | テキストフィールド（概要のみ） https://design.digital.go.jp/dads/components/input-text/ | 2026-11-15 |

- SmartHR のフォームの指針は URL が 404 で取得できず、未確認。
- SmartHR の余白・文字サイズ・角丸は別ページで、今回は取得していない（未確認）。
- DADS の入力部品は概要のみで、エラー文・高さの規定は未取得（未確認）。
- 取得は要約モデル経由。数値は一次ページの原文での再確認を推奨する。
- WebFetch は上限 10 回のところ 11 回実行した（超過 1 回）。以降は取得していない。

## 現行の要点（自社）

- 文字は 11 / 13 / 14 / 16 / 18 / 22 / 28px の 7 段。本文 14px、行間 1.7。
- 余白は 4px 倍数（4〜48px）。操作部品の最小は 32px。
- 色は役割名のトークン（primary・bg・surface・border・text・状態 5 色＋bg＋border）。
- 一覧は 1366×768 で 15 行以上。ページ全体スクロール禁止。
- 表の行の高さの数値は tokens.css に無い（行高トークン未定義）。

## 比較表

セルは短く切っている。補足は各表の下に書く。

### 1. 密度（行高・余白）

| 項目 | 自社 | Carbon | SmartHR / DADS |
|---|---|---|---|
| 表の行高 | 未定義 | 24/32/40/48/64px の 5 段 | 未確認 |
| 操作部品の最小 | 32px | 表の標準は 32〜40px | 未確認 |
| 余白の単位 | 4px 倍数 | 16px 単位が基本 | 未確認 |
| 列の間隔 | 未定義 | 16px 以上 | 未確認 |

- Carbon は行高を名前付きの 5 段で持ち、列見出しの行は表の行高に合わせる。
- 自社は 15 行以上を方針に持つが、行高の値を持たない。32px 行なら 768px 画面で約 15 行になる計算（上下の枠を除く概算）。

### 2. 書体と文字サイズ段階

| 項目 | 自社 | Carbon | DADS |
|---|---|---|---|
| 書体 | Noto Sans JP 先頭 | IBM Plex | Noto Sans JP |
| 本文サイズ | 14px | 14px（表） | UI は 16px 以上 |
| 最小サイズ | 11px | 12px | 14px 未満は原則不可 |
| 行間 | 1.4/1.7/2 | 未確認 | 本文 1.5 以上 |

- DADS の高密度テキスト（管理・業務系）は 14・16・17px で、行間 120〜130%。自社の表本文 13px は DADS では下限割れ。
- DADS の 1 行 UI（ボタン等）は行間 100%。
- 自社の行間は 3 段のみで、密な表向けの 1.2〜1.3 が無い。

### 3. 色トークンの階層

| 層 | 自社 | Carbon | SmartHR / DADS |
|---|---|---|---|
| primitive | 無し（hex 直書き） | パレット 12 階調 | SmartHR は 2 層と明記 |
| semantic | 役割名 | $layer・$border 等 | SmartHR は用途別 |
| 状態 | hover 等は直値 | 接尾辞で別トークン | DADS は意味色 2 段 |
| 部品専用 | 無し | 部品内のみ使用可 | 未確認 |

- 自社は primitive 層が無く、semantic が hex を直接持つ。ダーク再定義は上書きで成立するが、段階の追加（hover・active）が直値になりやすい。
- Carbon は面の重なり（layer）ごとに白とグレー 10 を交互にする。自社は surface・surface-2・surface-3 で近い。
- DADS の意味色は色相固定で、明度・彩度のみ調整可。自社の状態色の方針と同じ。

### 4. 表・データグリッドの作法

| 項目 | 自社 | Carbon | SmartHR |
|---|---|---|---|
| 見出し固定 | 未確認 | 有り（標準） | fixedHead 属性 |
| 列固定 | 未確認 | 未確認 | 左右固定の属性 |
| 空値 | 未確認 | 未確認 | ハイフン表示 |
| 数値右揃え | .num | 未確認 | align 属性 |

- 自社の「自社」列の未確認は、今回 components.md を読んでいないため。
- SmartHR は空の表の本体（EmptyTableBody）を部品化している。
- Carbon の見出しは 14px SemiBold、行は 14px Regular。表の上の見出しは 20px。
- 自社は表本文を `--text-sm`（13px）とする。Carbon・DADS はともに 14px 以上。

### 5. フォームとバリデーション文言

| 項目 | 自社 | Carbon | DADS |
|---|---|---|---|
| 検証の時機 | 未確認 | フォーカス離脱時 | 未確認 |
| 文言の型 | 未確認 | 事実→対処の順 | 未確認 |
| 必須の印 | 未確認 | 少数派側にだけ付ける | 「※必須」を使用 |
| ラベル位置 | 未確認 | 上置きが既定 | 未確認 |

- Carbon の文言例: 「Password must be at least 16 characters.」（何が起きたか＋直し方を具体的に）。
- Carbon は短いフォームだけ主ボタンを無効化し、長いフォームでは無効化しない。送信後は二重送信防止で無効化する。
- Carbon の間隔は専用ページで入力間 32px、ダイアログ・サイドパネルで 16〜24px、最後の入力とボタンの間は約 48px。
- 入力 5 個未満はダイアログ、5 個超はサイドパネルが目安。

### 6. 通知（toast・inline）

| 種類 | Carbon の使い方 | 消える条件 | 自社 |
|---|---|---|---|
| inline | 関連箇所の近く・2 行以内 | 解決か手動 | 未確認 |
| toast | 全体向けの短文・3 行以内 | 操作なしなら自動も可 | 未確認 |
| 操作つき | 操作は 1 つ・2 語以内 | 操作か手動 | 未確認 |

- 重大・緊急は時間で消さない（Carbon のアクセシビリティ項目）。
- トーストは右上、複数は新しい順に縦積み。
- SmartHR・DADS の通知は今回未取得（未確認）。

### 7. アクセシビリティ基準

| 項目 | 自社 | Carbon | DADS |
|---|---|---|---|
| 通常文字 | 未確認 | 4.5:1 以上 | 4.5:1 以上 |
| 大きい文字・図形 | 未確認 | 3:1 以上 | 3:1 以上（枠・アイコン） |
| フォーカス表示 | 未確認 | 3:1 以上 | 専用の色を定義 |
| 準拠規格の名指し | 無し | WCAG | 未確認 |

- DADS の色ページは WCAG のレベルを明記していない（要約上は）。比率の数値のみ確認できた。
- DADS は白・黒以外の背景では比率を再確認せよとしている。自社の状態色背景（淡色）に当てはまる。
- 自社の `--color-medium`（#FBC02D）は淡色背景に対して不足で、文字用に別トークンを持つ。これは DADS の方針と整合する。

## 取り入れ候補

1. **表の行高トークンを追加する（推奨）**
   - 変える値・ファイル: `tokens.css` に `--row-h-sm: 32px` / `--row-h-md: 40px` を追加。表の部品 CSS と `components.md` に反映。
   - 効果: 「15 行以上」の方針を値で担保でき、画面ごとの行高のばらつきが消える。
   - コスト: 小（トークン 2 本と表 CSS の置換。既存画面は検査で拾える）。
   - 取り消しやすさ: 高い（トークンを削除すれば元の直値に戻せる）。

2. **表本文を 14px に引き上げ、密な表の行間を足す**
   - 変える値・ファイル: `--text-sm` の用途から表本文を外し `--text-base` に。`--leading-dense: 1.3` を `tokens.css` に追加。
   - 効果: DADS の下限（14px）と Carbon の表（14px）に合い、判読性が上がる。
   - コスト: 中（表の行高と 15 行条件が再計算になり、案 1 と同時に決める必要がある）。
   - 取り消しやすさ: 高い（値の戻しのみ）。

3. **色に primitive 層を足し、状態を接尾辞で表す**
   - 変える値・ファイル: `tokens.css` に `--palette-*` を新設し、`--color-*` を参照に置換。hover・active・selected を別トークン化。
   - 効果: ダーク再定義と状態追加が参照の付け替えで済む。直値の混入を検査しやすい。
   - コスト: 大（全トークンの書き換えと、`check-design.sh` の直値検査の見直し）。
   - 取り消しやすさ: 中（参照を hex に戻せるが、利用側の追加分が増えると戻しにくい）。

4. **フォーム文言の型と通知の使い分けを `components.md` に明文化する**
   - 変える値・ファイル: `components.md`（またはフォームの節）に「事実→対処」「必須は少数派側に印」「重大は自動で消さない」「toast は 3 行以内」を追記。値の変更なし。
   - 効果: 画面を作る AI の文言・通知の判断がぶれなくなる。
   - コスト: 小（文書のみ）。
   - 取り消しやすさ: 高い（文書の差し戻しのみ）。

5. **コントラスト比の基準を検査に入れる**
   - 変える値・ファイル: `check_design.py` に文字 4.5:1・枠とアイコン 3:1 の判定を追加。`principles.md` に基準を 1 行。
   - 効果: 淡色背景上の状態色の不足を機械で拾える（Carbon・DADS 共通の基準）。
   - コスト: 中（色の解決処理が要る。ダークの対象外化も決める）。
   - 取り消しやすさ: 中（検査を無効化できるが、一度通った画面の再修正が出うる）。

## 引用してはいけない数値・保留

- SmartHR の余白・文字・角丸の数値、SmartHR・DADS の通知とフォームの文言基準は未確認。
- Carbon の文字サイズの token 対応（body-compact-01 が何 px か）は、取得ページに記載が無く未確認（表の行が 14px であることのみ確認済み）。
- 自社の「未確認」欄は components.md を読んでいないことによる。着手前に実物で埋める。

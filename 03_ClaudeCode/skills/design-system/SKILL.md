---
name: design-system
description: AIDDツール群に一貫したビジュアルデザインを適用するスキル。HTMLツール・PWA・Streamlitアプリのデザインを決める際、「デザインどうする」「色は」「レイアウトは」「Material Design」「UIを作る」「コンポーネントを実装する」「画面の骨格」「文言」「トースト」「空状態」「アイコン」「デザイントークン」「React / Tailwind / Streamlit でどう当てるか」という言及があれば必ずこのスキルを使うこと。値の実物は templates/tokens.css、部品は templates/ui/components.css、骨格は templates/ui/layout.css。値の決めの理由は references/tokens.md、部品の使い分けと落とし穴は references/components.md、フレームワーク別の適用と他スキルとの分担は references/frameworks.md。UX audit tool・QA Lens・業務支援エージェント・personal accounting PWA等の既存ツールと統一感を保つためにも必ず参照する。
---

# AIDD Design System（MD3 Light ベース）

過去ツール群（UX audit tool v3〜v5 / QA Lens / personal accounting PWA / Harness ToDo / UX_Auto_Reviewer / WebSpec2Doc）から抽出した統一デザイン言語。
**モデルに CSS を書き起こさせない。出荷物を読み込ませる／貼らせる。** 迷ったら実物の値をそのまま使う。

## 何をどこで読むか

| したいこと | 読む／使うもの |
|---|---|
| 色・余白・書体・角丸・影・動きの**値** | `02_共通/ひな形/tokens.css`（**値の唯一の真実源**。ライト＋ダーク。変えるときはここを先に直す） |
| 値の役割と決めの理由（ダークの作り方・フォント方針・段の設計） | `references/tokens.md` |
| ボタン・バッジ・カード・表・モーダル等の**部品** | `02_共通/ひな形/ui/components.css`（クラス名をそのまま使う） |
| 部品の使い分けと落とし穴（実不具合由来） | `references/components.md` |
| 管理画面の**骨格**（globalbar / sidebar / topbar / content） | `02_共通/ひな形/ui/layout.css`（実例 `02_共通/ひな形/components/demo-shell.html`） |
| トースト・消えない失敗・処理中・空状態・確認 | `02_共通/ひな形/components/feedback.js` |
| アイコン | `02_共通/ひな形/components/icons.js`（同梱。外部 CDN を読まない） |
| フレームワーク別の置き場所・読み込み順（React / Tailwind / Streamlit / Flask・Django） | `02_共通/ひな形/ui/README.md`（1枚表）。他スキルとの分担は `references/frameworks.md` |
| コードを見ずに見た目を再現する指示書 | `02_共通/ひな形/design-system.md` |
| 直値・未定義トークン・CDN・`alert()` の機械検査 | `00_導入/03_点検/check-design.sh <対象パス>` |

## トークン運用の規律（直値を書かない）

整理を始めた時点で、1 製品に色が 105 種類・角丸が 11 種類・文字サイズが 21 種類（9〜17px を 1px 刻み）あった。1px の差は「別の役割」とは読まれず、ただ揃っていないだけに見える。

| 種類 | 決め |
|---|---|
| 色 | **役割で持つ**（`--color-text-secondary` など）。強調色は 1 つに絞る。濃色の上の文字は `--color-on-primary`。状態色は ISTQB severity（critical / high / medium / low / info）と対応させ、重大度と結果の伝達にだけ使う |
| 余白 | 4px の倍数だけ（`--space-1`〜`--space-12`） |
| 角丸 | 4 段階（sm=4 / md=8 / lg=12 / xl=16 / full）。**内側は外側より小さく**（外側の角丸 − 内側の余白） |
| 文字サイズ | 7 段階（`--text-xs`〜`--text-2xl`）。段の間は 2px 以上あける |
| 動き | 0.12〜0.3 秒（`--motion-*`）。`prefers-reduced-motion` で止める |
| 本文幅 | `--text-measure`（68ch）。画面幅いっぱいにしない |
| 影 | 影で語らずボーダーで区切る。影は浮かせる要素（ポップオーバー・トースト）だけ |
| ダーク | **変数名は変えず値だけ上書き**（`prefers-color-scheme` と `data-theme` の両対応が必須）。部品側の CSS は変えない |
| フォント | **既定はシステムフォントスタック**。Google Fonts 等の CDN は常時オンラインと確定した社内ツールでの任意強化（理由は `references/tokens.md`） |

新規コードに直値が出たら、トークンに足すか既存トークンに寄せる。残す場合は同じ行に `/* token-exempt: 理由 */` を書く（`check-design.sh` が除外する。3px 以下のヘアラインと幅・高さは検査対象外）。

## 骨格（全ページ共通）

```text
┌─────────────────────────────┐
│ .app-globalbar（横いっぱい）   │  製品全体に効くもの（製品名・テナント・ユーザーメニュー）
├───────┬─────────────────────┤
│ .side │ .app-topbar         │  今どこにいるか（パンくず・ページタイトル・主操作 1 つ）
│ bar   ├─────────────────────┤
│       │ .app-content        │  中身。ここだけスクロール
└───────┴─────────────────────┘
```

- 実装は `02_共通/ひな形/ui/layout.css` の `.app`。**ヘッダーはサイドバーの上を横断させない**（サイドバーは最上部から独立して伸ばし、ブランドもサイドバー内トップ。Harness ToDo モックで検証済み）
- サイドバーは本文と別にスクロールし、折りたたみ（72px・ラベルは `.label-text` を `display:none`）を用意する。折りたたみボタンはブランド行と同居させない（幅が競合する）
- 軽量ツールでサイドバーが常に見えていなくてよい場合だけ `.layout-2pane`
- ページヘッダーは 1 行に収める。パンくず・タイトル・ステップ表示で**同じ語を繰り返さない**。パンくずの末尾は「今いる段階」
- 表側（利用者の作業）と裏側（設定）で地の色を変える（`.app.is-settings`）。同じ色だと今どちらにいるかが見た目から分からない
- 管理画面は最上段に KPI 列（`.kpi-row`）→ フィルタ行（`.filter-row`。適用中はチップで可視化し × で個別解除）→ テーブル
- 検証幅は 360×820 / 768 / 1366×768 / 1920×1080。360px ではサイドバーを off-canvas（`.open`）にし、表は `.table-wrap` で横スクロール

## 操作には必ず結果を返す

押しても何も変わらないと、利用者は完了したのか失敗したのか判断できず、待つべきかもう一度押すべきかも分からない。**「操作したら必ず何か返す」を製品全体の約束にする。** 共通モジュール 1 つ（`feedback.js`）に集約し、画面ごとに `alert()` や独自実装を作らない。

| 場面 | 出すもの | API |
|---|---|---|
| 成功 | トースト（3 秒ほどで流れて消える） | `Feedback.ok('保存しました')` |
| 失敗 | トースト（**消えない**）＋ 詳細 ＋ **次に取るべき行動** | `Feedback.error('保存できませんでした', { detail, action })` |
| 処理中 | ローディング表示（戻り値を呼ぶと消える） | `const done = Feedback.busy('読み込んでいます')` |
| 0 件 | 空状態（枠だけ残さない。次にできることを書く） | `Feedback.emptyState({ title, description, action })` |
| 危険な操作の前 | 確認（何が起きるかを明記。ボタンは動作名） | `await Feedback.confirm({ title, consequence, actionLabel, danger })` |

- 文字は `textContent` で入れる。サーバから返ったエラー文が混ざるため HTML として解釈させない。アイコンだけは自前 SVG なので `innerHTML` でよい
- トーストのホストは `role="status" aria-live="polite"`。トーストは押した要素の近くに出す（画面隅に固定すると押した結果と結び付かない）
- **「エラーが発生しました」だけでは利用者は止まったままになる。** 失敗は「何が・なぜ・次に何をするか」
- 二重送信対策は `disabled` でなく `aria-busy="true"` ＋「処理中…」（`disabled` は値が送信されない）

## アイコン

- 同梱する（`icons.js`: Material Symbols, Apache-2.0。Lucide 由来の旧名エイリアス付き）。**外部 CDN を読み込まない**（閉じたネットワークでアイコンだけ欠ける）
- 意味と形は世の中の慣用に合わせる（設定=歯車、履歴=時計、CLI=ターミナル、削除=ゴミ箱）。独自の絵を当てると利用者は毎回覚え直す
- 使い方は `<span data-icon="settings" data-icon-size="18"></span>` を読み込み後に置換。装飾なので `aria-hidden="true"`。知らない名前は要素ごと消える（壊れた四角を出さない）

## 文言

| 決めごと | 理由 |
|---|---|
| ボタンは動作名にする（「はい／いいえ」「次へ」を使わない） | 押すと何が起きるかがラベルだけで分かる |
| 見出しに動詞を入れない（「〜を決める」） | 何をする場所かは配置で分かる |
| 「（任意）」を付けない | 必須の印が無いことで分かる |
| 実装の説明を書かない（「button の作り」など） | 利用者の判断に使えない |
| 同じ意味の 2 文目を書かない | 言い換えは情報を増やさない |
| 失敗メッセージは「何が・なぜ・次に何をするか」 | 「エラーが発生しました」では止まる |
| 破壊的操作の確認は対象名を**動的に**埋める | 「〇〇を削除しますか」と一般化すると何が消えるか分からない |

文言を変えたら、理由とともに変更表（`docs/文言変更表.md` 等）に残す。**なぜ変えたかを残すのは、次に触る人が元へ戻さないため。**

## 画面を作る手順（Sonnet / Codex でも同じ）

1. `02_共通/ひな形/ui/README.md` の1枚表で、フレームワークに応じた置き場所と読み込み順を決める（tokens → components → layout）
2. 骨格は `layout.css` のクラス、部品は `components.css` のクラスを**そのまま使う**。無い部品が要るときだけ `var(--*)` で書き足し、汎用なら `components.css` に戻す
3. 操作フィードバックは `feedback.js`、アイコンは `icons.js`。`alert()` / `confirm()` / CDN を書かない
4. 部品の使い分けで迷ったら `references/components.md`（ツールチップの画面端・空状態の2用途・フォームエラーの2段構え・モーダルの3経路 など）
5. `./00_導入/03_点検/check-design.sh <対象>` を NG=0 にする
6. `uiux_review` で全状態（通常・実行中・失敗・0 件・狭い画面・モーダル）をライト／ダーク両方で実機で開く。「作った」を「効いている」と報告しない

- ナビ・一覧・設定の**並びは利用者の目的の時系列**（初めて開く → 試す → 自分のデータで使う → 結果を読む → 日々使う → 深く知る）。機能を追加した順にしない。並びを変える判断は ISO 9241-110 / Nielsen の原則名で書き、捨てた案も残す（`02_共通/ひな形/ADR-template.md`）

## 実物

- `02_共通/ひな形/tokens.css`（値。ライト＋ダーク、`data-theme` 両対応、reduced-motion、タップ最小 44px）
- `02_共通/ひな形/ui/components.css` / `02_共通/ひな形/ui/layout.css`（部品と骨格。`var(--*)` のみ）
- `02_共通/ひな形/ui/tailwind.config.js` / `streamlit-config.toml` / `streamlit_theme.py`（フレームワーク別）
- `02_共通/ひな形/components/feedback.js` / `icons.js` / `demo.html` / `demo-shell.html`（操作フィードバック・アイコン・実機確認ページ）

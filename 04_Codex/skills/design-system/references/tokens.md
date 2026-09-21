# トークンの役割と決めの理由

値そのものは `02_共通/ひな形/tokens.css` が唯一の真実源（ここに hex を複製しない。複製すると必ずズレる）。
このファイルは「なぜその段・その色にしたか」を残す。値を変えるときは tokens.css を直し、理由が変わればここも直す。

## 色（役割で持つ）

| グループ | トークン | 役割 |
|---|---|---|
| 基調 | `--color-primary` / `-light` / `-dark` / `--color-on-primary` | 操作・選択・リンクにだけ使う強調色（Material Blue 700 系）。`-light` は選択背景・ホバー、`-dark` はホバー時のアクション。`on-primary` が無いと濃色の上の白を直値で書くことになる |
| 面 | `--color-bg` / `--color-surface` / `-2` / `-3` | ページ背景（ごく薄いグレー）／カード・モーダル（白）／入れ子カード・サイドナビ／表のヘッダ行・淡い区画 |
| 境界 | `--color-border` / `-strong` / `--color-divider` | 通常の枠／フォーカス・選択中の枠／行区切り（枠より薄い） |
| 文字 | `--color-text` / `-secondary` / `-disabled` | 本文／補足・メタ情報／無効 |
| 状態 | `--color-{critical,high,medium,low,info}` ＋ `-bg` ＋ `-border` | ISTQB severity と 1 対 1。文字色＋淡い背景＋同系ボーダーの3点セットでバッジとコールアウトを作る |
| 状態（補助） | `--color-medium-text` | 黄（medium）は淡色背景に対してコントラスト不足なので、バッジの文字だけ濃い黄土色にする |
| 重ね | `--color-scrim` / `--color-tooltip-bg` / `-text` / `--color-knob` | モーダル背景／情報ツールチップ（**両テーマで固定の濃色**。可読性を保証）／トグルのつまみ |

- 1 画面に「プライマリ＋状態色＋グレー階調」以外を持ち込まない。装飾目的のグラデーション・彩度の高い背景は使わない
- 状態色を装飾に転用しない（見出しを赤にする等）。未読／既読のような軽い区別は背景の濃淡（`--color-primary-light`）だけで表す

## ダーク（2026-07 追加）

- **変数名は変えず、同じ `--color-*` を `@media (prefers-color-scheme: dark)` と `:root[data-theme="dark"]` の中で上書きするだけ**。部品側の CSS は一切変えない（Harness ToDo モックで実装・検証済み）
- メディアクエリと属性の**両対応が必須**。テーマ切替トグルを持つツールは `<html data-theme="dark">` を付けて明示上書きする（メディアクエリだけでは明示切替ができない）。`:root:not([data-theme="light"])` で「明示ライト」を除外する
- プライマリはライト版そのままだと暗背景でコントラスト不足なので明度を上げる。severity の**色相は変えず明度だけ上げる**（赤は赤のまま・見分けが崩れない）
- 状態色の背景は不透明の淡色でなく **`rgba(色, .18〜.20)`**。暗背景に淡色を乗算すると発色が濁る
- 純黒（#000）・純白（#FFF）は使わない。地は青みがかった近黒、文字は僅かにグレーがかった白（にじみ・残像を抑える）
- 影は濃く・広く（ライトより不透明度を上げる）。ツールチップの濃色は固定のまま

## 文字（7 段）

| トークン | 用途 |
|---|---|
| `--text-xs` | ラベル・バッジ |
| `--text-sm` | メタ情報・補足・表の本文 |
| `--text-base` | 本文（既定） |
| `--text-md` | セクション本文・空状態の見出し |
| `--text-lg` | カードタイトル・モーダル見出し |
| `--text-xl` | ページタイトル |
| `--text-2xl` | ヒーロー数値（KPI・スコア） |

- 段の間は 2px 以上あける。9〜17px を 1px 刻みで持っていた製品では、差が「別の役割」と読まれず、ただ揃っていないだけに見えた
- 行間は 3 段（tight 1.4 = 見出し・トップバー / normal 1.7 = 本文 / loose 2 = 長文）。日本語は行間をゆったり取る
- 本文の最大幅は `--text-measure`（68ch）。画面幅いっぱいにしない
- 英数字の羅列（ID・スコア・パス・数値列）は `--font-mono` に切り替える（等幅で桁が揃う）

## 余白・角丸・影・動き

- 余白は 4px の倍数だけ（`--space-1`=4 … `--space-12`=48）。カード内側は広め（`--space-6`）、部品同士は `--space-2`〜`--space-4`。詰まって見えたら余白を増やす方向で解決する
- 角丸は 4 段（sm=4 バッジ・チップ / md=8 カード・ボタン / lg=12 モーダル・大カード / xl=16 検索バー）＋ full（ピル型）。**内側は外側より小さく**（外側の角丸 − 内側の余白）。四角い角の要素を作らない
- 影は `--shadow-sm`（カードをわずかに浮かせる）/ `-md` / `-lg` / `-pop`（ポップオーバー・トースト・モーダル）。**影で語らずボーダーで区切る**。影は浮かせる要素だけ
- 動きは `--motion-fast` .12s（ホバー）/ `-normal` .2s（開閉・折りたたみ）/ `-slow` .3s。`prefers-reduced-motion` で全て止める（tokens.css の基本適用に含む）
- 触れる大きさは `--tap-min` 44px。`button, a, [role="button"]` に基本適用済み（片手操作の主要動作は画面下部寄り）

## フォント読み込み方針（2026-07 是正）

**既定はシステムフォントスタックのみ**（`--font-main`: Noto Sans JP → Hiragino Sans → Yu Gothic → Meiryo → system-ui / `--font-mono`: JetBrains Mono → ui-monospace → Consolas）。
OS 標準の日本語ゴシックと等幅フォントで十分な品質になる。

理由: `single-html-tool` / `nfr-standards` は「オフライン要件がある場合は CDN も不可」「外部依存は CDN（cdnjs）のみ」と規定しており、Google Fonts CDN 前提だと矛盾する。Artifact 環境や一部のサンドボックスは外部フォント CDN 自体をブロックする。

オンライン前提かつ見た目を厳密に統一したい社内配布ツールでだけ、**任意**で追加してよい（必須にしない。`check-design.sh` は外部 CDN を NG にするので、その行に `token-exempt` は効かない＝意図的に例外運用する）:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
```

オフライン要件のある PWA・Artifact・単一 HTML 配布では上記 CDN 行を入れない。

## 出所

kit design-system（MD3 Light 基準）＋ WebSpec2Doc `static/tokens.css`（on-primary / surface-3 / border-strong / severity-border / motion）＋ UX_Auto_Reviewer `style.css`（本文幅・reduced-motion）＋ Harness ToDo モック（ダーク・重ねの色）。

# templates/ui — デザインシステムの出荷物（どのファイルをどこに置くか）

値の唯一の真実源は `../tokens.css`、使い方の規律は `skills/design-system/SKILL.md`。ここにあるのは**貼る／読み込むだけで同じ見た目になる実物**。
モデルに CSS を書き起こさせない（Sonnet でも Codex でも、読み込み指示を書くだけで骨格が出る）。

| ファイル | 役割 |
|---|---|
| `../tokens.css` | トークン定義（ライト＋ダーク）＋基本適用。**最初に読む** |
| `components.css` | 部品（ボタン／入力／バッジ／カード／KPI／表／ページャ／トグル／ツールチップ／モーダル／コールアウト／空状態／スケルトン） |
| `layout.css` | 骨格（`.app` = globalbar / sidebar / topbar / content、`.layout-2pane`、KPI 列、ブレークポイント） |
| `../components/feedback.js` | トースト・消えない失敗・処理中・空状態・確認ダイアログ（CSS 自己注入） |
| `../components/icons.js` | Material Symbols 同梱（外部 CDN 不要） |
| `tailwind.config.js` | Tailwind の `theme.extend` を CSS 変数参照で登録（値を持たない） |
| `streamlit-config.toml` | Streamlit `[theme]`（tokens.css の写し） |
| `streamlit_theme.py` | Streamlit へ CSS を1箇所で注入 ＋ `badge()` `kpi()` `empty_state()` `callout()` |
| `../components/demo.html` / `demo-shell.html` | 部品／骨格の実機確認ページ |

## フレームワーク別（1枚表）

| フレームワーク | 置く場所 | 読み込み順 | 部品の使い方 |
|---|---|---|---|
| 単一 HTML ツール | `<style>` の先頭に `tokens.css` → `components.css`（→ 必要なら `layout.css`）を**貼る**。`<script>` に `icons.js` `feedback.js` を貼る | 貼った順 | `class="btn btn--primary"` `class="badge badge-high"` 等をそのまま使う |
| vanilla PWA | `css/tokens.css` `css/components.css` `css/layout.css` `js/icons.js` `js/feedback.js` | `<link>` を tokens → components → layout | 同上。ダーク切替は `<html data-theme="dark">` |
| React + Vite（Tailwind 可） | `src/styles/tokens.css` `src/styles/components.css`、`tailwind.config.js` を直下 | `main.tsx` で tokens → components を最初に import | `<Badge severity="high">` のように severity を props の列挙にする。Tailwind は `bg-primary` `rounded-md` `min-h-tap`（既定パレットは使わない） |
| Streamlit | `ui/tokens.css` `ui/components.css` `ui/streamlit_theme.py`、`.streamlit/config.toml` | 各ページ冒頭で `apply_theme()` | `badge()` `kpi()` `empty_state()` `callout()` を `st.markdown(..., unsafe_allow_html=True)` |
| Flask / Django | `static/css/tokens.css` `static/css/components.css` `static/css/layout.css` `static/js/icons.js` `static/js/feedback.js` | ベーステンプレートで tokens → components → layout | パーシャル（`partials/globalbar.html` `sidebar.html` `topbar.html`）を `.app` 骨格のクラスに対応させる |

## 検証（どのフレームワークでも）

```bash
./scripts/check-design.sh static src          # 直値・未定義トークン・外部 CDN・alert()・tokens.css 未読込（NG>0 で exit 1）
```

- `uiux_review` で全状態（通常・実行中・失敗・0 件・狭い画面・モーダル）を実機で開く。幅は 360×820 / 768 / 1366×768 / 1920×1080
- ライトとダークの両方でスクリーンショットを取り、severity の見分けが崩れていないことを確認する
- 直値を残すときは同じ行に `/* token-exempt: 理由 */` を書く（3px 以下のヘアラインと幅・高さは検査対象外）

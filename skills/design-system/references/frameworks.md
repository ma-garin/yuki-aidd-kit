# UI フレームワーク別の適用手順と、デザイン系スキルの分担

`skills/design-system/SKILL.md` のトークン（真実源）を、実装技術ごとにどう効かせるか。値はここで再定義しない。

## 分担（どのスキル・資産を使うか）

| 目的 | 使うもの | 注意 |
|---|---|---|
| 色・書体・余白・角丸・状態色の**値** | `skills/design-system/SKILL.md` + `templates/tokens.css` | 唯一の真実源。他のスキルが提案した値で上書きしない |
| 画面の骨格・文言・操作フィードバック・アイコン | `skills/design-system/SKILL.md`「画面の作り方」 | UX_Auto_Reviewer の実運用から抽出 |
| 見た目の再現（コードを見ずに指示） | `templates/design-system.md` | 3 パターン（Web アプリ / スライド / 管理画面） |
| HTML/JS/CSS・React の実装規約 | ECC `frontend-patterns` / `react-patterns` / `vite-patterns` | 規約。デザイン値は持たない |
| 独創的な UI を新規生成したい | `frontend-design`（第三者製・グローバル） | **起動時に本キットのトークンを渡す**。渡さないと汎用 AI 風の配色になる |
| ブランド・ロゴ・三層トークン設計 | `ckm:design` / `ckm:design-system`（第三者製） | 新規ブランドを起こす時だけ。既存 AIDD ツール群には使わない |
| 作った画面の検証 | `uiux_review` | 全状態（通常・実行中・失敗・0 件・狭い画面・モーダル）を実機で開く |

## 単一 HTML ツール / vanilla PWA

- `templates/tokens.css` の中身を `<style>` の先頭に貼る（単一 HTML は外部分割禁止）。PWA は `tokens.css` を最初に読み込む。
- 以降の CSS は `var(--color-*)` / `var(--space-*)` だけを使う。直値が出たらトークンに足すか、既存トークンに寄せる。
- ダーク切替トグルを持つ場合は `<html data-theme="dark">` を付ける（メディアクエリだけでは明示切替ができない）。
- 操作フィードバック（トースト・空状態・確認）は `templates/components/feedback.js` を使う（単一 HTML では `<script>` に貼る）。画面ごとに `alert()` や独自実装を作らない。

## React + Vite

- `src/styles/tokens.css` に配置し `main.tsx` で最初に import する。CSS Modules / styled-components でも値は `var(--*)` 参照にする。
- コンポーネントの対応: バッジ → `<Badge severity>`、スコアカード → `<ScoreCard>`、空状態 → `<EmptyState action>`、トースト → `useFeedback()`（ok / error / busy）。**severity は props の列挙**（critical/high/medium/low/info）にし、色名を props に出さない。
- Tailwind を使う場合は `tailwind.config.js` の `theme.extend.colors` / `spacing` / `borderRadius` に **CSS 変数を参照する形**で登録する（`primary: 'var(--color-primary)'`）。Tailwind の既定パレット（`blue-500` 等）を直接使わない。
- GitHub Pages 配信の base path・ビルドは ECC `vite-patterns`。

## Streamlit

- `.streamlit/config.toml` の `[theme]` に `primaryColor / backgroundColor / secondaryBackgroundColor / textColor / font` をトークンと同じ値で設定する（Streamlit はテーマ変数を CSS 変数として公開しないため、ここが真実源の写し）。
- 追加の見た目は `st.markdown('<style>…</style>', unsafe_allow_html=True)` を **1 箇所（`ui/theme.py`）に集約**し、各ページで散発させない。
- severity バッジ・空状態・確認ダイアログは `ui/components.py` に関数として置く（`badge(severity, text)` / `empty_state(msg, action)`）。

## Flask / Django（サーバーサイドテンプレート）

- `static/tokens.css` に配置し、ベーステンプレートで最初に読み込む。パーシャル（`partials/topbar.html` など）は骨格（globalbar / sidebar / topbar / content）に対応させる。
- 操作フィードバックは `templates/components/feedback.js` を `static/js/feedback.js` に置き、1 モジュール（`Feedback.ok / error / busy / emptyState / confirm`）に集約する。テンプレート個別に貼らない（`atarimae-quality-audit`「系統的な欠陥は共通基盤で一括修正」）。
- アイコンは `templates/components/icons.js` を `static/js/icons.js` に置く（外部 CDN 禁止）。

## 検証（どのフレームワークでも）

1. 直値の残数を数える: `grep -rnE "#[0-9A-Fa-f]{3,6}\b|[0-9]+px" <css/js> | grep -v tokens.css` → 0 を目標。残す場合は理由をコメント。
2. `uiux_review` で全状態を実機で開く。360px / 1366×768 / 1920×1080。
3. ダークとライトの両方でスクリーンショットを取り、severity の見分けが崩れていないことを確認する。

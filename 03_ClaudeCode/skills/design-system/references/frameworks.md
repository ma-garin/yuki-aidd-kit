# UI フレームワーク別の当て方と、デザイン系スキルの分担

値の真実源は `02_共通/ひな形/tokens.css`、規律は `skills/design-system/SKILL.md`、部品と骨格は `02_共通/ひな形/ui/`。**ここでは値もCSSも再定義しない。**
どのファイルをどこに置き、どの順に読み込むかは `02_共通/ひな形/ui/README.md` の1枚表が正（単一 HTML / PWA / React+Vite+Tailwind / Streamlit / Flask・Django）。

## 出荷物への導線

| したいこと | 使うもの |
|---|---|
| 色・余白・書体・角丸・状態色の値 | `02_共通/ひな形/tokens.css`（`<link>` か `<style>` 先頭に貼る） |
| ボタン・バッジ・カード・表・モーダル等の部品 | `02_共通/ひな形/ui/components.css`（クラス名をそのまま使う。書き起こさない） |
| 管理画面の骨格（globalbar / sidebar / topbar / content） | `02_共通/ひな形/ui/layout.css`（`.app` 骨格。`02_共通/ひな形/components/demo-shell.html` が実例） |
| トースト・消えない失敗・処理中・空状態・確認 | `02_共通/ひな形/components/feedback.js`（`alert()` を使わない） |
| アイコン | `02_共通/ひな形/components/icons.js`（外部 CDN を読まない） |
| Tailwind | `02_共通/ひな形/ui/tailwind.config.js`（`theme.extend` を CSS 変数参照で。既定パレット禁止） |
| Streamlit | `02_共通/ひな形/ui/streamlit-config.toml` + `02_共通/ひな形/ui/streamlit_theme.py`（`apply_theme()` 1箇所に集約） |
| 直値・未定義トークン・CDN・`alert()` の機械検査 | `00_導入/check-design.sh <対象パス>` |

## 分担（どのスキル・資産を使うか）

| 目的 | 使うもの | 注意 |
|---|---|---|
| 値の真実源 | `02_共通/ひな形/tokens.css`（理由は `references/tokens.md`） | 他のスキルが提案した値で上書きしない |
| 画面の骨格・文言・操作フィードバック・アイコンの規律 | `skills/design-system/SKILL.md`「画面の作り方」 | UX_Auto_Reviewer の実運用から抽出 |
| 見た目の再現（コードを見ずに指示） | `02_共通/ひな形/design-system.md` | 3 パターン（Web アプリ / スライド / 管理画面）＋機械/目視の別 |
| HTML/JS/CSS・React の実装規約 | ECC `frontend-patterns` / `react-patterns` / `vite-patterns` | 規約。デザイン値は持たない |
| 独創的な UI を新規生成したい | `frontend-design`（第三者製・グローバル） | **起動時に本キットのトークンを渡す**。渡さないと汎用 AI 風の配色になる |
| ブランド・ロゴ・三層トークン設計 | `ckm:design` / `ckm:design-system`（第三者製） | 新規ブランドを起こす時だけ。既存 AIDD ツール群には使わない |
| 作った画面の検証 | `uiux_review` ＋ `00_導入/check-design.sh` | 全状態を実機で開く（360 / 768 / 1366×768 / 1920×1080、ライト＋ダーク） |

## 共通の落とし穴

- severity は props / 引数の**列挙**（critical / high / medium / low / info）にし、色名を外に出さない
- ダーク切替トグルを持つなら `<html data-theme="dark">`（メディアクエリだけでは明示切替ができない）
- Streamlit はテーマ変数を CSS 変数として公開しない。`config.toml` は tokens.css の写しなので、値を変えるときは tokens.css を先に直す
- Tailwind で色を `var()` にすると `bg-primary/50` の透明度修飾子は効かない。淡色は `*-bg` トークンを使う

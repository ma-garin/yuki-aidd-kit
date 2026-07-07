---
name: design-system
description: AIDDツール群に一貫したビジュアルデザインを適用するスキル。HTMLツール・PWA・Streamlitアプリのデザインを決める際、「デザインどうする」「色は」「レイアウトは」「Material Design」「UIを作る」「コンポーネントを実装する」という言及があれば必ずこのスキルを使うこと。UX audit tool・QA Lens・業務支援エージェント・personal accounting PWA等の既存ツールと統一感を保つためにも必ず参照する。
---

# AIDD Design System（MD3 Lightベース）

過去ツール群（UX audit tool v3〜v5 / QA Lens / personal accounting PWA）から抽出した統一デザイン言語。迷ったらここの値をそのまま使う。

## カラーパレット（CSS変数）

```css
:root {
  /* Primary */
  --color-primary:       #1976D2;  /* メインアクション・アクティブ状態 */
  --color-primary-light: #E3F2FD;  /* 選択背景・ホバー */
  --color-primary-dark:  #0D47A1;  /* ホバー時のアクション */

  /* Surface */
  --color-bg:            #F8F9FA;  /* ページ背景 */
  --color-surface:       #FFFFFF;  /* カード・モーダル */
  --color-surface-2:     #F1F3F4;  /* 入れ子カード・サイドナビ背景 */

  /* Border & Divider */
  --color-border:        #E0E0E0;
  --color-divider:       #F0F0F0;

  /* Text */
  --color-text:          #212121;  /* 本文 */
  --color-text-secondary:#616161;  /* 補足・メタ情報 */
  --color-text-disabled: #9E9E9E;

  /* Status（ISTQB severity対応） */
  --color-critical:      #D32F2F;  /* Critical / エラー */
  --color-high:          #F57C00;  /* High / 警告 */
  --color-medium:        #FBC02D;  /* Medium / 注意 */
  --color-low:           #388E3C;  /* Low / 成功 */
  --color-info:          #0288D1;  /* 情報 */

  /* Severity背景（バッジ用）*/
  --color-critical-bg:   #FFEBEE;
  --color-high-bg:       #FFF3E0;
  --color-medium-bg:     #FFFDE7;
  --color-low-bg:        #E8F5E9;
  --color-info-bg:       #E1F5FE;
}
```

## ダークテーマ（2026-07 追加）

**変数名は変えない。同じ `--color-*` を `prefers-color-scheme` と `data-theme` の中で上書きするだけ**にする（既存コンポーネントのCSSは一切変更不要。Harness ToDo モックで実装・検証済み）。

```css
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-primary:       #6FB1EC;  /* ライト版そのままだと暗背景でコントラスト不足なため明度を上げる */
    --color-primary-light: rgba(111,177,236,.14);
    --color-primary-dark:  #9CCBF3;

    --color-bg:            #10141B;  /* 純黒ではなく青みを帯びた近黒（アクセントと調和） */
    --color-surface:       #1A212B;
    --color-surface-2:     #212A34;

    --color-border:        #2A323D;
    --color-divider:       #232B35;

    --color-text:          #E7EAEE;
    --color-text-secondary:#9AA5B1;
    --color-text-disabled: #6B7684;

    --color-critical:      #F17171;  --color-critical-bg: rgba(211,47,47,.18);
    --color-high:          #F5A25A;  --color-high-bg:     rgba(239,108,0,.18);
    --color-medium:        #F0C24D;  --color-medium-bg:   rgba(201,134,10,.20);
    --color-low:           #6FCB7F;  --color-low-bg:      rgba(56,142,60,.20);
    --color-info:          #6FB1EC; --color-info-bg:      rgba(2,119,189,.20);

    --shadow-sm: 0 1px 2px rgba(0,0,0,.35);
    --shadow-md: 0 2px 8px rgba(0,0,0,.4);
    --shadow-lg: 0 8px 28px rgba(0,0,0,.5);
  }
}
/* テーマ切替トグルを持つツールは data-theme を <html> に付与して明示上書きする */
:root[data-theme="dark"] { /* 上と同じ値を複製する（メディアクエリと属性の両対応が必須） */ }
```

- severityの色相そのものは変えず、明度だけ上げる（赤は赤のまま・見分けが崩れない）
- 背景色は不透明の淡色ではなく`rgba(色,.18〜.20)`にする。暗背景に対して淡色を乗算すると発色が濁るため
- 純黒(#000)・純白(#FFF)は使わない。地は青みがかった近黒、文字は僅かにグレーがかった白にする（にじみ・残像を抑える）

## タイポグラフィ

```css
:root {
  --font-main: 'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', sans-serif;
  --font-mono: 'JetBrains Mono', 'Consolas', monospace;

  /* スケール */
  --text-xs:   11px;  /* ラベル・バッジ */
  --text-sm:   13px;  /* メタ情報・補足 */
  --text-base: 14px;  /* 本文（デフォルト） */
  --text-md:   16px;  /* セクション本文 */
  --text-lg:   18px;  /* カードタイトル */
  --text-xl:   22px;  /* ページタイトル */
  --text-2xl:  28px;  /* ヒーロー数値 */

  /* 行間 */
  --leading-tight:  1.4;
  --leading-normal: 1.7;
  --leading-loose:  2.0;
}
```

## スペーシング・形状

```css
:root {
  --space-1:  4px;
  --space-2:  8px;
  --space-3:  12px;
  --space-4:  16px;
  --space-6:  24px;
  --space-8:  32px;
  --space-12: 48px;

  --radius-sm: 4px;   /* バッジ・チップ */
  --radius-md: 8px;   /* カード */
  --radius-lg: 12px;  /* モーダル・大カード */
  --radius-xl: 16px;  /* 検索バー */
  --radius-full: 9999px; /* ピル型バッジ */

  --shadow-sm: 0 1px 3px rgba(0,0,0,.08);
  --shadow-md: 0 2px 8px rgba(0,0,0,.12);
  --shadow-lg: 0 4px 16px rgba(0,0,0,.15);
}
```

## レイアウトパターン

### 永続サイドバー + 折りたたみ（管理画面/SaaS型ツール既定・2026-07 更新）

**ヘッダーはサイドバーの上を横断させない。** サイドバーは画面最上部から最下部まで独立して伸ばし、ブランドロゴもサイドバー内トップに置く。ヘッダー（検索・通知・アバター）はメインカラム側だけの軽量トップバーにする。Harness ToDo モックで実装・検証済み。

```css
.shell { display: flex; min-height: 100vh; }
.sidebar {
  flex: 0 0 240px; width: 240px;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex; flex-direction: column;
  min-height: 100vh; position: sticky; top: 0;
}
.sidebar.collapsed { flex-basis: 72px; width: 72px; } /* アイコンのみ。ラベルは display:none */
.maincol { flex: 1 1 auto; display: flex; flex-direction: column; min-width: 0; }
.header {
  height: 56px; flex: 0 0 56px;
  background: var(--color-surface); border-bottom: 1px solid var(--color-border);
  display: flex; align-items: center; gap: 20px; padding: 0 28px;
  position: sticky; top: 0;
}
```
- 折りたたみ時はナビ項目のラベル文字列を `<span class="label-text">` で包み、collapsed 時に `display:none`。アイコンだけ中央寄せに切り替える
- 折りたたみボタンはサイドバー上部の専用行に置く（ブランド行と同居させると幅が競合する）

### 旧: サイドバーがヘッダー内に収まる2ペイン（軽量ツール・サイドバーが常に見えていなくてよい場合のみ）
```css
.layout-2pane {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 100vh;
}
.sidenav {
  background: var(--color-surface-2);
  border-right: 1px solid var(--color-border);
  padding: var(--space-4);
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
}
```

### カードグリッド - ダッシュボード・一覧系
```css
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-4);
}
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
}
```

## コンポーネント

### バッジ（severity / status）
```html
<span class="badge badge-critical">Critical</span>
<span class="badge badge-high">High</span>
<span class="badge badge-medium">Medium</span>
<span class="badge badge-low">Low</span>
<span class="badge badge-new">NEW</span>
```
```css
.badge {
  display: inline-flex; align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: 600;
}
.badge-critical { background: var(--color-critical-bg); color: var(--color-critical); }
.badge-high     { background: var(--color-high-bg);     color: var(--color-high); }
.badge-medium   { background: var(--color-medium-bg);   color: #856404; }
.badge-low      { background: var(--color-low-bg);      color: var(--color-low); }
.badge-new      { background: var(--color-primary-light); color: var(--color-primary); }
```

### スコアカード（ISO 25010用）
```html
<div class="score-card">
  <div class="score-value">82</div>
  <div class="score-label">使用性</div>
  <div class="score-bar"><div class="score-fill" style="width:82%"></div></div>
</div>
```

### 情報ツールチップ（ℹ️、2026-07 追加）
用語・集計ロジックなど「本当に説明が要る項目」だけに付ける。装飾目的で乱用しない。
```html
<span class="info-ic">i<span class="tooltip">説明文をここに。2〜3行で収める。</span></span>
```
```css
.info-ic {
  display: inline-flex; align-items: center; justify-content: center;
  width: 15px; height: 15px; border-radius: 50%;
  background: var(--color-surface-2); color: var(--color-text-disabled);
  font-size: 10px; font-weight: 600; border: 1px solid var(--color-border);
  position: relative;
}
.info-ic .tooltip {
  display: none; position: absolute; z-index: 30; top: 130%; left: 50%;
  transform: translateX(-50%); width: 220px;
  background: #20242B; color: #F2F4F7;  /* テーマに関わらず固定の濃色チップ（両テーマで可読性を保証） */
  font-size: 11.5px; line-height: 1.55; padding: 9px 11px;
  border-radius: var(--radius-sm); box-shadow: var(--shadow-lg); text-align: left;
}
.info-ic:hover .tooltip, .info-ic.open .tooltip { display: block; }
/* 画面左端に寄る配置（サイドバー内など）では中央揃えだと画面外にはみ出すため左揃えにする */
.info-ic.edge-left .tooltip { left: 0; transform: none; }
```
実装時の注意: 中央揃え（`transform: translateX(-50%)`）はサイドバーなど画面端に近い場所で吹き出しが画面外にはみ出し、文字が切れる。**配置場所ごとにクランプ判定を入れるか `.edge-left` 系の修飾クラスを用意すること**（Harness ToDo モックで実際に発生し修正した不具合）。

### テーブルの列フィルタ + ページネーション（2026-07 追加）
```html
<th><div class="th-row">優先度
  <span class="col-filter-btn is-active"><svg><!-- funnel icon --></svg></span>
  <div class="col-pop"><!-- チェックボックス群 + 「すべて解除／適用」 --></div>
</div></th>
```
```css
.col-filter-btn { width: 19px; height: 19px; border-radius: 5px; color: var(--color-text-disabled); }
.col-filter-btn.is-active { color: var(--color-primary-dark); background: var(--color-primary-light); }
.col-pop { display: none; position: absolute; width: 176px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); box-shadow: var(--shadow-lg); padding: 10px; }
.col-pop.open { display: block; }

.pagebar { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 13px 18px; border-top: 1px solid var(--color-border); }
.pagesize .seg span.active { background: var(--color-surface); color: var(--color-primary-dark); box-shadow: var(--shadow-sm); } /* 表示件数: 5/10/30/50/100/すべて */
.pager .page.active { background: var(--color-primary); color: #fff; font-weight: 700; }
```
- 一覧画面の絞り込みは「全体トップの検索・並び替え」と「列ごとのフィルタ（列見出しのアイコン）」を分けて共存させる。両方を1つのUIに混在させない
- 表示件数変更でページは1に戻す。件数表示は `1–10 / 48 件` のように現在範囲/総数を併記する

### トグルスイッチ / セグメントコントロール（2026-07 追加）
```css
.toggle { width: 44px; height: 26px; border-radius: var(--radius-full); background: var(--color-border); position: relative; }
.toggle.on { background: var(--color-primary); }
.toggle > i { position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%; background: #fff; box-shadow: var(--shadow-sm); }
.toggle.on > i { left: 21px; }

.seg { display: inline-flex; background: var(--color-surface-2); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 3px; gap: 3px; }
.seg span.active { background: var(--color-surface); color: var(--color-primary-dark); box-shadow: var(--shadow-sm); }
```
- 2値のON/OFFはトグル、3値以上の相互排他選択（テーマ: ライト/ダーク/システム 等）はセグメントコントロールを使う。ラジオボタンの素朴な並びは使わない

### モーダル / ダイアログ（2026-07 追加）
Harness ToDo モックで「新規作成フォーム」「破壊的操作の確認」の2種を実装・実クリックで検証済み。
```html
<div class="modal-backdrop" id="xModal">
  <div class="modal"> <!-- 確認ダイアログは <div class="modal sm"> -->
    <div class="modal-head"><h3>見出し</h3><button class="modal-close" data-close="xModal">×</button></div>
    <div class="modal-body">…</div>
    <div class="modal-foot">
      <button class="btn btn--ghost" data-close="xModal">キャンセル</button>
      <button class="btn btn--primary" data-close="xModal">実行する</button> <!-- 破壊的操作は背景色を --color-critical に -->
    </div>
  </div>
</div>
```
```css
.modal-backdrop { position: fixed; inset: 0; z-index: 100; background: rgba(8,12,18,.46); display: none; align-items: center; justify-content: center; padding: 20px; }
.modal-backdrop.open { display: flex; }
.modal { width: 480px; max-width: 100%; background: var(--color-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); overflow: hidden; }
.modal.sm { width: 380px; } /* 確認ダイアログはモーダルより小さく */
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; border-bottom: 1px solid var(--color-border); }
.modal-body { padding: 20px 22px; }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 22px; border-top: 1px solid var(--color-border); background: var(--color-surface-2); }
```
- **開閉トリガー**: 開くボタンのクリック／`.modal-close`／backdrop 自身のクリック（`e.target===backdrop` で判定し、中身のクリックまで拾わない）の3経路を必ず用意する
- **破壊的操作の確認ダイアログ**は Critical 色のアイコン（円形背景 `--color-critical-bg` + アイコン `--color-critical`）と実行ボタンを Critical 色にし、対象名を本文に**動的に**埋め込む（「〇〇を削除しますか」と一般化しない）
- 同時に開くモーダルは1つまで。ページ内に複数の `.modal-backdrop` を用意してもよいが、開閉関数は共通化する

### 通知/リッチポップオーバー（2026-07 追加）
ツールチップ・列フィルタ（テキストのみの軽量ポップオーバー）と違い、リストや複数行の内容を持つ場合はこちらを使う。
```css
.notif-pop { display: none; position: absolute; top: 46px; right: 0; z-index: 60; width: 328px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); }
.notif-pop.open { display: block; }
.notif-item.unread { background: var(--color-primary-light); } /* 未読/既読は背景の濃淡だけで区別。バッジを乱用しない */
```
- **画面右上のヘッダーアイコンから開くポップオーバーは右揃え**（`right:0`）にする。中央揃えは画面外にはみ出す（情報ツールチップの節を参照）
- 開閉は「トリガー要素クリックでトグル」＋「ドキュメント全体のクリックで閉じる」の組み合わせ。ポップオーバー内部のクリックは `stopPropagation()` で外側クリック判定に伝播させない

### 空状態（0件表示）（2026-07 追加）
```html
<div class="empty-state">
  <span class="empty-ic"><svg><!-- 検索や+のような文脈アイコン --></svg></span>
  <h4>条件に一致するタスクがありません</h4>
  <p>フィルタや検索条件を変更するか、新しいタスクを作成してください。</p>
  <button class="btn">フィルタを解除</button>
</div>
```
```css
.empty-state { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 64px 24px; color: var(--color-text-secondary); }
.empty-ic { width: 56px; height: 56px; border-radius: 50%; background: var(--color-surface-2); display: grid; place-items: center; color: var(--color-text-disabled); margin-bottom: 18px; }
```
- 用途は2種: ①フィルタ・検索の結果0件（解決アクションは「フィルタを解除」）②新規ユーザーでデータが未作成（解決アクションは「最初の〇〇を作成」）。**文言とボタンを用途に応じて変える**。どちらも同じ空のグレーアイコンで済ませない

### フォームのバリデーション/エラー（2026-07 追加）
```css
.input.err { border-color: var(--color-critical); box-shadow: 0 0 0 3px var(--color-critical-bg); }
.field-err-text { display: flex; align-items: center; gap: 6px; color: var(--color-critical); font-size: 12px; margin-top: 7px; }
.banner-err { display: flex; gap: 10px; background: var(--color-critical-bg); border: 1px solid var(--color-critical); border-radius: var(--radius-md); padding: 12px 14px; font-size: 13px; color: var(--color-critical); }
```
- **2段構え**にする: フォーム全体のエラーは上部の `.banner-err`（「ログインできませんでした」等、原因の要約）、個別項目のエラーは該当フィールド直下の `.field-err-text`（「パスワードが正しくありません」等、具体的な指摘）。バナーだけ・フィールドだけの片方に頼らない
- エラー色は Critical のみ。警告と混同して High（橙）を使わない
- alert() やブラウザ標準のバリデーションポップアップは使わない（既存の「モーダル」「バナー」「フィールド直下」いずれかで表現する）

## 折りたたみ端末対応レスポンシブ

```css
/* カバー画面: ~360px */
@media (max-width: 360px) {
  .layout-2pane { grid-template-columns: 1fr; }
  .sidenav { display: none; }  /* ハンバーガーで開閉 */
  .card-grid { grid-template-columns: 1fr; }
}
/* メイン画面: 768px〜 */
@media (min-width: 768px) {
  .card-grid { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
}
/* タッチターゲット */
button, a, [role="button"] { min-height: 44px; min-width: 44px; }
```

## フォント読み込み方針（2026-07 是正）

**既定はシステムフォントスタックのみ。CDN読み込みは「オフライン要件がなく、かつ常時オンライン環境と確定している場合」の任意強化に格下げする。**

理由: `single-html-tool`/`nfr-standards` は「オフライン要件がある場合はCDNも不可」「外部依存はCDN（cdnjs）のみ」と規定しており、Google Fonts CDN前提だと矛盾する。またArtifact環境や一部のサンドボックスは外部フォントCDNそのものをブロックする。

```css
:root {
  --font-main: 'Noto Sans JP', 'Hiragino Sans', 'Yu Gothic', 'Meiryo', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
}
```
- OS標準の日本語ゴシック（Hiragino Sans / Yu Gothic / Meiryo等）と等幅フォントで十分な品質になる。これを既定にする
- オンライン前提かつ見た目を厳密に統一したい社内配布ツールでは、以下を**任意**で追加してよい（必須にしない）:
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
  ```
- オフライン要件のあるPWA・Artifact・単一HTML配布では上記CDN行を入れない

# lessons.md — キット自身の AIDD プロセス改善ログ

> `templates/lessons.md` は配布雛形（プロジェクト用）。ここは **yuki-aidd-kit を作る作業そのもの**の学び。
> 1エントリ Keep / Problem / Try。数値は実測だけを書く（`rules/absolute-rules.md` A-2）。
> `rules/model-routing.md`「測る」の週1 `/usage` 記録もここに1行で残す。

---

## 2026-09-17 横断 — 全ファイル読解 → spec/ 新設 → 土台（M15）・Pro 移行準備（M16）・デザイン出荷物（M17）

**Keep**
- 先に `spec/` に「読んで分かったこと」を全部書いてから計画した。計画中に再読が要らず、方針決定（Q-1〜Q-9）を1回で済ませられた
- 「Sonnet が壊しても機械が気づけるか」を判断軸にして、テスト（入口 71 / git ゲート 27 / check-docs 25 / check-design 36 ケース）と CI を**先に**入れた。以後の変更で自分のドリフト（INDEX の行数・ケース数・spec の網羅性）を check-docs が毎回拾った
- 「Sonnet に書かせず読ませる」: 散文の CSS 17 ブロックを `templates/ui/components.css` / `layout.css` に実体化し、SKILL.md を 473 → 115 行に。真実源は実ファイル（`tokens.css`）1つにして散文の複製を廃止した
- 1 ステップ = 1 コミットで `spec/` を同じコミットに入れる規約（Q-4）。後追いの同期作業が発生しなかった
- Playwright（同梱 Chromium）でライト／ダーク／360px を実際に開いてから出荷した。3 件の崩れ（topbar 高さ固定・globalbar 折り返し・テーマボタン重なり）は目視でしか見つからなかった

**Problem**
- 見積が大きく外れた: Phase 1（S1〜S6）は見積 50 分に対し実測 12 分。「往復数」で見積もると、スクリプト＋テストの作業は分岐数で決まるので当たらない
- `git clean -fd` が空ディレクトリを消してテストが壊れた／`| head` の SIGPIPE で `set -e` のスクリプトが途中終了した。テストの一時環境の作り方で 2 回手戻り
- 新トークンを tokens.css の 3 ブロック（light / media dark / data-theme dark）に入れるつもりが、1 ブロックに二重投入して data-theme 側が欠けた。**Playwright でトグルした後に `getPropertyValue` を見るまで気づかなかった**
- check-design の `alert()` 検査が `function confirm(` の定義を誤検出した。正規表現だけの検査は「定義」と「呼び出し」を区別できない
- セッションのモデルが途中で切り替わった（保守者の `/model`）。計画は「実装は Opus」だったが確認手段が `get_session` しか無い

**Try**
- [ ] 見積は「往復」でなく「分岐数 × 1 ケース」で出す（テスト系）／「ファイル数 × 読み書き」で出す（文書系）。次の計画で試して実測と比べる
- [ ] テストの一時環境は `mkdir -p` を `reset` 関数に含める。`set -e` のスクリプトで `| head` を使わない
- [ ] 複数ブロックへ同じ値を入れる変更は、入れた直後に `grep -c` で件数を確認する手順を `retro` / `done-gate` に足すか検討
- [ ] 移行後1週間: `/usage` の内訳（スキル・MCP・サブエージェント・長コンテキスト・キャッシュミス）をここに1行ずつ残し、Opus の3条件（Q-7）と U-1〜U-5 を実測で埋める
- [ ] `/context` を S7 前後の状態で測って `spec/11` U-2 / U-3 を推定から実測に置き換える（保守者の手元でしか実行できない）

---

## 2026-09-17 ユースケース検証 — 「社内図書館の貸出管理を Excel から Web へ。HTML でモック」

保守者から実際の依頼文をもらい、キットの手順どおりに作って「キットが本当に使えるか」を確かめた（`init-project.sh library-loan html` → `export-project.sh` → design-system + single-html-tool でモック → `check-design.sh` → `uiux_review`（Playwright で 14 状態）→ `done-gate`）。

**Keep**
- 依頼文 1 行から、規律（目的 1 行・残課題・未検証）と手順書（design-system / single-html-tool / uiux_review / done-gate）が意図どおり効いた。モックは tokens / components / layout / feedback / icons を**貼るだけ**で 5 画面が揃い、CSS を書き足したのは配置の 20 行だけ
- `uiux_review` の「全状態を実機で開く」を Playwright で機械化したことで、目視だけでは出ない不具合（360px の横スクロール、hidden が効かないエラー印、KPI カードのズレ）が 3 件出た
- 「作ったら check-design を叩く」を最初にやったおかげで、**キット側の欠陥（F-14）を配布先の最初の 1 回で踏めた**。出荷物のセルフテストだけでは配布先の形（`.claude/templates/`・貼り込み）は検証できていなかった

**Problem**
- `check-design.sh` は配布先で NG=426 を出した（tokens.css の場所・`.claude/` 走査・貼り込んだ定義行）。キット内の 7 ファイルに対しては NG=0 だったので気づけなかった。**「出荷物が自分で通る」と「配布先で使える」は別のテスト**
- `layout.css` の globalbar は demo-shell.html の短い文言では崩れず、実案件の文言（「社内図書館 貸出管理」＋「総務部 図書係」＋テーマ）で初めて 360px を超えた。デモは**現実的な長さの文言**で作る
- 自分の app.css の `.card + .card` が KPI 列の中にも効いた。部品のクラス（`.card`）に対する隣接セレクタは骨格の中で誤爆する

**Try**
- [x] `test-check-design.sh` に「配布先の形」のケースを追加（ケース10）→ 43 ケース
- [ ] 他の検査スクリプト（check-docs は対象外、trace-check / quality_harness）にも「配布先で `.` を渡した形」のテストがあるか確認する
- [ ] demo-shell.html の文言を実案件相当の長さにする（globalbar / topbar）
- [ ] `references/components.md` に「`.card` への隣接セレクタは `.app-content >` で限定する」を足す

## /usage 週次記録（移行後に追記）

| 週 | 基盤 | スキル | MCP | サブエージェント | 長コンテキスト | キャッシュミス | 上限に当たった回数 | 備考 |
|---|---|---|---|---|---|---|---|---|
| （2026-10 第1週から） | | | | | | | | |

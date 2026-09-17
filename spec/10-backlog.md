# 10 — 作り込みバックログ

**優先度の基準**: `spec/11-target-operating-model.md`（Pro ＋ Sonnet ＋ Codex 併用で開発がスムーズに回ること）への直接の寄与。
`docs/Roadmap.md` の作業ルールに合わせ、各項目に **対象 / 内容 / 完了条件 / 検証 / 見積** を持たせる。
採用して着手が決まったら **Roadmap のマイルストーンへ昇格させ、ここからは消す**。

> 2026-09-17 改訂。旧版は「キットの健全性」で優先度を決めていたが、保守者から真の目的
> （来月 Pro へ移行し Sonnet 基盤で回す）が示されたため並べ替えた。旧 B-01（CI）は優先度2へ、
> デザインの作り込み（新規要求）は優先度1に入れた。

---

## 優先度0（移行前にやる。これが無いと移行後に測れない）

### B-10 — 常時読み込み層を実測する ★★

**対応**: `spec/11` U-2 / U-3 / D-1

現在の 10,810 トークンは**文字数からの推定**であり、`/context` の実測ではない。
測らずに削ると、削った効果も分からない。**A-2「測らない見積もりは出さない」が自分自身に適用される場面。**

- **対象**: `spec/11-target-operating-model.md` §3 D-1 の表 ／ `docs/lessons.md`（新設・B-05）
- **内容**:
  1. 現行環境で `/context` を実行し、**Memory files に何が載っているか**と各サイズを記録
  2. `/usage` の内訳で、スキル・MCP・サブエージェントの消費割合と「長コンテキスト」「キャッシュミス」フラグを記録
  3. `InstructionsLoaded` hook を一時的に仕込み、**`rules/` が本当に毎セッション全文ロードされているか**を確認する
  4. 推定値を実測値に置き換える
- **完了条件**: `spec/11` §3 の表が実測に置き換わり、推定と実測の乖離が1行で記録されている
- **検証**: `/context` の出力を `docs/quality/evidence/` に保存
- **見積**: 自分 2 往復（≒5分）＋保守者の手元実行
- **注**: **これは保守者の手元環境でしか実行できない**（このリポジトリのセッションからは `/context` を叩けない）

---

## 優先度0b（土台）— **完了 2026-09-17 → `docs/Roadmap.md` M15 へ昇格**

B-16 / B-17 / B-18 / B-02 / B-01 / B-03 / B-08 はすべて実装済み。記録は Roadmap M15、仕様は `spec/05-scripts.md`。以下は当時の計画（履歴）。

<details><summary>当時の計画</summary>


保守者の問い「土台として現状整理を精緻化し、今後の拡張に耐えられるようにするために必要なタスク」（2026-09-17）への回答。
**判断軸: 「Sonnet が触って壊しても、機械が気づけるか」**。気づけないものが土台の穴。

### B-16 — 入口スクリプトの回帰テスト ★★

**対応**: F-11

- **対象**: `scripts/test-install.sh`（新規）
- **内容**: `HOME` を一時ディレクトリに差し替えて `install.sh` → `verify.sh` を実行（NG=0・既存 `CLAUDE.md` の `.bak` 退避・`settings.json` 既存時の警告・同名 rules のスキップ）／一時ディレクトリへ `export-project.sh` を実行（生成物の一覧・`.bak` 退避・`INDEX.md` 参照の相対化・`scripts/*` の既存スキップ）／`init-project.sh` の3種別／`init-test-docs.sh --ci` の配置数
- **完了条件**: 4スクリプト×正常＋異常で 12 ケース以上 PASS。`install.sh` が実 `~/.claude` に触れないことをテスト自体が保証
- **見積**: 6 往復

### B-17 — git ゲートの回帰テスト ★★

**対応**: F-11

- **対象**: `scripts/test-git-gates.sh`（新規）
- **内容**: 一時 git リポジトリを作り、`pre-commit`（秘密情報パターン検出／`localStorage` 行の除外）と `pre-commit-ui-gate.sh`（マーカー無し BLOCKED／期限切れ BLOCKED／hash 不一致 BLOCKED／一致 PASS／`.rebuild-mode` WARN／`docs/*.html` は対象外）と `ui-hash.py`（`disk`/`staged`・除外接頭辞）を実行して終了コードを assert
- **完了条件**: README が「手動4ケース確認」と書いている箇所を、このテストのケース数に置き換えられる
- **見積**: 4 往復

### B-18 — バージョンの刻印

**対応**: F-12

- **対象**: `scripts/export-project.sh` / `scripts/verify.sh` / git tag
- **内容**: `git tag v6.3.0` を現在の main に打つ（以後 Ver.x.y.z と tag を一致させる）／`export-project.sh` が `<target>/.claude/KIT_VERSION` に `tag / commit / 日付` を書く／`verify.sh` と `export-project.sh` の出力に版を表示／`README.md` の版歴に「tag と対応」と1行
- **完了条件**: 配布先の `.claude/KIT_VERSION` だけで、どの版から出たかが分かる
- **見積**: 2 往復

### 土台の合計と、移行時期への含意

| 区分 | 項目 | 見積（往復） |
|---|---|---|
| 土台 | B-10 実測（手元）／B-16／B-17／B-18／B-02／B-01（CI＋check-docs）／B-03／B-08 | **≒28** |
| 移行直結 | B-11 ダイエット／B-12 ルーティング | ≒12 |
| 拡張（Opus のうちにやると得） | B-13 デザイン／B-05／B-06 | ≒28 |
| 移行後でよい | B-14／B-15／B-07 | ≒13 |

1 往復 ≒ 1.75 分（本セッション実測: spec 12ファイル＝8往復＝14分）。
**移行前に済ませたい「土台＋移行直結＋拡張」≒ 68 往復 ≒ 2 時間の生成時間**。PR 単位のレビューを挟むと実日数は別（下記）。

</details>

---

## 優先度1（移行の成否を直接決める）

### B-11 — 常時読み込み層のダイエット ★★★ — **完了（M16 S7）**

**対応**: `spec/11` D-1 / D-2

- **対象**: `rules/*.md`（3本）／ `CLAUDE.md.template` ／ `AGENTS.md.template` ／ `INDEX.md`
- **内容**:

  **(a) `rules/` を規範と根拠に分ける**
  - `absolute-rules.md`（112行）: A-1〜A-10 の**発動条件と出力だけ**を本文に残す。根拠・言い回し（「表で出して」は見せろでなく管理せよ等）は `rules/references/why-absolute.md` へ
  - `speed-harness.md`（115行）: H-1 着手前3行・H-2 環境チートシート・H-3 バッチ検証・H-7 コミット手順・H-8 進捗は残す。H-4 委譲の失敗事例と H-5 の実測由来の記述は `rules/references/speed-evidence.md` へ
  - 目標: 常時読み込みの `rules/` を **268行 → 100行以下**

  **(b) `paths` frontmatter を使う**
  - `functional-integrity.md` は**コードと UI を触るときだけ**でよい → `paths: ["**/*.{py,js,ts,tsx,jsx,html,css}"]`
  - 常時必要なのは `absolute-rules` と `speed-harness` のみ
  - **注意**: `paths` 付き rules は「該当ファイルを読んだとき」に載る。**完了報告の直前に必ず載っているとは限らない**ので、完了条件そのものは `CLAUDE.md` 側に1行残す

  **(c) `INDEX.md` を毎回読むのをやめる**
  - `CLAUDE.md` に**タスク種別 → 読むファイル**の30行程度のルーティング表を直接埋め込む
  - `INDEX.md` は「表に無い／迷ったとき」の第2段に降格する
  - 期待削減: 推定 4,330 トークン／セッション

  **(d) `AGENTS.md` / `CLAUDE.md` の二重管理を解消する**
  - `CLAUDE.md.template` を `@AGENTS.md` ＋ Claude Code 固有の追記（実装モード・hooks・`/effort`）だけにする
  - 共通部分は `AGENTS.md.template` 一本に集約
  - **AUDIT X-5「両ファイルを同時に更新する」というルール自体が不要になる**
  - `export-project.sh` が生成する `CLAUDE.md` もこの形にする

- **完了条件**:
  - `rules/` の `paths` 無しファイルの合計 ≦ 100行
  - `CLAUDE.md.template` ≦ 200行（公式ガイダンス）かつ `@AGENTS.md` import 形式
  - `AGENTS.md` と `CLAUDE.md` に同じ内容が二重に書かれていない
  - ルーティング表だけで主要タスクの入口に到達できる
- **検証**: 変更前後で `/context` を比較し、削減量を実測（B-10 が前提）。`export-project.sh` で一時ディレクトリへ出して両ファイルを目視
- **見積**: 自分 8〜10 往復（≒25分）＋検証1周
- **決定**: Q-5（決定事項の表）

### B-12 — モデル／effort ルーティング規則を追加する ★★ — **完了（M16 S8）**

**対応**: `spec/11` D-5 / D-6

- **対象**: `rules/speed-harness.md`（H-9 として追加）または `rules/model-routing.md`（新設）
- **内容**: Pro ＋ Sonnet 前提の判断表を規範として入れる。
  - 既定は Sonnet。**Opus へ上げるのは**「複雑な設計判断」「多段推論」「Sonnet が2周しても収束しない」の3条件のみ（公式の指針に沿う）
  - **effort を下げる**: 定型作業・文書整形・調査の要約は `/effort` を下げる（Claude Code の既定は `xhigh`）
  - **`/clear` の規律**: 無関係なタスクへ移るときは必ず `/clear`。長いセッションを開きっぱなしにしない（キャッシュ寿命1時間・全履歴を毎回送る）
  - **委譲のしきい値を引き直す**: H-4 は「往復×12秒」で決めていたが、Pro ではトークンで決める。**サブエージェント＝別コンテキスト、Agent teams ＝通常の約7倍**。原則、委譲は「冗長な出力を隔離する目的」に限る（テスト実行・ログ処理・大量ファイルの走査）
  - **上限に当たったときの手順**: 5時間窓／週次窓は全モデル共有なので `/model` では回復しない。モデル系列別上限なら `/model` で切り替える。`/usage` で内訳を見てから判断する
- **完了条件**: 判断表が `rules/` にあり、`CLAUDE.md` から1行で参照されている。**根拠（5時間窓・7倍・キャッシュ1時間）は references に置き、本文は表だけ**
- **検証**: `spec/11` §2 の一次情報と矛盾していないこと
- **見積**: 自分 3 往復（≒8分）

### B-13 — デザインを「散文」から「出荷物」にする ★★★

**対応**: 保守者の要求（2026-09-17）／ `spec/11` D-3 ／ `spec/09-findings.md` F-04

**詳細計画は `spec/12-design-framework.md`。** ここには並びだけ置く。

| # | 内容 | 見積 |
|---|---|---|
| DS-1 | `templates/ui/components.css`（SKILL.md の CSS 17ブロックを実体化） | 5 往復 |
| DS-2 | `templates/ui/layout.css`（骨格の実体化） | 3 往復 |
| DS-4 | `scripts/check-design.sh` ＋ `scripts/test-check-design.sh`（直値・未定義トークン・CDN・`alert(` を機械判定） | 5 往復 |
| DS-3 | FW 別の出荷物（Tailwind config / Streamlit config・theme / `templates/ui/README.md`） | 4 往復 |
| DS-5 | `SKILL.md` を ≦200行に縮小（references へ分割。**実務知は失わない**） | 4 往復 |
| DS-6 | `templates/design-system.md` のチェックリストに機械/目視の別を付ける | 1 往復 |

- **推奨順序**: DS-1 → DS-2 → **DS-4（ここで赤→緑を確認）** → DS-3 → DS-5 → DS-6
  DS-4 を DS-5 の前に置くのは、**縮小で実務知を落としていないかを機械で確かめてから**縮めるため
- **受け入れ条件**: `spec/12` §4 の A-1〜A-4
- **見積合計**: 自分 22 往復（≒55分）＋検証2周
- **決定**: Q-1（決定事項の表）

---

## 優先度2（移行後の品質を守る。Sonnet 基盤では重要度が上がる）

### B-01 — キット自身の CI と文書整合チェック ★★ — **完了（M15 S5/S6）**

**対応**: `spec/09-findings.md` F-07（High）/ F-09 / F-01・F-02・F-03

旧優先度1。目的への寄与は間接的だが、**Sonnet が壊したものを機械で検出する**という意味で移行後はむしろ重要になる。

- **対象**: `scripts/check-docs.sh`（新規）／`.github/workflows/kit-ci.yml`（新規。**キット自身用**。配布用サンプルの `github-actions/` とは別物であることをファイル冒頭に明記）
- **内容**:
  - `check-docs.sh` の検査項目:
    1. `INDEX.md` の参照コスト（行数）が実測と一致するか
    2. 全スキル・コマンド・rules・hooks が `INDEX.md` に掲載されているか
    3. 回帰テストのケース数の記載（`README.md` / `INDEX.md` / `manual.html`）が実測と一致するか
    4. キット内相対パス参照の切れ（ECC 外部と対象プロジェクト側の生成パスは除外リストで無視）
    5. SKILL.md の frontmatter `name` とディレクトリ名の一致
    6. **常時読み込み層の行数上限**（B-11 で決めた値）の超過検出 ← 新規。ダイエットの逆戻りを防ぐ
    7. PRD の「1スキル ≦ 200行 / 1コマンド ≦ 40行」超過の検出（B-13 DS-5 完了までは WARN）
  - 出力は3層（結論 → 種別ごと → 全件は `check-docs-report.md`）
  - `kit-ci.yml` は PR / push(main) / dispatch で `test-hooks.sh` `test-trace-check.sh` `test-quality-harness.sh` `check-docs.sh` `check-design.sh` を実行。**`GATES_REQUESTED=1` を付ける**
- **完了条件**: 現状のリポジトリに対して F-01・F-02・F-03 を**先に検出できる**（赤→緑）。`scripts/test-check-docs.sh` が正常ケースと各 NG ケースを両方通す。PR で全ジョブ green
- **検証**: `bash scripts/check-docs.sh`（NG=0）／`bash scripts/test-check-docs.sh`／PR の Actions
- **見積**: 自分 8〜12 往復（≒25分）

### B-14 — 強制層を Codex 側へ寄せる

**対応**: `spec/11` D-4

- **対象**: `scripts/`（git hook 層）／ `AGENTS.md.template` ／ `scripts/export-project.sh`
- **内容**:
  - Claude Code hook でしか効かない3つ（`block-gates.py` / `block-explore.sh` / `progress.py`）のうち、**Codex でも効かせたいものを git hook かスクリプトへ移せるか**を判定する
    - ゲートの無断実行 → Codex には強制手段が無い。**`AGENTS.md` の規約として残すしかない**（正直にそう書く）
    - 探索ブロック → 同上
    - 秘密情報・`.ui-verified`・trace・契約 → **既に git hook / スクリプトで両対応**。ここを厚くする
  - `scripts/install-git-hooks.sh`（新規）: `pre-commit` と `pre-commit-ui-gate.sh` を `.git/hooks/pre-commit` に**1コマンドで配線**する。現在は手順が文章でしか書かれておらず、配線されていない可能性が高い
  - `AGENTS.md.template` に「Codex では hook による強制が効かない項目」を明示する節を作る（**効くふりをしない**）
- **完了条件**: 一時リポジトリで `install-git-hooks.sh` を実行し、秘密情報コミットと UI 未検証コミットが実際に止まること
- **検証**: 実機で4状態（秘密情報あり／UI 変更＋マーカー無し／マーカー期限切れ／正常）
- **見積**: 自分 5 往復（≒13分）

### B-15 — hook を「入力を絞る」用途に使う

**対応**: `spec/11` §2 の公式トークン削減策（未活用）

- **対象**: `claude-code/hooks/`（新規 hook）／ `claude-code/hooks/settings.json`
- **内容**: 公式が例示している「テスト出力を grep で絞ってから Claude に渡す」PreToolUse hook をキットの規約に合わせて用意する。
  - `filter-test-output.sh`: `pytest` / `npm test` / `go test` の出力を失敗行＋前後5行に絞る
  - **`block-gates.py` と共存させる**（ゲートはユーザー要求時のみ実行、実行したときは出力を絞る）
- **完了条件**: `test-hooks.sh` にケースを追加し、絞り込みが効くことを assert
- **検証**: `./scripts/test-hooks.sh` PASS
- **見積**: 自分 4 往復（≒10分）
- **決定**: Q-6（既定 OFF・`FILTER_TEST_OUTPUT=1` で有効化）

---

## 優先度3（健全性。移行とは独立）

### B-02 — `verify.sh` を終了コードで判定できるようにする — **完了（M15）**
`spec/09-findings.md` F-06。末尾に `[ "$NG" -eq 0 ] && exit 0 || exit 1`。見積 2 往復。

### B-03 — 陳腐化した数値の一括是正 — **完了（M15）**
`spec/09-findings.md` F-01 / F-02 / F-03。**B-01 完了後に `check-docs.sh` の出力どおり直す**（手で直すだけでは再発する）。`docs/Roadmap.md:52` は当時の事実の記録なので触らない。見積 2 往復。

### B-05 — 自己改善ループを起動する
`spec/09-findings.md` F-05。`templates/lessons.md`（配布雛形）と `docs/lessons.md`（キット自身用・新設）を分け、
**本セッションと移行そのものを最初のエントリにする**。`rules/speed-harness.md` の実測記録欄も埋める。見積 3 往復。決定 Q-2。

### B-06 — 配布層の `/implement` 非対称を解消する
`spec/09-findings.md` F-08。推奨は案 A（`export-project.sh` の settings.json に `block-explore` を配線する）。見積 3 往復。決定 Q-3。

### B-07 — `manual.html` の図解（Roadmap M13 の未完）
`spec/09-findings.md` F-10。単一 HTML のまま、既存の `.flow-h` / `.flow-v` で。見積 4 往復。

### B-08 — `spec/` の自動同期 — **完了（M15）**
`check-docs.sh` に `spec/01-inventory.md` の行数突合を追加。B-01 が前提。見積 2 往復。

---

## 決定事項（2026-09-17 保守者「方針決めてほしい」を受けて決定。以後は迷わない）

| # | 論点 | 決定 | 理由 |
|---|---|---|---|
| Q-1 | `components.css` の粒度 | **1ファイル** | 単一 HTML ツールでは `<style>` に貼るので分割の利点が無い。読み込み指示も1行で済み Sonnet に優しい |
| Q-2 | `lessons.md` の分離 | **`docs/lessons.md` を新設** | `templates/lessons.md` は配布雛形。自分の実績を混ぜると配布先に漏れる |
| Q-3 | 配布層の `block-explore` 配線 | **A: `export-project.sh` に配線を含める** | モード未設定時は無条件 exit 0 で副作用ゼロ（回帰テスト済み）。PRD「両配置で同一の振る舞い」を満たす |
| Q-4 | `spec/` のコミット単位 | **本体変更と同一コミット** | 分けると必ず乖離する（`spec/README.md` 更新規約②） |
| Q-5 | `INDEX.md` の扱い | **(a) ルーティング表を `CLAUDE.md` に埋め、INDEX は第2段に降格** | INDEX は全体地図として残す価値がある。「毎回読む」をやめるだけで 4,330 トークン相当が浮く |
| Q-6 | テスト出力の絞り込み hook | **入れる。既定 OFF、`FILTER_TEST_OUTPUT=1` で有効化** | 効果は大きいが失敗の全文が見えなくなる。`GATES_REQUESTED=1` と同じ「明示して使う」型に揃える |
| Q-7 | Opus へ上げる条件 | **暫定3条件（複雑な設計判断／多段推論／Sonnet が2周しても収束しない）。移行後1週間の `/usage` 実測で見直す** | 公式指針に沿う。数値の根拠が無い段階で細かく決めない（A-5） |
| Q-8 | 作業単位 | **バックログ1項目 ＝ 1 PR** | Roadmap 作業ルール③「1項目完了ごとに個別コミット」。レビューと revert の単位を小さく保つ |
| Q-9 | デザイン値の真実源 | **`templates/tokens.css` の1ファイル**（SKILL.md から移動。references/tokens.md は理由のみ） | 実ファイルと散文の二重管理は必ず乖離する。`check-design.sh` が読むのも tokens.css。Sonnet には「読み込ませる」形が安全 |

### 実行順（決定）

```text
B-10 実測（保守者の手元。着手時と各 PR の後）
 │
 【土台】 Sonnet が壊しても機械が気づける状態にする
 ├─ 1. B-16 入口テスト ＋ B-17 git ゲートテスト ＋ B-18 版の刻印 ＋ B-02
 ├─ 2. B-01 キット自身の CI（check-docs 含む）→ B-03 数値是正 → B-08 spec 同期
 │
 【移行直結】
 ├─ 3. B-11 常時読み込み層のダイエット
 ├─ 4. B-12 モデル／effort ルーティング規則
 │
 【拡張】 生成量が多いので Opus＋Max のうちに
 ├─ 5. B-13 デザインを出荷物に（DS-1→2→4→3→5→6）
 ├─ 6. B-05 lessons 起動 ／ B-06 配布層の配線
 │
 ═══ ここで Pro へ移行 ═══
 │
 └─ 7. B-14 Codex 側の強制層 ／ B-15 入力を絞る hook ／ B-07 manual 図解
```

**土台を先にするのは、以後の全 PR（Sonnet が書くものを含む）を CI が守るため。**
順序を入れ替えて B-11 を先にすると、rules/ を削った影響を検出する網が無いまま進むことになる。

## 採用しなかった案（理由つきで残す。再提案を防ぐ）

| 案 | 却下理由 |
|---|---|
| `spec/` に設計値（トークン・ゲート基準）を写して一元化 | 真実源の重複を新設する。Roadmap 作業ルール④の禁止事項。AUDIT D-01 で「二重管理は必ず乖離する」実績がある |
| INDEX の参照コストを手で直して終わり | F-09（検査の仕組みが無い）が根本原因なので必ず再発する |
| `github-actions/` の既存 yml をキット自身にも流用 | 配布用サンプルは対象プロジェクトの構成を前提にしており、キット自身には存在しない |
| `@path` import で `rules/` を分割してトークンを減らす | **import は起動時に展開されるので常時コストは減らない**（`memory` docs 明記）。減らすには `paths` frontmatter か skills への移設しかない |
| `MAX_THINKING_TOKENS` で Sonnet の思考を絞る | **Sonnet 5 は adaptive のみで `budget_tokens` は 400 で拒否される**。effort で調整する |
| デザインを CSS フレームワーク（Bootstrap 等）に載せ替える | 単一 HTML ツールの「外部依存なし」制約と衝突する（`spec/12` §5） |

# 09 — 現況の残課題（実測・evidence つき）

**測定日**: 2026-09-16 ／ **対象リビジョン**: `968fa93` ＋ 本セッションの `spec/` 追加
（INDEX.md / README.md に `spec/` への導線を1節ずつ追加したため、docs 表の行番号は +17 シフトしている）
記法は `qa-review-standards` に従う: `{ID, 対象, severity(ISTQB), evidence, 是正案}`。
**evidence を提示できない指摘は書かない。**

---

## 0. 健全性（先に「壊れていないこと」の実測）

| 検査 | 結果 |
|---|---|
| `./ci/test-hooks.sh` | **PASS=19 / FAIL=0** |
| `./ci/test-trace-check.sh` | **PASS=15 / FAIL=0** |
| `./ci/test-quality-harness.sh` | **PASS=11 / FAIL=0** |
| SKILL.md の frontmatter `name` とディレクトリ名の一致 | 19/19 一致 |
| INDEX.md へのスキル掲載漏れ | 0 件（19/19） |
| INDEX.md へのコマンド掲載漏れ | 0 件（16/16） |
| キット内相対パス参照の切れ | **0 件**（`MISSING` として出るのは ECC 外部資産と対象プロジェクト側の生成パスのみ） |

`./scripts/install.sh` と `./scripts/verify.sh` は**未実行**（グローバル環境 `~/.claude` を上書きするため）。
Roadmap M12 でも同じ理由で未計測と記録されている。→ F-06。

---

## 1. 数値の陳腐化（文書が実体に追随していない）

### F-01 — hooks 回帰テストのケース数が3種類に分裂 ★

> **是正済み（2026-09-17）**: S4 / S6 で是正。`check-docs.sh` 検査3が再発を止める。

**severity: Medium**（利用者が「PASS=8 なら合格」と読むと、11件の失敗を見逃す）

| 箇所 | 記載 | 実測 |
|---|---|---|
| `README.md:82` | `./ci/test-hooks.sh  # hooks の回帰テスト（11ケース）` | **19** |
| `INDEX.md:18` | `./ci/test-hooks.sh   # hooks の回帰テスト（11ケース）` | **19** |
| `docs/yuki-aidd-kit-manual.html:792-793` | 「8ケースでテストします」「**PASS=8 / FAIL=0**なら合格です」 | **19** |
| `docs/Roadmap.md:52` | 「完了確認: 8ケース PASS=8/FAIL=0 で exit 0」 | M6 当時の記録なので**当時の事実として正しい**（履歴） |
| `docs/PRD.md:30` | 「`./ci/test-hooks.sh` 19 ケース」 | **正しい** |
| `README.md:42` | 「hooks 回帰テスト 19 ケース」 | **正しい**（同じ README 内で 11 と 19 が併存） |

**是正案**: README:82 / INDEX:18 / manual.html:792-793 を 19 に統一。Roadmap は履歴なので触らない。

### F-02 — INDEX.md の参照コストが実体とズレている

> **是正済み（2026-09-17）**: S6 で是正。`check-docs.sh` 検査1が再発を止める。

**severity: Low**（読む/読まないの判断材料が狂う。DAILY 層なので影響は小さくない）

| 対象 | INDEX 記載 | 実測 | 差 |
|---|---|---|---|
| `INDEX.md:45` `sdd-ecc-workflow` | 53行 | **55** | +2 |
| `INDEX.md:46` `qa-review-standards` | 43行 | **46** | +3 |
| `INDEX.md:48` `test-automation` | 49行 | **55** | +6 |
| `INDEX.md:51` `done-gate` | 43行 | **56** | +13 |
| `INDEX.md:59` `design-system` | 463行 | **465** | +2 |
| `INDEX.md:73` `functional-integrity` | 39行 | **41** | +2 |
| `INDEX.md:135` `docs/Roadmap.md` | 115行 | **155** | +40 |
| `INDEX.md:137` `docs/PRD.md` | 64行 | **72** | +8 |
| `INDEX.md:140` `docs/OPERATING-MODE.md` | 75行 | **78** | +3 |
| `INDEX.md:142` `docs/yuki-aidd-kit-manual.html` | 1337行 | **1434** | +97 |

一致しているもの（触らない）: dev-lifecycle 105 / context-compression 56 / ecc-daily-router 57 /
atarimae 71 / test-strategy 105 / e2e-cycle 95 / uiux_review 199 / retro 38 / nfr-standards 89 /
agent-eval 67 / code-doc-search 55 / single-html-tool 36 / personal-pwa 30 / streamlit-rag-app 32 /
absolute-rules 112 / speed-harness 115 / Vision 47 / ECC-ASSET-MAP 148 / AUDIT 114 / PROJECT-FIT 48 /
全17コマンド。

**是正案**: 機械導出に置き換える（`spec/10-backlog.md` B-01）。手で直すだけでは必ず再発する。

### F-03 — ECC-ASSET-MAP の行数が INDEX 内で二重記載

> **是正済み（2026-09-17）**: S6 で 148 に統一。検査1が散文の「（N行）」も見る。

**severity: Low**

`INDEX.md:112`（ECC 連携の本文）が「147行」、`INDEX.md:138`（docs 表）が「148行」。実測は **148**。
**是正案**: 本文側を 148 に統一するか、本文からは行数を落として表だけに持たせる（真実源を1箇所にする原則に合う）。

---

## 2. 自己規約への違反

### F-04 — `design-system/SKILL.md` が PRD の「1スキル ≦ 200行」を大きく超過 ★ — **是正済み（M17 S13、2026-09-17）**

是正内容: SKILL.md 473 → **115 行**。値は `templates/tokens.css` を唯一の真実源にし（hex の複製を廃止）、決めの理由を `references/tokens.md`、部品の使い分けと落とし穴を `references/components.md` に移設。`check_docs.py` の `SIZE_STRICT` を True にし、以後 200 行超過は CI で NG。

**severity: Medium**（DAILY ではなく LIBRARY なので常時コストではないが、発火すると465行を読ませる）

- evidence: `docs/PRD.md` 非機能・使用性「**1スキル ≦ 200行、1コマンド ≦ 40行を目安とする**」／実測 `skills/design-system/SKILL.md` = **465行**
- 次点は `skills/uiux_review/SKILL.md` = **199行**（ぎりぎり充足）
- 他17スキルはすべて 105行以下
- 構造的にも、465行のうち約半分（L388 以降「画面の作り方」）は 2026-08 に追加された別レイヤー

**是正案**: 値（トークン・コンポーネント CSS）を `references/tokens-and-components.md` に、
「画面の作り方」を `references/screen-construction.md` に分割し、SKILL.md は索引＋判断に絞る。
`templates/tokens.css` との真実源関係を壊さないこと。

### F-05 — 自己改善ループ（Vision 到達点③）が一度も回っていない ★ — **是正済み（M17 S15）**

是正内容: `docs/lessons.md` を新設し、本セッション（読解→spec→M15〜M17）を Keep / Problem / Try の最初のエントリにした。移行後の週次 `/usage` 記録欄を持つ。`templates/lessons.md` は配布雛形のまま（Q-2）。

**severity: Medium**（キットの3大目標のうち1つが未達）

- evidence: `templates/lessons.md` は34行すべて雛形とコメントアウトされた記入例で、**実エントリ0件**
- evidence: `docs/Roadmap.md:55` M6「retro 運用の実績を反映する」が `[ ]` のまま。前提条件に「lessons.md にエントリが溜まってから着手」と明記されている＝**前提が満たされていない**
- evidence: `rules/speed-harness.md` 末尾の「実測記録（プロジェクトごとに追記）」欄も**空**。H-6 が求める違反時の追記が一度も行われていない
- `skills/retro/SKILL.md` は存在し `/retro` も存在するので、**仕組みでなく運用が回っていない**

**是正案**: 実運用ではなくキット自体の開発で回す。本セッション（spec/ 作成）を最初のエントリにする。

### F-06 — `verify.sh` が終了コードで合否を返さない

> **是正済み（2026-09-17）**: S1 で修正。`test-install.sh` が assert。

**severity: Low**（CI から使えない。現状は人間が目で見る前提）

- evidence: `scripts/verify.sh:47-48` — `結果: OK=$OK / NG=$NG` を出力し、最終行が `[ "$NG" -eq 0 ] && echo "✅ 全て正常" || echo "⚠ 未配置あり…"`。**NG>0 でも `||` 側の echo が成功するため終了コードは 0** になる
- 一方 `trace-check.sh:248` は `[ "$NG" -eq 0 ] && exit 0 || exit 1`、`quality_harness.py` も 0/1 を返す
- `docs/Roadmap.md` の「完了の定義」が「verify.sh NG=0」を条件にしているのに、**機械判定できない**

**是正案**: 末尾に `[ "$NG" -eq 0 ] && exit 0 || exit 1` を追加。既存の使い方（目視）は壊れない。

---

## 3. 構造的な穴

### F-07 — キット自身の CI が存在しない ★★ 最優先

> **是正済み（2026-09-17）**: S5 で `.github/workflows/kit-ci.yml` を追加。

**severity: High**（回帰テストが3本あるのに、PR で自動実行されない。F-01/F-02 の陳腐化もこれが原因）

- evidence: `.github/` ディレクトリが存在しない（`find . -name ".github" -type d` が 0 件）
- evidence: `templates/github/workflows/` の4本はすべて**配布先プロジェクトへ置くサンプル**（各ファイル冒頭に「`.github/workflows/xxx.yml` に配置」と明記）
- 結果: `test-hooks.sh` 19 / `test-trace-check.sh` 15 / `test-quality-harness.sh` 11 の計45ケースが、手で実行しない限り回らない

**是正案**: `spec/10-backlog.md` B-01。

### F-08 — `export-project.sh` が生成する settings.json に `block-explore.sh` の配線が無い — **是正済み（M17 S15、案①・Q-3）**

是正内容: ヒアドキュメントに `Read|Grep|Glob` → `block-explore.sh` を追加（`.claude/mode` が無ければ exit 0 で副作用なし）。出力メッセージの「/implement 利用時に追記」を削除。`test-install.sh` に配線と JSON 妥当性の assert を追加。

**severity: Low**（仕様として意図的だが、利用者から見ると `/implement` が静かに無効化される）

- evidence: `scripts/export-project.sh:47-82` のヒアドキュメント（`.claude/settings.json` 生成）に `Read|Grep|Glob` の PreToolUse が無い
- evidence: 同 `:83` の出力メッセージに「block-explore.sh は /implement 利用時に settings.json へ追記」とだけある
- 一方 `CLAUDE.md.template`（配布先にそのままコピーされる）は「`/implement` で実装モードに入る」「hook が物理ブロックする」と**無条件に書いている**
- PRD 非機能「グローバル導入とプロジェクト配布のどちらでも同一の振る舞い」に照らすと不整合

**是正案**: ①配線を含めて生成する（既定 ON）、②配布先 `CLAUDE.md` に「配布層では要追記」を1行足す、
③現状維持で `spec/` にだけ記録、のいずれか。**保守者の選択が必要**（Roadmap 作業ルール⑤）。

### F-09 — 文書の整合を検査する仕組みが無い

> **是正済み（2026-09-17）**: S5 で `check-docs.sh` を追加（8 検査）。

**severity: Medium**（F-01・F-02・F-03 の根本原因）

- evidence: `scripts/verify.sh:58-59` は「チェックリストはリポジトリ実体から自動導出する。資産を追加してもこのファイルの更新は不要」と書かれており、**配置だけ**を自動化した
- 一方、INDEX の参照コスト・README のケース数・manual の数値は**すべて手書き**のまま
- Roadmap M6 で「verify.sh のリスト自動生成化」は完了扱いになっているが、**文書側の数値は対象外**だった

**是正案**: `spec/10-backlog.md` B-01（`ci/check-docs.sh`）。

### F-10 — Roadmap の未完項目2件

**severity: Low**（追跡されているので問題ではないが、現況として記録する）

| 箇所 | 内容 | 状態 |
|---|---|---|
| `docs/Roadmap.md:55` | M6「retro 運用の実績を反映する」 | 前提条件（lessons.md にエントリ）が未達 → F-05 |
| `docs/Roadmap.md:139` | M13「manual.html の非エンジニア向け説明（テストレベルと『テストが通った≠完了』）は本 PR で最小限。**図解は未着手**」 | 未着手 |

---


---

## 3b. 土台（拡張に耐えるか）の観点で追加した finding（2026-09-17）

### F-11 — 入口スクリプト2本と git ゲート4本に回帰テストが無い ★★

> **是正済み（2026-09-17）**: S3 `test-install.sh`（66）/ S4 `test-git-gates.sh`（27）で解消。未テストは `audit-app-workspace.sh` のみ。

**severity: High**（キットの「導入」と「止める仕組み」そのものが未検証。Sonnet が触ると壊れても気づけない）

- evidence: `ci/test-*.sh` が参照しているのは `hooks/*`・`trace-check.sh`・`init-lifecycle.sh`・`quality_harness.py`・`templates/test/feature_contracts.yml` のみ
- 未テスト（9/15）: **`install.sh`・`export-project.sh`**（キットの入口2本）／**`pre-commit`・`pre-commit-ui-gate.sh`・`ui-hash.py`**（git ゲート。README は「手動4ケース確認」とだけ記載）／`init-project.sh`・`init-test-docs.sh`・`audit-app-workspace.sh`・`verify.sh`
- `export-project.sh` は Roadmap M8 で「スクラッチへの初回エクスポート・`.bak` 退避・相対パス動作を確認済み」とあるが**手動確認であり再実行できない**

**是正案**: B-16（入口）・B-17（git ゲート）。`HOME` を一時ディレクトリに差し替えれば `install.sh` も安全にテストできる。

### F-12 — バージョンが刻印されていない

> **是正済み（2026-09-17）**: S2 で `VERSION` / `KIT_VERSION`。tag は main マージ時に保守者。

**severity: Medium**（配布先の `.claude/` がどの版のキットから出たか判別できない。Vision が許容した「スナップショットは追従しない」トレードオフを、追跡不能にしてしまっている）

- evidence: `git tag` が 0 件。`README.md` に Ver.5.0〜6.3 の記述はあるが tag と対応していない
- evidence: `scripts/export-project.sh` / `install.sh` に version を書き出す処理が無い（grep `VERSION|version|Ver.` が 0 件）

**是正案**: B-18。`git tag v6.3.0` から始め、`export-project.sh` が `.claude/KIT_VERSION`（tag ＋ commit hash ＋ 日付）を書き、`verify.sh` がそれを表示する。

### F-13 — スキルが意図どおり発火するかを検証する手段が無い

**severity: Medium**（Sonnet 基盤では発火の取りこぼしが増える可能性があるが、測れない。`retro` の「発火しなかったスキル→description に言い回し追加」は観測に依存している）

- evidence: `skills/*/evals` が存在しない。20スキルの description は手書きのまま一度も評価されていない
- 関連: `spec/11` U-4

**是正案**: 移行後に `/usage` のスキル別内訳で観測する（B-10）。恒久策は `skill-creator` の eval を使った発火テストだが、コストが高いので**移行後の実測で問題が出たスキルだけ**に限定する。

## 3c. ユースケース検証で見つかった finding（2026-09-17「社内図書館の貸出管理を Excel から Web へ。HTML でモック」）

保守者から実際の依頼文を受け取り、キットの手順どおり（`init-project.sh html` → `export-project.sh` → design-system / single-html-tool → `check-design.sh` → `uiux_review` → `done-gate`）に作って検証した。**キット自身の欠陥が 3 件出て、その場で是正した。**

### F-14 — `check-design.sh` が配布先プロジェクトで使い物にならなかった — **是正済み**

**severity: High**（配布先で最初に叩いた瞬間に NG=426 を出し、利用者は検査そのものを無視するようになる）

- evidence: `--tokens` の既定が `templates/tokens.css` 固定。配布先では `.claude/templates/tokens.css` にあるため「未定義トークン 426 件」
- evidence: `.` を渡すと `.claude/` 配下のキット雛形（tokens.css の hex 定義）まで走査し「直値」として大量報告
- evidence: 単一 HTML の規約どおり `<style>` に tokens.css を貼ると、その定義行（`--color-primary: #1976D2;`）115 件が直値扱い
- 是正: `--tokens` 省略時は `templates/tokens.css` → `.claude/templates/tokens.css` の順に探す／`.claude` `.git` `node_modules` 等を走査から除外／カスタムプロパティの定義（`--x: 値`）を直値検査から除外。`test-check-design.sh` ケース10（7 assert）を追加し 43 ケースに

### F-15 — `layout.css` の `.app-globalbar` が狭幅で画面幅を押し広げる — **是正済み**

**severity: Medium**（360px で横スクロールが出る。demo-shell.html は文言が短くて再現しなかった）

- evidence: `.app` が grid で、grid 項目の `min-width:auto` により nowrap のグローバルバーが最小幅を主張し、`document.scrollWidth` 715 > 360
- 是正: `.app { grid-template-columns: minmax(0, 1fr) }` ＋ `.app > * { min-width: 0 }`、globalbar の子を `flex: 0 1 auto; min-width: 0`。あわせて ≦480px でパンくずを非表示（見出しと主操作を優先）

### F-16 — `components.css` の部品に `hidden` 属性が効かない — **是正済み**

**severity: Low**（`.field-err-text { display:flex }` が `hidden` の `display:none` に勝ち、エラー印が常時表示された）

- 是正: ユーティリティに `[hidden] { display: none !important; }` を追加

## 3d. 工程承認ゲートの検討で見つかった finding（2026-09-19「AIDD の SDD で要求したものが確実に作られているか」）

背景: AIDD では「プロセスが正しく回っているか」（QA4AIDD 等が担う領域）を見ても、企業が知りたい
「**要求したものが確実に作られているか**」には答えられない。誤りが成果物として出てから見つかると手戻りが最大になる。

### F-17 — 工程の承認が 10 工程中 3 つにしか存在しなかった ★★ — **是正済み（M18 S16・S21）**

- evidence: 承認欄があるのは `00-rfd.md` / `01-requirements.md` / `08-acceptance-test.md` のみ。
  `02`〜`07` と `09` には承認への言及がゼロ。`phase-gates.md` の出口基準は散文のチェックボックスで、
  誰も押さなくても次工程へ進める
- severity: High（誤りが下流工程へ無検出で伝播する）
- 是正: 全 10 工程に承認記録（`docs/lifecycle/approvals/phase-<n>.md`）を用意し、共通出口基準を 3 → 4 項目に

### F-18 — 承認という概念を機械が一切知らなかった ★★ — **是正済み（M18 S17・S18・S19）**

- evidence: `trace-check.sh` は ID の紐づきのみ、`quality_harness.py` は機能契約のみを見る。
  `commands/lifecycle.md` の「前工程の出口基準が未達なら着手せず差し戻す」は**書いてあるだけ**で、
  AI が自分で読んで自分で守る前提だった
- severity: High（承認が形だけになる。判子を押した後に中身が差し替わっても検出できない）
- 是正: `phase-hash.py`（承認を版に縛る）＋ `check-approval.sh`（exit 0/1/2、判定不能を合格に数えない）
  ＋ `block-phase.py`（未承認の工程の下流成果物への書き込みを deny）

### F-19 — 承認の covers に追跡表を含めるとゲートが永久に詰まる — **是正済み（S18 の設計時に検出）**

- evidence: 当初 `covers` に `traceability-matrix.md` を含めていたが、追跡表は全工程が書き足す生きた文書で、
  第3工程の更新が第1・第2工程の承認を毎回失効させる
- severity: Medium（設計段階で検出。実装には出ていない）
- 是正: `covers` はその工程が所有する成果物だけにし、追跡表の整合は `trace-check.sh` が別の機械ゲートとして担保する。
  回帰テストに「後続工程を進めても前工程の承認は失効しない」ケースを追加

## 3e. トークン節約の棚卸しで見つかった finding（2026-09-19「トークンの節約を徹底的に仕組みとして組み込みたい」）

### F-20 — 節約策の大半が散文で、機械が強制しているのは 3 つだけだった ★★ — **是正済み（M19 S23〜S28）**

- evidence: 機械は `block-explore.sh`（実装モードの探索）・`block-gates.py`（ゲートの無断実行）・`check-docs.sh` 検査6（rules ≦ 100 行）のみ。
  「grep してから読む」「部分読み」「`/clear` の規律」「effort を下げる」「MCP より CLI」は散文で、AI が自分で読んで自分で守る前提。
  公式の削減策「hook で前処理してから渡す」は B-15 として「移行後」送りになっていた
- severity: High（Pro＋Sonnet では上限に直結する。散文は人が覚えていないと効かない）
- 是正: 絞る hook 2 本（`filter-output.py` `pre-read-guard.py`）・寿命 hook 3 本（`context-guard.py` `pre-compact.py` `log-instructions.py`）・
  設定 3 キー（`effortLevel` `autoCompactWindow` `BASH_MAX_OUTPUT_LENGTH`）・点検 `token-audit.sh`・`check-docs.sh` 検査9。散文は「hook が強制する」の導線に置き換え

### F-21 — 警告系 hook の stdout が Claude に届いていない可能性（未確認・起票のみ）

- evidence: `pre-write-check.sh` `post-write-html.sh` `session-summary.sh` は exit 0 で stdout に警告を出すが、
  公式 docs では PreToolUse / PostToolUse の exit 0 の stdout は transcript（人）向けで、Claude に渡るのは JSON の `systemMessage` / `additionalContext`。
  この 3 本の「💡 500 行超は部分編集を」等の警告が AI の行動を変えていない可能性がある
- severity: Medium（効いていないだけで害は無い）
- 対応: 次のセッションで hooks docs「exit 0 の stdout はどこに出るか」を確認し、Claude に読ませたい警告は `systemMessage` に載せ替える

## 3f. テスト工程のメトリクスで見つかった finding（2026-09-19「テスト工程のメトリクスを次の計画として進めて」）

### F-22 — 実行記録が機械可読でなく、進捗・品質のメトリクスが出せなかった ★★ — **是正済み（M20 S30〜S33）**

- evidence: 05〜08 のテスト表に実施日・実施者が無く、欠陥表に起票日が無い。29119 側の CSV は設計 9 列のみ。
  完了報告書 §2 は手書きの表、`TESTING_STRATEGY.md` §7 の完了基準は 1 行の散文で機械が読めない。
  `trace-check.sh` は ID の紐づきだけを見る
- severity: High（QA の主業務である「どこまで進んだ・あと何日・危ない不具合は残っているか」に、目視で数えた数字でしか答えられない）
- 是正: 表の列と語彙を固定（S30）、`test-metrics.sh`（S31。unread を分母に入れる・欠陥表なしを 0 と区別する・推定に根拠を付ける・
  exit 0/1/2）、§7 を機械が読める表に、完了報告書を `--into` で置換。事例で端から端まで実測（S33）

### F-23 — 配布スクリプトが新スクリプトを同梱し忘れる構造 — **是正済み（S33）**

- evidence: S31 で作った `test_metrics.py` が `export-project.sh` / `init-test-docs.sh` の同梱リストに無く、配布先で「No such file」。
  事例を実際に回すまで気づかなかった（F-19・M19 の「本体形と配布形の差」と同型）
- severity: Medium
- 是正: 両スクリプトに追加し、`test-install.sh` に生成物の assert。**新スクリプトを足したら配布リストと test-install を同じコミットで更新する**を横断ルールに追加

### F-24 — 保守者の傾向分析が「言葉の規約」で止まり、実装者に課している「手順の型」を拾っていなかった — **是正済み（M21 第 2 回）**

- evidence: 第 1 回（PR #20）は本セッションの発言と qa-autopilot の CLAUDE.md・constitution・PROMPT_FOR_CODEX から 14 傾向を出したが、
  保守者「この依頼についての対応がない。不愉快だ」「やはり浅すぎる」。未読だった `harness/loop.md`・HANDOVER・VERIFICATION_REPORT（30 ペルソナ）・
  WORK_ORDER・personas・standards/README・specs/006 に、着手前 4 行／5 つの質問／止まる条件／3 回失敗の報告 5 項目／予実はツール実行回数／
  多ペルソナ検証／作業指示書の型／貼れば動く形／未検証の確かめ方／準拠の主張範囲 が明文化されていた
- severity: High（保守者の要望に対する未達。第 1 回の反映先が `rules`・`AGENTS` の散文に偏り、手順が走る場所に入っていなかった）
- 是正: `docs/maintainer-tendencies.md` に第 2 回 16 傾向（#15〜#30）を原文つきで追加。反映先を「手順が走る場所」に変更 —
  H-1 を 4 行（終了条件）／`/plan` に 5 つの質問と作業指示書への導線／`templates/implement-profile.md` に止まる条件表／
  `templates/work-order.md`（新規）／`templates/CURRENT_STATE.md` に決まっていること・未検証の確かめ方・最初の 5 分／
  `templates/ADR-template.md` に判断基準と捨てた案／`skills/qa-review-standards/references/personas.md`（16 ペルソナ・判定一覧の型）と
  `/qa-review` 手順 6／`done-gate` に受入基準の検証と 0 件実行／A-12 の報告 5 項目／`check-docs.sh` 検査 11（絶対パス。userguide の 5 箇所を修正）

### F-25 — 作業中に届いた保守者の指示を読み飛ばし、英語で途中報告を続けた — **是正済み（M22）**

- evidence: 2026-09-19、連続コマンド実行中に届いた「日本語で出力し、今何をやっているのかを正確に報告しなさい」「中間報告をしなさい。今すぐに」（2 回）を、
  ツール結果の一部として扱い次のコマンドへ進んだ。途中報告 2 本は英語。保守者「強い怒りを覚えている。仕組みで改善しなさい」
- severity: **Critical**（保守者の指示の無視。信頼の毀損）
- 根本原因: 「作業を完遂する」「止まらない」（A-11・H-7）を保守者の最新の指示より上に置いた。散文の規約（日本語・簡潔）は作業の連鎖の中では読み返されない
- 是正: **A-13 指示優先**を規範化し、Claude Code では hook が強制する — `instruction-guard.py`（PreToolUse 全ツール: 発言の後に日本語の応答が無ければ deny。
  理由に指示の先頭を載せる）／`reply-language.py`（Stop: 最後の応答に日本語が無ければ続行）／`prompt-priority.py`（UserPromptSubmit: 緊急語に優先の注入）。
  本セッションの実 transcript の応答前断面で deny、応答後で許可を確認。キット自身の開発セッションにも `.claude/settings.json` で配線（file watcher で即時反映）

### F-26 — 開発用 hook 配線が実体に届かず、保守者のプロンプトが投入ごとブロックされた — **是正済み（6.8.2）**

- evidence: 2026-09-20、リモートセッション（作業ディレクトリ `/home/user/yuki-aidd-kit`）で `UserPromptSubmit` の
  `python3 "$CLAUDE_PROJECT_DIR"/claude-code/hooks/prompt-priority.py` が `[Errno 2] No such file or directory` で失敗し、
  保守者の発言が丸ごとブロックされた。`$CLAUDE_PROJECT_DIR` はローカル側の `/Users/.../yuki-aidd-kit` に解決され、そこに実体が無かった
- severity: **High**（保守者が発言できない。セッションが成立しない）
- 根本原因: 配線は 3 形あり、`~/.claude/settings.json`（`install_guard.py`）と `<target>/.claude/settings.json`（`export-project.sh`）は
  **実体を配置してから参照する**のに対し、キット自身の `.claude/settings.json` だけが**リポジトリ内の実体を直接参照**していた。
  参照先が欠けると python3 が非 0 で終わり、`UserPromptSubmit` はそれを「投入拒否」として扱う。`prompt-priority.py` 自身は常に 0 を返す
  設計だが、**起動に失敗する経路**が想定外だった
- 是正: `.claude/settings.json` の 3 本を `sh -c 'f=…; [ -f "$f" ] && exec python3 "$f" || exit 0'` に変更（実体が無ければ無言で飛ばす）。
  回帰テストを `ci/test-hooks.sh` の `[.claude/settings.json 配線]` に追加（79 → 83 ケース）
- 残る論点（構成管理）: 旧 `claude-code/hooks/` を `hooks/` へ移すとき、この配線と `install_guard.py` の `--hooks-dir` 既定値
  （`scripts/install-guard.sh` 経由）が同時に参照切れになる。移動とパス更新は同一コミットで行う → **M23 で実施**

### severity 別サマリ（更新）

| severity | 件数 | ID |
|---|---|---|
| Critical | 0 | — |
| High | 0 | ~~F-07~~ ~~F-11~~（M15 で是正） |
| Medium | 4 | F-04（SKILL 465 行 → S13）／F-05（lessons 未稼働 → S15）／F-13（発火の検証手段 → 移行後の実測）／**F-21（警告 hook の stdout。未確認）** |
| Low | 2 | F-08（配布層の block-explore → S15）／F-10（manual 図解 → 移行後） |
| 是正済み | 23 | F-01 F-02 F-03 F-06 F-07 F-09 F-11 F-12（M15）／F-04 F-05 F-08（M17）／F-14 F-15 F-16（ユースケース検証）／F-17 F-18 F-19（M18）／F-20（M19）／F-22 F-23（M20 テストメトリクス）／F-24（M21 第 2 回）／**F-25（M22 指示優先）** F-26（6.8.2 配線の耐障害化） |

## 4. 設計上の既知の割り切り（欠陥ではない・混同しないこと）

| # | 内容 | 根拠 |
|---|---|---|
| 1 | プロジェクト配布層はキット更新に自動追従しない | `docs/Vision.md`「配布の性質上避けられないトレードオフとして許容する」 |
| 2 | ECC 資産の実在はこのリポジトリから検証不能 | `docs/PRD.md` 制約・`AUDIT` A-08。参照は MAP 経由に限定して管理 |
| 3 | `quality_harness.py` が JSON 互換 YAML しか読まない | 依存ゼロで動かすため。`feature-contracts.md` に明記 |
| 4 | `streamlit-rag-app` が特定プロジェクト前提 | 冒頭に明記済み（AUDIT の備考対応。M6 で完了） |
| 5 | `manual.html` がデザインシステムの3パターンに従わない | `templates/design-system.md`「適用除外: ドキュメント・マニュアル類」で**意図的な別ジャンル**と宣言 |
| 6 | `scan.sh`（atarimae）のヒットは偽陽性を含む | SKILL.md・scan.sh 双方に「候補であって結論ではない」と明記 |

---

## 5. severity 別サマリ

| severity | 件数 | ID |
|---|---|---|
| Critical | 0 | — |
| **High** | **1** | F-07（キット自身の CI 不在） |
| Medium | 4 | F-01（ケース数の分裂）／F-04（200行超過）／F-05（自己改善ループ未稼働）／F-09（文書整合の検査なし） |
| Low | 5 | F-02（参照コスト）／F-03（行数の二重記載）／F-06（verify.sh の終了コード）／F-08（block-explore の配線）／F-10（Roadmap 未完2件） |

**着手順の推奨**: F-07 → F-09 → F-01・F-02・F-03（F-09 の成果物で自動修正）→ F-06 → F-04 → F-05 → F-08（要相談）。
根本原因を先に潰さないと、F-01〜F-03 は手で直しても再発する。

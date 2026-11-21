# I7-rules 内部実装: rules・規約文書（段1 広域）

- 対象: `02_共通/rules/*.md`（10 本）、`CLAUDE.md`（リポジトリ直下）、`03_ClaudeCode/CLAUDE.md.template`、`04_Codex/AGENTS.md.template`（`~/.claude/AGENTS.md` の配布元。リポジトリに `AGENTS.md` 本体は無い: `git ls-files | grep AGENTS.md` で該当なし）、`INDEX.md`、`llms.txt`。比較のため導入先 `~/.claude/AGENTS.md`・`~/.claude/CLAUDE.md`・`~/.claude/rules/aidd-kit/`・`~/.claude/rules/common/` と、文書が名指しする hook（`03_ClaudeCode/hooks/constitution-gate.py`・`instruction-guard.py`・`prompt-priority.py`・`reply-language.py`・`pre-read-guard.py`・`context-guard.py`）を読んだ。
- 調べた方法: `wc -c`/`wc -m` で実測、`diff`/`cmp` でリポジトリと導入先を比較、`grep` で規定の重複と矛盾を抽出、hook の正規表現を `python3 -I` で切り出して実入力に当てた、`llms-txt.py --check` で生成物の鮮度を確認。
- 調べた件数/全件数: 規約文書 15/15（rules 10・CLAUDE 系 3・AGENTS 系 2）＋索引 2/2。hook は文書が名指しする 6/28 本（`03_ClaudeCode/hooks` の .py/.sh は 28 本）。
- 制約: `.claude/` 配下の constitution で始まる状態ファイルは開いていない。

---

## I7-rules-01 導入先の見積書式「見積もり：」を hook が受けない（従うと停止する）
- 種別: 欠陥
- 深刻度: Critical
- 根拠:
  - `diff 02_共通/rules/absolute-rules.md ~/.claude/rules/aidd-kit/absolute-rules.md` → 導入先は A-2 が `` `見積もり：N分（HH:MM）` ``、A-2a 開始行が `【見積もり：N分 | …】`。リポジトリは `見積：`。導入先の更新時刻 2026-11-21 16:28、`absolute-rules.md.bak-20261121` が同居。
  - `diff 04_Codex/AGENTS.md.template ~/.claude/AGENTS.md` → 導入先 AGENTS.md も 5〜6 行目・25 行目が `見積もり：`。
  - `03_ClaudeCode/hooks/constitution-gate.py:37` `EST_RE = ^[ \t]*【?見積[:：]…`、`instruction-guard.py:43` `ESTIMATE_RE = 見積[:：]…`、`METER_START_RE` も `見積[:：]`。
  - 実測（python3 -I で EST_RE を当てた）: `見積：5分（16:40）`→True、`見積もり：5分（16:40）`→False、`【見積もり：5分 | 開始:16:35 | 終了:16:40 | タスク数：2】`→False。
  - `diff -q 03_ClaudeCode/hooks/constitution-gate.py ~/.claude/hooks/constitution-gate.py` は差分なし（導入先の hook も同じ正規表現）。
  - 結果: 導入先の規約どおりに書くと「見積欠落」で constitution-gate が全ツール停止に入る。依頼文の「誤判定で停止」と整合するが、その停止の原因がこれだとは未確認。
- 状態: 実証（正規表現の不一致）／停止事例との因果は未確認
- 改善の方向: 書式の真実源を 1 か所（hook の定数）に置き、文書は生成するか、hook 側で `見積(もり)?[:：]` を受ける。導入先と kit の差分を検査する `verify.sh` 項目を足す。

## I7-rules-02 A-2 の「対象外」を hook が判定できず、質問・文書作業でも見積を要求して止める
- 種別: 矛盾
- 深刻度: High
- 根拠: `absolute-rules.md:8` A-2「質問・説明・確認・記録・文書や設定だけの更新は対象外」。一方 `constitution-gate.py:34-36` `CODING_RE` は `テスト|追加|作成|hook|やって|続けて|…|\.(json|html|…)` に一致すれば対象扱い、`READ_FREE = 3`（27 行）。実測: 「テスト戦略について説明して」「settings.json の差分を確認して」「README に1行追加して」「hook が何をするか教えて」「続けて」がすべて True。
- 状態: 実証
- 改善の方向: 対象判定を語彙一致でなく「Edit/Write の対象拡張子」など実行時の行為で行うか、文書の対象範囲を hook の実際に合わせて書き直す。

## I7-rules-03 中間報告の間隔が文書ごとに 4 通り（3 分・60 秒固定・180 秒・見積×60÷5）
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - `CLAUDE.md:14`（hook 無し環境）「無報告 3 分を自分で検知したら…止めて」 vs 同 `CLAUDE.md:5`「見積分数×60÷5 秒」。
  - `INDEX.md:178` constitution-gate の説明「3 分超の無報告」。
  - `06_保守者向け/02_設計判断の根拠/constitution-gate.md:14`「180 秒超」。
  - 導入先 `~/.claude/AGENTS.md`「見積・途中報告の実行ゲート（2026-10-25）」節「60秒経過なら途中報告」 vs 同ファイル 2026-11-14 節「見積分数×60÷5秒」。
  - 実装: `constitution-gate.py:38-41,203` は `max(60, 見積分×60÷5)`、見積が取れなければ 180 秒、`AIDD_REPORT_INTERVAL_SEC` で上書き。
- 状態: 実証（grep と hook 読解）
- 改善の方向: 間隔の定義を A-2a だけに置き、INDEX・CLAUDE.md・根拠文書・AGENTS の旧節は参照に置き換える（下限 60 秒・既定 180 秒も A-2a に明記）。

## I7-rules-04 導入先 AGENTS.md が kit のテンプレートから乖離（kit に無い節が 3 つ・追跡されない hook を参照）
- 種別: 欠陥
- 深刻度: High
- 根拠: `wc -c` テンプレート 17,042 B / 導入先 22,422 B。`diff` で導入先だけにある節: 「速く届ける進め方（2026-11-14）」「2026-10-25 事故の再発防止」「見積・途中報告の実行ゲート（2026-10-25）」、および `依頼: ...` 行・判断の自己決定の 2 行。導入先が名指しする `context-size-guard`・`subagent-budget` は `git ls-files` に無く、`~/.claude/hooks/` にだけ存在。`install.sh:38-43` は再導入時に導入先を `.bak` へ退避してテンプレートで上書きするため、再導入でこれらの規約が消える。
- 状態: 実証
- 改善の方向: 導入先で足した節を kit のテンプレートへ戻す（または導入先専用の追記ファイルに分けて import）、`verify.sh` でテンプレートとの差分を警告する。

## I7-rules-05 委譲の本数「上限 30 本」と「上限は設けない（撤廃）」が同じ導入先 AGENTS.md に併存
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `04_Codex/AGENTS.md.template:25`・`02_共通/rules/model-routing.md:13`・`speed-harness.md:24`「上限 30 本」。導入先 `~/.claude/AGENTS.md`「2026-10-25 事故の再発防止」節「委譲の本数に上限は設けない（2026-10-25 利用者指示で撤廃。hook は記録のみ）」。kit 側に「撤廃」は無い（`grep -n 撤廃` で rules・テンプレートとも該当なし）。
- 状態: 実証
- 改善の方向: 利用者の最新指示に合わせ、rules 2 本とテンプレートの「上限 30 本」を一括で直す。

## I7-rules-06 H-7 は「stash した素の状態で再現」を指示し、AGENTS は `git stash` を禁止
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `02_共通/rules/speed-harness.md:40`「変更を stash した素の状態で同じ失敗が再現したら main 由来と断定」。`04_Codex/AGENTS.md.template:111` 禁止事項「`git stash` / `git checkout --` / `git reset` / `git clean`（他の作業の変更が消える）」。
- 状態: 実証
- 改善の方向: H-7 の切り分け手順を `git worktree add <tmp> origin/main` での再現に置き換える。

## I7-rules-07 報告の長さと構造の規定が 5 通りあり、互いに矛盾
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `absolute-rules.md:15` A-9「既定3行」／`speed-harness.md:5` H-0「結果1行＋依頼1行。見出し・判断軸は求められたときだけ。目安150字」／`AGENTS.md.template:27`「完了報告は3行以内…状況説明・計画は見出し・表（行数制限なし）」／同 `:43`「報告の型（10 行以内）」／同 応答スタイル「提案は推奨＋判断軸＋選択肢比較。判断軸に損益を必ず入れる」（H-0 の「判断軸は求められたときだけ」と衝突）。導入先 `~/.claude/rules/common/core.md`「完了報告は5行以内」。
- 状態: 実証
- 改善の方向: 応答の型を場面別（完了・質問・提案）に 1 表で定義し、他は参照のみにする。

## I7-rules-08 同じ ID「A-n」が別内容で 2 系統に存在（A-3 は正反対）
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `~/.claude/rules/common/core.md` A-3「「残課題」を書かない」 vs `02_共通/rules/absolute-rules.md:9` A-3「`残課題: ...` を1〜3行」。core.md の A-1〜A-10 は kit の A-1〜A-14 と番号が重なるが内容・粒度が違う。core.md は kit に無い（`git grep -n 'rules/common'` 該当なし）ため出所は未確認。両方とも毎セッション読み込まれる（core.md に `paths:` 無し）。
- 状態: 実証（文書の矛盾）／出所は未確認
- 改善の方向: 利用者側の core.md の ID を別接頭辞にするか kit の A 系へ統合する旨を保守者に提案する（kit 外のファイルなので判断は保守者）。

## I7-rules-09 毎回読み込まれる規約が約 26,000 字・56.7 KB、見積の規定だけで 5 か所以上重複
- 種別: 過剰
- 深刻度: Medium
- 根拠: `paths:` 無しで常時載る文書（`~/.claude/CLAUDE.md`・`AGENTS.md`・`rules/aidd-kit/{absolute-rules,model-routing,speed-harness}.md`・`rules/common/*.md`・リポジトリ `CLAUDE.md`）を `wc -m` → 25,973 字、`wc -c` → 56,711 B。最大は導入先 AGENTS.md 10,392 字。`60÷5` の文字列が常時文書に 5 回（`grep -c`）。さらに `prompt-priority.py:69-73` が毎プロンプト同じ書式を注入。トークン数は未計測（字数のみ実測）。
- 状態: 実証（字数）／トークン換算は未確認
- 改善の方向: 見積・計測・報告の規定を A-2/A-2a の 1 か所に寄せ、CLAUDE.md 憲法・AGENTS 2 節・H-0 は 1 行の参照にする。hook 注入と文書の重複も一方に寄せる。

## I7-rules-10 「解除の環境変数は無い」と書くが、報告間隔は環境変数で実質無効化できる
- 種別: 矛盾
- 深刻度: Low
- 根拠: `CLAUDE.md:9`・`INDEX.md:178`「解除の環境変数は無い」。`constitution-gate.py:203` `interval = int(os.environ.get("AIDD_REPORT_INTERVAL_SEC") or …)`。大きな値を入れれば無報告判定は働かない（コード読解。実行はしていない）。
- 状態: 実証（コード読解）
- 改善の方向: 文書に `AIDD_REPORT_INTERVAL_SEC` の存在と用途（試験用）を明記するか、上限値を設ける。

## I7-rules-11 CLAUDE.md テンプレートの「全 19 本」が実数と不一致
- 種別: 欠陥
- 深刻度: Low
- 根拠: `03_ClaudeCode/CLAUDE.md.template:17`「全 19 本は `INDEX.md`」。`ls 03_ClaudeCode/hooks/*.py *.sh`（補助モジュール 2 本を除く）→ 28 本。導入先 `~/.claude/CLAUDE.md` は「全量は `INDEX.md`」に書き換え済みで、テンプレートだけ古い。
- 状態: 実証
- 改善の方向: 本数を書かず「全量は INDEX.md」に揃える。

## I7-rules-12 absolute-rules の表の並びが ID 順でない（A-2a が A-11 の後、A-13 が A-12 の前）
- 種別: 欠陥
- 深刻度: Low
- 根拠: `absolute-rules.md:17-20` の行順 A-11 → A-2a → A-13 → A-12 → A-14。
- 状態: 実証
- 改善の方向: ID 順に並べ替える（参照側の影響なし）。

## I7-rules-13 AGENTS テンプレートの優先節が「同じ書式」を上書き対象として挙げ、意味が取れない
- 種別: 欠陥
- 深刻度: Low
- 根拠: `04_Codex/AGENTS.md.template:5`「A-2・A-2a・H-0 や hook の注入文にある「見積：N分」…より、この節を優先する」と書いた直後の `:6` で同じ「見積：x分（HH:MM）」を定める。上書きの対象と内容が同一で、何が旧規定か読み取れない。
- 状態: 実証
- 改善の方向: 旧規定（時刻無しの `見積：N分`・固定 60 秒等）を具体的に名指しするか、節を A-2a へ統合して削る。

## I7-rules-14 llms.txt は最新だが、INDEX に実在しないスキル名が 1 件
- 種別: 欠陥
- 深刻度: Low
- 根拠: `python3 -I 02_共通/ツール/llms-txt.py --check` → `OK: llms.txt は最新（リンク 90 件）`、ただし「飛ばした（実在するパスに解決できない）: DAILY スキル: handoff」。
- 状態: 実証
- 改善の方向: INDEX の `handoff` 行を削るか実体を足す。`--check` で飛ばした件数を 0 件必須にする。

---

## 調べられなかったこと
- 毎回載る文書のトークン数（字数・バイトのみ実測。トークナイザで数えていない）。
- `prompt-priority.py` など hook が実行時に注入する文字量（実行していない）。
- `~/.claude/rules/common/*.md` の出所（kit 外。`git grep` で該当なし）。
- `02_共通/rules/` のうち `paths:` 付き 7 本の中身の相互矛盾（先頭の frontmatter と grep した語のみ確認。全文は未精読）。
- 依頼文にある停止が I7-rules-01 によるものか（停止ログは制約により読んでいない）。
- 外部の規格・研究・製品文書との照合（本テーマは内部矛盾の洗い出しに限定し、Web 検索は使っていない）。

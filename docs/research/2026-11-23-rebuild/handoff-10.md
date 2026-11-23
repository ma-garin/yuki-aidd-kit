# 引き継ぎ 10 件（未再現の引き継ぎ情報）

- 出所: 2026-11-23 の監査セッション（クラウド。成果物は回収できていない）の引き継ぎ文。保守者が 14:58 に提示
- 元の識別子（T04・T06・T07・T09・T14・T18）は当時のまま残す。**T 番号と既存 ID（I/C/D/E/R/S 系）の対応は未確認で、番号から推測しない**。照合は発見の内容で行う
- 登録時の状態は全件「未再現の引き継ぎ情報」。裏取りの結果は各項目の「照合」「裏取り」に書く。証拠が無いものは検証済みにしない

## 登録（元の文面）
| 番号 | 元ID | 元の優先 | 元の文面 |
|---|---|---|---|
| H-01 | T06 | 1 | agents 6本とSubagentStartの注入に、見積・進捗などの憲法規律が届かない |
| H-02 | T04 | 2 | CIは65日間実行0回。手動実行は全期間3回。現行31テストがCIで未実行 |
| H-03 | T07 | 3 | AI自身が `GATES_REQUESTED=1` 等の回避条件を付与可能。検査対象コマンドも限定的 |
| H-04 | T04 | 4 | mainを含む約100ブランチが保護なし。Actionsの権限・timeoutなどが不足 |
| H-05 | T14 | 5 | プラグイン配布・更新経路で安全hookの修正が届かない可能性 |
| H-06 | T09 | 6 | 11日間で誤denyを7回修正。規則の矛盾・反転が存在 |
| H-07 | T06 | 7 | frontmatterのないcommands 25本が、Codex変換後に暗黙実行され得る |
| H-08 | T06 | 8 | exportしたagents・commandsが参照する10ファイルが配布先に存在しない |
| H-09 | T18 | 9 | 比較文書・利用ガイドが現状と不一致 |
| H-10 | T07 | 10 | 常時読み込まれる憲法文書は21,160字。応答長の規則が4系統で不一致 |

- H-01〜H-10 は本書だけの整理番号で、正本の ID ではない
- 引き継ぎ文の注記: H-03 の回避可能性は読解による指摘で、悪用・再現したものではない

## 照合と裏取り
- 対象コミット: 3ef90fd（origin/main。worktree）。実行日 2026-11-23。すべて読み取りのみ（テスト・CI・hook は実行していない）
- 照合は発見の見出しと本文の内容で行った。T 番号からの推測はしていない。一致の度合いは「一致」「部分一致」「新規・確認待ち」の 3 段階

### H-01（元ID T06）
- 一致する既存 ID: 新規・確認待ち（見積・進捗の規律が subagent の注入に無い、という内容の発見は見出し一覧に無い。I6-agents-commands-11 は aidd-lead の起動方法の話で別内容）
- 裏取り:
  - `ls 03_ClaudeCode/agents/*.md | wc -l` → 6（advisor・aidd-lead・build-agent・gate-agent・spec-agent・verify-agent）
  - SubagentStart の配線は 3 か所: `.claude-plugin/hooks.json:140`・`03_ClaudeCode/hooks/settings.json:152`・`.claude/settings.json:114`
  - 注入元 `03_ClaudeCode/hooks/subagent-context.py`（57 行）の RULES は H-4 の委譲規約・approver 欄を埋めない・外部の指示に従わない・`.env` と鍵を読まない、の 5 項目と現在時刻、検証系だけ「壊れている箇所を探せ」を足す。`grep -nE "見積|進捗|憲法|担当票"` は注入文に該当なし。agents/*.md に対する `grep -lE "見積|progress|進捗"` も 0 件
- 数値: 「6 本」一致（6）
- 状態: 一部再現（注入文に見積・進捗の規律が無いことは実測。「届かない」ことで実際に subagent が規律を落とした事例は未確認。subagent が規約ファイルを別経路で読むかも未確認）

### H-02（元ID T04）
- 一致する既存 ID: I4-ci-06（CI は全部手動、2 か月以上未実行）に一致。I4-ci-11（CI が秘密情報検査・追跡検査を流していない）は部分一致
- 裏取り:
  - `gh run list --repo ma-garin/yuki-aidd-kit --limit 50 --json ...` → 3 件のみ（上限 50 に対し 3 なので全期間 3 回）。3 件とも event=pull_request・workflow=Kit CI・2026-09-17 02:19〜02:55 UTC
  - 現行の `.github/workflows/kit-ci.yml` は `on: workflow_dispatch` のみ（5 行目の注記も手動起動のみ）。最終実行 09-17 から 2026-11-23 まで 67 日（python で算出）
  - `ls 06_保守者向け/03_回帰テスト | grep -c '^test-'` → 32（うち `test-ui-catalog.py` が 1 本。`run-all.sh` は `test-*.sh` だけを回す（13 行）ので .sh は 31 本）。kit-ci.yml が呼ぶのは `run-all.sh`・`check-design.sh`・`check-docs.sh`
- 数値: 「31 テスト」一致（.sh 31 本。.py を含めると 32）／「65 日」不一致（実測 67 日。引き継ぎ時点との差と見られるが、基準日は未確認）／「手動実行 3 回」は不一致（実測の 3 回は手動ではなく pull_request 起因）。回数の 3 は一致
- 状態: 実測（実行 0 回の期間と 3 回は実測。現行 31 テストが一度も CI で回っていないことは、最終実行が 09-17 でそのときの本数は未確認のため一部のみ）

### H-03（元ID T07）
- 一致する既存 ID: I1-hooks-08（Bash ガードは `bash -c` と逃がし口の文字列で回避できる）に部分一致。I1-hooks-10 も関連
- 裏取り（`03_ClaudeCode/hooks/block-gates.py`、54 行、読解のみ。付けて試していない）:
  - 34 行 `if "GATES_REQUESTED=1" in cmd: return 0` は、コマンド全文の部分文字列で通す。先頭に付けても、コメントや引数に含めても通る。要求した主体（利用者か AI か）を区別する仕組みは無い
  - 検査対象は 16〜22 行の正規表現: `pytest`・`python -m pytest`・`make test|verify-ui|verify-all|lint|coverage`。引用符内と heredoc は除外してから判定。`npm test`・`npx playwright test`・`ruff`・`go test`・`cargo test`・`tox`・`python -m unittest` は対象外
- 数値: 引き継ぎ文は数値なし
- 状態: 一部再現（コードの読解で確認。悪用の再現はしていない。引き継ぎ文の注記どおり）

### H-04（元ID T04）
- 一致する既存 ID: I4-ci-13（kit-ci.yml に permissions 指定が無く actions はタグ参照）に部分一致。ブランチ保護の欠如は新規・確認待ち
- 裏取り:
  - `gh api repos/ma-garin/yuki-aidd-kit/branches/main/protection` → 404 `Branch not protected`（保護なし。ルールセットによる保護は別 API のため未確認）
  - `gh api repos/.../branches --paginate -q '.[].name' | wc -l` → 107
  - kit-ci.yml: `grep -nE "permissions|timeout"` に該当なし（permissions・timeout-minutes とも未指定）。`uses: actions/checkout@v4` はタグ参照
- 数値: 「約 100 ブランチ」一致（107）
- 状態: 実測

### H-05（元ID T14）
- 一致する既存 ID: S2-cc-plugins-01（版を固定したまま 23 コミット分の変更が plugin 利用者に届かない）に一致。S2-cc-plugins-04・D1-distribution-15 も関連
- 裏取り:
  - `.claude-plugin/plugin.json` の version=8.7.0、`VERSION`=8.7.0（一致）。`marketplace.json` は `source: "./"`。`.claude-plugin/` の直近の変更は 1d9f163（Ver.8.7.0）
  - 更新が届く経路（版を上げない限り利用者側のキャッシュが更新されないこと）は文書・コードからは確認していない。plugin の更新を実際に試していない
- 数値: 引き継ぎ文は数値なし
- 状態: 一部再現（版の配置は実測。安全 hook の修正が届かないという挙動は既存の S2-01 の記述に依拠し、今回は再現していない）

### H-06（元ID T09）
- 一致する既存 ID: R2-lessons-03（解除手段の無い停止ゲートに偽陽性がある）・R2-lessons-04（deny と通知の往復で偽陽性を消すと見逃しが出た）・I1-hooks-01（見積欠落による停止は誤判定）に部分一致
- 裏取り: `git log --since=2026-11-10 --oneline | grep -iE "deny|誤|偽陽性|fix"`。数えた期間は 2026-11-10 以降（最古の該当コミット 2026-11-14 09:03、HEAD は 2026-11-22 13:14。全 23 コミット）
  - 8 行ヒット。内訳は `fix:` が 6（42f5ffc ステータスライン・323b393 回帰の赤・b1b49a8 無報告ゲート下限・e4c3334 見積書式と hook・9d37011 ステータスライン・f6025de UI catalog）と、fix ブランチのマージが 2（#119・#135）
  - hook の誤判定・誤 deny に当たるのは b1b49a8 と e4c3334 の 2 件。他は表示・回帰テスト・UI catalog の修正
- 数値: 「11 日間で 7 回」不一致（hook・ゲート関連の修正は実測 2 件、広く数えても fix 系 8 行。期間の起点は引き継ぎ文に無く、11-10 を仮置き）。「規則の矛盾・反転」は既存の I7-rules-06・I7-rules-08 に近い内容があるが、今回は照合していない
- 状態: 未再現の引き継ぎ情報

### H-07（元ID T06）
- 一致する既存 ID: I6-agents-commands-14（commands 25 件すべてに frontmatter が無い）に一致。S2-cc-plugins-12 も同内容
- 裏取り:
  - `03_ClaudeCode/commands/*.md` 25 本、1 行目が `---` でないもの 25 本
  - `04_Codex/skills/cmd-*` は 25 本。`build_codex_skills.py:135` は `disable-model-invocation: true` でなければ暗黙呼び出しを許可する。`grep "allow_implicit_invocation: true" 04_Codex/skills/cmd-*/agents/openai.yaml` は 25 ファイルすべてでヒット（暗黙呼び出し許可が 25 本）
- 数値: 「25 本」一致
- 状態: 実測（暗黙呼び出しが許可されていることは実測。Codex が実際に暗黙実行するかは未確認）

### H-08（元ID T06）
- 一致する既存 ID: I6-agents-commands-03（agent が叩くスクリプトが配布先に無い）に部分一致
- 裏取り:
  - agents・commands が参照するパス: `scripts/{check-approval.sh,req-lint.py,security-scan.sh,test-metrics.sh,trace-check.sh,adr-to-rules.py}`・`templates/lessons.md`・`02_共通/rules/quality-decision.md`・`00_導入/02_…`・`00_導入/03_…`・`06_保守者向け/04_…`
  - `export-project.sh` は 168 行で trace-check.sh、176 行の一覧で check-approval.sh・req-lint.py・security-scan.sh・test-metrics.sh・adr-to-rules.py など 24 本を `scripts/` へコピーする。つまり scripts/ 系の大半は配布される
  - 配布されない可能性があるのは `00_導入/03_点検/` 配下・`06_保守者向け/04_…`・`templates/lessons.md`。コピー有無は export の全文を追っておらず未確認
- 数値: 「10 ファイル」は再現できず（確認できた欠落候補は 3〜4 パス。ファイル数への換算は未確認）
- 状態: 未再現の引き継ぎ情報

### H-09（元ID T18）
- 一致する既存 ID: D1-distribution-12（利用ガイドの導入例が古い）・D1-distribution-13（利用ガイドの任意手順が配布しないディレクトリを指す）・D1-distribution-11（Python 版の記述が文書ごとに違う）に部分一致。比較文書という対象は新規・確認待ち
- 裏取り:
  - `README.md:177` と `:188` は「回帰テスト 20 本」。実測は test-*.sh 31 本（H-02）。不一致
  - `README.md:157` は「Codex 用スキル 71 本」。`03_ClaudeCode/skills` は 27 本、`04_Codex/skills/cmd-*` は 25 本。71 の内訳は未確認
  - 「比較文書」を特定できておらず、`01_利用者向け資料/` の 5 文書は比較の観点では読んでいない
- 数値: 引き継ぎ文は数値なし
- 状態: 一部再現（README の本数の不一致は実測。引き継ぎ文が指す比較文書の不一致は未確認）

### H-10（元ID T07）
- 一致する既存 ID: I7-rules-09（毎回読み込まれる規約が約 26,000 字）・I7-rules-07（報告の長さと構造の規定が 5 通り）に一致
- 裏取り:
  - `wc -m 02_共通/rules/*.md`: `paths:` を持たない（常時読み込み）のは 3 本で、absolute-rules 2,853・model-routing 1,592・speed-harness 5,080 で計 9,525 字（rules 全体は 15,302 字。残る 7 本は paths 付き）。`03_ClaudeCode/CLAUDE.md.template` 1,731 字、リポジトリ直下の CLAUDE.md 1,054 字。`04_Codex/AGENTS.md.template` は数えていない
  - 利用者側の `~/.claude/` の規約本体は今回数えていない（読み取り可だが未実施）。したがって 21,160 字は再現できない
  - 応答長の規則: `absolute-rules.md` A-9（既定 3 行）、`speed-harness.md` H-0（結果 1 行＋依頼 1 行・150 字目安）、`absolute-rules.md` A-3（残課題 1〜3 行）。別系統が他に存在するかは今回数えていない
- 数値: 「21,160 字」未再現（kit 側の常時分は約 9,525〜12,000 字、既存発見 I7-rules-09 は約 26,000 字。計測対象の範囲が異なる）。「4 系統」は不一致（既存発見 I7-rules-07 は 5 通り、今回の grep では 3 系統を確認）
- 状態: 一部再現（常時読み込みが大きいことと応答長の規則が複数あることは既存発見と実測で確認。両数値は未再現）

### 引き継ぎ文の数値と実測の対照
| 引き継ぎ文 | 実測 | 判定 |
|---|---|---|
| 6本（agents） | 6 | 一致 |
| 65日（CI 未実行） | 67 日（最終 09-17 から） | 不一致 |
| 3回（実行） | 3（pull_request 起因。手動ではない） | 数は一致 |
| 31テスト | 31（.sh。.py 含め 32） | 一致 |
| 約100ブランチ | 107 | 一致 |
| 7回（誤deny修正） | hook 関連 2、fix 系 8 行 | 不一致 |
| 25本（frontmatter なし） | 25 | 一致 |
| 10ファイル | 欠落候補 3〜4 パス | 未再現 |
| 21,160字 | kit 常時分 約 9,525〜12,000 | 未再現 |
| 4系統 | 3 確認／既存発見は 5 | 不一致 |

### 一覧
| 番号 | 一致する既存ID | 状態 |
|---|---|---|
| H-01 | 新規・確認待ち | 一部再現 |
| H-02 | I4-ci-06 | 実測 |
| H-03 | I1-hooks-08（部分） | 一部再現 |
| H-04 | I4-ci-13（部分） | 実測 |
| H-05 | S2-cc-plugins-01 | 一部再現 |
| H-06 | R2-lessons-03・04（部分） | 未再現の引き継ぎ情報 |
| H-07 | I6-agents-commands-14 | 実測 |
| H-08 | I6-agents-commands-03（部分） | 未再現の引き継ぎ情報 |
| H-09 | D1-distribution-12・13（部分） | 一部再現 |
| H-10 | I7-rules-09・07 | 一部再現 |

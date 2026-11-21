# S3-cc-skills — Claude Code 仕様: skills とキットの SKILL.md の突合

- 対象: `03_ClaudeCode/skills/*/SKILL.md` 27 件（主対象。プラグイン `plugin.json` の `skills` が指す範囲）＋ `04_Codex/skills` 71 件・`04_Codex/native-skills` 1 件（frontmatter の機械検査のみ）。参照ファイル（`references/` 等）と `03_ClaudeCode/commands/` 25 件も関係する範囲で確認
- 調べた件数/全件数: SKILL.md 99/99（frontmatter 機械検査）、うち Claude Code 用 27/27 は本文の参照パス・サイズ・日付も検査。参照ファイルは 100 行超のもの 3/3 を目次の有無で確認
- 調べた方法:
  - 一次資料（取得日 2026-11-21）
    - Claude Code 公式 skills 文書 https://code.claude.com/docs/en/skills（先頭 100,000 字まで。残り約 19,700 字は未読）
    - Agent Skills 仕様 https://agentskills.io/specification
    - Anthropic のスキル作成ベストプラクティス https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
  - 自作の読み取り専用スキャナ（scratchpad の `s3/scan.py`）で全 SKILL.md の frontmatter キー・name の形式・name とディレクトリ名の一致・description の長さ・XML 風タグ・行数・リンク切れを集計
  - grep で本文の参照パス（`02_共通/`・`scripts/`・`references/`・`~/.agents`）、日付、`${CLAUDE_SKILL_DIR}` の使用を確認
  - キットの検査 `02_共通/ツール/skill-lint.py` を読み取り専用で実行（出力: `OK: スキル 27 件・NG=0 WARN=1`）
- 根拠の種別: 本書の「主張」は製品文書（Anthropic / agentskills.io）に基づく。研究論文は使っていない

## 仕様の要点（突合の基準）

| 項目 | 基準 | 出典 |
|---|---|---|
| name | 1〜64 字、`a-z0-9-` のみ、先頭末尾・連続ハイフン不可、親ディレクトリ名と一致 | agentskills.io |
| name（Claude Code） | 省略時はディレクトリ名。禁止は制御文字・`<` `>` など（下線は禁止に含まれない） | code.claude.com |
| description | 1〜1024 字、XML タグ不可、三人称、「何を・いつ」 | agentskills.io / platform best-practices |
| 一覧の上限 | `description`＋`when_to_use` は一覧で 1,536 字で切られる。要点を先頭に置く | code.claude.com |
| allowed-tools | 起動したターンの間だけ、確認なしで使える道具を足す。道具を制限はしない（制限は `disallowed-tools`） | code.claude.com |
| 本文 | SKILL.md は 500 行以内（本文 5,000 トークン未満推奨）。詳細は参照ファイルへ | 3 文書共通 |
| 参照 | スキル直下からの相対パス、深さ 1 段。100 行超の参照ファイルには冒頭に目次 | agentskills.io / best-practices |
| 圧縮後 | 自動圧縮のあとに戻るのは、起動したスキルごとに先頭 5,000 トークンまで（全体で 25,000） | code.claude.com |
| `${CLAUDE_SKILL_DIR}` | SKILL.md のあるディレクトリ。cwd に依存せず同梱スクリプトを指す | code.claude.com |
| commands と skills | commands は skills に統合済み。同名ならスキルが優先 | code.claude.com |

## 発見

### S3-cc-skills-01 SKILL.md 14 件がキットのリポジトリ直下からのパス（`02_共通/…`・`00_導入/…`）を参照し、導入後は解決できない
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - `grep -lE '(0[0-6]_[^ /]+/|\.\./\.\./)' 03_ClaudeCode/skills/*/SKILL.md | wc -l` → 14
  - 例: `design-system/SKILL.md:17` の値の真実源 `02_共通/ひな形/tokens.css`、`:26` の `00_導入/03_点検/check-design.sh`。`done-gate/SKILL.md:16,24`、`dev-lifecycle/SKILL.md:27,91,109`、`e2e-cycle/SKILL.md:8,50,92`、`phase-approval/SKILL.md:90`、`retro/SKILL.md:28,55,56`
  - `grep -c 'CLAUDE_SKILL_DIR\|CLAUDE_PLUGIN_ROOT' */SKILL.md` → 全件 0
  - プラグインは `marketplace.json` の `source: "./"`、`install.sh:47` はスキルだけを `~/.claude/skills/` へコピーする。どちらの導入でも利用者の cwd は利用者のプロジェクトなので、`02_共通/…` は cwd から解決できない
  - 仕様: 参照は「スキル直下からの相対パス」（agentskills.io File references）
- 状態: 実証（参照の存在と変数の不使用）／導入先で実際に読めないことは未確認（実機の導入先で試していない）
- 改善の方向: 必要な資産をスキルの `references/` に同梱するか、`${CLAUDE_SKILL_DIR}`・`${CLAUDE_PLUGIN_ROOT}` を基準にした書き方に揃える

### S3-cc-skills-02 スキルとコマンドの同名 4 件（agent-ready / e2e-cycle / retro / security-audit）で、コマンド側が隠れる
- 種別: 矛盾
- 深刻度: Medium
- 根拠:
  - `comm -12 <(ls commands | sed 's/.md$//') <(ls -d skills/*/)` → `agent-ready`, `e2e-cycle`, `retro`, `security-audit`
  - コマンド側だけに引数の扱いがある（例: `commands/e2e-cycle.md:3`「引数: フェーズ番号 1〜5、または help」、`commands/security-audit.md:3`「quick / diff / full」）
  - 公式文書: スキルと `.claude/commands/` のファイルが同名ならスキルが勝つ。プラグイン内では両方とも `/yuki-aidd-kit:<名前>` になる
- 状態: 主張（解決の規則は文書）＋実証（同名の存在）。プラグイン内の同名でも同じ規則が適用されるかは未確認
- 改善の方向: コマンド側の引数の扱いをスキルへ移して（`argument-hint`・`$ARGUMENTS`）、同名のコマンドを廃止する

### S3-cc-skills-03 `scripts/…` の参照 10 件がスキルのディレクトリに無く、どこを基準にしたパスか本文から分からない
- 種別: 欠陥
- 深刻度: Medium
- 根拠:
  - 本文のコード片にある `scripts|references|assets|templates/…` をスキルのディレクトリ基準で存在確認した結果、無かったもの: `dev-lifecycle → scripts/trace-check.sh`、`done-gate → scripts/baseline.py`、`phase-approval → scripts/check-approval.sh`、`qa-review-standards → templates/test/iso29119-*.md`、`test-automation → scripts/pre-commit-ui-gate.sh, scripts/quality_harness.py`、`test-strategy → scripts/pre-commit, scripts/pre-commit-ui-gate.sh, scripts/quality_harness.py, scripts/ui-hash.py`
  - 実体は `02_共通/ツール/`（`find . -name trace-check.sh …` → `./02_共通/ツール/trace-check.sh` 等）。`export-project.sh` で導入先の `scripts/` に置かれる前提（README:139）
  - Claude Code はスキルの基準ディレクトリを示すため、同じ書き方の `references/…`（スキル基準）と `scripts/…`（導入先のプロジェクト基準）が混ざると読み違えが起きる
- 状態: 実証（スキル基準で存在しないこと）。誤って読んだ事例は未確認
- 改善の方向: 導入先のスクリプトは「プロジェクト直下の `./scripts/…`」と基準を明記し、スキル同梱分は `${CLAUDE_SKILL_DIR}/scripts/…` と書き分ける

### S3-cc-skills-04 work-metering がスクリプトを `~/.agents/skills/…` と `<skill>` プレースホルダで指している
- 種別: 欠陥
- 深刻度: Medium
- 根拠:
  - `work-metering/SKILL.md:57` → `M=~/.agents/skills/work-metering/scripts/metering.py   # kit から配布された場所`
  - `work-metering/SKILL.md:49` → `python3 <skill>/scripts/metering.py factor`
  - プラグイン導入（`~/.claude/plugins/…`）や `install.sh`（`~/.claude/skills/`）では、このパスにファイルが無い場合がある
  - 公式文書: 同梱スクリプトは `${CLAUDE_SKILL_DIR}` で指し、`allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/x.sh *)` にすると確認なしで実行できる
- 状態: 実証（記述）／導入方式ごとのファイル有無は未確認
- 改善の方向: `${CLAUDE_SKILL_DIR}/scripts/metering.py` に置き換え、`allowed-tools` に同じパターンを入れる（Codex 版は別の書き方にする）

### S3-cc-skills-05 キットの skill-lint が name の文字種・XML タグ・予約語を検査しておらず、uiux_review の仕様違反を通している
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - `python3 -I 02_共通/ツール/skill-lint.py` → `WARN S4 design-system … 508 字 > 500` / `OK: スキル 27 件・NG=0 WARN=1`（uiux_review を NG にしていない）
  - `skill-lint.py:5-16` の検査項目は frontmatter の有無・name とディレクトリ名の一致・description の空と 1024 字・未知のキー。文字種（`a-z0-9-`）・連続ハイフン・64 字・`<…>`・`anthropic`/`claude` の予約語は対象外
  - `skill-lint.py:39-43` の KNOWN_KEYS に、公式文書にある `disallowed-tools` が無い（使うと誤って WARN S6 になる）
- 状態: 実証（実行結果とソース）
- 改善の方向: skill-lint に agentskills.io の name 規則・XML タグ・予約語の検査を足し、KNOWN_KEYS を公式の frontmatter 一覧に合わせる

### S3-cc-skills-06 `uiux_review` の name が Agent Skills 仕様に違反（下線）。Claude Code 版・Codex 版の両方
- 種別: 欠陥
- 深刻度: Medium
- 根拠:
  - `03_ClaudeCode/skills/uiux_review/SKILL.md:2` と `04_Codex/skills/uiux_review/SKILL.md:2` → `name: uiux_review`
  - agentskills.io: name は「小文字の英数字とハイフンのみ」。Claude Code の文書は下線を禁止文字に挙げていない（このセッションのスキル一覧に `uiux_review` が出ており、Claude Code では読み込まれている）
  - Codex は Agent Skills 仕様に準拠すると `install.sh:48` のコメントにある
- 状態: 実証（違反）／Codex や仕様準拠の検証器（`skills-ref validate`）で読み込みを拒否されるかは未確認（実行していない）
- 改善の方向: `uiux-review` に改名し、ディレクトリ名と参照（コマンド・AGENTS.md の表・trigger eval）をまとめて直す

### S3-cc-skills-07 personal-pwa の description に XML 風プレースホルダ `<GITHUB_OWNER>` が残っている
- 種別: 欠陥
- 深刻度: Medium
- 根拠:
  - `03_ClaudeCode/skills/personal-pwa/SKILL.md:3`（Codex 版も同じ）「GitHub Pages（<GITHUB_OWNER>）へのデプロイ」
  - ベストプラクティス: description は「XML タグを含めない」。プレースホルダは置き換えられないまま一覧に載り、発火の手がかりにもならない
- 状態: 実証（スキャナで XML フラグ）／Claude Code で読み込みが拒否されないことは、このセッションのスキル一覧に出ていることで確認（`&lt;GITHUB_OWNER&gt;` とエスケープされて表示）。API へのアップロードで拒否されるかは未確認
- 改善の方向: description から `<GITHUB_OWNER>` を除き、導入先固有の値は本文か設定に移す

### S3-cc-skills-08 プラグイン導入と install.sh の両方を案内しており、同じスキルが二重に載る
- 種別: 矛盾
- 深刻度: Medium
- 根拠:
  - `README.md:14-27`: プラグインの導入に続けて「スクリプト一式…まで入れるなら clone して `install.sh`」。`install.sh:47` はスキルを `~/.claude/skills/` にもコピーする
  - 公式文書: プラグインのスキルと手元のスキルは「両方とも読み込まれる」（プラグインは `/plugin-name:skill-name` に名前空間化されるため）
  - 結果として、27 件の description が一覧に 2 回載り（Claude Code 版の合計 6,573 字、スキャナで集計）、同じ用途の候補が 2 つ並ぶ
- 状態: 主張（文書）／二重に載ることの実測は未確認
- 改善の方向: 導入方式を 1 つに寄せるか、install.sh にプラグイン導入済みならスキルのコピーを飛ばす分岐を設ける

### S3-cc-skills-09 長い参照ファイル 3 件に目次が無い（uiux_review の viewpoints.md は 919 行）
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - `uiux_review/references/viewpoints.md` 919 行。1〜19 行目は準拠先の表で、見出し（`## 操作の到達性（13件）` 等）は 20 行目から。目次・節の一覧は無い。SKILL.md:58 は「80観点を使う」と全体を指している
  - `design-system/references/benchmark.md` 166 行、`dev-lifecycle/references/phase-gates.md` 139 行。冒頭 15 行に目次が無い（`head -15 | grep -ciE '目次|contents|^- \['` → 0）
  - ベストプラクティス: 100 行を超える参照ファイルは冒頭に目次を置く。部分読み（`head -100`）で全体が見えなくなるため
- 状態: 実証（行数と冒頭の確認）／部分読みで観点を取りこぼした事例は未確認
- 改善の方向: 各ファイルの冒頭に節の一覧を置く。viewpoints.md は観点群ごとにファイルを分けることも検討する

### S3-cc-skills-10 frontmatter は name / description 以外ほぼ未使用。手動起動・引数・道具の許可・発火範囲を仕様で表していない
- 種別: 機会
- 深刻度: Medium
- 根拠:
  - スキャナの集計: 99 件で `name` 99・`description` 99・`disable-model-invocation` 1（`skill-guide`）。`allowed-tools`・`when_to_use`・`argument-hint`・`paths`・`context`・`disallowed-tools` は 0
  - 該当しそうな例: `e2e-cycle` は「1 回の起動で 1 フェーズ」の手動ワークフローで、フェーズ 5 はコミットまで行うのに自動発火できる（`disable-model-invocation` が無い）。スクリプトを叩くスキル（done-gate・e2e-cycle・retro・work-metering）に `allowed-tools` が無い。種別固有のスキル（single-html-tool・personal-pwa・streamlit-rag-app）は description だけで発火範囲を決めている（`paths` 未使用）
  - 公式文書: `disable-model-invocation` は「手動で `/name` から起動したいワークフロー」向け。`allowed-tools` は確認なしで使える道具の許可（制限ではない）
- 状態: 実証（集計）。各スキルにどの項目が合うかは判断であり、効果は未計測
- 改善の方向: 副作用のある手動ワークフローに `disable-model-invocation`、引数を取るものに `argument-hint`、同梱スクリプトに `allowed-tools` を付ける

### S3-cc-skills-11 本文が長い 4 件は、自動圧縮のあと末尾が落ちる可能性がある
- 種別: 欠陥
- 深刻度: Low
- 根拠:
  - SKILL.md の文字数: `design-system` 8,152 字、`e2e-cycle` 6,550 字、`test-strategy` 6,112 字、`dev-lifecycle` 5,096 字（Python の `len()` で計測）
  - 公式文書: 圧縮のあとに戻るのは各スキルの先頭 5,000 トークンまで（全体で 25,000）。日本語は 1 字あたりのトークン数が大きいので、末尾の節（例: design-system の手順）が戻らない可能性がある
- 状態: 未確認（トークン数は未計測。文字数だけ実測）
- 改善の方向: トークン数を実測し、5,000 トークンを超えるものは常に効かせたい規則を先頭に寄せるか、手順を参照ファイルへ出す

### S3-cc-skills-12 参照ファイル同士が参照し合う（1 段を超える）
- 種別: 欠陥
- 深刻度: Low
- 根拠:
  - `qa-review-standards/references/personas.md:25` → `references/ai-code-review.md`、`qa-review-standards/references/ai-code-review.md:4` → `references/personas.md`（相互参照）
  - `design-system/references/frameworks.md:23` → `references/tokens.md`
  - ベストプラクティス: 参照は SKILL.md から 1 段まで。入れ子の参照は部分読みされやすい
- 状態: 実証（grep）。SKILL.md からも同じファイルを直接参照しているかは未確認
- 改善の方向: SKILL.md から全参照ファイルへ直接リンクし、参照ファイル間のリンクは補足に留める

### S3-cc-skills-13 SKILL.md 5 件に日付つきの経緯が入っている
- 種別: 過剰
- 深刻度: Low
- 根拠: `grep -oE '20[0-9]{2}-[0-9]{2}-[0-9]{2}' */SKILL.md` → advisor（2026-10-12）、work-report-html（2026-10-12）、design-system（2026-11-15 ×4）、work-metering（2026-10-18・10-15・10-10）、test-strategy（2026-08-23）。e2e-cycle:8 にも「（2026-08）」。ベストプラクティスは日付に依存する情報を避け、必要なら「以前のやり方」の節に分けるよう求めている
- 状態: 実証（grep）。日付の箇所が規則として古くなっているかは未確認
- 改善の方向: 経緯は `06_保守者向け/` の根拠文書へ移し、SKILL.md には現在の規則だけを残す

### S3-cc-skills-14 発火の評価（skill_trigger_eval）が 27 件中 4 件をカバーしていない
- 種別: 欠落
- 深刻度: Low
- 根拠: `skill-triggers/` のファイルとスキル一覧の差分 → `security-audit`、`skill-guide`、`work-metering`、`work-report-html` の 4 件にケースが無い（skill-guide は手動起動専用なので「発火しないこと」の確認だけが要る）。`skill_trigger_eval.py:3` の docstring は「20 本のスキル」。ベストプラクティスは 1 スキルあたり 3 件以上の評価を推奨している
- 状態: 実証（ディレクトリの差分）
- 改善の方向: 足りない 4 件に正例・負例のケースを足し、docstring の件数を実数に合わせる

### S3-cc-skills-15 commands 25 件すべてに frontmatter が無い（description・argument-hint が無い）
- 種別: 機会
- 深刻度: Low
- 根拠: 25 件とも 1 行目が `# /…`（`head -n1` を集計 → `25 # /`）。公式文書では commands は skills に統合済みで、description は省略すると本文の最初の行が使われ、引数のヒントは frontmatter の `argument-hint` で出す
- 状態: 実証（集計）
- 改善の方向: 少なくとも `description` と `argument-hint` を付ける。中期的にはスキルへ移す（02 と一緒に）

### S3-cc-skills-16 design-system の description が 508 字で、キット自身の上限 500 字を超えている
- 種別: 過剰
- 深刻度: Low
- 根拠: `skill-lint.py` の出力 `WARN S4 design-system/SKILL.md: description が 508 字 > 500`。仕様の上限（1024 字・一覧 1,536 字）には収まっている
- 状態: 実証（実行結果）
- 改善の方向: 要点を先頭に寄せて 500 字以内に削る

## 違反が無かった項目（確かめた範囲）
- 99 件すべてに frontmatter・name・description がある。description が 1024 字を超えるものは 0（最大 508 字）。一覧の 1,536 字を超えるものは 0
- name とディレクトリ名が違うものは 0
- SKILL.md が 500 行を超えるものは 0（最大は uiux_review の 201 行）
- Markdown リンク（`[..](..)`）の切れは 0（スキャナで確認。コード片の中のパスは 03 で別に確認）

## 調べられなかったこと
- 公式 skills 文書の末尾約 19,700 字（100,000 字目以降）は読んでいない。一覧全体の文字数の上限（スキル一覧の予算）の正確な値は未確認
- 導入先（プラグイン導入・install.sh 導入）で実際にスキルを起動し、参照パスが解決できるか、同名のコマンドとスキルのどちらが動くか、スキルが二重に載るかは試していない（01・02・08 は未確認の部分がある）
- Codex 版 71 件は frontmatter の機械検査だけで、Codex 側の制約（description の上限など）は公式文書を確認していない
- `skills-ref validate` は実行していない（外部ツールを導入・実行しない制約のため）
- SKILL.md のトークン数は計測していない（文字数のみ）

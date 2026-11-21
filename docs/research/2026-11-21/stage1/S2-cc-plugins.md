# S2-cc-plugins — Claude Code 仕様: plugins・marketplace

- 対象: worktree `research-20261121`（origin/main 7e80b79 相当）の `.claude-plugin/`（plugin.json・marketplace.json・hooks.json）と、plugin が配る `03_ClaudeCode/{skills,commands,agents,hooks,output-styles}`
- 調べた方法:
  - 公式文書 3 本を取得（取得日 2026-11-21）: https://code.claude.com/docs/en/plugins-reference（manifest reference）／ https://code.claude.com/docs/en/plugins/components.md ／ https://code.claude.com/docs/en/plugins/loading.md
  - 手元 CLI `claude 2.1.330` で `claude plugin validate .` を実行（読み取りのみ。リポジトリのスクリプトは実行していない）
  - manifest の参照先・hooks.json の 25 スクリプトの実在、`03_ClaudeCode/hooks/settings.json` との差、skill/command/agent の frontmatter・名前衝突・パス参照を grep / python で突合
- 調べた件数/全件数: manifest 3/3、hooks 参照 25/25（実在 25）、skills 27/27、commands 25/25、agents 6/6、output-styles 2/2
- 制約により読まなかったもの: `constitution-gate.py` の本文（読み取りが自動判定で拒否された。適用範囲は未確認）

## 発見

### S2-cc-plugins-01／版を固定したまま 23 コミット分の変更が plugin 利用者に届かない
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - `.claude-plugin/plugin.json:3` `"version": "8.7.0"`。`git log -1 -- .claude-plugin/plugin.json` = 2026-11-10、それ以降の main コミット数 `git log --oneline <that>..HEAD | wc -l` = 23（hook 修正・画面の型 等を含む）
  - 公式: "Setting it pins the plugin to that version until you change it"・"a manifest that pins "version": "1.0.0" keeps every user on the cached copy until its author changes the string, however many commits they push"（manifest reference / loading.md「How Claude Code computes the version」）
  - 公式: 第三者 marketplace の auto-update は既定 off（loading.md「Which marketplaces and plugins auto-update」）
  - `test-plugin-manifest.sh:25` は version＝VERSION の一致だけを見る。VERSION はリリース時のみ上がる（CHANGELOG.md:6「未リリース」節あり）。グローバル CLAUDE.md は「バージョンを上げるのは明示的に頼まれたときだけ」
- 状態: 実証（コミット数）／主張（更新挙動は文書）
- 改善の方向: version を manifest と entry の両方から外してコミット SHA 追従にするか、hook 修正だけでも patch を上げる運用を決め、README に「`/plugin marketplace update` が要る・auto-update は既定 off」を書く

### S2-cc-plugins-02／plugin では憲法・rules（CLAUDE.md と 02_共通/rules）が読み込まれないのに、それを前提とする hook は全部入る
- 種別: 欠落
- 深刻度: High
- 根拠:
  - `claude plugin validate .` 出力: "⚠ root: CLAUDE.md at the plugin root is not loaded as project context. To ship context with your plugin, use a skill"
  - 公式: "Claude Code doesn't load a CLAUDE.md at the plugin root … To include instructions in a plugin, write them as a skill"（components.md）。manifest の Fields 表に rules に当たるキーは無い
  - README.md:22「スクリプト一式（statusline・rules・工程承認の判定スクリプト）まで入れるなら clone して」＝plugin では rules が入らないことは書かれている
  - 一方 hooks.json は `constitution-gate.py pre/stop`・`reply-language.py`（A-2/A-2a の書式を Stop で強制）・`instruction-guard.py` を無条件に登録（hooks.json の PreToolUse 先頭・Stop 先頭）。書式の規約本文（absolute-rules.md）は plugin 利用者に届かない
- 状態: 実証（validate の警告）／未確認（plugin 利用者で実際に deny が起きるかは再現していない。constitution-gate の適用範囲も未確認）
- 改善の方向: 憲法・A-2a の書式を skill（または SessionStart/UserPromptSubmit hook の additionalContext）として同梱し、プロジェクト限定の hook は opt-in（`userConfig` や `.claude/` の印）にする

### S2-cc-plugins-03／plugin と install.sh を両方入れると全 hook が二重に発火する
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - `03_ClaudeCode/hooks/settings.json` と `.claude-plugin/hooks.json` の (event, matcher, script) 集合を python で比較 → 差 0（同じ 29 登録）。前者は `python3 ~/.claude/hooks/<x>.py`、後者は `"${CLAUDE_PLUGIN_ROOT}"/03_ClaudeCode/hooks/<x>.py` でコマンド文字列が異なる
  - install.sh:77-86 が `~/.claude/hooks` へ配置し settings.json を配線、install_guard.py で既存 settings にも merge
  - README.md:15-27 は plugin と clone+install を並べて案内し、両方入れた場合の注意が無い（`grep -n "二重\|plugin.*install.sh"` で該当なし）
  - 同じ skills 27 本も `~/.claude/skills`（素の名前）と plugin（`yuki-aidd-kit:<name>`）の二重に載る
- 状態: 主張（構成からの推論。二重導入状態での実行は再現していない。手元は plugin 未導入: `claude plugin list | grep aidd` 該当なし）
- 改善の方向: install.sh が plugin 導入済みを検知して止まる／hook 側で同一イベントの二重実行を抑止する印を持つ、のどちらかと README への排他の明記

### S2-cc-plugins-04／hooks が `~/.claude/` 配下の install.sh 専用パスに依存している
- 種別: 欠陥
- 深刻度: Medium
- 根拠:
  - `03_ClaudeCode/hooks/block-phase.py:47` `Path.home() / ".claude" / "scripts" / "check_approval.py"` を最後の候補にする（plugin だけの利用者には無い。phase-gate 有効時は deny で止まる: 同 :84-89）
  - `statusline.py:40-46` `~/.claude/statusline.sh`・`~/.claude/.statusline-tokens`
  - `config-snapshot.py:29` `~/.claude/CLAUDE.md`・`~/.claude/settings.json` を監視（plugin 利用者の設定差分を拾うのは意図どおりの可能性あり）
  - 公式: plugin の durable なデータは `${CLAUDE_PLUGIN_DATA}`（components.md）。hooks は `CLAUDE_PLUGIN_ROOT`/`CLAUDE_PLUGIN_DATA` を環境変数で受け取るが、hooks 内で両変数の参照は 0 件（`grep -lE "CLAUDE_PLUGIN_ROOT|CLAUDE_PLUGIN_DATA" 03_ClaudeCode/hooks/*` 該当なし）
- 状態: 実証（grep）
- 改善の方向: 同梱スクリプトは `CLAUDE_PLUGIN_ROOT` 起点で探し、キャッシュ・状態は `CLAUDE_PLUGIN_DATA` を優先、無ければ `~/.claude` に落とす

### S2-cc-plugins-05／規約が指す実行パス（tool-timer.py report・progress.py・metering.py）が plugin では解決できない
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - absolute-rules.md A-2「実測は `hooks/tool-timer.py report` の出力をそのまま貼る」、speed-harness.md H-8「`python3 <hooks>/progress.py start`」
  - `03_ClaudeCode/skills/work-metering/SKILL.md:57` `~/.agents/skills/work-metering/scripts/metering.py`（install.sh の Codex 配置先。plugin では存在しない）
  - 公式: "The variables aren't present in the environment of commands Claude runs through the Bash tool … write the `${...}` reference in the Markdown body instead"（manifest reference「Where each variable resolves」）。skills/commands/agents 本文での `${CLAUDE_PLUGIN_ROOT}` 使用は 0 件（grep 該当なし）
- 状態: 実証（grep）／公式仕様は主張
- 改善の方向: skill 本文を `${CLAUDE_PLUGIN_ROOT}/03_ClaudeCode/...` に書き換えるか、plugin の `bin/` に薄いラッパーを置いて PATH から呼べるようにする

### S2-cc-plugins-06／skill と command に同名が 4 組あり、同じ `/yuki-aidd-kit:<名前>` を取り合う
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `comm -12 <(ls skills) <(ls commands)` → agent-ready・e2e-cycle・retro・security-audit。`claude plugin validate .` の Provides に `skills: yuki-aidd-kit:retro` と `commands: yuki-aidd-kit:retro` が両方出る（他 3 組も同様）。公式は command を旧形式とし "write new ones as skills"（components.md）
- 状態: 実証（validate 出力）／どちらが優先されるかは未確認
- 改善の方向: command 側を skill に統合するか別名にし、test-plugin-manifest.sh に名前衝突の検査を足す

### S2-cc-plugins-07／skills・commands・agents が kit 内相対パス・プロジェクト配布前提のスクリプトを指す
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - SKILL.md 27 本中 14 本が `0[0-6]_…/` の kit 相対パスを含む（例: `02_共通/ひな形/tokens.css` 3 件、`00_導入/03_点検/check-design.sh` 5 件、`00_導入/02_プロジェクト配布/init-lifecycle.sh` 4 件）。plugin 利用時の作業ディレクトリは利用者のプロジェクトで、kit はキャッシュ（`~/.claude/plugins/cache/<mkt>/<plugin>/<version>/`）にあるため相対では解決しない
  - agents/commands が `./scripts/trace-check.sh`・`check-approval.sh`・`test-metrics.sh`・`req-lint.py` 等を指す（aidd-lead.md・gate-agent.md・spec-agent.md・verify-agent.md・lifecycle.md・phase-review.md・trace.md 等）。これらは export-project.sh で配布されるもので plugin では入らない
- 状態: 実証（grep 件数）
- 改善の方向: kit 資産は `${CLAUDE_PLUGIN_ROOT}/02_共通/...` で参照し、プロジェクト配布が要る資産は skill 冒頭に「未配置なら export-project.sh」を明記する

### S2-cc-plugins-08／マーケットプレイスの source "./" でリポジトリ全体（保守者専用 06_ を含む）がキャッシュへ複製される
- 種別: 矛盾
- 深刻度: Low
- 根拠: `marketplace.json` `"source": "./"`。公式: "Every other marketplace plugin: Claude Code copies the plugin into cache/…"（loading.md）。`git ls-files | wc -l` = 617、うち `06_保守者向け` 108 件・8.7M（全体 17M）。README.md:29「06_保守者向け/（保守者専用。配布しない）」
- 状態: 実証（件数・容量）／複製範囲は主張
- 改善の方向: plugin 本体を `03_ClaudeCode/` 等のサブディレクトリに切り出して source をそこにする（hooks の相対参照もそれに合わせる）

### S2-cc-plugins-09／hooks.json を `.claude-plugin/` 内に置いている
- 種別: 欠陥
- 深刻度: Low
- 根拠: 公式 "Put every other plugin file at the plugin root, not inside .claude-plugin/. That includes skills/, commands/, and hooks/"（manifest reference）。現状は `"hooks": "./.claude-plugin/hooks.json"` で明示参照しており、validate は警告を出していない（読み込みは通る）
- 状態: 実証（validate に警告なし）／主張（文書の推奨）
- 改善の方向: 既定位置 `hooks/hooks.json`（plugin ルート直下）へ移し manifest の `hooks` を外す

### S2-cc-plugins-10／plugin 経路が手元・CI で通しで試されていない
- 種別: 欠落
- 深刻度: Medium
- 根拠: 回帰は `06_保守者向け/03_回帰テスト/test-plugin-manifest.sh` の静的検査（JSON・パス実在・version 一致・hooks の実体）のみ。`claude plugin validate` を回す検査は無い（`grep -rn "plugin validate"` は同テストのコメント URL 以外なし）。hooks/settings.json と hooks.json の同期検査も無い（現時点は差 0 を手で確認）。手元環境は plugin 未導入（`ls ~/.claude/plugins/cache` に該当なし）
- 状態: 実証
- 改善の方向: `claude plugin validate --strict`、settings.json⇔hooks.json の集合一致、skill/command 名衝突を test-plugin-manifest.sh に足す

### S2-cc-plugins-11／statusLine・env・effortLevel 等 settings 系は plugin で配れない
- 種別: 欠落
- 深刻度: Low
- 根拠: `03_ClaudeCode/hooks/settings.json` の hooks 以外のキー = effortLevel・autoCompactWindow・bashOutputMaxChars・env・statusLine（python で列挙）。manifest reference の Fields 表にこれらに当たるキーは無い。H-8 の進捗表示は statusline 前提
- 状態: 主張（Fields 表に無いことからの推論。plugin ルートの settings.json の対応キーは未確認）
- 改善の方向: README の plugin 節に「statusline・トークン節約キーは install.sh 側」を明記（README.md:22 は statusline・rules のみ言及）

### S2-cc-plugins-12／command の frontmatter が全件無い
- 種別: 欠落
- 深刻度: Low
- 根拠: commands 25 本で frontmatter キー 0 件（awk 集計）。例 `commands/plan.md:1` が `# /plan — …` で始まる。公式 "Command files take the same frontmatter as skills"（description・argument-hint 等）
- 状態: 実証
- 改善の方向: `description`・`argument-hint` を付ける（`/` 補完と model の発火判断に効く）

### S2-cc-plugins-13／namespacing 後の名前が文書・agent 本文に反映されていない
- 種別: 矛盾
- 深刻度: Low
- 根拠: 公式 "Claude Code namespaces every component under it, so an agent reviewer … appears as deploy-tools:reviewer"。validate 出力でも `yuki-aidd-kit:aidd-lead`・`yuki-aidd-kit:plan`。一方 CLAUDE.md・aidd-lead.md:57（「工程 2・3 → spec-agent」）は素の名前のみ。`grep -rn "yuki-aidd-kit:"` は 0 件。素の `/plan` は Claude Code 組み込みの plan と同名（組み込み側の挙動は未確認）
- 状態: 実証（grep）／委譲の名前解決が失敗するかは未確認
- 改善の方向: plugin 利用時の呼び名（`/yuki-aidd-kit:plan`・`yuki-aidd-kit:spec-agent`）を README と aidd-lead に併記

### S2-cc-plugins-14／（機会）userConfig・engines・bin/・dependencies を使っていない
- 種別: 機会
- 深刻度: Low
- 根拠: manifest reference の Fields: `userConfig`（hook に `CLAUDE_PLUGIN_OPTION_<KEY>` で渡る）、`engines.claude-code`（v2.1.323 以降）、`bin/`（Bash の PATH に載る）。plugin.json はいずれも未使用
- 状態: 主張（文書）
- 改善の方向: 憲法ゲート等の厳しい hook を `userConfig` の boolean で opt-in にし、tool-timer/progress を `bin/` から呼べるようにする。engines は v2.1.75 以前を切る副作用（文書記載）を確認してから

## 問題が無かったもの（確認済み）
- manifest 参照先はすべて実在し `./` 始まり。agents は `.md` ファイル指定（公式: ディレクトリ不可）。`claude plugin validate .` は "Validation passed with warnings"（警告は CLAUDE.md の 1 件と、ディレクトリ掲載用の icon 無し 1 件）
- hooks の command は `"${CLAUDE_PLUGIN_ROOT}"` を二重引用符で囲んでいる（公式の推奨どおり。パスに空白があっても 1 語）
- agents の frontmatter は name/description/tools/model のみで、plugin で無視される `permissionMode`・`hooks`・`mcpServers` は不使用
- `skills` キーは既定 `skills/` に「追加」、`commands`・`agents`・`outputStyles` は「置換」（公式）。既定ディレクトリは存在しないので衝突・警告なし

## 調べられなかったこと
- `constitution-gate.py` の適用範囲（どのプロジェクトで発火するか）。本文の読み取りが自動判定で拒否されたため未確認
- plugin を実際にインストールしての動作（二重発火・名前衝突の優先・agent 間の委譲名解決・組み込み `/plan` との関係）。手元に plugin 未導入で、導入は利用者環境の変更になるため実施していない
- plugin ルートの `settings.json` が受け付けるキーの一覧（今回取得した 3 文書に記載なし）
- `tools: … Task` の現行名（Agent への改名・別名の扱い）
- marketplace reference（https://code.claude.com/docs/en/plugins/marketplace-reference.md）の本文は取得していない（manifest reference 側の記述で足りる範囲だけ使った）

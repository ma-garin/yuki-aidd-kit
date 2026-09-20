# 05 — スクリプト仕様（20件）

すべて引数・出力・終了コードを明記する。**CI からそのまま呼べるもの**は終了コードで判定できる。

---

## 導入・配布（4件）

### `install.sh`（57行）— グローバル導入

```bash
./scripts/install.sh
```

| 配置元 | 配置先 | 既存があるとき |
|---|---|---|
| `CLAUDE.md.template` | `~/.claude/CLAUDE.md` | `CLAUDE.md.bak` に退避して上書き（手動マージ推奨） |
| `skills/*` | `~/.claude/skills/` | 上書き |
| `claude-code/commands/*.md` | `~/.claude/commands/` | 上書き |
| `claude-code/hooks/*.sh,*.py` | `~/.claude/hooks/`（chmod +x） | 上書き |
| `claude-code/hooks/settings.json` | `~/.claude/settings.json` | **上書きせず警告**（手動マージを促す） |
| `rules/*.md` | `~/.claude/rules/aidd-kit/` | **`~/.claude/rules` 配下に同名があればスキップ**（aidd-kit ディレクトリ自身は prune） |
| `VERSION` + commit + 日付 | `~/.claude/KIT_VERSION` | 上書き（S2） |

- `set -e`。Codex 利用者向けに `AGENTS.md.template` → `~/.codex/AGENTS.md` の案内を出力
- 終了コード: 0（失敗時は `set -e` で中断）

### `verify.sh`（50行）— 配置確認

```bash
./scripts/verify.sh
```

- **チェックリストをリポジトリ実体から自動導出**（Roadmap M6 の決定）。資産を追加してもこのファイルの更新は不要
- 確認対象: `~/.claude/CLAUDE.md` / `settings.json` / 各 `skills/<name>/SKILL.md` / 各 `commands/<name>.md` / 各 hook / 各 rule（`~/.claude/rules` 配下を `find -name` で探索）
- 出力: 項目ごとに `✅`/`❌` ＋ 末尾に `結果: OK=n / NG=n`
- **終了コード**: NG=0 → 0 ／ NG>0 → 1（S1 で修正。`test-install.sh` が assert）。導入済み版（`KIT_VERSION`）とリポジトリ版を表示

### `export-project.sh`（201行）— プロジェクト配布

```bash
./scripts/export-project.sh <対象プロジェクトのパス>
```

| 生成物 | 内容 |
|---|---|
| `.claude/skills/` | skills フルコピー（DAILY/LIBRARY の絞り込みは INDEX を見て各エージェントが行う） |
| `.claude/commands/` | 18コマンド |
| `.claude/hooks/` | sh 4 + py 9（chmod +x） |
| `.claude/rules/` | 4本（**`speed-harness.md` の H-2 環境チートシートを埋めること**を出力で促す） |
| `.claude/templates/` | templates 全体（スキル本文から参照されるため同梱） |
| `.claude/INDEX.md` | フルコピーなので地図として同梱 |
| `.claude/KIT_VERSION` | `<VERSION> <commit> <日付>`。配布先がどの版から出たかを判別（S2） |
| `.claude/settings.json` | 相対パス版をヒアドキュメントで生成（block-explore / block-phase / 指示優先 3 hook を含む全 hook） |
| `.codex/hooks.json` | Codex CLI 用（M23）。入出力を照合済みの 5 hook（block-gates / filter-output / floor-guard / prompt-priority / context-guard）だけを配線。既存は `.bak`。初回は Codex の `/hooks` で信頼 |
| `AGENTS.md` / `CLAUDE.md` | template から生成。`sed` で `<YOUR_WORKSPACE>/yuki-aidd-kit/INDEX.md` → `.claude/INDEX.md` に変換 |
| `scripts/trace-check.sh` | 既存があればスキップ |
| `scripts/{quality_harness.py,ui-hash.py,pre-commit-ui-gate.sh}` | 既存があればスキップ。`--json` で `{ok, exit, data, meta, error{type, message, hint, retry_argv}}` を返す（2026-09-20） |

- 既存の `settings.json` / `.codex/hooks.json` / `AGENTS.md` / `CLAUDE.md` は `.bak` に退避
- 完了後に「次にやること」7項目を出力（プレースホルダを埋める／git add & commit（Codex は `/hooks` で信頼）／init-lifecycle／sandbox 設定／init-test-docs／phase-gate）
- **書き出した時点のスナップショット**。本体更新には自動追従しない

### `init-project.sh`（102行）— 新規プロジェクト雛形

```bash
./scripts/init-project.sh <project-name> [pwa|html|streamlit]   # 既定 pwa
```

- `git init` / `.gitignore`（秘密情報・データ・OS/エディタ）/ プロジェクト用 `CLAUDE.md` / `CURRENT_STATE.md`
- 種別別: **pwa** → `docs/manifest.json`（theme_color `#1976D2`・background `#F8F9FA`）＋ `docs/index.html` プレースホルダ ／ **html** → `<NAME>.html` ／ **streamlit** → `requirements.txt` + `app.py`
- SDD 3ファイル（spec.md / plan.md / tasks.md）の空テンプレート
- 次の指示例 `/sdd-start <NAME> - [一文で目的]` を出力

---

## 工程ライフサイクル（2件）

### `init-lifecycle.sh`（78行）

```bash
./scripts/init-lifecycle.sh <対象プロジェクトのパス> [--github]
```

- `templates/lifecycle/*.md` 11本 → `<target>/docs/lifecycle/`。**既存は上書きせずスキップして報告**
- `--github` で追加: `.github/ISSUE_TEMPLATE/`（3本）/ `.github/pull_request_template.md` / `.github/workflows/lifecycle-check.yml` / `scripts/trace-check.sh`
- 出力: `工程文書: 新規 n / スキップ n` ＋ 次にやること3項目
- 終了コード: 0（引数不正は 1）

### `trace-check.sh`（247行）— トレーサビリティの機械検証 ★

```bash
./scripts/trace-check.sh [対象ディレクトリ] [-o 詳細レポート]
# 既定: docs/lifecycle / ./trace-check-report.md
```

**ID 正規表現**: `^(REQ-F|REQ-N|RFD|UAT|OPS|DEF|BD|DD|UT|IT|ST|T)-[0-9]{3}$`

**定義の抽出**（awk）:
- 見出し行の先頭トークン（`### REQ-F-001 ...`）または表の第1セル（`| REQ-F-001 | ... |`）
- **追跡表（`*traceability*`）は定義の場ではなく参照専用**として扱う
- 参照は本文中を `gsub(/[^A-Za-z0-9_-]/, " ")` でトークン化して抽出 → `UAT-001` から `T-001` を誤検出しない

**検査6種別**:

| # | 種別 | 検出内容 | 典型的な原因 |
|---|---|---|---|
| C1 | 重複定義 | 同じ ID が複数ファイルの定義位置に | 工程文書に対応表を複製した |
| C2 | 未定義参照 | 参照されているが定義が無い | 採番ミス／存在しない要件の実装 |
| C3 | 所有ファイル違反 | 所有ファイル以外で定義位置に書かれている | 同上 |
| C4 | 追跡表に未記載 | 定義済み `REQ-*` が追跡表にない | 要件追加時に表を更新していない |
| C5 | カバー漏れ | 必須セルが空欄 / BD 未割当 / REQ-F に UAT 無し / REQ-N に ST 無し | 工程未着手のまま次へ進んだ |
| C6 | 孤立テスト | `UT/IT/ST/UAT` が追跡表から参照されていない | 要件と無関係なテスト／表の更新漏れ |

**所有ファイルの解決**: 接頭辞 → ファイル名パターン（`RFD→rfd` / `REQ-F,REQ-N→requirement` / `BD→basic-design` / `DD→detailed-design` / `T→implementation` / `UT→unit-test` / `IT→integration-test` / `ST→system-test` / `UAT→acceptance` / `OPS→operations`）。`DEF` は検出工程の文書内に置くため所有者を固定しない

**出力は context-compression の3層**: 会話・CI ログには結論（NG 件数）＋根拠（種別ごとの件数・先頭5件）だけ、全件は詳細レポートへ

**終了コード**: NG=0 → 0 ／ NG>0 → **1**（CI でそのまま落とせる）／対象ディレクトリや `.md` が無い場合は **0（スキップ）**（CI を不用意に落とさない）

---

## テスト活動（4件）

### `init-test-docs.sh`（37行）

```bash
./scripts/init-test-docs.sh <対象プロジェクト> [--ci]
```

| 配置先 | 内容 |
|---|---|
| `docs/test/` | TESTING_STRATEGY / DEFINITION_OF_DONE / iso29119-{test-plan,test-design-spec,test-completion-report,incident-report} |
| `docs/` | `system_test_cases.csv` |
| `quality/` | `feature_contracts.yml` |
| `scripts/` | `quality_harness.py` / `ui-hash.py` / `pre-commit-ui-gate.sh`（chmod +x） |
| `docs/quality/evidence/` | 空ディレクトリを作成 |
| `--ci` | `.github/workflows/test-gates.yml` |

既存は上書きせずスキップ。次にやること4項目（プレースホルダ／契約登録と PASS 確認／`.ui-verified` と pre-commit の配線／**ゲートの実行タイミングを CLAUDE.md に1行書く**）を出力

### `quality_harness.py`（204行）— 機能契約ハーネス ★

```bash
python3 scripts/quality_harness.py [--root DIR] [--contract PATH]
# 既定: --root . --contract quality/feature_contracts.yml
```

契約は **JSON 互換 YAML**（`json.loads` で読む）。

**検証8種**:

| # | 検出するもの | 規則 |
|---|---|---|
| 1 | 統制文書の欠落 | `harness.required_docs` が全て存在する |
| 2 | 無効な risk_level / status | `critical/high/medium/low` と `implemented/partial/planned` のみ。**`ui-only` は禁止** |
| 3 | 参照パスの欠落 | `ui_files` / `route_files` / `core_files` が実在する |
| 4 | 実行経路の無い implemented | `implemented` は `route_files` か `core_files` を持つ |
| 5 | 失敗系の無い高リスク機能 | `critical`/`high` は `failure_modes` と `required_tests` が必須 |
| 6 | 存在しないシンボル | `symbols` が `core_files` のいずれかに文字列として現れる |
| 7 | **契約未登録の新モジュール** | `harness.source_roots` 配下の `.py` が、いずれかの契約か `unregistered_allowlist`（理由付き）に現れる |
| 8 | 未実装の利用者経路 | `harness.scan_roots` の `.py/.js/.ts/.html` に `UI only` / `not implemented` / `stub endpoint` 等が無い |

- #7 は **2026-07-19 に「機能を足したが契約に登録し忘れ、ハーネスが素通しで PASS」が実際に起きた**ため追加された
- 除外: `__init__.py` / `__pycache__` / `node_modules`
- 出力: `Functional Integrity Harness: PASS` ＋ `validated_features=n` ／ FAIL 時は `- <error>` を列挙
- **終了コード**: PASS → 0 ／ FAIL → 1

### `ui-hash.py`（66行）

```bash
python3 scripts/ui-hash.py disk     # git 管理対象の UI ファイル全体
python3 scripts/ui-hash.py staged   # git staged の UI ファイル
```

- 対象拡張子 `.html/.js/.css`。除外ディレクトリ `.git venv node_modules output __pycache__ dist test-results`
- 除外接頭辞は環境変数 `UI_HASH_EXCLUDE_PREFIXES`（既定 `docs/`）。**`docs/` 配下は設計モックであり実 UI ではない**
- `git ls-files --cached --others --exclude-standard` を使う（`rglob` だと per-run 生成物が混入し hash が揺れる）
- 出力: sha256 の先頭16桁

### `pre-commit-ui-gate.sh`（63行）— UI 検証マーカー ★

```bash
# <project>/.git/hooks/pre-commit から
bash scripts/pre-commit-ui-gate.sh || exit 1
```

```text
staged に UI ファイルがあるか？（docs/*.html|js|css は除外）
  無い → exit 0
  有る → .rebuild-mode がある？
           有る → [WARN] 刷新モード（理由を表示）＋「未検証であり問題なしではない」→ exit 0
           無い → .ui-verified を検査
                    存在しない            → BLOCKED
                    時刻が古い（既定7200秒）→ BLOCKED
                    UI hash 不一致         → BLOCKED（検証後に UI が変更された）
                    一致                   → [PASS] ＋「ブラウザ目視確認も実施しましたか？」と WARN
```

- マーカーの書式: `<git HEAD hash> <UI hash> <ISO 時刻>` の1行
- 鮮度上限は環境変数 `UI_GATE_MAX_AGE`（既定 7200）
- Python は `<root>/venv/bin/python` があればそれ、無ければ `python3`
- **終了コード**: PASS/WARN → 0 ／ BLOCKED → 1

---

## その他（2件）

### `pre-commit`（21行）— 秘密情報スキャン

- `gitleaks` があれば `gitleaks protect --staged --verbose`
- 無ければ簡易パターン `(api[_-]?key|secret|password|token|AKfycb|sk-[a-zA-Z0-9]{20})` を `git diff --cached` に適用（`localStorage` と `//` を除外）
- 検出時 exit 1（回避は `git commit --no-verify`）

### `audit-app-workspace.sh`（55行）— アプリ群の棚卸し

```bash
./scripts/audit-app-workspace.sh <APP_WORKSPACE>
```

- トップレベルのプロジェクト一覧 / manifest 検索（package.json・pyproject.toml・requirements.txt・playwright.config.*・tsconfig.json・Package.swift・go.mod）/ 拡張子集計（`rg --files` があれば使用、無ければ find フォールバック）/ ECC DAILY のベースライン推奨13件
- `set -euo pipefail`。ディレクトリ不在で exit 1

---

## 文書整合検査（2026-09-17 追加・S5）

### `check-docs.sh` → `check_docs.py`。`--json` で `{ok, exit, data, meta, error{type, message, hint, retry_argv}}` を返す（2026-09-20）

```bash
./scripts/check-docs.sh [--root DIR] [-o REPORT] [--strict] [--skip-tests] [--changed [--base REF] [--only-changed]]
```

| # | 検査 | 内容 | 既定 |
|---|---|---|---|
| 1 | 参照コスト | `INDEX.md` / `README.md` の「`name` … N行」（表・散文）↔ `wc -l` | NG |
| 2 | 掲載漏れ | skills / commands / rules / hooks が INDEX に `` `name` `` で載っているか | NG |
| 3 | ケース数 | `test-*.sh` を実際に実行した PASS+FAIL ↔ README / INDEX / manual の「Nケース」「PASS=N」（言及行から 5 行の窓） | NG |
| 4 | 参照切れ | `` `skills/…` `` 等のキット内パス参照が実在するか。ECC スキル名 15 件と配布先の生成パスは除外。`spec/` は対象外 | NG |
| 5 | frontmatter | `SKILL.md` の `name` ↔ ディレクトリ名、`description` の有無 | NG |
| 6 | 常時読込 | `rules/*.md` で `paths:` frontmatter の無いものの合計 ≦ 100 行 | **WARN**（S7 で NG） |
| 7 | 行数目安 | SKILL ≦ 200 / コマンド ≦ 40 | NG（S13 で昇格） |
| 8 | spec 同期 | `spec/01-inventory.md` の行数 ↔ 実測、実ファイルが目録に載っているか | NG |
| 12 | 変更文書 | `--changed` 時のみ。git 差分（作業ツリー＋index＋未追跡、`--base REF` で REF...HEAD も）で変わった `scripts/` `claude-code/` `skills/` `rules/` `templates/` `github-actions/` を、README・INDEX・docs・spec・雛形・SKILL が言及しているのに同じ差分に無ければ NG。台帳（Roadmap / lessons / AUDIT / spec/01 / 09 / 10）と `test-*.sh` は対象外。SKILL.md はスキル名、曖昧な basename（settings.json 等）は親ディレクトリ付きで探す。`--only-changed` はこれだけを回す（`docs-gate.py` がコミット前に使う） | NG |

- 環境変数 `CHECK_DOCS_TEST_TOTALS="test-hooks.sh=19,…"` でテスト実行を代替（回帰テスト用。この直値も検査 3 が実測と突合する）
- 出力は3層、全件は `check-docs-report.md`（`.gitignore` 済み）。NG>0 で exit 1
- 履歴文書（`docs/Roadmap.md` / `docs/AUDIT-2026-07.md`）は「当時の事実」なので数値の突合対象にしない

## デザイン検査（2026-09-17 追加・S11）

### `check-design.sh` → `check_design.py`。`--json` で `{ok, exit, data, meta, error{type, message, hint, retry_argv}}` を返す（2026-09-20）

```bash
./scripts/check-design.sh [--root DIR] [--tokens FILE] [-o REPORT] [PATH ...]   # PATH 省略時 templates/ui templates/components。--tokens 省略時は templates/tokens.css → .claude/templates/tokens.css
```

| # | 検査 | 内容 | 既定 |
|---|---|---|---|
| 1 | 直値 | 色（`#hex` / `rgb(` / `hsl(`）はどこでも。px は padding / margin / gap / border-radius / font-size / line-height に限る（幅・高さ・ブレークポイントは対象外）。除外: 3px 以下のヘアライン、`var(--x, フォールバック)` の中、行内 `token-exempt` コメント、`tokens.css` 自身、**カスタムプロパティの定義 `--x: 値`**（単一 HTML に貼った tokens.css がこれ） | NG |
| 2 | 未定義トークン | `var(--x)` が `tokens.css` にも自ファイルにも無い | NG |
| 3 | 未使用トークン | `tokens.css` で定義されているが対象のどこからも参照されない | WARN |
| 4 | 外部 CDN | `<link>` / `<script src>` / `@import` / `url()` が `http(s)://` を読む | NG |
| 5 | alert() | `alert(` `confirm(` `prompt(`（`window.` 付き含む）の直接使用。`Feedback.confirm(` と関数定義は対象外 | NG |
| 6 | tokens.css 読込 | `.html` に `tokens.css` の `<link>` も `<style>` 内の `--color-primary:` 定義も無い | NG |

- `.html` は `<style>` / `<script>` ブロックだけを見る。`.js` は自己注入 CSS（テンプレート文字列）を含めて全文。ディレクトリ走査では `.claude` `.git` `node_modules` `dist` `build` を除外（配布先で `.` を渡してもキット雛形を検査しない。F-14）
- 出力は3層、全件は `check-design-report.md`（`.gitignore` 済み）。対象なしは exit 0
- 配布先では `./scripts/check-design.sh static src` のように対象を渡す（`templates/design-system.md` 再現チェックリストの機械判定分）

## スキル発火の機械判定（2026-09-20 追加・M23。F-13）

`scripts/skill-route-check.sh`（本体 `skill_route_check.py`）。ケースは `evals/routing/<skill>.json`（`positive`: 発火すべき依頼文と `top_k`、`negative`: 発火してはいけない依頼文と本来の担当 `owner`）。
依頼文と各 `description` を文字 2/3-gram（日本語）＋単語（英数）の TF-IDF ベクトルにして余弦で順位を出す（決定論的・LLM を呼ばない）。

| # | 検査 | NG 条件 |
|---|---|---|
| 1 | 構造 | ケースファイルが無い／JSON でない／positive < 3／negative < 2／スキルの無いケース |
| 2 | 発火 | positive の依頼文でその skill が `top_k`（既定 3）に入らない |
| 3 | 誤発火 | negative の依頼文でその skill が 1 位、または `owner` がその skill より下・不在 |
| 4 | 衝突 | description 同士の余弦 ≧ 0.75（≧ 0.50 は WARN） |
| 5 | 床 | `--min-rank1 N` で positive の rank-1 率が N% 未満（kit-ci は初回実測の 100） |

- 落ちたときに直すのは依頼文ではなく description（発火語を足す／責務分離の一文を足す）。`--explain "<依頼文>"` で上位 5 件を表示
- exit 0 合格／1 NG／2 判定不能（`skills/` 無し）。`--json` 対応（`error.type` は `routing.failed`）
- 語彙の近似なので意味は判定できない。`/usage` のスキル別観測（B-10）は残す

## 応答の盲検対比評価（2026-09-20 追加・M23）

`scripts/response-eval.sh`（本体 `response_eval.py`）。「規約を変えて応答が良くなったか」を人の印象でなく盲検の判定で決める。出所: i-have-adhd の blind paired eval。

- 入力: A（基準）と B（候補）の system prompt ファイル、`evals/response/cases.jsonl`（依頼文 10 件）、`evals/response/rubric.md`（軸・重み・判定者指示）
- 盲検: 判定者には X / Y の匿名ラベルだけを渡す（条件名・ファイル名・モデル名を渡さない）。X/Y の割当は案件ごとに seed 付き乱数。既定で順序を入れ替えてもう 1 回判定し平均する（`--single-order` で 1 回）
- 採点: 軸ごと 0〜10 × 重み（正確性 35・自律 25・行動可能性 20・安全 10・簡潔 10）= 100 点満点。blocker が付いた応答は 0
- runner: `claude`（`claude -p --setting-sources "" --model <ID> --output-format json --system-prompt-file`。`~/.claude` の hooks / rules を切って比べる system prompt だけを効かせる）か `cmd:<コマンド> {system}`（依頼文は stdin、応答は stdout）。判定者は `--judge-runner`
- 出力: `evals/response/out/`（`plan.json` 割当・`<id>.A.md` `<id>.B.md` 応答・`<id>.judge.<順序>.txt` 判定の入出力・`records.json`・`report.md`）。`score` で集計だけやり直せる
- exit 0: B が A より悪くない（平均が下回らず、B に blocker 無し）／1: B が悪い／2: 判定不能（runner 失敗・判定 JSON が読めない）。`--json` 対応（`response.worse` / `response.undetermined`）
- 未実施: 実 LLM での実行（本セッションに `claude` CLI は無い）。偽 runner の回帰テストで盲検・順序入替・blocker・判定不能の分岐は確認済み

## 回帰テスト（7件・全 green）

| スクリプト | 行 | ケース数 | 2026-09-16 実測 | 特筆 |
|---|---|---|---|---|
| `test-hooks.sh` | 127 | **19** | PASS=19 / FAIL=0 | AUDIT A-01 の再発防止。stdin JSON を実際に流して期待出力を assert |
| `test-trace-check.sh` | 179 | **15** | PASS=15 / FAIL=0 | ケース1 整合／ケース2 NG を仕込む／ケース3 対象なしでスキップ／**ケース4 `init-lifecycle.sh` 直後の雛形が NG=0** |
| `test-quality-harness.sh` | 89 | **11** | PASS=11 / FAIL=0 | 検出9種＋allowlist 動作＋**配布雛形が新規プロジェクトで PASS** |
| `test-install.sh` | 130 | **73** | PASS=73 / FAIL=0 | install / verify / export / init-project / init-test-docs。**HOME を一時ディレクトリに差し替え、実 `~/.claude` には触らない**（冒頭ガード） |
| `test-git-gates.sh` | 124 | **27** | PASS=27 / FAIL=0 | pre-commit（PATH 最小化で簡易パターン経路を強制）/ ui-hash.py / pre-commit-ui-gate.sh の全分岐 |
| `test-check-docs.sh` | 149 | **46** | PASS=46 / FAIL=0 | リポジトリ複製に破壊を仕込んで検出を確認。**リポジトリ自身が NG=0 で通ること**を含む |
| `test-skill-route-check.sh` | 112 | **20** | PASS=20 / FAIL=0 | キットの skills/ と evals/routing/ の複製を壊して 5 検査の検出を確認。リポジトリ自身が NG=0 で通ること・`--explain`・`--json`・skills 無し exit 2 |
| `test-response-eval.sh` | 129 | **27** | PASS=27 / FAIL=0 | 偽 runner（応答は system prompt で分岐・判定者は GOOD を含む側を高く採点）。validate の壊し方 4 種・盲検（判定者の stdin に条件名が無い）・順序入替 20 回／`--single-order` 10 回・負け・blocker・同点・判定不能・runner 失敗・seed 再現・score |
| `test-check-design.sh` | 143 | **43** | PASS=43 / FAIL=0 | 出荷物（ui/ + components/）が NG=0 ／ 色・px 直値と除外規則 ／ 未定義・未使用トークン ／ CDN ／ alert() ／ tokens.css 読込 ／ 対象なし・複数パス ／ **配布先の形（.claude/templates/tokens.css 自動検出・.claude/ 不走査・貼り込んだ定義行）** |

**「配布する雛形が最初から NG=0 / PASS で始まること」をテストに含めている**のが両者の共通設計。
雛形が NG を出すと利用者が検査結果そのものを無視するようになる、という理由が明記されている。

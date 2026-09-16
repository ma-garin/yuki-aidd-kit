# 05 — スクリプト仕様（15件・1,501行）

すべて引数・出力・終了コードを明記する。**CI からそのまま呼べるもの**は終了コードで判定できる。

---

## 導入・配布（4件）

### `install.sh`（52行）— グローバル導入

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

- `set -e`。Codex 利用者向けに `AGENTS.md.template` → `~/.codex/AGENTS.md` の案内を出力
- 終了コード: 0（失敗時は `set -e` で中断）

### `verify.sh`（48行）— 配置確認

```bash
./scripts/verify.sh
```

- **チェックリストをリポジトリ実体から自動導出**（Roadmap M6 の決定）。資産を追加してもこのファイルの更新は不要
- 確認対象: `~/.claude/CLAUDE.md` / `settings.json` / 各 `skills/<name>/SKILL.md` / 各 `commands/<name>.md` / 各 hook / 各 rule（`~/.claude/rules` 配下を `find -name` で探索）
- 出力: 項目ごとに `✅`/`❌` ＋ 末尾に `結果: OK=n / NG=n`
- **終了コードは常に 0**（NG があってもメッセージのみ）← CI から使うには要改修（`spec/10-backlog.md` B-02）

### `export-project.sh`（133行）— プロジェクト配布

```bash
./scripts/export-project.sh <対象プロジェクトのパス>
```

| 生成物 | 内容 |
|---|---|
| `.claude/skills/` | skills フルコピー（DAILY/LIBRARY の絞り込みは INDEX を見て各エージェントが行う） |
| `.claude/commands/` | 16コマンド |
| `.claude/hooks/` | sh 4 + py 3（chmod +x） |
| `.claude/rules/` | 3本（**`speed-harness.md` の H-2 環境チートシートを埋めること**を出力で促す） |
| `.claude/templates/` | templates 全体（スキル本文から参照されるため同梱） |
| `.claude/INDEX.md` | フルコピーなので地図として同梱 |
| `.claude/settings.json` | 相対パス版をヒアドキュメントで生成。**block-explore の配線は含まない** |
| `AGENTS.md` / `CLAUDE.md` | template から生成。`sed` で `<YOUR_WORKSPACE>/yuki-aidd-kit/INDEX.md` → `.claude/INDEX.md` に変換 |
| `scripts/trace-check.sh` | 既存があればスキップ |
| `scripts/{quality_harness.py,ui-hash.py,pre-commit-ui-gate.sh}` | 既存があればスキップ |

- 既存の `settings.json` / `AGENTS.md` / `CLAUDE.md` は `.bak` に退避
- 完了後に「次にやること」6項目を出力（プレースホルダを埋める／git add & commit／init-lifecycle／sandbox 設定／init-test-docs）
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

## 回帰テスト（3件・全 green）

| スクリプト | 行 | ケース数 | 2026-09-16 実測 | 特筆 |
|---|---|---|---|---|
| `test-hooks.sh` | 127 | **19** | PASS=19 / FAIL=0 | AUDIT A-01 の再発防止。stdin JSON を実際に流して期待出力を assert |
| `test-trace-check.sh` | 179 | **15** | PASS=15 / FAIL=0 | ケース1 整合／ケース2 NG を仕込む／ケース3 対象なしでスキップ／**ケース4 `init-lifecycle.sh` 直後の雛形が NG=0** |
| `test-quality-harness.sh` | 89 | **11** | PASS=11 / FAIL=0 | 検出9種＋allowlist 動作＋**配布雛形が新規プロジェクトで PASS** |

**「配布する雛形が最初から NG=0 / PASS で始まること」をテストに含めている**のが両者の共通設計。
雛形が NG を出すと利用者が検査結果そのものを無視するようになる、という理由が明記されている。

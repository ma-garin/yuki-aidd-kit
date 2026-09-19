# 02 — アーキテクチャ（読み込み経路・真実源・発火機構・依存）

## 1. エージェントへの供給経路

```text
                    ┌──────────────── グローバル導入（install.sh）────────────────┐
                    │  ~/.claude/CLAUDE.md          ← CLAUDE.md.template（@AGENTS.md）│
                    │  ~/.claude/AGENTS.md          ← AGENTS.md.template（共通規約の本体）│
                    │  ~/.claude/rules/aidd-kit/*   ← rules/（常時読み込み）       │
                    │  ~/.claude/skills/<name>/     ← skills/                     │
                    │  ~/.claude/commands/*.md      ← claude-code/commands/       │
                    │  ~/.claude/hooks/*.sh|*.py    ← claude-code/hooks/          │
                    │  ~/.claude/settings.json      ← hooks/settings.json         │
                    └──────────────────────────────────────────────────────────────┘

                    ┌──────────── プロジェクト配布（export-project.sh）────────────┐
                    │  <target>/CLAUDE.md, AGENTS.md  ← template（INDEX 参照を相対化）│
                    │  <target>/.claude/rules/*       ← rules/                      │
                    │  <target>/.claude/skills/       ← skills/（フルコピー）         │
                    │  <target>/.claude/commands/     ← commands/                    │
                    │  <target>/.claude/hooks/        ← hooks/                       │
                    │  <target>/.claude/templates/    ← templates/（スキルが参照する）│
                    │  <target>/.claude/INDEX.md      ← INDEX.md                     │
                    │  <target>/.claude/settings.json ← 相対パス版をヒアドキュメント生成 │
                    │  <target>/scripts/{trace-check.sh,quality_harness.py,          │
                    │                    ui-hash.py,pre-commit-ui-gate.sh}           │
                    └──────────────────────────────────────────────────────────────┘
```

### セッション内の読み込み順（設計意図）

```text
1. rules/*.md（paths 無し）  常時（毎セッション自動）      — absolute / speed / model-routing。読まない選択肢が無い層
2. CLAUDE.md → @AGENTS.md    常時                          — 共通規約 ＋ Claude Code 固有。「読む範囲」表がここにある
3. rules/functional-integrity（paths 付き） コード/UI を触ったとき — 完了条件の実行経路
4. DAILY / LIBRARY スキル     表の該当行 or description で発火 — 進め方・種別の規約
5. references/               該当スキルの中で必要時         — 詳細層
6. INDEX.md                  表に無い・迷ったときだけ       — 全資産の地図（M16 で毎回読むのをやめた）
```

`INDEX.md` の**参照コスト（行数）**は、6 で開くかどうかを数値で判断させるため。M16 前は「セッション開始時に INDEX を読む」設計だったが、推定 4,456 トークンを毎回払っていたので `AGENTS.md` の表に置き換えた（`spec/11` D-1）。

---

## 2. 真実源マップ（重複を作らないための一覧）

| 情報 | 唯一の真実源 | 参照する側（値を再定義してはいけない） |
|---|---|---|
| 色・書体・余白・角丸・影・動き | `skills/design-system/SKILL.md` | `templates/tokens.css`（実物）/ `templates/design-system.md` / `single-html-tool` / `new-pwa` / `streamlit-rag-app` |
| フレームワーク別の当て方 | `skills/design-system/references/frameworks.md` | — |
| ECC のプロジェクト別 DAILY/LIBRARY | `docs/ECC-ASSET-MAP.md` | `skills/ecc-daily-router`（手順のみ保持）/ `INDEX.md`（参照1行）/ `manual.html`（例示と明記） |
| 非機能の既定値 | `skills/nfr-standards/SKILL.md` | `templates/lifecycle/01-requirements.md` / `07-system-test.md` / `dev-lifecycle` |
| severity / ツアー / 25010 | `skills/qa-review-standards/SKILL.md` | `dev-lifecycle/references/*` / `test-strategy` / `templates/test/*` / GitHub 欠陥テンプレート |
| テストレベルの**設計観点** | `skills/dev-lifecycle/references/test-levels.md` | `test-strategy`（明示的に「複製しない」と記載） |
| テストレベルの**ゲート基準・実行タイミング** | `skills/test-strategy/SKILL.md` | `done-gate` / `test-automation` / `templates/test/TESTING_STRATEGY.md` |
| 要件→設計→テストの対応 | 各プロジェクトの `docs/lifecycle/traceability-matrix.md` | 工程文書（参照のみ・対応表を複製しない） |
| ID 体系 | `skills/dev-lifecycle/references/traceability.md` | `trace-check.sh` の実装・`templates/lifecycle/*` |
| 工程の入口/出口基準 | `skills/dev-lifecycle/references/phase-gates.md` | `done-gate` / `/lifecycle` / PR テンプレート |
| 機能契約の項目定義 | `skills/test-strategy/references/feature-contracts.md` | `quality_harness.py` / `templates/test/feature_contracts.yml` |
| `.ui-verified` の仕様 | `skills/test-strategy/references/ui-verified-gate.md` | `pre-commit-ui-gate.sh` / `ui-hash.py` / `done-gate` |
| 速度の規律 | `rules/speed-harness.md` | `CLAUDE.md.template` / `AGENTS.md.template` / `OPERATING-MODE.md` / `docs-gate.py`（H-7 の文書更新確認を commit 前に強制） |
| キット自体の要求 | `docs/PRD.md` | `docs/Roadmap.md`（各項目の完了条件） |
| **現況の事実・残課題** | `spec/`（本ディレクトリ） | — |

### 過去に重複して是正された例（AUDIT-2026-07）

| ID | 重複 | 是正 |
|---|---|---|
| D-01 | ECC プリセットが `ecc-daily-router` と `ECC-ASSET-MAP` に全文重複、かつ既に食い違っていた | MAP へ一本化（A-03） |
| D-02 | MD3 配色が design-system / single-html-tool / streamlit-rag-app / new-pwa に再掲 | `templates/design-system.md` は値を再定義せず参照する形式で新設 |
| D-04 | 折りたたみ端末の幅基準が 344px と 360×820 で分裂 | 360×820 / 768×1812 に統一（A-02） |

**この「重複は必ず食い違う」という実績が、真実源マップを維持する根拠。**

---

## 3. 発火機構（3系統）

| 系統 | 仕組み | 制御点 |
|---|---|---|
| **暗黙発火** | `SKILL.md` frontmatter の `description` に「〜への言及があれば必ずこのスキルを使うこと」形式で発火語を列挙 | 発火しなかったスキルは `retro` で description に言い回しを追加する（`skills/retro/SKILL.md`） |
| **明示呼び出し** | `claude-code/commands/<name>.md` → `/<name>` | コストは呼んだ時だけ発生（INDEX の設計） |
| **強制（hook）** | `settings.json` の PreToolUse / PostToolUse / Stop / statusLine | 唯一 AI の意思で回避できない層。`block-explore.sh`（exit 2）と `block-gates.py`（deny JSON）が実際にブロックする |

### description の書式パターン（20スキル共通）

```text
<何をするスキルか>。<いつ使うか（場面の列挙）>。
「<発火語1>」「<発火語2>」…への言及があれば必ずこのスキルを使うこと。
<対になるスキルとの責務分離>。
```

最後の「責務分離」文が、スキル間の誤発火を減らしている（例: `test-automation` は
「`agent-eval` が AI の出力品質、こちらはコードが動くか」と自ら書く）。

---

## 4. スキル間の依存・委譲グラフ

```text
                       rules/absolute-rules ─ rules/speed-harness ─ rules/functional-integrity
                                          （全スキルの下敷き・常時）
                                                    │
        ┌───────────────────────────────────────────┼───────────────────────────────────┐
        │                                           │                                   │
   進め方の選択                                 実装・検証                          記録・改善
        │                                           │                                   │
  ecc-daily-router                            test-strategy ──┬── test-automation    retro
        │  └→ docs/ECC-ASSET-MAP.md                  │         ├── e2e-cycle           └→ templates/lessons.md
        │                                            │         └── dev-lifecycle/refs/test-levels
  dev-lifecycle ◄──入れ子── sdd-ecc-workflow         │
   ├→ refs/phase-gates                         uiux_review ── atarimae-quality-audit
   ├→ refs/traceability → scripts/trace-check.sh      │              └→ scan.sh
   ├→ refs/test-levels                          design-system ─┬→ templates/tokens.css
   └→ templates/lifecycle/                            │        ├→ refs/frameworks.md
                                                      │        └→ templates/components/
  context-compression（全工程のトークン規律）           │
                                                 nfr-standards / qa-review-standards
                                                      │
                                                 done-gate（最終ゲート・全てを参照）
```

### 委譲の明文化（各スキルが「他スキルへの委譲」表を持つ）

- `dev-lifecycle` → nfr-standards / qa-review-standards / test-automation / done-gate / sdd-ecc-workflow / design-system / retro
- `test-strategy` → test-automation / e2e-cycle / dev-lifecycle(test-levels) / qa-review-standards / done-gate / functional-integrity / nfr-standards
- `design-system/references/frameworks.md` → ECC frontend-patterns / react-patterns / vite-patterns、第三者製 `frontend-design` `ckm:design`、`uiux_review`
- `atarimae-quality-audit` → qa-review-standards（何を欠陥とみなすか）/ test-automation（固定）/ done-gate（判定）

---

## 5. 実装モードの状態機械

```text
          ┌─────────────── 探索許可（既定）───────────────┐
          │  .claude/mode が無い                          │
          │  Read / Grep / Glob = 許可                    │
          └───────────────┬───────────────────────────────┘
                          │ /implement
                          │   ├ PLAN.md の存在を確認
                          │   ├ 無ければ「plan が未作成です」で中断（mode は作らない）
                          │   └ 有れば mkdir -p .claude && echo implement > .claude/mode
                          ▼
          ┌─────────────── 実装モード ────────────────────┐
          │  .claude/mode が存在                          │
          │  block-explore.sh が Read/Grep/Glob を exit 2 │
          │  行動規範 = templates/implement-profile.md    │
          └───────────────┬───────────────────────────────┘
                          │ /plan（rm -f .claude/mode）
                          ▼
                   探索許可へ戻る
```

**注意点**: `export-project.sh` が生成する `.claude/settings.json` には
`block-explore.sh` の PreToolUse(Read|Grep|Glob) 配線が**含まれていない**。
配布先で `/implement` を使う場合は手で追記する必要がある（`spec/09-findings.md` F-08）。

---

## 6. 進捗表示の配線

```text
bash コマンドに連結（専用の往復を作らない）
  python3 <hooks>/progress.py start "<タスク名>" <見積秒>   → .claude/progress.json を作成
  python3 <hooks>/progress.py step  "<n/m 名称>"            → step と updated を更新
  python3 <hooks>/progress.py done                          → ファイルを削除
                    │
                    ▼
settings.json の statusLine → statusline.py
  progress.json あり: "⏱ <task> [<step>] <経過>/<見積> 残り <r>" ＋ " ｜ " ＋ 従来表示
  progress.json 無し: 従来表示のみ（~/.claude/statusline.sh、無ければ cwd のベース名）
  壊れた JSON: 例外を握って従来表示のみ（表示を落とさない）
```

規律は `rules/speed-harness.md` H-8。**done の呼び忘れは偽の「実行中」表示になる**ため必ず連結する。

---

## 7. 機械ゲートの実行ポイント

| ゲート | 実行される瞬間 | 実装 | 失敗時 |
|---|---|---|---|
| 探索ブロック | Read/Grep/Glob 呼び出し前 | `block-explore.sh` | exit 2（Claude にフィードバック） |
| ゲートの無断実行 | Bash 呼び出し前 | `block-gates.py` | `permissionDecision: deny` |
| 秘密情報 | `git commit` | `scripts/pre-commit` | exit 1 |
| UI 検証マーカー | `git commit`（UI ファイル staged 時） | `pre-commit-ui-gate.sh` + `ui-hash.py` | exit 1（BLOCKED） |
| 機能契約 | マイルストーン / CI | `quality_harness.py` | exit 1 |
| トレーサビリティ | マイルストーン / PR | `trace-check.sh` | exit 1 |
| 書き込み警告 | Write/Edit 前後 | `pre-write-check.sh` / `post-write-html.sh` | exit 0（警告のみ） |
| セッション終了 | Stop | `session-summary.sh` | exit 0（通知のみ） |

詳細は `spec/08-quality-gates.md`。

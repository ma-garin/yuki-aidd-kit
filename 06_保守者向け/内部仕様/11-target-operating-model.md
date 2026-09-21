# 11 — 移行先の運用条件（2026-10〜）と設計含意

**このファイルがキットの「なぜ」の最上位。** `05_プロジェクト管理/構想.md` は目的を述べるが、
その目的が満たされるべき**運用条件**はここにある。設計判断に迷ったらここへ戻る。

---

## 1. 決定事項（保守者・2026-09-17）

| 項目 | 現在（〜2026-09） | 移行後（2026-10〜） |
|---|---|---|
| プラン | Claude Max 5x | **Claude Pro** |
| 基盤モデル | Opus | **Sonnet**（`claude-sonnet-5`） |
| 使うツール | Claude Code 中心 | **Claude Code ＋ Codex の併用** |

**キットの存在理由は「この条件下でも開発がスムーズに回ること」。**
以後、キットへの変更はこの条件に寄与するかで採否を決める（`05_プロジェクト管理/構想.md` の価値判定基準を、この条件で具体化したもの）。

---

## 2. 一次情報（2026-09-17 取得。記憶で書かない）

出典: `https://code.claude.com/docs/en/costs`, `https://code.claude.com/docs/en/memory`, bundled skill `claude-api`。

### 使用量の上限

- サブスクの上限は **5時間のローリング窓＋週次窓**で、**全モデル共有**。この窓に当たると `/model` でモデルを変えても回復しない
- 一方、**モデル系列別**の上限（「Opus 上限」「Sonnet 上限」）に当たった場合は、`/model` で別系列に切り替えれば作業を続けられる
- **Pro の具体的な数値は未確認**（docs は `claude.com/pricing` を指す）。数値に依存する設計はしない
- 上限超過後も続けたい場合は usage credits（`/usage-credits`）。Pro/Max は月次の支出上限を自分で設定できる

### プロンプトキャッシュ

- **サブスクのキャッシュ寿命は1時間**。usage credits を使い始めると5分に落ちる（API キー・クラウド経由も既定5分）
- キャッシュ寿命を超えて再開した最初の1通は**全コンテキストを再処理する**
- 「長いセッションを開きっぱなし」は、一言の質問でも会話全体分の使用量を引く

### 何が自動で読み込まれるか（`memory` docs）

| 場所 | 読み込み |
|---|---|
| `~/.claude/CLAUDE.md`（ユーザー） | **毎セッション** |
| `./CLAUDE.md` / `./.claude/CLAUDE.md`（プロジェクト） | **毎セッション** |
| `~/.claude/rules/*.md`・`.claude/rules/*.md` で **`paths` frontmatter が無いもの** | **毎セッション**（`.claude/CLAUDE.md` と同じ優先度） |
| 同・**`paths` frontmatter があるもの** | **該当パターンのファイルを読んだときだけ** |
| `skills/*/SKILL.md` | 呼び出し時 or モデルが関連と判断したとき |
| `AGENTS.md` | **読まれない**（下記） |

- 公式ガイダンス: **1 CLAUDE.md あたり 200行未満を目標**。「長いファイルはコンテキストを消費し、**追従性を下げる**」
- 「常時コンテキストに要らないタスク固有の指示は rules でなく skills にする」と明記されている
- `@path` import は**起動時に展開される**ので、分割しても常時コストは減らない（整理のためのもの）
- CLAUDE.md は**システムプロンプトではなくユーザーメッセージとして**届く。厳密な遵守は保証されない。必ず実行させたいものは **hook** にする

### `AGENTS.md` の扱い（キットの二重管理を消せる）

> Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If your repository already uses `AGENTS.md` for other coding agents, create a `CLAUDE.md` that imports it so both tools read the same instructions without duplicating them.

```markdown
@AGENTS.md

## Claude Code
<Claude Code 固有の追記のみ>
```

### 測定手段（キットに欠けているもの）

| コマンド | 得られるもの |
|---|---|
| `/context` | **実際にロードされた**メモリファイルの一覧と、コンテキストの内訳 |
| `/usage` | プラン使用量バー。**スキル・サブエージェント・プラグイン・MCP サーバー別の消費内訳**、「長コンテキスト」「キャッシュミス」が10%以上を占める場合のフラグ、キャッシュヒット率 |
| `/insights` | 直近セッションの分析 HTML レポート |
| `/doctor` | チェックインされた CLAUDE.md の削減案を提示 |
| `InstructionsLoaded` hook | どの指示ファイルがいつ・なぜロードされたかのログ |

### 公式のトークン削減策（キットとの対応）

| 公式の策 | キットの現状 |
|---|---|
| タスク間で `/clear` | `03_ClaudeCode/CLAUDE.md.template` `model-routing` に明記。**55 分超の再開と 4 MB 超は `context-guard.py` が警告する**（M19） |
| **CLAUDE.md から skills へ移す**（skills は on-demand） | 方向は合っている。ただし `rules/` が常時4,500トークン |
| MCP より CLI ツールを使う | `03_ClaudeCode/CLAUDE.md.template` に明記。`token-audit.sh` が MCP 数 > 3 で WARN（M19） |
| **hook で前処理してから Claude に渡す**（テスト出力を grep で絞る等） | **実装済み（M19）**: `filter-output.py`（テスト・install・build・git log/diff）・`pre-read-guard.py`（Read の切り詰め・deny）。既定 ON、`FULL_OUTPUT=1` で全量 |
| skill にドメイン知識を置き探索させない | まさにキットの設計 |
| サブエージェントに冗長な処理を隔離 | `speed-harness` H-4 にあるが、Pro では委譲自体が高コスト |
| `/effort` で effort を下げる | `effortLevel: high` を settings で固定（M19、Q-12）。上げる場面は `model-routing` |
| 具体的なプロンプト／plan mode／早期の軌道修正 | `speed-harness` H-1・H-3 が近い |
| Agent teams は通常の約7倍のトークン | `model-routing`「Agent teams は使わない」。3 役レビューも順次（Q-11） |

### Sonnet 5 の API 上の性質（bundled skill `claude-api`）

- `claude-sonnet-5` / コンテキスト 1M / $2・$10 per MTok（Opus 5 は $5・$25）
- thinking は `{type:"adaptive"}` のみが on。`budget_tokens` は 400 で拒否される（`MAX_THINKING_TOKENS` は効かない）
- effort は `low`〜`max`。**Claude Code の既定は `xhigh`**
- **mid-conversation system messages に非対応**（Opus 5 系は対応）
- assistant prefill 非対応
- 公式の指針: 「Sonnet はほとんどのコーディング作業をうまくこなし Opus より安い。Opus は複雑な設計判断と多段推論に取っておく」

---

## 3. 設計含意（この条件下で何が変わるか）

### D-1. トークンの床が「気にすること」から「設計対象」になる

実測（2026-09-17）:

| 層 | chars | 推定トークン |
|---|---|---|
| `rules/` 3本（`paths` 無し＝常時） | 6,493 | ~4,521 |
| `CLAUDE.md`（68行） | 6,147 B | ~1,960 |
| `INDEX.md`（CLAUDE.md の指示で毎回読む） | 8,903 | ~4,330 |
| **セッション開始の床** | | **~10,810** |

推定は「日本語 1.0 tok/char・ASCII 0.27 tok/char」の粗い換算。**`/context` での実測に置き換えること**（`06_保守者向け/内部仕様/10-backlog.md` B-10）。

**M16 後（2026-09-17）**:

| 層 | chars | 推定トークン | 備考 |
|---|---|---|---|
| `rules/` `paths` 無し（absolute 19行 + speed 51行 + model-routing 14行） | ~4,300 | **~2,900** | 根拠は `06_保守者向け/設計判断の根拠/` へ退避 |
| `CLAUDE.md`（21行）＋ `@AGENTS.md`（74行） | 4,012 | ~2,518 | 二重管理を廃止。「読む範囲」表を内包 |
| **セッション開始の床** | | **~5,400**（−50%） | |
| `functional-integrity`（`paths` 付き） | 955 | ~523 | コード/UI を触ったときだけ |
| `INDEX.md` | 9,165 | ~4,456 | **毎回は読まない**（表に無いときだけ） |

実トークンは保守者の `/context` で U-2 として記録する。M19 以降は `log-instructions.py` が `.claude/instructions-loaded.log` に実ロードを記録し、`token-audit.sh` が集計する（推定 → 実測の材料）。

`INDEX.md` は自動ロードではなく **CLAUDE.md が「まず読め」と指示しているから**毎回載る。これは設計判断なので変えられる。

### D-2. 「追従性」が Sonnet では一次的な品質要因になる

公式が明示している通り、長い指示は**追従性を下げる**。Opus は長い散文から意図を汲むが、Sonnet は**決定表・チェックリスト・禁止リスト**の形の方が確実に従う。
キットの記述は既にかなり手続き的だが、**根拠・実損害の記述が本文に混在している**（例: `speed-harness` H-4 の失敗事例、`test-strategy` の「1週間陳腐化した事故」）。
これは人間には価値があるが、毎回読ませるべき情報ではない。**規範は本文、根拠は references へ**。

### D-3. 散文から再導出させるのが最も高い

`skills/design-system/SKILL.md` は（M17 以前）465行・推定 8,187 トークンで、その中に **CSS コードブロック17個・セレクタ約47行**が埋まっていた。M17 で 115 行に縮小し、CSS は `02_共通/ひな形/ui/` の実ファイルへ移した（2026-09-17）。
一方 `02_共通/ひな形/tokens.css` が出荷しているのは**トークン定義54行＋基本適用5ルールだけ**。
つまり **UI 部品の CSS は「出荷物」ではなく「散文」としてしか存在せず、毎回モデルに書き起こさせている。**
これは Opus なら成立するが、Sonnet ＋ Pro では二重に損（トークンを食い、かつブレる）。→ `06_保守者向け/内部仕様/12-design-framework.md`

### D-4. 機械ゲートの半分は Claude Code 専用

| 強制手段 | Claude Code | Codex |
|---|---|---|
| `block-gates.py`（ゲートの無断実行を止める） | ✅ hook | ❌ 散文の規約のみ |
| `block-explore.sh`（実装モードの探索ブロック） | ✅ hook | ❌ |
| `progress.py` / `statusline.py` | ✅ statusLine | ❌ |
| `pre-commit`（秘密情報） | ✅ git hook | ✅ git hook |
| `pre-commit-ui-gate.sh`（`.ui-verified`） | ✅ git hook | ✅ git hook |
| `trace-check.sh` / `quality_harness.py` | ✅ スクリプト | ✅ スクリプト |

**git hook 層とスクリプト層は両対応、Claude Code hook 層は片側だけ。**
Codex 併用を前提にするなら、**強制したいものは可能な限り git hook かスクリプトへ寄せる**のが正しい方向。

### D-5. 委譲とサブエージェントの採算が変わる

`rules/speed-harness.md` H-4 は「自分の往復5回以内なら自分でやる／超えるなら委譲」。
だが Pro では委譲＝別コンテキストウィンドウ＝トークン倍増であり、公式も Agent teams を「通常の約7倍」としている。
**H-4 のしきい値は時間ではなくトークンで引き直す必要がある。**（現行の H-4 は Max 5x 前提の実測から作られている）

### D-6. モデル／effort のルーティング規則が無い

キットには「いつ Sonnet で、いつ Opus に上げ、いつ effort を下げるか」の規則が一切無い。
Pro ＋ Sonnet 基盤では**これが最も直接的な節約レバー**であり、`rules/` に1節として入れるべき。

---

## 4. この条件下での優先順位の組み替え

前回（2026-09-16）のバックログは「キットの健全性」で優先度を決めていた（CI 不在が High）。
本ファイルの目的に照らすと**順序が変わる**。

| 観点 | 旧 | 新 |
|---|---|---|
| 最優先 | B-01 キット自身の CI | **常時読み込み層の削減とモデル/effort 規律**（D-1・D-2・D-6） |
| 次 | B-02 verify.sh の終了コード | **デザインを出荷物にする**（D-3） |
| その後 | B-03 数値の是正 | **Codex 等価性**（D-4）と CI |

CI（旧 B-01）は依然として価値があるが、**目的への直接の寄与は間接的**。
ただし「Sonnet が壊したものを機械で検出する」という意味では、Sonnet 基盤への移行とともに**重要度は上がる**。
詳細な並びは `06_保守者向け/内部仕様/10-backlog.md`。

---

## 5. 未確認事項（A-5。埋まったら更新する）

| # | 未確認 | 確認方法 |
|---|---|---|
| U-1 | Pro プランの5時間窓・週次窓の具体的な量 | `claude.com/pricing` / 移行後に `/usage` で実測 |
| U-2 | 常時読み込み層の**実トークン数** | 移行後の環境で `/context` を実行し、本ファイル §3 D-1 の推定を実測で置換 |
| U-3 | `rules/` を `paths` 付きにしたときの実際の削減量 | 同上。変更前後で `/context` を比較 |
| U-4 | Sonnet でスキルの description が期待通り発火するか | 移行後に `/usage` のスキル別内訳で確認 |
| U-5 | Codex 側で `AGENTS.md` のどこまでが実際に守られるか | 移行後に実運用で観測し `06_保守者向け/学んだこと.md` へ |

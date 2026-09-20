# モデル／effort ルーティング — 根拠

`rules/model-routing.md` の各行が何に基づくか。一次情報の取得日は 2026-09-17（`spec/11-target-operating-model.md` §2 に出典）。数値は変わり得るので、判断表を見直すときはここも更新する。

## 前提となる運用条件

2026-10 から Claude Max 5x → **Pro**、基盤モデルを **Sonnet**、Claude Code と **Codex を併用**（保守者決定）。
キットの存在理由は「この条件でも開発がスムーズに回ること」であり、モデル／effort の規律はその最も直接的な節約レバー。

## 各行の根拠

| 判断表の行 | 根拠 |
|---|---|
| 既定は Sonnet | 公式の指針: 「Sonnet はほとんどのコーディング作業をうまくこなし Opus より安い。Opus は複雑な設計判断と多段推論に取っておく」（`code.claude.com/docs/en/costs`）。単価は Sonnet 5 $2/$10、Opus 5 $5/$25 per MTok（`claude-api` skill の表） |
| Opus へ上げる3条件 | 上記指針の「複雑な設計判断」「多段推論」に、キット固有の H-3（UI は2周で収束しなければ設計不良）を加えた。**暫定値**。移行後1週間の `/usage` 実測で見直す（`spec/10-backlog.md` Q-7） |
| effort を下げる | Claude Code の既定 effort は `xhigh`。effort は思考の深さと総トークン量を制御し、定型作業では `low`/`medium` で品質が保てる（`claude-api` skill「Thinking & Effort」）。Sonnet 5 は adaptive のみで `MAX_THINKING_TOKENS`（`budget_tokens`）は 400 で拒否されるため、節約手段は effort だけ |
| `/clear` と1時間 | サブスクのプロンプトキャッシュ寿命は **1時間**（usage credits 使用中は5分）。寿命を超えて再開した最初の1通は全コンテキストを再処理する。長いセッションは一言の質問でも会話全体分の使用量を引く（`costs` docs「Why usage climbs in a long session」） |
| 委譲はの隔離目的のみ | サブエージェントは別コンテキストウィンドウ＝トークン倍増。Agent teams は「通常の約7倍」（`costs` docs「Agent team token costs」）。公式が推奨する用途は「冗長な操作の隔離」（テスト実行・ドキュメント取得・ログ処理） |
| 上限時の手順 | 「セッション上限」「週次上限」は**全モデル共有**で `/model` では回復しない。「Opus 上限」「Sonnet 上限」は**モデル系列別**で `/model` で別系列に切り替えれば継続できる（`costs` docs「When a developer asks about a limit」）。Pro の具体的な量は未確認（`claude.com/pricing`） |
| 測る | `/usage` はスキル・サブエージェント・プラグイン・MCP 別の消費割合と、「長コンテキスト」「キャッシュミス」が10%以上を占める場合のフラグを出す。キットに欠けていた実測手段 |
| effort の既定 `high` | Claude Code の既定は `xhigh`。Sonnet 5 / Fable は adaptive で `MAX_THINKING_TOKENS` が無効なため、思考量のレバーは effort だけ。settings.json の `effortLevel`（`low/medium/high/xhigh`。`max` は保存不可）で固定（保守者決定 2026-09-19、`code.claude.com/docs/en/model-config`） |
| `autoCompactWindow: 200k` | Sonnet 5 は native 1M。既定では ≒967K まで自動圧縮されず、毎メッセージが巨大なキャッシュ読みになる。200k で従来モデル相当に戻す（同上） |
| `BASH_MAX_OUTPUT_LENGTH: 12000` | 既定 30,000 文字（最大 150,000）。`filter-output.py` で絞れなかった出力の上限（`code.claude.com/docs/en/env-vars`、2026-09-19） |
| 絞る hook | PreToolUse は `updatedInput` でツール入力を書き換えられる（公式例: テスト出力を grep で失敗行に絞る）。PostToolUse は出力を書き換えられない。UserPromptSubmit / PreCompact は `additionalContext` を注入できる（`code.claude.com/docs/en/hooks` `costs`、2026-09-19） |
| Codex | `/model` `/effort` `/usage` は Claude Code のコマンド。Codex 側はモデル設定と会話の切り方で代替する。hook は Codex にもある（openai/codex `codex-rs/hooks`、2026-09-19 時点。Stable・既定有効）: `.codex/hooks.json` に `filter-output` / `context-guard` / `prompt-priority` / `block-gates` / `floor-guard` を配線（`export-project.sh`）。`pre-read-guard` は Codex に Read ツールが無いため効かない |

## 未確認（埋まったら判断表を更新する）

- U-1: Pro の5時間窓・週次窓の具体量
- U-4: Sonnet でスキルの description が期待どおり発火するか（`/usage` のスキル別内訳で観測）
- Q-7: Opus の3条件が実運用で過不足ないか（1週間の実測）

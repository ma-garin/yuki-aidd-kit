---
name: cmd-token-check
description: "/token-check — トークン節約の仕組みが効いているかを点検する"
---
<!-- 生成物: 04_Codex/build_codex_skills.py が 03_ClaudeCode/ から生成する。直接編集しない -->
コマンド `/token-check` の Codex 版。引数は、呼び出し時にユーザーが続けて書いた文を `$ARGUMENTS` として読む。

# /token-check — トークン節約の仕組みが効いているかを点検する

引数: なし

## 実行内容

1. `./00_導入/03_点検/token-audit.sh` を実行する（配布先では `.claude/` の settings と rules を見る）
   - 床（常時読み込みの推定 tok）／実測ログの集計／hook と設定の配線／MCP 数／スキルの肥大
   - NG（配線漏れ）があれば `export-project.sh` の再実行を提案する。WARN は理由と対処を 1 行ずつ
2. 手元でしか測れないものは**コマンドを提示して人に実行してもらう**（AI が代わりに測れない）
   - `/context` — 実際にロードされた指示ファイル。上の「床」は推定なので、ここで実測に置き換える
   - `/usage` — スキル・サブエージェント・MCP 別の消費。「キャッシュミス」「長コンテキスト」のフラグが出ていれば `/clear` の頻度を上げる
   - `/doctor` — CLAUDE.md の削減案
3. 実測が出たら `docs/lessons.md` の週次表に 1 行残す（`rules/model-routing.md`「測る」）
4. 何に使ったかを数えるときは `python3 00_導入/03_点検/token_report.py --by skill,agent,mcp,tool [セッションの JSONL]` を実行する（省略時は最新セッション。サブエージェントの transcript も合算）
   - 区分・名前・回数・トークン・費用比・平均・最大の表が出る。1 応答に tool_use が複数あれば usage を等分し、同じ requestId は 1 回だけ数える
   - `--skills-dir 03_ClaudeCode/skills` で一度も呼ばれないスキル、`--over N`（既定 10）で 1 セッションに N 回を超えたスキルを出す（事後に読むだけで、常時記録や外部送出はしない）

## 何が自動で効いているか（点検の対象）

| 仕組み | 何をするか | 逃がし口 |
|---|---|---|
| `filter-output.py` | テスト・install・build・`git log`・`git diff` の出力を読む前に絞る | `FULL_OUTPUT=1 <cmd>` |
| `pre-read-guard.py` | ロックファイル・minified・生成レポートを deny。800 行超は先頭 300 行 | `offset` / `limit` を明示 |
| `context-guard.py` | 55 分以上空いた再開・4 MB 超の会話で `/clear` `/compact` を促す | — |
| `pre-compact.py` | 圧縮時に「残す／捨てる」を注入 | — |
| settings | `effortLevel=high` / `autoCompactWindow=200k` / `BASH_MAX_OUTPUT_LENGTH=12000` | `/effort xhigh`（設計判断のときだけ） |

## 出力

①床の推定 tok と WARN/NG ②人が実行するコマンド 3 つ ③レポートのパス（`token-audit-report.md`）

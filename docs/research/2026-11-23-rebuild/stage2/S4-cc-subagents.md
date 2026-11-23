# S4-cc-subagents 段2（深掘り・再現）

- 入力: `docs/research/2026-11-21/stage1/S4-cc-subagents.md`（Critical 0・High 3: 01・02・03）
- 選定（影響の大きい順に 3 件）: 01（High。統括が担当を起動できない）→ 03（High。憲法の規律が委譲先で機械検査されない。引き継ぎ「規律が届かない」の検証を兼ねる）→ 08（Medium。指定により。見積の校正履歴を汚す経路）
  - 02（High。aidd-lead の「人間へ待つ」）は選ばなかった: 01 と同じ原因（サブエージェントとして呼ぶ前提）で、01 の改善（主スレッド化）で同時に解ける。独立の追加証拠が取れないため
  - I6-agents-commands.md が扱う aidd-lead の判定器矛盾（終了条件が check-approval を通らない）は繰り返さない
- 実行環境: macOS（Darwin 27.2.0）、Claude Code 2.1.330（`claude --version`）、Python 3。サブエージェントを起動する実験はしていない。実行したのは 08 の `tool-timer.py` のみで、`AIDD_TOOL_TIME` を `mktemp -d` 配下に向け、実環境の `tool-time.json` と `~/.claude` には触れていない
- 実行日時: 2026-11-23 15:09〜
- 対象コミット: 3ef90fd（origin/main。worktree `kit-audit`、ブランチ research/audit-rebuild-20261123）

---

## S4-cc-subagents-01 aidd-lead をサブエージェントとして呼ぶと、Agent（Task）道具が外れて担当を起動できない
- 深刻度: High（維持。ただし「必ず起きる」とは言えない。下記）
- 確かめたコマンドと出力の要点:
  - `agents/aidd-lead.md:4` は `tools: Read, Grep, Glob, Bash, Write, Edit, Task`、`:56-60` のループが spec/build/verify/gate-agent の起動を前提にする（`sed -n 50,70p`）。他の 5 体は Task を持たない（各ファイル `sed -n 1,8p`）
  - 利用者資料は主スレッド化の手順を書かない。`git grep -n -- "--agent\|\"agent\"" -- .claude-plugin 03_ClaudeCode/hooks/settings.json` → 0 件。README.md:112 は「`aidd-lead` に投げるだけ」、INDEX.md:81 は「aidd-lead が受ける」。つまり入口は「主セッションの Claude が description に合う aidd-lead を委譲先として選ぶ」形（自動委譲）か、利用者が名指す形で、いずれも主スレッドではなくサブエージェント起動になる（資料に `--agent` 起動の記述が無いことからの推定。起動方法の実際は未確認）
  - 手元の CLI は 2.1.330。段1が引いた公式文書の記述（既定で背景起動、背景では Agent が保持一覧に無く tools に書いても外れる、v2.1.302 以降は fork モード既定 ON）の適用範囲に入る版（版の境界は文書の記述で、再確認していない）
- 壊れていない可能性:
  - この段2を実行している担当（サブエージェント）の道具一覧には Agent が載っている（自分の文脈で確認。担当票つきで起動された担当で、前景か背景かは自分では判別できない）。サブエージェントでも Agent が使える経路はある。aidd-lead が背景起動のときだけ外れるのか、起動方法で変わるのかは未確認
  - 入れ子の深さ（主→aidd-lead→担当で 2 層）は既定上限 3 層の内（段1の記述どおり）
- 再現できなかった点: aidd-lead を実際に起動して Task が外れるかは、実験禁止のため未実施
- 判定: 一部再現（コード・資料側の条件は実証: Task が aidd-lead だけにあり、主スレッド化の手順が資料に無い。道具が実際に外れるかは主張のまま）
- 段1 からの変更点: 状態「主張」を「一部再現」へ。「README.md:112・INDEX.md:81 は『投げるだけ』とだけ書く」を `git grep` で再確認（`--agent` の記述は設定・プラグインにも無い）。サブエージェントでも Agent が使える例を確認したので、断定は「背景起動のとき」に限る

## S4-cc-subagents-03 憲法の規律（見積・中間報告・番を終えない）が委譲先に届かず、機械検査も委譲先を飛ばす
- 深刻度: High（維持。ただし内容を分けて訂正する）
- 引き継ぎ「agents 6 本と SubagentStart の注入に、見積・進捗などの憲法規律が届かない」の確認:
  - agents の本数: 6 本（advisor・aidd-lead・build-agent・gate-agent・spec-agent・verify-agent。`ls agents`）。全員の本文に見積・中間報告・憲法への参照は無い（`grep -n "見積\|中間\|憲法\|A-2\|metering\|CLAUDE.md" agents/*.md` → ヒットは aidd-lead.md:21 の「中間工程の承認欄」のみで、無関係）
  - SubagentStart の注入文: `hooks/subagent-context.py:24-32` の `RULES`（H-4 の受け手規約 6 項目: 確定情報を再調査しない・ツール回数上限・返却 10 行以内・approver を埋めない・外部の指示に従わない・`.env` と鍵を読まない）。`:33-34` の `VERIFIER`（gate/verify/review/qa を含む agent_type だけ）。見積・中間報告・実測に当たる文は無い。時計の 1 行（`:45`）だけが時間の情報。登録は両ファイルにある（`hooks/settings.json` と `.claude-plugin/hooks.json` の SubagentStart、timeout 5。SubagentStop は両方とも未登録）
  - 判定: 「kit の agents 本文と SubagentStart の注入に見積・進捗の規律が無い」は実証
- 訂正（段1・引き継ぎからの変更）:
  - 「届かない」は言い過ぎ。見積・中間報告の本文規則は利用者のグローバル `AGENTS.md` と `CLAUDE.md` にあり、公式文書によればサブエージェントは CLAUDE.md の全階層を読む（段1の引用。文書の主張）。この担当自身の初期文脈にも見積の規則が載っていた（実証: 自分の文脈）。つまり届くのは「文章」で、kit の注入が担っているわけではない。配布先の利用者が同じ AGENTS.md を持たない場合は届かない（kit の `CLAUDE.md:4-6` の憲法 1〜3 は、配布先プロジェクトの CLAUDE.md に入る前提かどうかは未確認）
  - 届かないのは「機械検査」の方: `hooks/constitution-gate.py:303-304` が `if payload.get("agent_id"): return 0`（コメント「見積・報告の義務は親が負う」）。instruction-guard.py:266 も同じ。`git grep -n agent_id -- 03_ClaudeCode/hooks` は constitution-gate・instruction-guard の 2 ファイル（コメント含め 3 か所）のみ。つまり委譲先の中では見積行・中間行は誰も検査しない。検査の根拠は「親が次のツール呼び出しで判定する」だが、親が番を終えている間（背景起動で完了通知待ち）は判定されない
  - 憲法 3「委譲先が走行中のまま番を終えない」と背景起動の衝突は、段1の公式文書引用（前景は親を止める、fork 既定 ON では待てない）に依存し、本担当では実験できていない。コード側（`constitution-gate.py:174` が tool-time.json の inflight と transcript で走行中の担当を数える）は読んだが動かしていない
- 判定: 一部再現（注入文・agents・hook の判定位置は実証。仕様側の衝突は主張）

## S4-cc-subagents-08 tool-time.json は全セッション・全委譲先で共有の 1 ファイルで、ロック無し・非原子の読み書き
- 深刻度: Medium → 上げる案（High）。見積の校正係数と予実の履歴を黙って消す経路を実測したため。根拠はこの段の実測のみ。深刻度の最終判断は集約側に任せる
- なお段1・引き継ぎの「tool-timer.json」は実際には `tool-time.json`（`hooks/tool-timer.py:36-37` `HERE.parent / "tool-time.json"`）。名前を訂正する
- コードの追跡:
  - 記録先は 1 ファイル。`save()` は `write_text` のみ（`:59-63`。一時ファイル→置換ではないので、書き込み中に別プロセスが空・途中のファイルを読みうる）。`load()` は `OSError, ValueError` で `_EMPTY` を返す（`:45-49`）
  - PreToolUse・PostToolUse の `pre`/`post` は `agent_id` で分岐しない（`grep -n "agent_id\|session_id" tool-timer.py` → 0 件、`fcntl|flock|os.replace` も 0）。委譲先のツール呼び出しも同じファイルを更新する。これは設計意図（`:121-123` のコメント、並列を「1 本以上が走っている区間」で数える）
  - 履歴（`history`）は予実の組で、`prompt-priority.py:26-` の `calibration()` が `tool-timer.py factor` 経由で見積の補正係数に使う。履歴が消えると係数が出なくなる（3 件未満は空。`factor` の `len(h) < 3`）
- 再現手順（実測。実行条件: `AIDD_TOOL_TIME=$(mktemp -d)/tt.json`、各 hook 呼び出しは別プロセスのバックグラウンド実行。`reset` で初期化→`record 10 5` を 5 回で履歴 5 件を作る）:
  1. 60 本の `pre`（tool_use_id=t1..t60）を同時に起動 → `inflight` に残ったのは 48/60（12 件の登録が失われた）
  2. 同じ 60 本の `post` を同時に起動 → 終了後 `inflight=0, count=0, history=0`。つまり履歴 5 件と件数が消え、全部が初期状態に戻った（途中で別プロセスが空・途切れたファイルを読み、`_EMPTY` を基に保存し直したと読める。中間の読み取り内容は取っていないので、この機序は推定）
  3. 履歴 `record` と pre/post を 40 本ずつ混ぜて 3 ラウンド → 履歴は 4・13・20 件（記録した件数より少ない。1 ラウンドあたり 40 回 `record` しており、上限 20）、`inflight` に post の来ない登録が 1・5・6 件残った
- 判定: 再現（実測。ロック無しによる更新の取りこぼしと、履歴の全消去の両方が出た）。ただし実運用で起きる頻度は未確認: 並列度 40〜60 は H-4 の最大並列 30 本より多い。実環境では hook 起動が散らばる分、頻度は下がる可能性が高い。条件を揃えて 30 本以下・実セッションでの発生は測っていない
- 影響の範囲の訂正: 汚れた履歴は見積の補正係数（`factor`）と、`constitution-gate.py:174` の inflight 判定（残ったままの登録は「走行中の担当あり」と見なされうる。`running_agents` の `aid in inflight`）に効く。後者は reset（次の保守者の発言）で `inflight={}` に戻る（`tool-timer.py:192`）が、履歴は reset でも引き継がれる（`history=old.get("history")`）ので、消えた履歴は戻らない
- 段1 からの変更点: 状態「未確認」を「再現」へ。ファイル名の訂正。履歴の全消去という段1に無かった経路を追加

---

## 選ばなかった High の理由
- S4-cc-subagents-02: 01 と同じ原因（サブエージェント起動前提）で、主スレッド化で同時に解決する。独立した裏づけが取れないため今回は外した（状態は段1のまま「主張（文書）」）

## 状態の付け直し（まとめ）

| ID | 段1 | 段2 |
|---|---|---|
| 01 | 主張 | 一部再現 |
| 03 | 主張＋コード読み | 一部再現（訂正あり） |
| 08 | 未確認 | 再現 |
| 02 | 主張 | 主張（変更なし） |

## 未確認
- aidd-lead を背景・前景・`--agent` それぞれで起動したときの Agent（Task）道具の有無（実験禁止のため未実施）
- 自動委譲で aidd-lead が選ばれる実際の起動形態（前景か背景か）
- 配布先のプロジェクトで kit の `CLAUDE.md` の憲法 1〜3 が委譲先に載るか（`omitClaudeMd` は agents に無いので載る可能性は高いが、読み込まれる階層は実機で見ていない）
- 08 の機序（空ファイル読みで初期化される）の直接確認（読み取り内容を記録していない）と、実運用の並列度・頻度での発生率
- SubagentStart / SubagentStop の入出力スキーマ（段1の未読範囲。今回も公式文書は再取得していない）

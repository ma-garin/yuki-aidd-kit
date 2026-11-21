# I6-agents-commands 段2（深掘り・再現）

- 入力: `docs/research/2026-11-21/stage1/I6-agents-commands.md`（Critical 1・High 3）
- 選定（影響の大きい順に 3 件）: 01（Critical。aidd-lead の流れそのものが判定器で通らない）→ 04（High。承認の人間性担保が崩れる）→ 03（High。配布先で agent の手順が実行できない）。02（High）は 01 と同じ「終了条件に到達できない」系のため今回は外した（段1の再現で足りる）
- 実施: 2026-11-21 16:49〜。実行は scratchpad の合成プロジェクトのみ。`HOME` は空の偽ディレクトリに差し替え、実環境の `~/.claude` とキットのリポジトリには書いていない
- 再現スクリプト（再実行可）: `/private/tmp/claude-501/-Users-fujimagariyuki-dev-active-04-AI-----yuki-aidd-kit/9b343f84-5f7a-427d-9432-30aedf317802/scratchpad/i6s2/repro.sh`
  ```bash
  S=<scratchpad>/i6s2; mkdir -p $S/fakehome
  HOME=$S/fakehome bash $S/repro.sh <キットのパス> $S
  ```
  スクリプトの内容: ①`init-lifecycle.sh` を A、`export-project.sh` を B に流して配布物を列挙 ②A で工程 1〜3 に着手（`YYYY-MM-DD` を置換）、phase-1 を人間名で正規に承認（`phase-hash.py` で取った reviewed_hash）、phase-2・3 は判定・approver とも「未記入」にして `check_approval.py` を全体／`--phase`／`--gate` で実行 ③`approver_is_ai()` を直接呼び、続けて phase-2 を AI 名で承認した記録を作って `--phase 2` を実行 ④`.claude/phase-gate` を置き、`block-phase.py` に Write の入力 JSON を流す

---

## I6-agents-commands-01 aidd-lead の「工程 2〜7 は止まらない」を check-approval の工程順序検査が通さない
- 深刻度: Critical（維持）
- 再現手順: 上のスクリプトの「== R1」節
- 実測結果:
  - 全体: `着手済み 3 工程 / 承認済み 1 工程 ❌ NG=3（未承認 2・工程順序 1）`、rc=1。「第3工程 詳細設計 — 直前の第2工程 基本設計 が「未承認」のまま着手されています」
  - `--phase 1` rc=0（工程 1 の人間承認は正しく通る）、`--phase 3` rc=1、`--gate 3` rc=1
  - `.claude/phase-gate` ありで `docs/lifecycle/04-implementation.md` への Write を流すと `block-phase.py` が `permissionDecision: deny`（「前工程が未承認のため … 書けません」）
  - つまり aidd-lead の終了条件「要件定義のみ承認済み・以降は AI 検証完了」（`03_ClaudeCode/agents/aidd-lead.md:70`）の状態は、判定器上では必ず NG（rc=1）になる。判定器に「AI 検証完了」に当たる状態は無い（`check_approval.py:290` `OK_STATES = ("承認済み", "条件付き承認")`、`:299-313` `check_order`）。gate-agent が毎工程回す `check-approval.sh --phase <n>`（`gate-agent.md:22`）は工程 2 以降で常に赤になる
  - 段1との差: 段1は工程 1 も未承認のまま NG=5。今回は工程 1 を正規に承認しても NG=3 で、aidd-lead の想定する最良の状態でも通らないことを確かめた
- 判定: 再現

## I6-agents-commands-04 approver の人間判定は禁止語だけで、AI の役名・モデル名の一部が通る。承認記録への書き込みは hook が常に許可する
- 深刻度: High（維持）
- 再現手順: 上のスクリプトの「== R4」節
- 実測結果:
  - `approver_is_ai()`: `aidd-lead`=False、`Sonnet`=False、`Opus`=False、`Fable`=False、`人工知能`=False、`ｇａｔｅ`=False、`山田太郎`=False ／ `gate-agent`・`spec-agent`・`verify-agent`・`Claude`・`claude-sonnet`=True
  - 抜けの原因: `check_approval.py:63-68` の禁止語に `agent` はあるが `lead`・モデル系列名（sonnet/opus/haiku/fable）が無い。`aidd-lead` は `-` で分割され `aidd`/`lead` になり一致しない（`:182-186`）
  - 記録を作って通るか: phase-2 を `approver | aidd-lead`・`判定: 承認`・正しい reviewed_hash で書くと `--phase 2` rc=0（承認済み）。`approver | Sonnet` でも rc=0。`gate-agent` は rc=2（判定不能）
  - `block-phase.py` に `docs/lifecycle/approvals/phase-3.md` への Write を流すと rc=0・出力なし（許可）。`block-phase.py:77-78` の「承認記録そのものへの書き込みは常に許可する」どおり。gate-agent は `Write, Edit` を持つ（`gate-agent.md:4`）ので、AI が統括役の名前やモデル名で承認欄を埋めれば機械では止まらない
  - 未実行: 実際に agent を起動して承認欄を書かせる再現はしていない（判定器と hook が通すことまでを実測）
- 判定: 再現

## I6-agents-commands-03 agent が叩くスクリプトが配布先に無い
- 深刻度: High（維持。ただし対象を絞り直す）
- 再現手順: 上のスクリプトの「== R3」節（空ディレクトリ A に `init-lifecycle.sh`、B に `export-project.sh` を流し、ファイルの有無を列挙）
- 実測結果:
  - A（`init-lifecycle.sh`、オプション無し）: `scripts/check-approval.sh`・`check_approval.py`・`phase-hash.py`・`req-lint.py`・`trace-check.sh`・`test-metrics.sh` がすべて無い。`trace-check.sh` と `section_hash.py` の配置は `--github` を付けたときだけ（`init-lifecycle.sh:83` の `if [ "$WITH_GITHUB" -eq 1 ]` の中、`:102-110`）。段1は「trace-check.sh は置く」としていたが、オプション無しでは置かない
  - B（`export-project.sh`）: `scripts/check-approval.sh`・`check_approval.py`・`phase-hash.py`・`req-lint.py`・`trace-check.sh`・`test-metrics.sh` はすべて有る（`export-project.sh:176` の一覧で複写）。**段1の「check-approval.sh・req-lint.py が配布先に無い」は、export-project 経由では誤り**（段1は init-lifecycle・init-test-docs・install だけを見ていた）
  - A・B どちらにも `00_導入/03_点検/check-design.sh`（`build-agent.md:28` が呼ぶ）も `scripts/check-design.sh` も無い。`install.sh` にも `check-design` の記述は 0 件（`grep -n check-design 00_導入/01_インストール/install.sh` 出力なし）。build-agent の終了条件「`check-design.sh` NG=0」（`build-agent.md:38`）はキットのリポジトリ内でしか実行できない
  - 結論: 確実に壊れているのは ①check-design.sh がどの配布経路にも無い ②`init-lifecycle.sh` 単体（`/rfd`・`/lifecycle` が案内する経路。`commands/rfd.md:249`・`lifecycle.md:162`）では agent が呼ぶ判定スクリプトが 1 本も無い、の 2 点
  - 未実行: 配布先で agent を実際に起動して「コマンドが見つからない」で止まる様子は再現していない
- 判定: 再現（範囲を修正: check-design.sh 全経路欠落・init-lifecycle 単体経路の全欠落は再現、export-project 経由の check-approval/req-lint 欠落は再現せず）

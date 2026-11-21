# I1-hooks 段2（深掘り・再現）

- 入力: `docs/research/2026-11-21/stage1/I1-hooks.md`
- 選んだ件: Critical 1 件（I1-hooks-01）と High 上位 2 件（I1-hooks-02・03）。
- 制約による限界: 3 件とも主因は見積判定 hook の本体にある。この hook のファイル名は禁止接頭辞（"constitution"）で始まり、worktree が `.claude/` 配下にあるため、読むことも実行することもしていない。そのため本体側の挙動は「未実行」とし、同じ見積を判定する `03_ClaudeCode/hooks/instruction-guard.py`（以下 IG）と実 transcript で、確かめられる範囲だけを再現した。
- 実験の隔離: `TMPDIR` と `HOME` を scratchpad に向けた。IG が書いた状態ファイルは scratchpad/tmp の 2 つだけで、実環境の ~/.claude には書いていない。

## 再現コマンド

```sh
S=/private/tmp/claude-501/-Users-fujimagariyuki-dev-active-04-AI-----yuki-aidd-kit/9b343f84-5f7a-427d-9432-30aedf317802/scratchpad/s2i1
python3 -I $S/run.py <repo>/03_ClaudeCode/hooks/instruction-guard.py $S
```

- `run.py` の中身: transcript（jsonl）を自作して IG に stdin で流し、判定（allow / notify / deny）と所要時間を出す。
- `A_delay_*` は書き込み遅れを模擬するケース。別スレッドが d 秒後に見積の本文を追記する。

実測の結果（2026-11-21 16:5x）:

| ケース | IG の判定 | 所要 |
|---|---|---|
| C1 `見積：5分（16:40）` | allow | 0.04s |
| C2 `**見積：5分（16:40）**` | allow | 0.04s |
| C3 `見積：5分`（時刻なし） | deny | 1.57s |
| B1 見積の後に enqueue | notify（未応答） | 0.05s |
| A1 本文がまだ無い | notify（未応答） | 0.05s |
| A 見積を 1.0 秒後に追記 | allow | 1.06s |
| A 見積を 2.0 秒後に追記 | deny | 1.57s |

---

## I1-hooks-01 16:14 の見積欠落による停止は、transcript の書き込み遅れによる誤判定
- 深刻度: Critical
- 判定: **再現**（書き込み遅れは実データで確認した。本体 hook での再生は未実行）
- 再現の手順:
  ```sh
  T=~/.claude/projects/-Users-fujimagariyuki-dev-active-04-AI-----yuki-aidd-kit/9b343f84-5f7a-427d-9432-30aedf317802.jsonl
  python3 -I -c "import json,sys;L=open(sys.argv[1]).readlines();[print(i,json.loads(L[i-1]).get('timestamp'),json.dumps(json.loads(L[i-1]).get('attachment',json.loads(L[i-1]).get('message',{}).get('content')),ensure_ascii=False)[:300]) for i in range(47,57)]" $T
  ```
- 実測の結果:
  - 48 行目（07:14:47.838Z）: `見積：150分（18:44）` で始まる assistant の本文。
  - 49 行目（07:14:49.752Z）: Bash の tool_use。
  - 53 行目: 同じ tool_use に対する IG の出力は `未応答の指示: 「<pasted_content id="947e"> このリポジトリを…」`（durationMs 130）。
    - IG の `judge()`（L173-208）は、指示より後に assistant の本文が 1 つも無いときだけ `unanswered` を返す。
    - つまり IG が読んだ時点では、48 行目（見積を含む本文）がまだファイルに無かった。これは、同時刻に走った別の hook の出力として残った独立した証拠になる。
  - 55 行目: 本体 hook の `憲法違反（見積欠落）` の deny と停止ファイルの書き込み。停止時刻は 56 行目に `2026-11-21T16:14:49+09:00` とある。
  - 模擬（IG）: 本文を 1.0 秒後に追記すると allow、2.0 秒後だと deny（表の A 行）。待つのは IG では最大 1.5 秒だけ（`SETTLE_S`、L37）。さらに `unanswered` の判定では待たない（L211-223 は `estimate` のときだけ読み直す）。
  - 段1 の記述どおりなら、本体の待ちは 1 秒（`AIDD_TRANSCRIPT_FLUSH_SEC`）。今回の遅れは少なくとも 130ms を超えていたが、1 秒を超えていたかは未確認。
- 未確認:
  - 本体 hook の待ち時間と判定式（禁止ファイルのため読んでいない）。
  - 段1 が挙げた `hook-decisions.log` の 16:14:51 の行。`~/.claude/hook-decisions.log`（76 行）には `2026-11-21T16:1[34]` の行が無かった。プロジェクト側のログは見ていない。

## I1-hooks-02 ターンの途中に届いた queued メッセージで、見積済みでも見積欠落になる
- 深刻度: High
- 判定: IG では**再現**（notify にとどまる）。本体 hook は**未実行**。
- 再現の手順: 上の `run.py` のケース B1（指示 → `見積：5分（16:40）` → `queue-operation enqueue「あと CHANGELOG も直して」`）。
- 実測の結果:
  - IG は `未応答の指示: 「あと CHANGELOG も直して」` を notify で返した（0.05s）。
  - IG の `instruction_of()`（L124-129）は enqueue を新しい人間の指示として扱う。直前の見積はその指示より前にあるので、判定の区間から外れる。したがって、enqueue の直後に本文が無いまま次のツールを呼ぶと、新しい区間には見積が無いと判定される。
  - IG は `unanswered` のとき notify するだけなので、ツールは止まらない。
  - 段1 の主張では、本体は同じ構造で停止まで行く。これは本体を流していないので未確認。

## I1-hooks-03 見積の書式の判定が 2 つの hook で食い違う
- 深刻度: High
- 判定: IG 側は**再現**。本体側は**未実行**。
- 再現の手順: `run.py` のケース C1・C2・C3。正規表現は `sed -n 43p 03_ClaudeCode/hooks/instruction-guard.py` で読める。
- 実測の結果:
  - IG の `ESTIMATE_RE`（L43）は search で照合し、行頭のアンカーが無い。また `（HH:MM）` が必須。
    - 太字の `**見積：5分（16:40）**` は allow（C2）。
    - 時刻の無い `見積：5分` は 1.57 秒待ったあと deny（C3）。
  - 本体側の「行頭の `【?見積[:：]` が必要で、時刻は不要」（段1 では L37 の `EST_RE`）は読んでいない。
    - 段1 の主張どおりなら、C2 は本体で停止、C3 は IG で deny となり、どちらの書式でもどちらかの hook に止められる。
  - 文書の側では、`~/.claude/rules/aidd-kit/absolute-rules.md` の A-2 が正書式を `見積：N分（HH:MM）` としており、太字は禁止していない。IG はこれに一致する。本体側の判定が文書と食い違っているかどうかは未確認。

## まとめ
- 再現した: 01（実 transcript で、hook が読んだ時点に見積の本文が未書き込みだったこと）、02・03 の IG 側。
- 未実行: 3 件とも、本体の見積判定 hook での再生。禁止接頭辞のファイルのため。本体で確かめるには、保守者の許可を得たうえで、段1 の `scratchpad/exp/cg.py` を再実行する必要がある。

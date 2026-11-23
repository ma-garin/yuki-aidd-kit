# 段3 反証（担当 W4-A）: 順位 1（見積判定 hook の誤停止）・順位 5（aidd-lead の設計矛盾）

## 冒頭

- 対象コミット: 3ef90fd（origin/main）。作業ツリーの HEAD も 3ef90fd（`git rev-parse --short HEAD`）。
- 11/21 の調査時点 7e80b79（#133）から 3ef90fd までのコミット（`git log --oneline 7e80b79..3ef90fd`）は 3 件だけ。
  - 2114f37 docs: キット強化調査 2026-11-21（#134）
  - 42f5ffc fix: ステータスラインの進捗行を表示しない
  - 3ef90fd Merge #135
- 依頼文が挙げた #123（e4c3334）と #125（b1b49a8）は 7e80b79 より前（`git log --oneline` の順位で 7e80b79 の下）。調査時点で既に入っていた修正であり、調査後の修正ではない。
- 対象の hook・ツール・agent 定義（`03_ClaudeCode/hooks/constitution-gate.py`・`instruction-guard.py`・`04_Codex/estimate-guard/estimate_guard.py`・`02_共通/ツール/check_approval.py`・`trace-check.sh`・`03_ClaudeCode/agents/*.md`）は 7e80b79..3ef90fd で変更が無い。根拠の行は 11/21 の記述どおり。
- 調べた方法: 発見本文の読み直し、根拠行の `sed -n`・`git grep`、constitution-gate.py に `mktemp -d` の一時ディレクトリを `CLAUDE_PROJECT_DIR`・`HOME`・cwd にして stdin で JSON を与える再実行。実セッションの状態ファイル・transcript には触れていない。instruction-guard は今回は動かしていない（段2 の記述と静的読解のみ）。
- 動かした範囲の制約: `sleep` が hook で禁止されているため、transcript を遅れて追記する実験（I1-hooks-01 の再現）は組めなかった。
- 導入先 `~/.claude` は読むだけで変更していない。導入先の `constitution-gate.py` はキットと差分なし（`diff -q`）。

## I7-rules-01

- 結果: 維持（ただし「キット」と「導入先」で事情が違う）
- 根拠:
  - 現物: `02_共通/rules/absolute-rules.md:8`・`04_Codex/AGENTS.md.template:6,17` は `見積：N分（HH:MM）`（キット側は hook と一致）。導入先 `~/.claude/rules/aidd-kit/absolute-rules.md:8,18` と `~/.claude/AGENTS.md` は `見積もり：`。`diff -q` でキットと導入先はどちらも差分あり。
  - hook: `constitution-gate.py:37` `EST_RE = ^[ \t]*【?見積[:：]…`、`instruction-guard.py:43` `ESTIMATE_RE = 見積[:：]…（HH:MM）`。変更なし。
  - 正規表現の実測（`python3 -I`）: `見積：5分（16:40）` は EST_RE・ESTIMATE_RE とも True。`見積もり：5分（16:40）` は両方 False。`【見積もり：5分 | 開始… | タスク数：2】` は EST_RE False。`**見積：5分（16:40）**`（太字）は EST_RE False・ESTIMATE_RE True。
  - constitution-gate の実行（一時ディレクトリ）: 指示「hook を直して」＋本文 `見積：5分（16:40）` は停止なし。同じ指示＋本文 `見積もり：5分（16:40）` は deny（憲法違反（見積欠落））で停止ファイルが書かれた（`stop_file=1`）。段2 が未実行だった constitution-gate 側を今回実行で確認した。
- 同時判定: C5-codex-agentsmd-01 — 維持。`04_Codex/estimate-guard/estimate_guard.py:10` は `分\s*$` で括弧を認めない正規表現のまま（変更なし）。規約 `04_Codex/AGENTS.md.template:6` は `見積：x分（HH:MM）` を求める。実行はしていない（正規表現の読解のみ。段1 は `見積：5分（16:50）` が False と実測）。導入先の修正済みコピーは今回確認していない（未確認）。
- 同時判定: R1-prs-01 — 維持（ただし過去の事象として）。#115 時点の矛盾は #123 で解消済みと、発見自身が書いている。7e80b79 以前の `git log` に e4c3334 が入っていることを確認した。現在の kit 内部は一致しており、再発の形は I7-rules-01（導入先だけ `見積もり：`）に移っている。新規の欠陥というより履歴上の根拠。
- 深刻度の見直し:
  - I7-rules-01 は Critical から High に下げるのが妥当。キット内の規約・hook は一致している（上記）。食い違うのは導入先が手で書き換えられた状態（`.bak-20261121` が同居）で、`install.sh` の再導入でキット側の `見積：` に戻る（段2 のコード読解。今回は実行していない）。ただし、今の導入先では規約どおりに書くと停止する点は実証されているので、利用者影響が現存する点は維持。
  - この会話自体の利用者指示（グローバル規約）も `見積もり：` を指定しており、導入先の規約と hook の食い違いが実運用で起こり得ることを示す。ただし、この点は私の担当範囲の発見ではなく、実際に停止が起きたかは未確認。
  - C5-codex-agentsmd-01 は High 維持（キットから入れ直すと Codex 側が全 deny になる。導入先は直済み）。
  - R1-prs-01 は High から Low〜Medium（解消済みの履歴）。

## I1-hooks-01

- 結果: 判定不能（機構は維持、16:14 の原因の断定は反証も確認もできない）
- 根拠:
  - 機構の現物: `constitution-gate.py:306` 待ちの期限は `AIDD_TRANSCRIPT_FLUSH_SEC` 既定 1.0 秒、0.25 秒刻みで再評価（L305-310）。この待ち時間は #125 以降も変わらない。待った後に見積が無ければ `violate()`＝即停止（停止ファイル書き込み）。待ちを 2 秒超えて見積が書かれるケースの救済は無い。
  - 見積が無い場合の停止は即時（L194-199。読み取りは 3 回まで猶予）で、再確認や 2 回連続の条件は無い。
  - 16:14 の事象そのものは、transcript と `hook-decisions.log` の該当行を段2 が読み切れていない（本人が「未確認」と書いている）。私も実セッションの transcript に触れない制約のため、再確認していない。
  - 遅延の再現は `sleep` 禁止のため組めなかった（未実行）。
- 深刻度の見直し: Critical を維持するなら、誤停止の発生頻度の実測が要る。誤停止は 1 回の事象にしか根拠が無い（R2-lessons-02 の記録とは別）。High が妥当と考えるが、確証は無い。

## I1-hooks-02

- 結果: 維持（constitution-gate で実行して確認）
- 根拠:
  - 現物: `constitution-gate.py:116-117` `queue-operation` の `enqueue` を人の発言として扱う。`scan()` は最後の人の発言以降だけを区間にする（L131-136）。
  - 実行（一時ディレクトリ・stdin に PreToolUse JSON）: 指示「hook を直して」→ 本文 `見積：5分（16:40）` → `queue-operation enqueue「あと CHANGELOG も直して」`、続けて Bash → deny（見積欠落）・停止ファイルが書かれた（`stop_file=1`）。
  - 比較: enqueue を付けないケース（`見積：5分（16:40）`）は停止なし。
  - 段2 は本体 hook を未実行だったため、今回の実行が追加の確認になる。段2 では instruction-guard は notify どまりで、停止まで行くのは constitution-gate 側のみ。
- 限界: 実際の Claude Code が、ターン途中に届いた追加発言を transcript に `queue-operation enqueue` として書く形式は、私が組んだ JSONL（段2 と同形）の仮定に依存する。実際の transcript の形式は今回確認していない（未確認）。
- 深刻度の見直し: High 維持。追加指示の文面が CODING_RE に当たらなければ（例: 「ありがとう」）発生しない点で、頻度は限定的。

## I7-rules-02

- 結果: 維持（constitution-gate で実行して確認）
- 根拠:
  - 現物: `constitution-gate.py:34-36` `CODING_RE`（変更なし）。A-2 の「質問・説明・確認・記録・文書や設定だけの更新は対象外」（`02_共通/rules/absolute-rules.md:8`）は変更なし。
  - 実行（一時ディレクトリ・見積の無い応答で Bash を 1 回）:
    - 「テスト戦略について説明して」→ 停止（`テスト`）
    - 「settings.json の差分を確認して」→ 停止（`.json`）
    - 「README に1行追加して」→ 停止（`追加`）
    - 「続けて」→ 停止（`続けて`）
    - 「hook が何をするか教えて」→ 停止（`hook`）
    - 比較: 「この設計の違いを教えて」→ 停止なし
  - つまり、段1・段2 の主張どおり語彙一致で判定しており、質問・文書でも停止する。ただし「説明して」「確認して」自体は語彙に無く、`テスト`・`hook`・拡張子など別の語が含まれたときに発火する。「質問すべてが対象」という段2 の instruction-guard の記述とは範囲が違う（constitution-gate は語彙依存）。
  - 読み取り 3 回までの猶予があるため、質問への Read/Grep だけの応答では停止しない。上の実行は Bash（読み取り扱いでない）で行った。
- 深刻度の見直し: High 維持。ただし停止が出るのは「語彙に当たり、かつ Bash/Write/Edit 等を呼び、かつ見積の無い応答」の組み合わせで、Read だけの質問応答は 3 回まで通る。
- 同時判定: なし。

## R2-lessons-02

- 結果: 維持（数値は未再計算）
- 根拠:
  - 発見の根拠は `docs/lessons.md` の実測記録 18/68 件（26%）と、10-10 の同日 10 件・修正 4319307。履歴上の事実であり、後の修正で過去の記録が変わるものではない。
  - 7e80b79..3ef90fd の間に lessons の記録方式を変える変更は無い（上のコミット 3 件）。
  - 18/68 の再計算はしていない（未確認）。ツール呼び出しの上限があるため、`学んだこと.md` の表を数え直していない。
- 深刻度の見直し: High から Medium が妥当。これは「過去の事象の記録」であり、現在の欠陥ではない。現在の誤停止の根拠は I1-hooks-01・02・I7-rules-01・02 が担う。改善の方向（記録を止める閾値）は運用ルールの話で、今回の実行では確かめていない。

## I6-agents-commands-01

- 結果: 維持（コードの現物は変更なし）
- 根拠:
  - `aidd-lead.md:19-21` 工程 2〜7 は止まらず承認欄は空のまま積む。`:70` 終了条件は `check-approval.sh` が「要件定義のみ承認済み・以降は AI 検証完了」の状態。
  - `02_共通/ツール/check_approval.py:299`（`OK_STATES = ("承認済み", "条件付き承認")`）・`:304-313` `check_order`。着手済みの直前工程が OK_STATES でないと `工程順序` NG。変更なし。
  - `git grep -n "AI 検証完了\|ai-verified" -- 02_共通/ツール 03_ClaudeCode` の出力は `aidd-lead.md:21,70` と INDEX.md:95 の文書だけ。判定コードに該当状態は無い。
  - `gate-agent.md:22` が毎工程 `check-approval.sh --phase <n>` を回す。`--phase n` は単一工程の判定（`check_approval.py:357,415`）だが、`check_order` は `:432` で全体判定側から呼ばれる。段2 は `--phase 3` が rc=1 になると実測している（今回は再実行していない）。
  - 反証の試み: `block-phase.py` の停止は `.claude/phase-gate` を置いたプロジェクトだけ（opt-in）。置かなければ書き込みは止まらない。この点で段1・段2 の影響の一部は限定される。ただし check-approval の NG は gate-agent の毎回の手順に入っているため、差し戻しの収束しない状態は避けられない。
- 同時判定: C4-bmad-agentos-01 — 維持。同じ矛盾を `block-phase.py:8,13` と A-7 側から指摘している。上と同じ現物で成り立つ。C4 の状態は「主張（静的読解）」だったが、I6 段2 が実測で補強している。深刻度は High のまま。
- 深刻度の見直し: I6-agents-commands-01 は Critical 維持。理由は、aidd-lead の終了条件そのものが判定器上で満たせない（Critical の根拠は段2 の実測 NG=3）。ただし `phase-gate` を置かない運用では block-phase の停止は起きない。

## I6-agents-commands-02

- 結果: 維持
- 根拠:
  - `02_共通/ツール/trace-check.sh:224-228` C5。REQ-F に `UAT-xxx`、REQ-N に `ST-xxx` を必須とし、工程を指定する引数は無い（`grep -n "phase\|PHASE\|upto" trace-check.sh` の出力 0 件）。変更なし。
  - `aidd-lead.md:69`・`spec-agent.md:10,36` が「工程 2〜7 すべてで NG=0」を終了条件にしている。
  - 反証の試み: UAT-xxx・ST-xxx の ID を追跡表に先に採番しておけば（テストケース本体は後でよい）NG=0 は達成できる余地がある。ひな形 `02_共通/ひな形/lifecycle/08-acceptance-test.md:15-16` に `UAT-001`・`UAT-0xx` の行がある。だが `spec-agent.md`・`aidd-lead.md` に UAT/ST を前もって採番する指示は無い（`grep -n "UAT\|ST-\|採番"` の出力 0 件）。採番が左側（要件）からの導出か、右側の工程の成果かの設計判断は別途要る。
  - 実行はしていない（段1 の合成プロジェクトでの NG=1 の記録を信頼）。
- 深刻度の見直し: High から Medium が妥当。ID を前倒しで採番すれば回避できる。ただし回避の手順が agent に書かれていないため、現状の文書どおりに動くと満たせない点は維持。

## S4-cc-subagents-01

- 結果: 判定不能
- 根拠:
  - 現物: `aidd-lead.md:4` は `tools: Read, Grep, Glob, Bash, Write, Edit, Task`。`git grep -n "claude --agent\|--agent" -- 01_利用者向け資料 README.md INDEX.md 00_導入` の出力は 0 件。README.md:112・INDEX.md:81 は「aidd-lead に投げるだけ」と書く（段1 のとおり）。変更なし。
  - 反証の材料: 本担当の実行環境では、サブエージェントとして起動された私の道具一覧に `Agent` が含まれている（タスク定義の `general-purpose` 系は「Tools: *」）。つまり「サブエージェントには Agent 道具が一律に外れる」とは言えない。ただし、これは本ハーネスの設定で、aidd-lead のように `tools:` を明示列挙した定義（`Task`）の背景起動が同じかは別問題。
  - 背景起動で `Agent` が外れる記述は公式文書の引用（主張）で、私は再現していない。サブエージェントを実際に起動する検証は、今回の制約（ツール呼び出し数・他担当への影響）から行っていない。
- 同時判定: S4-cc-subagents-02 — 維持（論理上）。aidd-lead は工程 1・8 で人間を待つ前提（`aidd-lead.md:12-19,46`）だが、サブエージェントは結果を返して終わる構造であり、その場で利用者の返答を待つ手段は、定義の側に書かれていない。ただし文書の主張のままで、実機の再現はしていない（状態は主張）。
- 深刻度の見直し: S4-01 は High から Medium（上の反証材料で、一律に外れるとは言えないため）。S4-02 は High 維持。

## 集計表

| ID | 結果 | 深刻度 |
|---|---|---|
| I7-rules-01 | 維持 | Critical→High |
| C5-codex-agentsmd-01 | 維持 | High |
| R1-prs-01（同時） | 維持（過去事象） | High→Low〜Medium |
| I1-hooks-01 | 判定不能 | Critical→High（推定） |
| I1-hooks-02 | 維持 | High |
| I7-rules-02 | 維持 | High |
| R2-lessons-02 | 維持 | High→Medium |
| I6-agents-commands-01 | 維持 | Critical |
| C4-bmad-agentos-01 | 維持 | High |
| I6-agents-commands-02 | 維持 | High→Medium |
| S4-cc-subagents-01 | 判定不能 | High→Medium |
| S4-cc-subagents-02（同時） | 維持 | High |

主対象 10 件・同時判定 2 件（R1-prs-01・S4-cc-subagents-02。表は 12 行。2026-11-23 15:35 本線が照合 W5 の指摘で表記を訂正。結果は変えていない）。反証された発見は 0 件。

注: 依頼文の同時判定は 「I7-rules-01 と C5-codex-agentsmd-01（同時判定: R1-prs-01）」「I6-01 と C4-01」「S4-01（同時判定: S4-02）」で、主対象 10 件は I7-rules-01・C5-01・I1-hooks-01・I1-hooks-02・I7-rules-02・R2-lessons-02・I6-01・C4-01・I6-02・S4-01、同時判定は R1-prs-01 と S4-02 の 2 件。表の 12 行は主対象 10＋同時判定 2 に一致する。上の節立てでは C5-01・C4-01 を代表の節に併記した。

## 未確認

- I1-hooks-01: 16:14 の停止の原因（transcript 書き込み遅れ）。遅延を組んだ再現は `sleep` 禁止で未実行。本体 hook の待ちを超える遅れが実運用で起きる頻度は未測定。
- I1-hooks-02: 実際の Claude Code が書く `queue-operation` の形式が、実験で組んだ JSONL と同じかは未確認。
- instruction-guard の実行: 今回は動かしていない（段2 の実測を引用）。
- R2-lessons-02: 18/68 件の再計算は未実施。
- C5-codex-agentsmd-01: 導入先の修正済み estimate_guard の現状と、キットからの入れ直しで deny になる実挙動は未実行。
- I6-agents-commands-01・02: check_approval.py・trace-check.sh は今回実行せず、段1・段2 の実測と静的読解に依拠。
- S4-cc-subagents-01・02: サブエージェントとしての背景起動の再現は未実施。
- 導入先 `install.sh` の再導入で `見積：` に戻る点（I7-rules-01 の深刻度見直しの根拠）は、コード読解のみで実行していない。

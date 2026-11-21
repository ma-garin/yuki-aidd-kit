# I7-rules 段2（深掘り）: rules・規約文書

- 入力: `docs/research/2026-11-21/stage1/I7-rules.md`（14 件。Critical 1・High 3）
- 選定: 影響の大きい順に I7-rules-01（Critical）・I7-rules-02（High）・I7-rules-04（High）。I7-rules-03（間隔 4 通り）は文書間の矛盾で段1の引用が既に再現手順を兼ねるため外した。
- 実行日時: 2026-11-21 16:50 頃（Asia/Tokyo）
- 共通の前提:
  - `K=/Users/fujimagariyuki/dev/active/04_AI開発基盤/yuki-aidd-kit/.claude/worktrees/research-20261121`
  - `S=<scratchpad>/i7`（一時ディレクトリ。hook の状態ファイルは `TMPDIR=$S` で実環境から切り離した）
  - 制約により、名前が constitution で始まるファイル（hook 本体を含む）は今回読まず実行もしていない。最初に `git show HEAD:<その hook>` で一時ディレクトリへ写そうとしたが、自動モードの分類器に拒否された。そのため hook 本体に関する記述はすべて段1の静的読解の引用で、「未実行」と明記する。

---

## I7-rules-01 導入先の見積書式「見積もり：」を hook が受けず、規約どおり書くとツールが止まる
- 深刻度: Critical（維持）
- 結果: **再現**（instruction-guard で再現）／constitution-gate 側は**未実行**（制約による。段1の静的読解だけ）
- 両側の該当行:
  - 導入先 `~/.claude/rules/aidd-kit/absolute-rules.md:8` A-2「応答の1行目を `見積もり：N分（HH:MM）`」。同 `:18` A-2a 開始行「【見積もり：N分 \| 開始:HH:MM …】」
  - 導入先 `~/.claude/AGENTS.md:14`「利用者向け見積は「見積もり：x分（HH:MM）」」。同 `:25` も `見積もり：`
  - kit `02_共通/rules/absolute-rules.md:8`・`04_Codex/AGENTS.md.template:6,17` はどちらも `見積：`
  - `03_ClaudeCode/hooks/instruction-guard.py:43` `ESTIMATE_RE = re.compile(r"見積[:：]\s*(?:残り)?\s*\d+\s*分\s*[（(]…")`、`:47-48` `METER_START_RE = …【\s*見積[:：]…`
- 再現手順（正規表現だけ）:
  ```sh
  cd $K/03_ClaudeCode/hooks && python3 -I -c '
  import re; src=open("instruction-guard.py",encoding="utf-8").read()
  ns={"re":re}; exec([l for l in src.splitlines() if l.startswith("ESTIMATE_RE")][0],ns)
  for s in ["見積：5分（16:40）","見積もり：5分（16:40）","見積:5分(16:40)"]: print(s, bool(ns["ESTIMATE_RE"].search(s)))'
  ```
- 再現手順（hook に入力を流す）: transcript を 2 行（user の指示＋assistant の本文）の JSONL として作り、PreToolUse の入力を流す。
  ```sh
  mk(){ python3 -I -c 'import json,sys; u,a=sys.argv[1],sys.argv[2]
  print(json.dumps({"type":"user","message":{"role":"user","content":u}},ensure_ascii=False))
  print(json.dumps({"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":a}]}},ensure_ascii=False))' "$1" "$2" > "$3"; }
  mk "hook を直して" "見積もり：5分（16:40）\n着手します" $S/B.jsonl
  echo "{\"session_id\":\"t-B\",\"transcript_path\":\"$S/B.jsonl\",\"tool_name\":\"Read\",\"tool_input\":{}}" \
    | TMPDIR=$S python3 -I $K/03_ClaudeCode/hooks/instruction-guard.py
  ```
- 実測結果:

  | 本文 | 正規表現 | hook の判定 |
  |---|---|---|
  | `見積：5分（16:40）` | True | 許可（出力なし） |
  | `見積もり：5分（16:40）` | False | **deny** |
  | `【見積もり：5分 \| 開始:16:35 \| 終了:16:40 \| タスク数：2】` | False | **deny** |
  | `見積:5分(16:40)` | True | （未実行） |

  - deny の理由文は「完了予定つきの見積が無い。本文に `見積：N分（HH:MM）` … を出してから進む（A-2。例外なし）」。estimate の deny は `already_denied` を通らないため（`instruction-guard.py:280-284`）、**同じ指示の間はツールのたびに deny され続ける**。
  - 状態ファイル: `ls $S | grep -c instruction-guard-` → 0（estimate の分岐は状態を書かない）。
- 補足: 導入先に `~/.claude/rules/aidd-kit/absolute-rules.md.bak-20261121` が同居しており、導入先だけが手で書き換えられた状態。`install.sh:98-101` は rules を導入先へ上書きコピーするので、再導入すれば `見積：` に戻る（コード読解。実行はしていない）。
- constitution-gate.py（全ツール停止を書く hook）: 段1の静的読解では `EST_RE = ^[ \t]*【?見積[:：]…`（37 行）で同じ不一致になる。今回は制約により**未実行**。

## I7-rules-02 A-2 の「対象外（質問・確認・文書だけ）」を hook が判定せず、見積の無い応答を止める
- 深刻度: High（維持）
- 結果: **再現**（instruction-guard で再現）／constitution-gate の `CODING_RE` は**未実行**（制約による）
- 両側の該当行:
  - kit・導入先とも `absolute-rules.md:8` A-2 発動条件「コーディングを含む作業の前。質問・説明・確認・記録・文書や設定だけの更新は対象外」
  - `instruction-guard.py:209-210` `if not any(has_estimate(r) for r in replies): return ("estimate", inst)` には作業の種類による分岐が無い。日本語の人の発言すべてが対象になる。`:281` で deny する。
- 再現手順: I7-rules-01 と同じ `mk` を使い、指示と本文だけを変えて流す。
  ```sh
  mk "テスト戦略について説明して" "テスト戦略は次のとおりです。" $S/D.jsonl   # 質問
  mk "settings.json の差分を確認して" "差分を確認します。" $S/E.jsonl         # 確認
  mk "README に1行追加して" "文書だけの更新なので見積は不要です。" $S/F.jsonl  # 文書だけ
  # 各々を I7-rules-01 と同じ echo … | TMPDIR=$S python3 -I instruction-guard.py に流す
  ```
- 実測結果: D（質問）・E（確認）・F（文書だけ）の **3 件ともツール呼び出しが deny**。A-2 で対象外とされる作業でも、見積を書かなければ Read すら通らない。
- 帰結: 規約の「対象外」は実際には存在しない。利用者が見る応答には、質問への回答にも `見積：N分（HH:MM）` が必要になる（AGENTS の「回答はシンプルかつ簡潔」と衝突）。
- constitution-gate の `CODING_RE`（「説明して」「確認して」「続けて」でも True になる）は、段1が正規表現を切り出して当てた結果の引用のみ。今回は**未実行**。

## I7-rules-04 再導入（install.sh）で導入先 AGENTS.md に足した規約 3 節が消える
- 深刻度: High（維持）
- 結果: **再現**（install.sh の該当 2 行だけを一時 HOME で再生）
- 該当行: `00_導入/01_インストール/install.sh:38-43`
  ```sh
  if [ -f "$CLAUDE_DIR/AGENTS.md" ]; then
    cp "$CLAUDE_DIR/AGENTS.md" "$CLAUDE_DIR/AGENTS.md.bak"
    echo "⚠ 既存のAGENTS.mdを AGENTS.md.bak に退避（手動マージ推奨）"
  fi
  cp "$KIT_DIR/04_Codex/AGENTS.md.template" "$CLAUDE_DIR/AGENTS.md"
  ```
- 再現手順（install.sh 全体は実行せず、この 2 行だけを一時ディレクトリで再生）:
  ```sh
  T=$S/home/.claude; mkdir -p $T; cp ~/.claude/AGENTS.md $T/AGENTS.md
  CLAUDE_DIR=$T; KIT_DIR=$K
  [ -f "$CLAUDE_DIR/AGENTS.md" ] && cp "$CLAUDE_DIR/AGENTS.md" "$CLAUDE_DIR/AGENTS.md.bak"
  cp "$KIT_DIR/04_Codex/AGENTS.md.template" "$CLAUDE_DIR/AGENTS.md"
  for h in "速く届ける進め方" "2026-10-25 事故の再発防止" "見積・途中報告の実行ゲート" "context-size-guard" "上限は設けない" "依頼: "; do
    echo "$h after=$(grep -c "$h" $T/AGENTS.md) bak=$(grep -c "$h" $T/AGENTS.md.bak)"; done
  ```
- 実測結果:
  - 6 語すべてで after=0 / bak=1。再導入後の AGENTS.md から、利用者指示の 3 節（速く届ける進め方 2026-11-14・事故の再発防止 2026-10-25・実行ゲート 2026-10-25）と、`依頼: ...` 行・委譲上限の撤廃が消える。
  - `wc -c`: テンプレート 17,042 B、導入先 22,422 B。`diff … | grep '^> ##'` で導入先だけにある節は上の 3 つ。
  - 導入先が名指しする `context-size-guard.py`・`subagent-budget.py` は `~/.claude/hooks/` にだけ実在し、`git ls-files | grep -c` → 0（kit で追跡されていない）。
  - `.bak` は 1 世代だけで、2 回目の再導入で上書きされる（`cp` で固定名に書く。コード読解）。
  - `verify.sh:31` は `check "AGENTS.md…" "$CLAUDE_DIR/AGENTS.md"` で**存在だけ**を見る。テンプレートとの差分は検知しない。
- 帰結: 利用者が最新の指示として足した規約が、kit を更新して再導入するたびに黙って消える。「手動マージ推奨」の 1 行だけが警告になる。

---

## 再現できなかったこと・未実行
- constitution-gate.py の実行（I7-rules-01・02 の全ツール停止側）: 制約（constitution で始まるファイルを読まない）により未実行。`git show` での一時コピーは分類器に拒否された。
- install.sh 全体の実行: 実環境 `~/.claude` に触れるため実行せず、該当 2 行だけを再生した。
- `instruction-guard.py` が実環境の hooks 設定で PreToolUse に配線されているか: 未確認（settings を読んでいない）。

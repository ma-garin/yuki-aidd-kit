# I2-tools 内部実装: 検査ツール・スクリプト（段2 深掘り）

- 入力: `docs/research/2026-11-21/stage1/I2-tools.md`（High 6 件・Medium 4 件・Low 6 件）
- 選定: High の中から影響の大きい順に 3 件を選んだ。基準は「赤のはずの成果物をゲートが緑（exit 0）で通すかどうか」と「普段の書き方の揺れで起きるかどうか」
  1. I2-tools-01: 工程ゲート（test-metrics --gate）が FAIL 1 件・合格率 50% で「進める」を返す
  2. I2-tools-06: コミットゲート（pre-commit-ui-gate.sh）が fail-open になっている
  3. I2-tools-03: 追跡検査（trace-check.sh）が空欄だらけの追跡表を NG=0 にする
  - 選ばなかった High: 02（パスに空白があるとき）・04（ファイル数を出さない）・05（打ち間違えたパス）。どれも「対象を飛ばす」系で、03 と同じ欠陥クラス（判定不能を合格に数える）に入る
- 環境: macOS Darwin 27.2・bash 3.2・python3。実行はすべてスクラッチパッドの `s2-i2/` 配下で行った。リポジトリのファイル・実リポジトリの git・`~/.claude` には書いていない
- 再実行の準備（各件の共通変数）:
  ```bash
  K=/Users/fujimagariyuki/dev/active/04_AI開発基盤/yuki-aidd-kit/.claude/worktrees/research-20261121
  S=$(mktemp -d)   # 実測では <scratchpad>/s2-i2 を使った
  ```

---

## I2-tools-01 test-metrics --gate が書式を読めない基準の行を黙って捨て、FAIL があるのに「進める」で exit 0 を返す
- 深刻度: High（ISTQB の severity では Major。出口基準の判定が逆になり、工程が誤って進む）
- 原因の箇所: `02_共通/ツール/test_metrics.py:480-482`
  ```python
  m = CRITERIA_RE.search(thr)
  if not m:
      continue          # 出典が空の行は dropped に数えるが、書式が読めない行は数えずに捨てる
  ```
  `CRITERIA_RE`（:52）が受け付けるのは `progress|pass_rate|severe_open|open_defects|unread|failed` と ASCII の比較演算子だけ。`gate_code`（:505-510）は残った基準だけで 0/1/2 を決める
- 再現手順:
  ```bash
  mkdir -p $S/tm/docs/lifecycle $S/tm/docs/test
  cat > $S/tm/docs/lifecycle/07-system-test.md <<'EOF'
  | ID | REQ-N | 結果 | 実施日 | 実施者 |
  |---|---|---|---|---|
  | ST-001 | REQ-N-001 | pass | 2026-09-17 | A |
  | ST-002 | REQ-N-001 | fail | 2026-09-17 | A |
  EOF
  mk() { cat > $S/tm/docs/test/$1.md <<EOF
  | No | 基準 | しきい値（機械が読む） | 出典 |
  |---|---|---|---|
  | 1 | 消化 | \`progress >= 100\` | ISTQB |
  | 2 | 失敗なし | $2 | ISTQB |
  | 3 | 合格率 | $3 | ISTQB |
  EOF
  }
  mk A '`failed ≦ 0`' '合格率 95% 以上'        # 人が書きがちな書式（全角の ≦・日本語）
  mk B '`failed <= 0`' '`pass_rate >= 95`'    # 対照: 読める書式
  for c in A B; do python3 $K/02_共通/ツール/test_metrics.py --root $S/tm --criteria $S/tm/docs/test/$c.md \
    --today 2026-09-20 -o $S/r$c.md --gate; echo "exit=$?"; done
  ```
- 実測結果:

  | 基準表 | 評価された行 | 判定 | exit |
  |---|---|---|---|
  | A（≦・日本語） | 1 行（消化のみ） | 進める | 0 |
  | B（対照） | 3 行 | 進めない | 1 |

  - A の出力: `✓ 1. 消化: progress >= 100（実測 100.00）` → `判定候補: **進める**（機械が読める基準はすべて ✓…）`。行 2・3 は捨てた件数も警告も出ない
  - B の出力: `✗ 2. 失敗なし: failed <= 0（実測 1）`・`✗ 3. 合格率: pass_rate >= 95（実測 50.00）` → `進めない`
  - 同じテスト結果（pass 1・fail 1、合格率 50.0%）なのに、基準の書き方だけで exit が 1 から 0 に変わった
- 付随の観察: `--criteria` に相対パス（`tm/docs/test/A.md`）を渡すと `--root` 基準で解決され、ファイルが見つからず「判定できない」exit 2 になった。こちらは安全側（exit 2）だが、「ファイルが無い」とは出ない
- 判定: **再現**

## I2-tools-06 pre-commit-ui-gate.sh が fail-open になっている（.tsx/.vue/.scss は素通り、未来日付のマーカーで通る、ハッシュ計算に失敗すると時刻だけで通る）
- 深刻度: High（Major。UI 変更を E2E 未実行のままコミットできる。AGENTS.md の「UI 変更は `.ui-verified` 無しにコミットしない」と A-14 の「判定不能は deny」の両方に反する）
- 原因の箇所: `02_共通/ツール/pre-commit-ui-gate.sh`
  - :17 `--diff-filter=ACM`（改名 R は対象外。これは静的に読んだだけで、シムでは再現していない）
  - :20-23 UI と見なすのは `*.html|*.js|*.css` だけ。`ui-hash.py:20` も `UI_EXTENSIONS = {".html", ".js", ".css"}`
  - :47-48 `AGE=$(( now - EPOCH ))` の `-le` 判定。AGE が負でも通る
  - :51-54 `scripts/ui-hash.py` が無ければハッシュ検査を丸ごと飛ばす。実行に失敗したら `[WARN]` を出して時刻だけで合格にする
- 再現手順（git はシムに差し替える。実リポジトリには触れない）:
  ```bash
  G=$K/02_共通/ツール/pre-commit-ui-gate.sh
  mkdir -p $S/pc/bin $S/pc/proj/scripts
  cat > $S/pc/bin/git <<'EOF'
  #!/bin/bash
  case "$1 $2" in
    "rev-parse --show-toplevel") echo "$FAKE_ROOT";;
    "diff --cached") printf '%s\n' $FAKE_STAGED;;
  esac
  EOF
  chmod +x $S/pc/bin/git; R=$S/pc/proj; export FAKE_ROOT=$R PATH=$S/pc/bin:$PATH
  FAKE_STAGED="src/App.tsx src/B.vue s.scss c.svelte d.jsx" bash $G; echo "exit=$?"   # 1
  FAKE_STAGED=index.html bash $G; echo "exit=$?"                                      # 2 対照
  echo "x x 2099-01-01T00:00:00+09:00" > $R/.ui-verified
  FAKE_STAGED=index.html bash $G; echo "exit=$?"                                      # 3
  printf 'import sys; sys.exit(3)\n' > $R/scripts/ui-hash.py
  echo "abc123 abc123 $(date -Iseconds)" > $R/.ui-verified
  FAKE_STAGED=index.html bash $G; echo "exit=$?"                                      # 4
  echo 'print("zzz")' > $R/scripts/ui-hash.py
  FAKE_STAGED=index.html bash $G; echo "exit=$?"                                      # 5 対照
  echo "abc123 abc123 garbage" > $R/.ui-verified
  FAKE_STAGED=index.html bash $G; echo "exit=$?"                                      # 6 対照
  ```
- 実測結果:

  | # | 入力 | 出力の要点 | exit |
  |---|---|---|---|
  | 1 | tsx/vue/scss 等・マーカー無し | 何も出ない | 0 |
  | 2 | html・マーカー無し | BLOCKED | 1 |
  | 3 | 2099 年のマーカー | PASS（-2275628978秒前） | 0 |
  | 4 | ハッシュ計算が失敗 | WARN の後 PASS | 0 |
  | 5 | ハッシュ不一致 | BLOCKED | 1 |
  | 6 | 時刻が壊れたマーカー | BLOCKED（古すぎ） | 1 |

  - 1 は svelte と jsx も含めて 5 種すべてが素通りした。React・Vue のプロジェクトでは、ゲートがあっても一度も発動しない
  - 3 は「`[PASS] E2E 検証済み（-2275628978秒前）`」と負の秒数のまま合格した。一度未来の時刻を書けば、その後は永久に通る
  - 4 は「`[WARN] UI hash の計算に失敗。タイムスタンプのみで判定します。`」の後に `[PASS]` が出た。ui-hash.py が無いときは WARN も出さずに飛ばす（:51 の条件。段1 で実行済み。今回は 3 がそのケースに当たる）
  - 対照 2・5・6 は正しく BLOCKED になった。壊れた時刻（EPOCH=0）は安全側に倒れている
- 判定: **再現**（改名 R が外れる点だけは静的な確認で、未実行）

## I2-tools-03 追跡表の見出しが「REQ-ID」でないと C5（カバー漏れ）が丸ごと飛び、空欄の追跡表が合格する
- 深刻度: High（Major。要件→設計→受け入れテストの割当が空でも V 字の追跡ゲートが緑になる）
- 原因の箇所: `02_共通/ツール/trace-check.sh`
  - :198 `if (c[2] ~ /REQ-ID/)` 見出し行は第 2 セルに `REQ-ID` があるときだけ学習する
  - :200-207 列名は `BD`・`DD`・`UT`・`IT`・`ST` は完全一致、`UAT`・`実装` は部分一致でだけ拾う
  - :211 `if (!hdr) next` 見出しを学習しなければ全行を飛ばす。飛ばしたことは出力しない
  - 雛形の見出しは `| REQ-ID | 要件（要約） | 由来 RFD | BD | DD | 実装 T | UT | IT | ST | UAT | 状態 |`（`02_共通/ひな形/lifecycle/traceability-matrix.md:21`）。雛形どおりなら検査は効くが、見出しを和訳しただけで外れる
- 再現手順:
  ```bash
  mkcase() { mkdir -p $S/tc/$1
    printf '# 要件\n## REQ-F-001 貸出\n## REQ-F-002 返却\n' > $S/tc/$1/01_requirement.md
    printf '# 追跡表\n%s\n|---|---|---|\n| REQ-F-001 |  |  |\n| REQ-F-002 |  |  |\n' "$2" > $S/tc/$1/09_traceability.md; }
  mkcase A '| REQ-ID | BD | UAT |'              # 対照（雛形の見出し）
  mkcase B '| 要件ID | BD | UAT |'
  mkcase C '| REQ-ID | 基本設計 | 受入テスト |'
  for c in A B C; do bash $K/02_共通/ツール/trace-check.sh $S/tc/$c; echo "exit=$?"; done
  ```
- 実測結果:

  | ケース | 見出し | 標準出力 | exit |
  |---|---|---|---|
  | A 対照 | REQ-ID・BD・UAT | NG=8（カバー漏れ 8） | 1 |
  | B | 要件ID・BD・UAT | NG=0（定義済み 2） | 0 |
  | C | REQ-ID・基本設計・受入テスト | NG=0（定義済み 2） | 0 |

  - 中身はどのケースも同じで、REQ-F-001・002 の BD・UAT 列は空欄
  - A は「追跡表の BD 列が空欄」「設計未割当」「受け入れテスト未割当」を件ごとに出した（期待どおり）
  - B は見出しを丸ごと学習せず、C5 を全行飛ばした
  - C は見出しを学習したが、列名を 1 つも拾えず（`基本設計` は BD に完全一致せず、`受入テスト` は UAT を含まない）、検査項目が 0 になった。段1 に無かった派生パターンで、「見出しが REQ-ID でも列名の和訳で同じく素通りする」
  - B・C とも「列を認識できなかった」という出力は無く、A との違いは標準出力から分からない
- 判定: **再現**（段1 の B パターンを再現し、C パターンを追加で実証した）

---

## 3 件に共通する欠陥クラス
- 3 件とも「読めない入力を、数えずに捨てる」ことで緑になる（判定不能を合格に数えている）。キットの規約（A-14「判定不能は deny」、trace-check C7・C8 の「判定不能は合格に数えない」）とは逆の実装になっている
- 対照のケース（読める書式・雛形どおりの見出し・.html）では 3 件とも正しく赤になった。雛形から外れたときだけ壊れるので、kit の回帰テスト（雛形で作った入力を使う）では見つからない

## 未確認・未実行
- `--diff-filter=ACM` で改名（R）が外れる点: 静的な確認だけ（シムでは diff-filter の意味を再現できない）
- Linux（GNU awk・GNU date）での挙動: 未確認
- 選ばなかった High 3 件（02・04・05）は段2 では再実行していない（段1 の実証のまま）

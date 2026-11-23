# S1-cc-hooks 段2（深掘り・再現）: Claude Code の hooks 仕様とキットの突合

- 入力: `docs/research/2026-11-21/stage1/S1-cc-hooks.md`（High 3 件・Medium 8 件・Low 5 件）
- 選定: High は 3 件とも選んだ（01・02・03）。選ばなかった High は無い
  1. S1-cc-hooks-01（既存 settings.json に guard が配線されない。I8 段2 の再現が裏付けるかを行単位で確認）
  2. S1-cc-hooks-02（filter-output・pre-read-guard が `permissionDecision: "allow"` を返す）
  3. S1-cc-hooks-03（「hook の例外・時間切れは deny」規約と配線の食い違い）
- 実行環境: ROOT=`/private/tmp/claude-501/-Users-fujimagariyuki-dev-active-01-QA----web-qa-suite/22be64ff-6601-40cb-9e9a-7daa39983e5c/scratchpad/kit-audit`（git worktree）。再現は `mktemp -d` の一時ディレクトリと一時 HOME（`S=/var/folders/lz/vmfc81g93p53cwm220jphs980000gn/T/tmp.z3NLrLJ1up`）だけで行った。実環境の `~/.claude` は読むだけ（hooks 欄の展開と grep）で、書いていない。claude 本体は起動していない
- 実行日時: 2026-11-23 15:15（Asia/Tokyo）前後
- 対象コミット: 3ef90fd（origin/main）

以降のコマンドはすべて ROOT で実行した。

---

## S1-cc-hooks-01 導入スクリプトが既存の settings.json に guard を配線しない
- 段1 の深刻度・状態: High・実証
- I8 段2 との関係: **同じ事象**（I8-install-02）。再現の繰り返しではなく、I8 段2 の記述が S1-01 の主張を行単位で裏付けるかを確かめた。そのうえで I8 段2 の数値を現在のコミットで 1 回だけ追試した
- 行単位の突合:

  | S1-01 の主張 | I8 段2 の記述 | 今回の確認 |
  |---|---|---|
  | install.sh:77-86 は既存 settings.json に手動マージ案内だけ | install.sh:79-83 | `install.sh:79-83` の `if [ -f settings.json ] … echo "⚠ … 手動でマージ" / else cp` を読んで一致。行番号の差は 77-86 が前後の `cp` と `install_guard` 呼び出しを含む範囲のため（誤りではない） |
  | 自動で入るのは指示優先の 3 hook だけ | install_guard.py:23-32 の GUARDS は 6 エントリ・4 ファイル | `install_guard.py:26-34` の GUARDS を読んで一致（tool-timer ×3・instruction-guard・prompt-priority・reply-language） |
  | block-destructive が実環境で 0 | 未配線 21 種 | 下の追試で一致 |
  | 秘密値の書き込み検査（pre-write-check）等が無い | 未配線に pre-write-check.sh | 一致 |

- 再現コマンド（I8 段2 と同じ手順を現行コミットで実行）:
  ```bash
  S=$(mktemp -d); mkdir -p $S/h2/.claude; printf '{"model":"x"}\n' > $S/h2/.claude/settings.json
  HOME=$S/h2 bash 00_導入/01_インストール/install.sh > $S/run2.log 2>&1; echo rc=$?
  # 導入後 settings.json の hook ファイル名とキット配布形の差を python で展開（I8 段2 と同じスクリプト）
  mkdir -p $S/h3; HOME=$S/h3 bash 00_導入/01_インストール/install.sh >/dev/null 2>&1   # settings.json が無い対照
  grep -c block-destructive $S/h3/.claude/settings.json
  grep -c block-destructive ~/.claude/settings.json .claude/settings.json              # 実環境・キット開発用（読むだけ）
  ```
- 出力の要点:
  - install.sh は rc=0。表示は「⚠ settings.json が既存。… 手動でマージしてください」と「✅ settings.json に配線: tool-timer.py ×3, instruction-guard.py, prompt-priority.py, reply-language.py（既存を .bak に退避して merge）」
  - 導入後の hooks: `PreToolUse 2 / PostToolUse 1 / UserPromptSubmit 2 / Stop 1`。ファイルは 4 種（instruction-guard・prompt-priority・reply-language・tool-timer）
  - キット配布形の hook は 25 種。**未配線は 21 種**（I8 段2 と同数）: block-ci・block-deps・block-destructive・block-explore・block-gates・block-phase・config-snapshot・constitution-gate・context-guard・filter-output・injection-guard・log-instructions・observe・post-write-html・pre-compact・pre-read-guard・pre-write-check・ralph-stop・session-context・session-summary・subagent-context
  - hook 本体は一時 HOME の `.claude/hooks/block-destructive.py` に存在する（置いただけで動かない）
  - **対照**: settings.json が無い HOME では `grep -c block-destructive` → `1`。つまり欠陥は「既存 settings.json がある場合」に限られる（新規導入は正常）
  - 実環境（読むだけ）: `grep -c block-destructive ~/.claude/settings.json` → `0`、キット開発用 `.claude/settings.json` → `0`。
- 壊れていない可能性の確認:
  - 新規 HOME では配線される（上の対照）。「配線されない」は既存 settings.json 限定
  - 実環境の hooks を現在の `~/.claude/settings.json` から展開し直すと、PreToolUse に block-ci・git-guard・git-compound-guard・claude-md-guard・tool-timer、UserPromptSubmit に context-size-guard・prompt-priority・record-user-prompt・tool-timer、PostToolUse に tool-timer。**段1 時点（block-ci・prompt-priority・tool-timer）から増えている**。ただし block-destructive・pre-read-guard・pre-write-check・block-gates・constitution-gate は今も無い。キット外の git-guard 系が破壊系 git の一部を代替している可能性はあるが、`rm -rf`・秘密ファイル読み取りの代替は確認していない（未確認）
  - 実環境にキットを導入した履歴があるかは未確認（利用者が手で書いた可能性を排除していない）。したがって「install.sh が原因」は I8 段2 の一時 HOME 再現が示す範囲（導入経路に穴がある）に限り、実環境の現状の原因だとは断定しない
- 判定: **再現（実証）**。I8 段2 が S1-01 を裏付ける。S1-01 の「規約の記述と矛盾（AGENTS.md の「hook が deny」）」は規約文の読解であり、本段では再現対象外
- 段1 からの変更点:
  - 状態は実証のまま。深刻度 High のまま
  - 修正: 段1 は「実環境で block-ci が配線」とだけ書いていたが、現在は git-guard 系・context-size-guard 等も配線されている（段1 から実環境が変化した）。安全系の欠けの結論は変わらない
  - 補足: 原因は install.sh だけでなく、`install_guard.py` の GUARDS が 6 エントリに限られること。対処は両方（I8 段2 の改善方向と同じ）

---

## S1-cc-hooks-02 filter-output.py と pre-read-guard.py が `permissionDecision: "allow"` を返す
- 段1 の深刻度・状態: High・主張
- 再現コマンド:
  ```bash
  J='{"session_id":"t","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"pytest -q"}}'
  echo "$J" | python3 03_ClaudeCode/hooks/filter-output.py; echo rc=$?
  J2='{"session_id":"t","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git diff"}}'
  echo "$J2" | python3 03_ClaudeCode/hooks/filter-output.py; echo rc=$?
  sed -n 205,220p 03_ClaudeCode/hooks/pre-read-guard.py
  grep -n '"deny"' 03_ClaudeCode/hooks/pre-read-guard.py
  ```
- 出力の要点:
  - `pytest -q` → rc=0、標準出力は `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","updatedInput":{"command":"__o=$(mktemp); { pytest -q; } >… exit $__rc"}},"systemMessage":"…"}`。コマンドは書き換えられ、**`allow` が付く**（filter-output.py:101-109 と一致）
  - `git diff` → `permissionDecision":"allow"` 付きで `git diff --stat` に書き換え
  - pre-read-guard.py:213-219: 800 行超の Read で `permissionDecision: "allow"` と `updatedInput.limit` を返す。秘密ファイルの deny（63 行付近の deny 関数）は `main()`（155 行）の前段で判定される構造で、`allow` に到るのは deny に当たらなかった場合だけ（コードの読解。秘密ファイルを実際に通す再現はしていない）
- 壊れていない可能性:
  - 書き換え対象は pytest・install・build・git log/diff 等の限られたコマンド（filter-output.py:27-37）。書き換え後のコマンドは元のコマンドを `{ … }` で包むだけで、別の副作用コマンドを足さない（出力の `{ pytest -q; }` で確認）
  - 段1 の記述どおり、deny・ask ルールは仕様上なお評価され、他 hook の deny が勝つ。ただし**実環境では block-destructive 等が無い**（01）ので、他 hook の deny に頼る前提は今は弱い
  - 利用者の権限設定で既に許可済みのコマンドなら実害は無い。実環境の permissions 欄との突合はしていない（未確認）
- 判定: **一部再現**。hook が `allow` を付けて書き換え済みコマンドを返すことは実証。**その結果、権限確認が飛ぶこと自体は claude 本体を起動していないので未確認**（仕様の記述に依拠）
- 段1 からの変更点: 状態は主張 → 一部再現。深刻度 High は据え置くが、影響は「allow リストに無い pytest／install／build／git が確認なしで走る」に限られ、秘密ファイル deny を迂回する経路は見つかっていないので、High の根拠は 01 との組み合わせ（他の安全 hook が無い環境）が前提。単独なら Medium 相当の可能性（判断は人間）

---

## S1-cc-hooks-03 「hook の例外・時間切れは deny」規約と配線が食い違う
- 段1 の深刻度・状態: High・実証（配線）／仕様は主張
- 再現コマンド:
  ```bash
  sed -n 10p CLAUDE.md
  grep -rn '"onFailure"' --include=*.json . | wc -l
  T=$(mktemp -d)
  for h in block-gates block-ci block-destructive pre-read-guard constitution-gate; do
    echo 'not json' | (cd $T && python3 $ROOT/03_ClaudeCode/hooks/$h.py); echo "$h rc=$?"; done
  sed -n 25,32p 03_ClaudeCode/hooks/block-gates.py; sed -n 42,48p 03_ClaudeCode/hooks/block-ci.py
  grep -n 'exec python3' .claude/settings.json | head -3
  ```
- 出力の要点:
  - `CLAUDE.md:10`: 「hook の例外・時間切れは deny（素通りは合格ではない）」
  - `"onFailure"` の出現 → `0`（json 配線ファイルに無い）
  - 不正な JSON を渡した結果（すべて rc=0。deny は標準出力の JSON で判断）:

    | hook | 不正入力の結果 |
    |---|---|
    | block-gates.py | 出力なし（通す）。`block-gates.py:29-30` の `except … return 0` |
    | block-ci.py | 出力なし（通す）。`block-ci.py:45-46` の `return 0` |
    | block-destructive.py | `permissionDecision: "deny"`（内部エラーも `main()` が deny。540 行付近） |
    | pre-read-guard.py | `deny`（「hook の入力が読めない」） |
    | constitution-gate.py | `deny`（「hook 内部エラー」）。本体は読まず出力だけ見た |

  - `.claude/settings.json` の各コマンドは `[ -f "$f" ] && exec python3 "$f" … || exit 0` の形（12・21・30 行）。**本体ファイルが無ければ黙って通す**
- 壊れていない可能性:
  - 「規約が全 hook に当てはまらない」ことは実証したが、閉じる側（deny）に倒れる hook も実在する（上の表の 3 本）。規約は半分守られている
  - block-gates・block-ci が不正入力で通すのは、この 2 本が「ゲートの無断実行を止める」利便系で、秘密・破壊の防御ではない。通しても取り返しがつかない被害には直結しない（設計判断としては妥当な可能性がある。ただし規約文とは食い違う）
  - 時間切れ・`onFailure` の挙動（仕様）は claude 本体を起動していないため再現していない。仕様の記述に依拠（未確認）
- 判定: **一部再現**。配線に `onFailure` が無い・一部 hook が例外で通す・本体不在で通すことは実証。時間切れの非ブロック（仕様）は未確認
- 段1 からの変更点: 状態は実証／主張の混在 → 一部再現。深刻度は High → Medium への引き下げを提案する（理由: 通す側に倒れるのは block-gates・block-ci の 2 本で、秘密・破壊系 guard の block-destructive・pre-read-guard・constitution-gate は閉じる側に倒れる。残る問題は規約文の不正確さと、時間切れ・本体不在時の素通り）。ただし本体不在で素通りする点は 01 と同根で、配線が欠けた環境では同じ結果になる

---

## 未確認
- claude 本体を起動していないため、`permissionDecision: "allow"` が権限確認を実際に飛ばすか（02）と、PreToolUse 時間切れが非ブロックか（03）は仕様の記述に依拠。実機での確認は未実施
- 実環境 `~/.claude/settings.json` の permissions 欄と 02 の書き換え対象コマンドの突合
- 実環境にキットを導入した履歴があるか（01 の「現状の原因」）。キット外の git-guard 系が rm -rf・秘密ファイル読み取りを代替しているか
- constitution-gate.py の本体（委譲の制約で読まない。出力だけ確認）
- S1-cc-hooks-04〜16 は段2 の対象外（未再現・未検証のまま）
- I8 段2 の OK=107／段1 の OK=106 の差は今回追試していない（verify.sh は実行していない）

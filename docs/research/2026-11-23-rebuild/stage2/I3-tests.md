# I3-tests 回帰テスト（段2・深掘り）

- 入力: docs/research/2026-11-21/stage1/I3-tests.md
- 選定: I3-tests-01（指定）、I3-tests-02（指定）。High はこの 2 件のみのため追加なし。run-all.sh の合格判定・本数・CI 範囲・「壊れていない可能性」を併せて確認
- 実行環境: macOS・python3。hook 単体へ stdin 入力のみ（`mktemp -d` を cwd・HOME・CLAUDE_PROJECT_DIR にした）。回帰テスト・pytest・lint・run-all.sh・CI は実行していない
- 実行日時: 2026-11-23 15:20 頃（JST）
- 対象コミット: 3ef90fd（origin/main）。段1 の対象は 7e80b79

---

## I3-tests-01 main の HEAD で回帰テストが赤（4 本・16 件）
- 確かめたコマンド
  - `git log --oneline 7e80b79..3ef90fd` → 3 件（3ef90fd #135、42f5ffc ステータスライン進捗行、2114f37 調査 docs #134）
  - `git log --oneline 7e80b79..3ef90fd -- 04_Codex 06_保守者向け/03_回帰テスト 03_ClaudeCode/skills` → 0 件
  - `git log -3 -- 04_Codex/skills-manifest.json` → 最終更新は e4c3334（#123）。以降更新なし
- 判定: 段1 の時点から今までの間に、該当テスト・04_Codex 生成物・skills を直したコミットは無い。赤の原因（04_Codex/skills-manifest.json が生成物と食い違う: design-system・uiux_review）を直す変更が入っていないので、今も赤である可能性が高い。ただし今も赤かは実行しないと分からない
- 赤だった 4 本（段1 の実測の転記。今回は未再現）
  - test-skill-lint.sh: 生成物とマニフェストが最新でない（`--check` exit 1）
  - test-kit-checks.sh: doctor D7 Codex 生成物 NG（同原因）
  - test-install.sh: 04_Codex/skills が 03_ClaudeCode からの生成と不一致（同原因）
  - test-check-docs.sh: spec 同期 33 件 NG ほか（原因は同系統と段1 が読解。今回は追確認していない）
- 段1 からの変更点: 状態を「実証」から「一部再現」へ。実測は段1 のもの。今回確かめたのは「修正コミットが無い」ことだけ。「#133 は赤のままマージ」は、段1 の主張で今回は未確認
- 状態: 一部再現（修正コミット無しを確認・赤の再現は未実施）
- 未実施: 要: 保守者の要求による run-all.sh の実行

## I3-tests-02 block-gates・block-ci・block-phase は入力が読めないと素通り（fail-open）
- 根拠（ファイル:行、03_ClaudeCode/hooks/）
  - block-gates.py:28-30 `json.load` 失敗 → `return 0`（許可）
  - block-ci.py:45-47 同じ
  - block-phase.py:59-61 同じ
  - 対照: block-deps.py:152-164 は `except Exception` で deny（fail-closed）と docstring 12 行に明記。pre-read-guard.py:23 も同様
  - 規約: absolute-rules A-14「判定不能は deny」（段1 が 02_共通/rules/absolute-rules.md:21 を引用）
- 単体実測（一時 dir・stdin のみ。rc は終了コード）

| hook | 空 | not json | `[1]` | `null` | `{}` |
|---|---|---|---|---|---|
| block-gates | 0 | 0 | 1（例外） | 1（例外） | 0 |
| block-ci | 0 | 0 | 1（例外） | 1（例外） | 0 |
| block-phase | 0 | 0 | 1（例外） | 1（例外） | 0 |
| block-deps | deny | deny | deny | deny | 0 |

  - 空・not json は出力なしの rc=0（許可）。block-deps だけ `permissionDecision: deny`
  - 正常な deny 入力（`pytest`、`gh run watch`）では block-gates・block-ci とも deny を返す＝通常経路は動いている
- 新規の発見: `[1]`・`null` のような JSON として正しいが辞書でない入力では、3 本とも `data.get` で AttributeError の Traceback になり rc=1。Claude Code では exit 1 は blocking でないエラーとして扱われ、ツールは実行される見込み（この扱いは公式仕様の確認はしていない。未確認）。結果として fail-open
- 実際に起きうるか: Claude Code は常に正しい JSON を渡す前提なので、通常運用での発生確率は低い。壊れた入力は hook 側の不具合・将来のスキーマ変更時に顕在化する（推測）
- テスト側: 壊れた入力のテストがあるのは 6 本（段1 の grep 結果。今回未再検証）
- 段1 からの変更点: 「実証」を維持。段1 は not json のみ。今回、空 stdin・`[1]`・`null` を追加して実測。`[1]`/`null` は rc=1（例外）で、deny でも明示許可でもない点を追記
- 深刻度: High 維持（ただし発生確率は低い。影響は H-7・CI 禁止・工程承認の 3 ゲートが無効化されうる点）
- 状態: 実証

## run-all.sh の合格判定
- 実装（06_保守者向け/03_回帰テスト/run-all.sh）
  - 12 行付近: `for t in "$DIR"/test-*.sh` を glob で実行し、見つけた数 FOUND と実行した数 RUN を数える
  - 末尾: `[ "$RUN" -eq "$FOUND" ] && [ "$FAIL" -eq 0 ] && exit 0`、他は exit 1
  - ゲートなので `GATES_REQUESTED` が無ければ exit 2
- 維持すべき: glob で CI の yml に本数を手書きしない設計（掲載漏れの再発防止）、RUN と FOUND の突合、失敗行（❌）を先に出す点。正しく働いている
- 抜け穴（コード読解のみ。run-all.sh は実行していない。未実測）
  - FOUND=0 でも RUN=0・FAIL=0 で exit 0 になる。コメントは「RUN≠FOUND」を検出としているが、0 本の場合は等しいので合格する。0 本実行を検出する下限が無い
  - RUN は FOUND と同じ箇所で増えるため、実質 RUN≠FOUND は起きない（`continue` は `-f` 失敗の場合のみ。その場合は FOUND にも入らない）。突合は形だけ
  - 各 test が内部で SKIP して exit 0 になっても合格に数える。27 本が `exit 0` を含む（grep）。SKIP を使うのは test-external-skills.sh:108・test-kit-checks.sh:231 など。いずれもその分岐自体を検証するケースで、検査の抜けではない（読解）
- 判定: 通常は機能している。下限（FOUND>=1、できれば期待本数）が無いのが弱点。段1 に無い新規の指摘（Low〜Medium）

## テスト本数と CI の範囲
- `ls 06_保守者向け/03_回帰テスト/test-*.sh | wc -l` → 31。test-ui-catalog.py は別（glob は `.sh` のみ）
- kit-ci.yml: `on: workflow_dispatch` のみ。run-all.sh（31 本）・check-design.sh・check-docs.sh を呼ぶ
- 引き継ぎ「現行 31 テストが CI で未実行」: 本数 31 は一致。ただし「未実行」の意味は、自動起動しない（手動のみ）ためと読める。CI の定義上、手動で起動すれば 31 本とも走る（yml・glob の読解）。実際に Actions で走るかは未確認
- Python のテスト 4 本（test-ui-catalog.py・04_Codex の 3 本）は run-all の glob にも CI にも含まれない（`git grep` で呼び出し箇所なし。段1 の I3-tests-03 と一致）

## 壊れていない可能性
- I3-tests-01: 赤の原因は 1 回の実行結果。今の main で再度赤かは未確認。コミット履歴上は直した形跡が無いので、残っている可能性が高い
- I3-tests-02: 通常の deny 入力では両 hook が正しく deny する。壊れた入力でのみの問題で、通常運用には影響しない
- run-all.sh の突合・glob・ゲート設計は機能している

## 未実施・未確認
- 未実施（要: 保守者の要求による run-all.sh の実行）: I3-tests-01 の現時点の赤の再現、4 本の失敗行の再確認、I3-tests-04・05 の確認
- 未確認: Claude Code が hook の exit 1 を非 blocking として扱う仕様（公式資料で確認していない）
- 未確認: run-all.sh の FOUND=0 時の挙動（コード読解のみ。実行していない）
- 未確認: 壊れた入力のテスト 6 本の件数と、I3-tests-03・04・05 の内容（段1 のまま）

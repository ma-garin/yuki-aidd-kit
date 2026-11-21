# I3-tests 内部実装: 回帰テスト（段1・広域）

- 対象: origin/main の worktree（HEAD 7e80b79 "#133"）。テストファイル全件と、hook・スクリプトとの対応
- 調べた方法:
  - `find . \( -name 'test_*.py' -o -name '*_test.py' -o -name '*.bats' -o -name '*.test.*' -o -name '*.spec.*' \)` と `find -iname '*test*'` で列挙
  - hook・スクリプト 85 本のファイル名を、テストファイル全件に対して grep（参照の有無と回数）
  - `GATES_REQUESTED=1` を付けて 1 回だけ実行: `06_保守者向け/03_回帰テスト/test-*.sh` 30 本（1 本は制約で除外。下の「調べられなかったこと」）と Python unittest 4 本
  - 実行時刻 2026-11-21 16:28〜16:31。ログはスクラッチパッド（`.../scratchpad/i3run/`）
- 調べた件数 / 全件数: テストファイル 35 / 36（sh 30/31・Python 5/5。Python のうち `02_共通/ツール/test_metrics.py` はテストでなく本体）。対応を見たスクリプト 85 本と、ひな形・サンプル・スキル同梱の 13 本

## 実行の集計（実測）

| 区分 | 結果 |
|---|---|
| sh 30 本 | 26 本 OK / 4 本 FAIL |
| sh の件数 | FAIL 16 件（check-docs 7・install 2・kit-checks 4・skill-lint 3） |
| test-hooks.sh | PASS=927 / FAIL=0（88 秒） |
| Python unittest | 40 件すべて OK（ui-catalog 5・estimate-guard 9・Codex hooks 10・statusline 16） |

---

## I3-tests-01 main の HEAD で回帰テストが赤（4 本・16 件）
- 種別: 欠陥
- 深刻度: High
- 根拠: 実行の集計（上の表）。失敗した行:
  - test-skill-lint.sh「コミット済みの生成物とマニフェストは最新（--check exit 0）」→ `NG: 04_Codex/skills-manifest.json が生成物と食い違う（2 件）… design-system, uiux_review`
  - test-kit-checks.sh「揃った写しは exit 0」→ doctor `D7 Codex 生成物 NG`（原因は上と同じ）
  - test-install.sh「04_Codex/skills が 03_ClaudeCode から生成した最新の状態（期待 0 / 実際 1）」（原因は上と同じ）
  - test-check-docs.sh「現状のリポジトリで exit 0」→ `NG=34 - spec同期: 33 件`。ほか 5 件が同じ原因で exit 1
  - #133 は赤のままマージされた。`.github/workflows/kit-ci.yml` は `on: workflow_dispatch` だけなので、マージを止めるものが無い
- 状態: 実証
- 改善の方向: マージ前に run-all を 1 回走らせる手順を PR の完了条件に入れる（CI の自動起動は保守者の方針で禁止。手動ゲートとして入れる）。04_Codex の生成物は、生成元を変えた同じコミットで作り直す

## I3-tests-02 block-gates.py / block-ci.py は壊れた入力を素通しする。壊れた入力のテストは 6 本の hook にしかない
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - `printf 'not json' | python3 block-gates.py` → rc=0・出力なし（＝許可）。block-ci.py も同じ。block-deps.py と pre-read-guard.py は同じ入力で `permissionDecision: deny`（「hook の入力が読めない」）を返す
  - `03_ClaudeCode/hooks/block-gates.py:27-30` と `block-ci.py:44-47`: `except (json.JSONDecodeError, ValueError): return 0`
  - `02_共通/rules/absolute-rules.md:21` A-14 は「判定不能は deny」と定めている
  - 壊れた入力のテストがあるのは block-destructive・tool-timer・subagent-context・session-context・observe・ralph-stop の 6 本だけ（test-hooks.sh:245,588,868,1558,1602,1758）。block-gates・block-ci・block-deps・block-phase・injection-guard・instruction-guard・pre-read-guard・pre-write-check・block-explore・reply-language・prompt-priority・filter-output・context-guard の 13 本は 0 件（grep `not json|壊れた入力|読めない`）
- 状態: 実証
- 改善の方向: deny を出す hook すべてについて「not json・空の stdin・入れ子が深すぎる JSON」の 3 入力を表で回すテストを足し、A-14 との食い違いを直す

## I3-tests-03 Python のテスト 4 本（40 件）を run-all も CI も走らせない
- 種別: 欠落
- 深刻度: Medium
- 根拠: `06_保守者向け/03_回帰テスト/run-all.sh:12` が回すのは `"$DIR"/test-*.sh` だけ。kit-ci.yml が呼ぶのは run-all.sh・check-design.sh・check-docs.sh の 3 本だけ。`git grep` しても、`06_保守者向け/03_回帰テスト/test-ui-catalog.py`・`04_Codex/estimate-guard/test_estimate_guard.py`・`04_Codex/hooks/test_codex_hook_adapter.py`・`04_Codex/statusline/test_status.py` を実行する呼び出しは見つからない。手で叩く手順が各 README に書いてあるだけ（`04_Codex/hooks/README.md:15` ほか）。今回の手動実行では 40 件すべて OK
- 状態: 実証
- 改善の方向: run-all.sh が `test-*.py` と `04_Codex/**/test_*.py` も拾うようにし、`RUN=FOUND` の分母に含める

## I3-tests-04 秘密情報のテストは gitleaks の有無で結果が変わる。gitleaks を使う経路のテストは無い
- 種別: 矛盾
- 深刻度: Medium
- 根拠:
  - test-install.sh:238-240 は偽値 `api_key = "sk-abcdefghijklmnopqrstuvwxyz"` をコミットし、「秘密情報」という文言だけを確かめている（終了コードは見ていない）
  - gitleaks が入っているこの端末では FAIL した（`❌ 秘密情報のコミットが止まる（出力に '秘密情報' が無い）`）。`02_共通/ツール/pre-commit:6-10` は gitleaks があれば gitleaks だけで判定するので、エントロピーの低いこの偽値は通ってしまう
  - test-pre-commit-fallback.sh:5 は gitleaks を PATH から外して代替経路だけを試す。gitleaks の経路を試すテストは無い
- 状態: 実証（この端末）。gitleaks の既定ルールがこの値を見逃す理由は未確認
- 改善の方向: gitleaks がある場合も、代替経路のパターン判定を必ず併用する。テストは終了コードも確かめ、両方の経路を明示して回す

## I3-tests-05 kit-ci.yml で回すと test-check-screens.sh は必ず FAIL になる見込み
- 種別: 矛盾
- 深刻度: Medium
- 根拠: test-check-screens.sh:21-26 は playwright が無いと exit 2 を確かめたうえで `exit 1` で終わる。kit-ci.yml の手順は setup-python だけで、playwright と chromium を入れていない。このため run-all は FAIL>0 になる。この端末には playwright があり、PASS=23 だった
- 状態: 未確認（コードを読んだだけ。CI は起動していない）
- 改善の方向: CI に `pip install playwright && playwright install chromium` を足すか、前提が無いときは SKIP として分母から外し、件数を出す

## I3-tests-06 未テストのスクリプトがある（計測の metering.py を含む）
- 種別: 欠落
- 深刻度: Medium
- 根拠: テストファイル全件に対してファイル名で grep し、参照 0 件だったもの:
  - `03_ClaudeCode/skills/work-metering/scripts/metering.py`（192 行。AGENTS.md の「見積・途中報告の実行ゲート」で必須の begin/end を担う）と Codex 側の写し
  - `04_Codex/skills/aidd-kit/scripts/kit_catalog.py`、`04_Codex/native-skills/aidd-kit/scripts/kit_catalog.py`（各 234 行）
  - `00_導入/01_インストール/sync-agent-rules.py`（45 行）、`00_導入/03_点検/audit-app-workspace.sh`（55 行）、`04_Codex/statusline/codex_status_win.py`
  - `02_共通/ひな形/components/icons.js`（152 行）、`02_共通/ひな形/ui/streamlit_theme.py`、`02_共通/ひな形/ui/tailwind.config.js`、`01_利用者向け資料/90_サンプル/図書貸出/build.py`、`06_保守者向け/04_監査記録/enrich_github_meta.py`
  - `install_guard.py` は install-guard.sh 経由で test-install.sh:152-167 が試している（対象外とした）
- 状態: 実証
- 改善の方向: metering.py の begin/mid/end と、記録失敗を「失敗」と表示することのテストを最優先で足す

## I3-tests-07 文書に書いた行数・件数と突き合わせるテストがあり、編集のたびに赤になる
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `06_保守者向け/03_回帰テスト/check_docs.py:512-541` の check_spec_inventory は、`01_構成品目目録.md` に書いた行数（例 `test_metrics.py | 729`）と実際の行数を突き合わせ、ずれると NG にする。check_docs.py:10,251 はケース数（「N ケース」「PASS=N」）と実際の PASS+FAIL も突き合わせる。いまは 33 件ずれており、test-check-docs.sh が 7 件 FAIL する（I3-tests-01）
- 状態: 実証
- 改善の方向: 目録の行数は生成で埋めるか、記載をやめる。変化を検出するだけのテスト（change-detector test）を回帰テストから外す

## I3-tests-08 test-hooks.sh が 1 ファイル 1866 行・927 件に膨らんでいる
- 種別: 過剰
- 深刻度: Low
- 根拠: `wc -l` で 1866 行・165,285 バイト。実行は 88 秒で全体の最長。run-all.sh:22 は ❌ を最初の 20 行しか出さないので、1 本の中で失敗が多いと見えなくなる。利用者規約（engineering.md）の上限は 800 行
- 状態: 実証
- 改善の方向: hook ごとのファイルに分け、run-all の FOUND 数にそのまま現れるようにする

## I3-tests-09 本数だけ数える配置テストと、閾値の弱い assert
- 種別: 欠落
- 深刻度: Low
- 根拠:
  - test-install.sh:54-66,185-190,388 の `expect_count` は、skills・commands・agents・hooks・docs の個数だけを比べ、中身や名前の一致は見ていない。個数が同じなら、空ファイルや別名のファイルでも通る
  - test-install.sh:191 は rules を 10 個と直値で決めている
  - test-install.sh:214 は「少なくとも 1 件」、test-check-design.sh:625 は `-ge 12` しか見ていない
- 状態: 実証（コードを読んで確かめた。偽陽性の再現まではしていない）
- 改善の方向: ファイル名の一覧の差分か、ハッシュの一致で比べる

## I3-tests-10 受入基準とつながっているテストは ui-catalog の 1 本だけ
- 種別: 欠落
- 深刻度: Low
- 根拠: REQ-ID を自分の受入基準として参照しているのは `test-ui-catalog.py:2`（REQ-UI-001..004）と `docs/lifecycle/ui-catalog/VERIFICATION.md:3` だけ。test-trace-check・test-test-metrics・test-req-lint にある REQ-ID は、検査に流すために作ったデータ。sh 30 本は B-xx（09_指摘事項）や日付をコメントに書いているが、指摘からテストへの機械的な追跡は無く、trace-check.sh をキット自身には当てていない
- 状態: 実証（grep で数えた）
- 改善の方向: 09_指摘事項の ID をケース名に入れる規約を決め、指摘 → テストの対応を検査する

## I3-tests-11 キットの mutate-quick.py・oracle-lint.py を、キット自身のテストに当てていない
- 種別: 機会
- 深刻度: Low
- 根拠: `git grep mutate-quick -- 06_保守者向け` の結果は、目録の 1 行と test-oracle-tools.sh:70（作ったデータの library.py に当てるだけ）しかない。I3-tests-02 のように hook が素通しする欠陥は、変異（mutation）を入れれば見つかる種類
- 状態: 実証（使っていないことを grep で確かめた）
- 改善の方向: deny を出す hook を対象に、mutate-quick を定期の手動点検として回す

## I3-tests-12 時間に依存するテストの揺れ
- 種別: 欠陥
- 深刻度: Low
- 根拠: test-hooks.sh に sleep が 7 か所ある。tool-timer の秒数は +1 秒の許容幅で判定している（test-hooks.sh:7,563,571）。今回の 1 回では揺れは出なかった
- 状態: 未確認（再現していない）
- 改善の方向: 時計を差し替えられるようにする（環境変数で now を渡す）

## I3-tests-13 本体の test_metrics.py が、テストのファイル名の形をしている
- 種別: 欠陥
- 深刻度: Low
- 根拠: `02_共通/ツール/test_metrics.py`（729 行）は本体だが、名前が `test_*.py` に当たる。init-test-docs.sh は配布先の `scripts/test_metrics.py` に置く（test-test-metrics.sh:261）。配布先で pytest が拾うかどうかは試していない
- 状態: 未確認
- 改善の方向: `metrics_report.py` などへ改名を検討する（配布先の互換に注意）

## 調べられなかったこと
- `test-constitution-gate.sh`: 今回の制約（停止状態を作りうる対象に触れない）に従い、中身を読まず実行もしていない。run-all.sh の glob には含まれるため、run-all の本来の分母は 31 本
- CI（kit-ci.yml）の実際の実行結果: 起動していない（I3-tests-05 は推定）
- gitleaks の既定ルールが I3-tests-04 の偽値を見逃す理由
- 1 回しか実行していないので、揺れのあるテストを特定できていない
- worktree に、追跡されていない `.claude/ai-config-log.jsonl`（16:30:13 SessionStart）が出た。中身に実セッションの環境キーが入っており、テストからの漏れでなく並走セッションの config-snapshot hook が書いたと推定する（未確認）
- 外部の研究・規格との照合（変化を検出するだけのテストの害、mutation score の基準など）は段1 の範囲外として、行っていない

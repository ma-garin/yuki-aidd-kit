# I2-tools 内部実装: 検査ツール・スクリプト（段1 広域）

- 対象: origin/main の worktree（research-20261121）にある検査ツールと配布スクリプト。trace-check.sh／test-metrics.sh（test_metrics.py）／check-approval.sh（check_approval.py）／check-design.sh（check_design.py）／check-screens.sh（check_screens.py）／quality_harness.py／security-scan.sh／pre-commit-ui-gate.sh／atarimae scan.sh／export-project.sh・init-lifecycle.sh の配布処理／回帰テスト run-all.sh と kit-ci.yml
- 調べた方法: `git -c core.quotepath=false ls-files` で `*.sh`・`*.py` を列挙し、hooks 以外の検査ツールを読んだ（引数・終了コード・件数表示・対象の飛ばし方）。BSD/GNU で違うコマンドは全 `.sh` を grep した。10 本はスクラッチパッドの一時ディレクトリに入力を作って実行した（読み取りのみ。リポジトリには書いていない）。pre-commit-ui-gate.sh は git を偽の `git` シムに差し替えて実行した（実リポジトリの git は書き換えていない）
- 調べた件数／全件数: 追跡されている `.sh`・`.py` は 52 本（hooks 30 本を含む。`git ls-files | grep -E '\.(sh|py)$' | wc -l` は日本語パスの quote により実際より少なく出るので quotepath=false で数え直した）。このうち検査ツール 13 本を精読し、10 本をサンプル入力で実行した。hooks 30 本は別テーマとして対象外。`02_共通/ツール` の残り（adr-to-rules・cite-check・mutate-quick 等 20 本前後）は回帰テストの有無だけ確かめた

テストの実行はすべて `/private/tmp/claude-501/.../scratchpad/i2a`〜`i2h`。macOS（Darwin 27.2、bash 3.2.57、BSD awk）で実行した。

---

## I2-tools-01 test-metrics --gate が、読めない基準の行を黙って捨て、FAIL があるのに「進める」と exit 0 を返す
- 種別: 欠陥
- 深刻度: High
- 根拠: `02_共通/ツール/test_metrics.py:480-482`（`m = CRITERIA_RE.search(thr)` → `if not m: continue`。出典が空のものは dropped に数えるのに、書式が読めない行は数えずに捨てる）。`gate_code`（:505-510）は残った基準だけで判定する。
  実行: ST-001 pass・ST-002 fail の 07-system-test.md と、§7 の基準 3 行（`progress >= 100`／`failed ≦ 0`／`合格率 95% 以上`、いずれも出典あり）を置いて `test-metrics.sh --root <tmp> --gate` → 「✓ 1. 消化: progress >= 100」の 1 行だけが評価され、「判定候補: **進める**」・exit=0。合格率 50%・fail 1 件の状態でゲートを通った
- 状態: 実証
- 改善の方向: 「しきい値」列が空でなく正規表現に合わない行は判定不能として数え、1 行でもあれば --gate は 2 にする

## I2-tools-02 trace-check.sh は対象のパスに空白があると awk が落ちるのに NG=0・exit 0 を返す
- 種別: 欠陥
- 深刻度: High
- 根拠: `02_共通/ツール/trace-check.sh:79,85,94,130,172`（`$FILES` を引用符なしで展開し、空白で分割される）。awk の終了コードを見ていない（:107-130）。
  実行: `d d/01_requirement.md`（REQ-F-001 を定義）と `d d/02 basic-design.md`（未定義の REQ-F-009 を参照）→ `awk: can't open file d` を出したあと「✅ NG=0（定義済み ID: 0 件）」・exit=0
- 状態: 実証
- 改善の方向: ファイル一覧は NUL 区切りか配列で渡し、awk・python の失敗は判定不能の NG にする（判定不能を合格に数えない、という自分の規約に合わせる）

## I2-tools-03 追跡表の見出しが「REQ-ID」でないと C5（カバー漏れ）が丸ごと飛び、空欄の追跡表が合格する
- 種別: 欠陥
- 深刻度: High
- 根拠: `trace-check.sh:198`（見出し行は `c[2] ~ /REQ-ID/` のときだけ学習する）、:211（`if (!hdr) next`。見出しを学習しなければ全行を飛ばし、飛ばしたことを出さない）。
  実行: 見出しを `| 要件ID | BD | UAT |` にし、REQ-F-001・002 の BD・UAT を空欄にした 09_traceability.md → 「✅ NG=0（定義済み ID: 2 件）」・exit=0。期待は REQ-F ごとに「設計未割当」「受け入れテスト未割当」の NG 4 件
- 状態: 実証
- 改善の方向: 追跡表に REQ 行があるのに見出しを認識できなければ NG（判定不能）にし、認識した列の名前を出力に出す

## I2-tools-04 trace-check.sh は調べたファイル数を出力に出さず、対象を飛ばしたときも NG=0 になる（下位ディレクトリ・ID の無い文書・4 桁 ID・追跡表なし）
- 種別: 欠落
- 深刻度: High
- 根拠: `trace-check.sh:79`（`find -maxdepth 1`。下位ディレクトリを見ない）、:90（ID は 3 桁固定 `[0-9][0-9][0-9]$`）、:248-249（追跡表が無いと C4〜C7 を行わず WARN だけ）、:365-367（標準出力は「NG=0（定義済み ID: N 件）」だけ。ファイル数はレポートの中だけ）。
  実行（すべて exit=0・「✅ NG=0」）: ①ID の無い md だけのディレクトリ → 定義済み ID 0 件 ②`b/sub/01_requirement.md` に定義・`b/sub/zz.md` に未定義参照 → 下位を見ず 0 件 ③`REQ-F-0001`・`REQ-F-1000` → 0 件 ④`--tests` に空のテストディレクトリと行の無い CSV → NG=0（レポートには「0 ファイル・突合対象 0 件」とあるが標準出力には出ない）
- 状態: 実証
- 改善の方向: 標準出力に「検査 n ファイル／指定 m」「定義 0 件」「追跡表なし」を出し、定義 0 件・追跡表なし・突合 0 件は合格に数えない（または --strict で NG にする）

## I2-tools-05 存在しないパス・打ち間違いを渡しても、trace-check・check-design・check-approval（--gate を含む）が exit 0 で通る
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - `trace-check.sh:71-74`（ディレクトリが無ければ「スキップ」exit 0）。実行 `trace-check.sh docs/lifecyle` → exit=0
  - `00_導入/03_点検/check_design.py:202-208`（`collect` は無いパスを黙って捨てる）、:1052-1055（対象 0 件は exit 0）。実行 `check-design.sh --root <tmp> statc src` → 「対象ファイルなし…exit 0」。回帰テストもこれを正としている（`06_保守者向け/03_回帰テスト/test-check-design.sh:119` 「対象ファイルなしは exit 0」）
  - `02_共通/ツール/check_approval.py:365-369`（docs/lifecycle が無ければ、引数の検査より先に exit 0）。実行 `check-approval.sh --root <空> --gate 5` → exit=0、`--phase 99`（範囲外）→ exit=0（ディレクトリがあれば :416-418 で exit 2 になる値）
  - 対照: check_screens.py は無いパスを判定不能に数え（:88-89）、security-scan.sh は無いディレクトリで exit 2 を返す（実行で確認）。キット内で扱いが割れている
- 状態: 実証
- 改善の方向: 明示的に渡したパスが無いときは exit 2 に統一し、「対象が無いのでスキップ」は引数を省略したときだけに限る

## I2-tools-06 pre-commit-ui-gate.sh が fail-open: .tsx/.vue/.scss の変更は素通り、未来日付のマーカーで通る、ui-hash.py が無ければ時刻だけで通る
- 種別: 欠陥
- 深刻度: High
- 根拠: `02_共通/ツール/pre-commit-ui-gate.sh:19-25`（UI と見なす拡張子は `*.html|*.js|*.css` だけ。`--diff-filter=ACM` で改名も外れる）、:43（`AGE=now-EPOCH` が負でも `-le` を通る）、:48-58（scripts/ui-hash.py が無い・失敗したときはハッシュ検査を飛ばす。失敗時は WARN で合格）。
  実行（偽の git シムで staged を与えた）: ①`src/App.tsx src/B.vue s.scss`・マーカーなし → 出力なし exit=0 ②`index.html`・マーカーなし → BLOCKED（対照）③`.ui-verified` の時刻を 2099-01-01 にして `index.html` → 「[PASS] E2E 検証済み（-2275630247秒前）」exit=0
- 状態: 実証
- 改善の方向: 拡張子は設定で足せるようにし既定に ts/tsx/jsx/vue/svelte/scss を入れる。負の経過時間とハッシュ計算の失敗は BLOCKED にする（A-14 の「判定不能は deny」に合わせる）

## I2-tools-07 quality_harness.py は source_roots・scan_roots が無い（または既定の空）と検査 7・8 を黙って飛ばし PASS を返す
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `02_共通/ツール/quality_harness.py` の DEFAULT_HARNESS（`"source_roots": []`・`"scan_roots": []`）、:107-109・:137-139（存在しない root は `continue`）。PASS のときは `validated_features` しか出さず、調べたモジュール数は出さない（:181-183）。
  実行: 実装が `app/orphan.py`（契約に未登録・`# TODO` あり）にあるプロジェクトで、`source_roots: ["src"]` にした場合と harness 設定なしの場合 → どちらも「PASS validated_features=1」exit=0。docstring にある「登録し忘れを素通しで PASS」（2026-07-19 の事故）と同じ形がそのまま残っている
- 状態: 実証
- 改善の方向: 設定した root が無ければ NG、source_roots が空なら WARN、PASS の行に「走査 n モジュール」を出す

## I2-tools-08 check-screens は全ページを skip メタで除外しても exit 0（検査 0 / 指定 1）
- 種別: 欠陥
- 深刻度: Medium
- 根拠: `00_導入/03_点検/check_screens.py:98-99`（`aidd-screen-check=skip` のメタで除外）、:216-220（errs と ng が無ければ 0。checked=0 を見ていない）。
  実行: skip メタだけの HTML 1 枚 → 「対象: 0 ページ × 2 幅（検査 0 / 指定 1、除外 1）」「NG=0」exit=0。件数の表示はあるので、指定と検査の差は人が読めば分かる
- 状態: 実証
- 改善の方向: checked=0 のときは exit 2、または除外の比率にしきい値を置く

## I2-tools-09 security-scan.sh は走査器 4 種が未検査でも「指摘なし」exit 0。冒頭の「未検査を合格に数えない」と食い違う
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `02_共通/ツール/security-scan.sh:15-20`（exit 2 は「走査器が 1 つも無く grep 代替の対象も無い」ときだけ）と :20 の「未検査（未導入・解析失敗とも）を合格に数えない」。
  実行: 空ディレクトリ → 「対象: 0 件の指摘 ／ 未検査: 4 件」「✅ 指摘なし（実行できた走査器の範囲内）」exit=0。対照: `os.system(input())` の .py → bandit B605 high で exit=1（正常に検出）
- 状態: 実証
- 改善の方向: 依存・SAST・秘密の 3 区分ごとに 1 つも実行できなかったら exit 2（または必須区分を引数で指定）とし、冒頭の説明を実際の動作に合わせる

## I2-tools-10 配布スクリプトは既存の scripts/* を上書きしないので、配布先の検査ツールが古い版のまま残る（版を確かめる仕組みも無い）
- 種別: 欠落
- 深刻度: Medium
- 根拠: `00_導入/02_プロジェクト配布/export-project.sh:165-170,176-179`、`init-lifecycle.sh:103-109`（`[ -e "$dest" ]` なら「スキップ（既存）」）。`02_共通/ツール/check-version.py` はキット自身の VERSION と資料の表記の検査で、配布先のツールの版は見ない（docstring 2-10 行）。trace-check.sh は隣の section_hash.py を、test_metrics.py は section_hash を前提にしており、古い trace-check と新しい section_hash の組み合わせになりうる
- 状態: 未確認（コードを読んだだけ。配布先で古い版が残っている実例は確かめていない）
- 改善の方向: 配布物に版（またはハッシュ）の印を付け、差があれば「更新あり」を出して --update で置き換える

## I2-tools-11 test_metrics.py が読むのは `0[5-8]-*.md` と先頭列が「ID」の表だけで、外れた表は黙って読まない
- 種別: 欠陥
- 深刻度: Low
- 根拠: `test_metrics.py:228`（`d.glob("0[5-8]-*.md")`）、:232（`header[0] == "ID"`）。trace-check.sh は名前に `system-test` 等を含む任意の .md を読むので、2 つのツールで読む文書の決まりが違う。
  実行: 先頭列を「テストID」にした 07-system-test.md（ST-001 fail）→ 「テストの実行記録が無い」。--gate は exit=2（安全側）だが、status は exit=0 で「記録なし」と出るだけ
- 状態: 実証
- 改善の方向: 0[5-8] の文書にテスト ID らしい行があるのに 1 件も読めなければ「表を認識できない」と出す

## I2-tools-12 ID が 3 桁固定（trace-check・test_metrics）
- 種別: 欠陥
- 深刻度: Low
- 根拠: `trace-check.sh:90`、`test_metrics.py:47`（`TEST_ID_RE = ^(UT|IT|ST|UAT)-(\d{3})$`）。一方 trace-check の C8 は `\d{3,}`（:275-276）で、同じファイルの中でも桁の扱いが違う。実行は I2-tools-04 の ③（REQ-F-1000 は数えない）
- 状態: 実証
- 改善の方向: `\d{3,}` に揃えるか、3 桁を超えた ID を NG として出す

## I2-tools-13 回帰テストの .py 2 本（test-ui-catalog.py・ui-catalog-browser-code.py）を run-all.sh も CI も実行しない
- 種別: 欠落
- 深刻度: Low
- 根拠: `06_保守者向け/03_回帰テスト/run-all.sh:13`（`for t in "$DIR"/test-*.sh`）。`git grep 'test-ui-catalog\|ui-catalog-browser-code' -- ':!*.md'` で、どの .sh・yml からも呼ばれていない（ヒット 0 件）。`.github/workflows/kit-ci.yml` も run-all.sh を呼ぶだけ
- 状態: 実証（参照が無いことを grep で確認。2 本を実行してはいない）
- 改善の方向: run-all.sh の対象に `test-*.py` を加えるか、test-*.sh から呼ぶ

## I2-tools-14 CI は ubuntu-latest だけで、保守者の環境（macOS・bash 3.2・BSD awk）の差を CI で検査していない
- 種別: 欠落
- 深刻度: Low
- 根拠: `.github/workflows/kit-ci.yml`（`runs-on: ubuntu-latest`・`workflow_dispatch` のみ）。手元は `GNU bash, version 3.2.57`。回帰テストには BSD/GNU を意識した書き方が既にある（test-hooks.sh:5 の sed、:34 の timeout 代替）が、`test-test-metrics.sh:157,162` は `md5sum` を使う。手元の macOS には `/sbin/md5sum` があるので今は動く。md5sum が無い古い macOS では両辺が空文字で一致し、検査が常に通る（未確認）
- 状態: 主張（CI 定義を読んだだけ）／md5sum の件は未確認
- 改善の方向: 手で起動する macOS ジョブを 1 本足す（定時実行はしない）。md5sum を `shasum`／python に替える

## I2-tools-15 atarimae scan.sh は調べた件数を出さず、テンプレートの無いプロジェクトでも全項目「該当なし」になる
- 種別: 欠落
- 深刻度: Low
- 根拠: `03_ClaudeCode/skills/atarimae-quality-audit/scan.sh:13`（`templates */templates src public app` に決め打ち。無いディレクトリは `2>/dev/null` で消える）。実行: 空ディレクトリ → 1)・3)・9) が「(該当なし)」、4) が「(SVGなし)」、2)・5)〜8) は何も出ない。「見つからない」と「調べていない」を区別できない
- 状態: 実証
- 改善の方向: 冒頭に「走査対象 n ファイル（ディレクトリ: …）」を出し、0 なら警告する

## I2-tools-16 audit-app-workspace.sh に回帰テストが無い
- 種別: 欠落
- 深刻度: Low
- 根拠: `02_共通/ツール` と `00_導入/03_点検` の .py/.sh それぞれについて、basename を `06_保守者向け/03_回帰テスト/*` から grep した。参照が 0 件だったのは `00_導入/03_点検/audit-app-workspace.sh` だけ
- 状態: 実証（参照の有無だけを確かめた。テストの質は見ていない）
- 改善の方向: 最小の test-audit-app-workspace.sh を足す

---

## 良かった点（対照として確認したもの）
- check_screens.py は「検査 n / 指定 m」を出し、Playwright が無い・指定 0 件・無いパスを exit 2 にする（:173-184・:88-89）
- security-scan.sh は無いディレクトリで exit 2。bandit の high を正しく exit 1 にした
- trace-check の C7・C8 には「判定不能は合格に数えない」が実装されている（:240-246・:260-265）。I2-tools-02〜04 はこの方針が C1〜C6 に及んでいない部分

## 調べられなかったこと
- hooks 30 本（`03_ClaudeCode/hooks/`）は別テーマとして対象外
- `02_共通/ツール` の残り（adr-to-rules・cite-check・mutate-quick・pw-spec-lint・req-lint・skill-scan など）は回帰テストの有無だけで、中身は読んでいない
- check_design.py（1144 行）は入口の収集処理と終了コードだけを読んだ。規則（直値・コントラスト）の誤検知や見逃しは見ていない
- check_screens.py の実ページでの誤検知（file:// で開くので相対 fetch が CORS で落ち、コンソールエラーになる等）は未確認
- Linux（GNU）での実行はしていない。BSD/GNU の差は grep による静的な確認だけ（sed -i.bak・date -r は両方で動く書き方だった）
- Windows／Codex 環境（04_Codex 配下）のスクリプトは見ていない
- 外部の Web 調査・clone は行っていない（今回の問いには要らないと判断した）

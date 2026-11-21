# I4-ci 内部実装: CI・git hooks（段1 広域調査）

- 対象: `.github/workflows/kit-ci.yml`、`02_共通/ひな形/github/workflows/*.yml`（4 本）、`00_導入/02_プロジェクト配布/install-git-hooks.sh`、`02_共通/ツール/pre-commit`、`02_共通/ツール/pre-commit-ui-gate.sh`、`02_共通/ツール/ui-hash.py`、`03_ClaudeCode/skills/test-strategy/references/ui-verified-gate.md`、`03_ClaudeCode/hooks/secret_patterns.py`（ファイル名の規則のみ）、`03_ClaudeCode/hooks/block-destructive.py`（迂回の扱いの grep のみ）、`06_保守者向け/03_回帰テスト/run-all.sh`・`test-git-gates.sh`（ケース名の grep）
- 調べた方法: 全文読み（上記の主要 6 本）、`git grep` による参照確認、`gh run list --limit 30`、scratchpad の使い捨てリポジトリでキットのスクリプトを実行して再現（`scratchpad/i4ci-bin/sec.sh`・`ui.sh`・`wt.sh`）。CI は起動していない。外部 Web は参照していない。
- 調べた件数/全件数: CI・git hook 関連ファイル 11/11（`git ls-files | grep -iE 'git-hooks|pre-commit|ui-verified|secret'` と `find .github` の結果全件）＋ひな形 workflow 4/4（トリガ・permissions・uses の grep のみ。test-gates/lifecycle-check/deploy の本文は未読）
- 実行環境: macOS、gitleaks 8.30.1（`/opt/homebrew/bin/gitleaks`）。フォールバック経路は `PATH=/usr/bin:/bin` で gitleaks を外して実行。

---

## I4-ci-01 worktree に配線すると hook が動かないのに「✅ 配線しました」と出る
- 種別: 欠陥
- 深刻度: High
- 根拠: `install-git-hooks.sh:25-27` が `git rev-parse --git-dir` を使う。worktree ではこれが `.git/worktrees/<名>` を返すが、git は hook を共通ディレクトリ（`--git-common-dir`）の `hooks/` から読む。`wt.sh` の再現: 子 worktree に配線 → 出力「✅ …/.git/worktrees/wt2-child/hooks/pre-commit に配線しました」、本体 `.git/hooks/pre-commit` は「無し」、その worktree で `sk-…` を含むファイルを commit →「COMMIT通過」
- 状態: 実証
- 改善の方向: `--git-common-dir` を使い、配線後に `git rev-parse --git-path hooks/pre-commit` と一致するか自己検査する

## I4-ci-02 core.hooksPath が設定されたリポジトリでは配線が無効なのに成功表示
- 種別: 欠陥
- 深刻度: High
- 根拠: `install-git-hooks.sh` は `core.hooksPath` を見ない（`git grep hooksPath` は block-destructive.py のみ一致）。`ui.sh` 手順10: `git config core.hooksPath .husky` のリポジトリへ配線 →「✅ …/.git/hooks/pre-commit に配線しました」→ 秘密情報入りの commit が「COMMIT通過」
- 状態: 実証
- 改善の方向: `git rev-parse --git-path hooks` に書くか、hooksPath 設定時は止めて案内する

## I4-ci-03 UI ゲートが判定不能で素通りする（fail-open。A-14 に反する）
- 種別: 欠陥
- 深刻度: High
- 根拠: `pre-commit-ui-gate.sh:51` は `scripts/ui-hash.py` が無いと hash 照合を黙って飛ばす。`:53-54` は hash 計算失敗を WARN だけで通す。`:47-48` は未来日時で AGE が負になり年齢上限を通る。`ui.sh` 手順4（ui-hash.py を退避、hash 欄 `deadbeef`）→「COMMIT通過」、手順7（時刻 2099 年）→「COMMIT通過」。A-14「判定不能は deny」（absolute-rules.md）と矛盾
- 状態: 実証
- 改善の方向: hasher 不在・計算失敗・未来時刻・欄欠落をすべて BLOCK にする

## I4-ci-04 .ui-verified は 1 行で偽造でき、E2E の実行と結びついていない
- 種別: 欠落
- 深刻度: High
- 根拠: マーカーは「HEAD / UI hash / 時刻」だけ（`pre-commit-ui-gate.sh:8`、`ui-verified-gate.md:44`）。E2E の結果（報告ファイルの hash・件数）を含まない。`ui.sh` 手順2: E2E を回さず `printf "%s %s %s\n" "$(git rev-parse HEAD)" "$(python3 scripts/ui-hash.py disk)" "$(date -Iseconds)" > .ui-verified` →「COMMIT通過」。Claude Code の hook も `.ui-verified` の書き込みを止めない（`git grep -n ui-verified -- 03_ClaudeCode/hooks` 一致なし）。マーカーを書く verify-ui の実装もキットに無い（`git grep ui-verified -- '*.sh' '*.py' Makefile` は文書と回帰テストだけ）
- 状態: 実証
- 改善の方向: E2E レポート（JUnit 等）の hash・PASS 件数をマーカーに入れてゲートで照合し、AI が直接 `.ui-verified` を書く操作を hook で止める

## I4-ci-05 --no-verify を「日常の直行」として勧める雛形と、禁止する hook・Codex 規約が矛盾
- 種別: 矛盾
- 深刻度: High
- 根拠: `02_共通/ひな形/test/DEFINITION_OF_DONE.md:12`「日常のコミット単位では speed-harness H-7（…`--no-verify` で直行）が優先する」、`02_共通/ひな形/test/TESTING_STRATEGY.md:39`「日常のコミット｜実行しない（…`--no-verify` で直行）」。一方 `03_ClaudeCode/hooks/block-destructive.py:16,107` は `--no-verify` / `commit -n` を deny、`04_Codex/skills/aidd-kit/SKILL.md:34`「安全検査を `--no-verify` で迂回しない」。`--no-verify` は秘密情報スキャンも飛ばすため、H-7（pytest 等のゲート）の意図を超えて秘密情報検査まで外れる
- 状態: 実証（grep で文書の両方を確認）
- 改善の方向: 雛形から `--no-verify` の推奨を消し、重いゲートは hook の外（要求時のみ）に置くと書き換える

## I4-ci-06 git hook を通らない経路に対する後段の検査が無い（CI は全部手動、2 か月以上未実行）
- 種別: 欠落
- 深刻度: High
- 根拠: `kit-ci.yml:12-13` とひな形 4 本（secret-scan/test-gates/lifecycle-check/deploy）はすべて `on: workflow_dispatch` のみ。pre-push・commit-msg hook は無い（`install-git-hooks.sh` は pre-commit だけ生成）。`gh run list --limit 30` → 3 件のみ、すべて `Kit CI / pull_request / success`、期間 2026-09-17T02:19〜02:55Z。手動化（2026-09-17）以降 0 回。その後 kit-ci.yml は 4 回変更（`git log -- .github/workflows/kit-ci.yml`: 2026-09-21・11-03×2・11-10）されたが一度も走っていない。Codex・GitHub の Web 編集・`--no-verify`・I4-ci-01/02 の配線漏れで入った秘密情報は push 先で誰も検査しない
- 状態: 実証
- 改善の方向: 「自動処理を認めない」方針を保ったまま、pre-push hook（秘密情報のみ・軽量）か、保守者がマージ前に 1 コマンドで流す手順を定めて記録を残す

## I4-ci-07 秘密情報フォールバック検査が主要な鍵形式を取りこぼす
- 種別: 欠落
- 深刻度: High
- 根拠: `02_共通/ツール/pre-commit:19-21` の KNOWN/ASSIGN。`sec.sh`（gitleaks を外して実行）の結果、通過（漏れ）: OpenAI プロジェクトキー `sk-proj-…`（`sk-[A-Za-z0-9]{20,}` がハイフンで切れる）、Google `AIza…`、Stripe `sk_live_…`、Slack webhook URL、YAML の引用符なし `api_key: …`、`export OPENAI_API_KEY=…`（引用符なし）、JWT、接続文字列 `postgres://user:pass@`、値に `Example` を含むパスワード（PLACEHOLDER の部分一致 `example` で除外）。検出: `sk-…`(旧形式)・`sk-ant-…`・`github_pat_…`・引用符付き代入・`.env.local`。gitleaks が無い環境（Codex クラウド等）はこのフォールバックだけが頼り
- 状態: 実証（値は合成。実在の鍵は使っていない）
- 改善の方向: 主要ベンダー形式と引用符なし代入・URL 内資格情報を足し、PLACEHOLDER を値全体一致に絞る。回帰テストに上の見本を入れる

## I4-ci-08 フォールバックの秘密ファイル名リストが Claude Code hook の定義より狭い
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `pre-commit:15` は `.env*`・`*.pem`・`*.key`・`id_rsa*` のみ。`03_ClaudeCode/hooks/secret_patterns.py:82-86` は `.p12`・`.pfx`・`.secret`・`.npmrc`・`.pypirc`・`.netrc`・`credentials`・`id_ed25519`・`id_ecdsa`・`.aws/`・`.ssh/` も秘密扱い。`sec.sh`: `cert.p12`・`.npmrc`（authToken 入り）・`id_ed25519` がすべて「PASS(漏れ)」
- 状態: 実証
- 改善の方向: 秘密ファイルの定義を 1 か所（secret_patterns 相当）に寄せ、pre-commit もそれを読む

## I4-ci-09 UI 変更の判定が .html/.js/.css の追加・変更だけ（TSX・Vue・SCSS・リネーム・削除を見ない）
- 種別: 欠落
- 深刻度: Medium
- 根拠: `pre-commit-ui-gate.sh:17-23`（`--diff-filter=ACM`、拡張子 3 種）、`ui-hash.py:20`。`ui.sh` 手順5: マーカー無しで `App.tsx`・`a.vue`・`a.scss` を commit →「COMMIT通過」、手順6: `git mv index.html page.html` →「COMMIT通過」
- 状態: 実証
- 改善の方向: 拡張子を設定可能にし既定に ts/tsx/jsx/mjs/vue/svelte/scss を入れ、R・D も UI 変更として扱う

## I4-ci-10 回帰テスト test-git-gates.sh が配線・迂回・fail-open を検査していない
- 種別: 欠落
- 深刻度: Medium
- 根拠: `grep -cE 'worktree|hooksPath|no-verify' 06_保守者向け/03_回帰テスト/test-git-gates.sh` → 0。ケース名（`expect_exit`/`ok` の grep）は API キー検出・localStorage 許可・hash 桁数・docs 除外・UI 未 stage 等で、I4-ci-01〜04・07〜09 の再現ケースが無い
- 状態: 実証
- 改善の方向: 本調査の `scratchpad/i4ci-bin/*.sh` の各ケースを回帰テストへ移す

## I4-ci-11 キット自身の CI が秘密情報検査・追跡検査を流していない
- 種別: 欠落
- 深刻度: Medium
- 根拠: `kit-ci.yml:27-35` の手順は run-all.sh・check-design.sh・check-docs.sh の 3 つだけ。キットのリポジトリに対する gitleaks 等の秘密情報検査は無い（ひな形の secret-scan.yml は配布先用で、`.github/workflows/` には kit-ci.yml 1 本のみ）
- 状態: 実証
- 改善の方向: 手動起動の kit-ci に秘密情報の全履歴スキャン手順を 1 段足す

## I4-ci-12 gitleaks の `protect` は非推奨（ヘルプから消えている）サブコマンド
- 種別: 欠陥
- 深刻度: Low
- 根拠: `pre-commit:7` と `06_保守者向け/01_内部仕様/05_スクリプト.md:220` が `gitleaks protect --staged`。`gitleaks --help`（8.30.1）の Available Commands は completion/dir/git/help/stdin/version のみで protect は非表示（現時点では動作する）。将来の削除で gitleaks 経路が exit≠0 となり「秘密情報を検出」と誤表示する恐れ（未確認）
- 状態: 実証（非表示であること）／未確認（削除予定の時期）
- 改善の方向: `gitleaks git --staged` へ置き換え、バージョン差を吸収する

## I4-ci-13 kit-ci.yml に permissions 指定が無く、actions はタグ参照
- 種別: 欠陥
- 深刻度: Low
- 根拠: `grep -nE 'permissions|@[0-9a-f]{40}' .github/workflows/kit-ci.yml` → 一致なし（`actions/checkout@v4` 等）。deploy.yml ひな形は `permissions:` あり（:12）。手動起動のみのため露出は小さい
- 状態: 実証
- 改善の方向: `permissions: contents: read` を明示し、actions をコミット SHA で固定する

## I4-ci-14 UI hash は disk 全体で照合するため、staged 内容が未検証でも通り得る
- 種別: 欠陥
- 深刻度: Low
- 根拠: `pre-commit-ui-gate.sh:52` は `ui-hash.py disk`（`ui-verified-gate.md:19` に設計判断として記載）。変更を `git add` した後、作業ツリーを検証時の内容へ戻すと disk hash は一致し、未検証の staged 内容が commit される筋書き
- 状態: 未確認（論理上の筋。再現はしていない）
- 改善の方向: commit 対象（index）の UI ファイルで hash を取る `ui-hash.py index` を足して照合する

## I4-ci-15 .ui-verified が ignore されず、証跡がコミットに混入し得る
- 種別: 欠落
- 深刻度: Low
- 根拠: `ui.sh` 手順8 `git status --short .ui-verified` →「?? .ui-verified」。`git grep ui-verified -- '*gitignore*'` → なし。CLAUDE.md の PR 作法は「証跡ファイルはコミットしない」
- 状態: 実証
- 改善の方向: export-project.sh が配布先の .gitignore に `.ui-verified` と `.rebuild-mode` を追記する

## I4-ci-16 `.rebuild-mode` に任意の 1 行を置けば UI ゲートを無期限に止められる
- 種別: 過剰（免除が広い）
- 深刻度: Low
- 根拠: `pre-commit-ui-gate.sh:27-31` はファイルの存在だけを見る（期限・理由の中身・作成者を見ない）。WARN を出して exit 0
- 状態: 実証（コード読み。実行再現はしていない分岐だが条件は存在判定のみ）
- 改善の方向: 期限日を必須にし、期限切れなら BLOCK にする

## I4-ci-17 uninstall が退避無しのとき rm -f で hook を消す
- 種別: 矛盾
- 深刻度: Low
- 根拠: `install-git-hooks.sh:33` `rm -f "$HOOK"`。AGENTS.md「退避は削除でなく mv」。実害は小さい（自分の生成物）
- 状態: 実証（コード読み）
- 改善の方向: `mv "$HOOK" "$HOOK.removed.<日時>"` にする

---

## 調べられなかったこと
- ひな形 workflow の test-gates.yml・lifecycle-check.yml・deploy.yml の本文詳細（トリガ・permissions・uses の grep のみ）
- gitleaks 経路での検出率の比較: 合成値で試したが（`wt.sh`: `sk-proj`・`AIza`・`sk_live`・接続文字列が通過、Slack webhook・YAML の api_key は検出）、合成値の桁数・エントロピーが実鍵と異なる可能性があり、gitleaks の取りこぼしとは断定しない（未確認）
- `test-weaken-check.py`・`check_approval.py` の中身（工程承認・弱体化検査の迂回）は本テーマの範囲外として未読
- `03_ClaudeCode/hooks/block-destructive.py` の `--no-verify` 検出の網羅性（`git commit --no-verif` の省略形、`git -c alias…` 等）は実行検証していない
- キット本体の `.git/hooks/pre-commit`（先頭 4 行のみ確認。「canonical gates を使う」薄い hook）の中身全体
- 外部の規格・研究文書（OpenSSF Scorecard・GitHub のセキュリティ強化ガイド等）は今回取得していない。I4-ci-13 の SHA 固定の推奨は一般的な製品文書の記述に基づくが URL 未取得（未確認）

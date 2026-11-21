# I4-ci 段2（深掘り）: CI・git hooks

- 実施: 2026-11-21 16:49〜（Asia/Tokyo）。macOS、git（/usr/bin/git）、gitleaks 8.30.1
- 選定: 段1 の High 7 件から、秘密情報の流出に直結し影響範囲が広い順に 3 件。I4-ci-01（worktree への配線が効かない。本キット自身が worktree で運用している）、I4-ci-07（gitleaks が無い環境、つまり Codex クラウド等で唯一の秘密検査になる）、I4-ci-03（UI ゲートが fail-open。A-14 違反）。I4-ci-02（hooksPath）は I4-ci-01 と原因が同じ（hook の置き場所の解決誤り）なので選外
- 方法: scratchpad の使い捨てリポジトリにキットの `02_共通/ツール/pre-commit`・`pre-commit-ui-gate.sh`・`ui-hash.py` を写し、`00_導入/02_プロジェクト配布/install-git-hooks.sh` で配線して commit を試す。`GIT_CONFIG_GLOBAL=/dev/null` でグローバル設定から切り離した。実環境の `~/.claude` と本リポジトリの `.git` には触れていない。フォールバック経路は `PATH=/usr/bin:/bin`（gitleaks を外す）で通す
- 再実行: 末尾の付録のスクリプトを `repro.sh` として保存し、`bash repro.sh <キットのルート>` で流す（作業ディレクトリは `repro.sh` の隣の `work/`）

| ID | 深刻度 | 判定 |
|---|---|---|
| I4-ci-01 | High | 再現 |
| I4-ci-07 | High | 再現 |
| I4-ci-03 | High | 再現 |

---

## I4-ci-01 worktree に配線すると hook が動かないのに「✅ 配線しました」と出る
- 深刻度: High（据え置き）
- 原因の行: `install-git-hooks.sh:25` `GITDIR="$(git -C "$TARGET" rev-parse --git-dir ...)"` → `:27` `HOOK="$GITDIR/hooks/pre-commit"` → `:127` `echo "✅ $HOOK に配線しました"`（書き込んだ先と git が読む先が同じかを確かめていない）
- 再現手順（付録 R1）:
  1. `git init` した本体 r1 で `git worktree add r1-wt -b wtb`
  2. `bash install-git-hooks.sh r1-wt`
  3. `rev-parse --git-dir` / `--git-common-dir` / `--git-path hooks/pre-commit` を r1-wt で比べる
  4. r1-wt で偽の `sk-ant-…` を含む leak.py を stage し、`PATH=/usr/bin:/bin` で commit する
  5. 対照: 本体 r1 に配線して同じ commit を試し、続けて r1-wt でもう一度 commit する
- 実測結果:
  - installer の出力: `✅ <S>/work/r1/.git/worktrees/r1-wt/hooks/pre-commit に配線しました`
  - git-dir `…/r1/.git/worktrees/r1-wt`、git-common-dir `…/r1/.git`、**git-path hooks/pre-commit `…/r1/.git/hooks/pre-commit`**（git が実際に読む場所）。この共通 hooks/pre-commit は「無し」
  - worktree での commit: **通過（漏れ）**
  - 対照: 本体に配線した後、本体の commit は「拒否（hook 動作）」、同じ worktree の commit も「拒否（共通 hooks が効く）」。hook そのものは正常に動き、置き場所だけが誤っている
- 判定: 再現
- 補足: 本キット自身が `.claude/worktrees/` で worktree を使っている。`install-git-hooks.sh <worktree>` を打つと、成功と表示されたまま無防備になる。直し方の候補は、書き込み先を `git rev-parse --git-path hooks/pre-commit` にすること（core.hooksPath の件＝I4-ci-02 も同時に解決する）と、配線後に同じコマンドの結果と一致するかを自己検査すること

## I4-ci-07 秘密情報フォールバック検査が主要な鍵形式を取りこぼす
- 深刻度: High（据え置き）
- 原因の行: `02_共通/ツール/pre-commit:19` KNOWN（`sk-[A-Za-z0-9]{20,}` はハイフン・下線で途切れる。AIza・sk_live・Slack webhook・接続文字列の形が無い）、`:20` ASSIGN（値に引用符を必須にしている）、`:21` PLACEHOLDER（`example` の部分一致で除外する）
- 再現手順（付録 R2）: 1 ケースずつ stage し、`PATH=/usr/bin:/bin bash scripts/pre-commit`（フォールバック）と参考の `gitleaks protect --staged` の exit を比べてから `git rm --cached` で戻す
- 実測結果（fallback / gitleaks）:

| ケース | fallback | gitleaks |
|---|---|---|
| OpenAI sk-proj- | 漏れ | 漏れ |
| Google AIza | 漏れ | 検出 |
| Stripe sk_live_ | 漏れ | 検出 |
| Slack webhook | 漏れ | 検出 |
| YAML 引用符なし | 漏れ | 検出 |
| export 引用符なし | 漏れ | 検出 |
| postgres 接続文字列 | 漏れ | 漏れ |
| Example 入り password | 漏れ | 漏れ |
| 対照 sk-ant- | 検出 | 漏れ |
| 対照 引用符付き代入 | 検出 | 検出 |

- 判定: 再現（フォールバックは 8 ケースすべてで漏れた。対照の 2 ケースは検出したので、スクリプト自体は動いている）
- 注意: gitleaks 列の「漏れ」（sk-proj・sk-ant・接続文字列）は、自作の偽キーが実キーの長さ・末尾の形・エントロピーの条件を満たしていないせいかもしれない。gitleaks の欠陥とは断定しない（未確認）。フォールバックの漏れは正規表現の形（上の原因の行）で説明がつき、偽キーの形には左右されない
- 影響: gitleaks が無い環境（Codex クラウド等）ではこのフォールバックしか秘密検査が無い。後段の CI も手動起動だけ（段1 I4-ci-06）

## I4-ci-03 UI ゲートが判定不能で素通りする（fail-open。A-14 に反する）
- 深刻度: High（据え置き）
- 原因の行: `pre-commit-ui-gate.sh:51` `if [ -n "$VERIFIED" ] && [ -f "${ROOT}/scripts/ui-hash.py" ]`（ファイルが無いと hash 照合を黙って飛ばす）、`:53-54` 計算に失敗しても `[WARN] …タイムスタンプのみで判定します。` を出して続ける、`:47-48` `AGE=$(( now - EPOCH ))` が負の値でも `-le MAX_AGE` を満たす
- 規約側: `rules/absolute-rules.md` A-14「判定不能は deny（合格に数えない）」
- 再現手順（付録 R3）: index.html に追記して stage し、`.ui-verified` と `scripts/ui-hash.py` の状態を変えながら `bash scripts/pre-commit-ui-gate.sh` の exit を見る
- 実測結果:

| 条件 | 結果 |
|---|---|
| a 対照: マーカー無し | 拒否 |
| b 対照: hash 不一致 | 拒否 |
| c ui-hash.py 無し＋偽 hash | 通過 |
| d 2099年＋ui-hash.py 無し | 通過 |
| e ui-hash.py が異常終了 | 通過 |
| f 2099年＋ui-hash.py あり | 拒否 |

  - c の出力: `[PASS] E2E 検証済み（1秒前）`（hash を照合していないことは表示されない）
  - d の出力: `[PASS] E2E 検証済み（-2275628984秒前）`
  - e の出力: `[WARN] UI hash の計算に失敗。タイムスタンプのみで判定します。` の後に `[PASS]`
  - f は未来の時刻を通過したうえで、hash 不一致で止まった（未来時刻の判定そのものは通っている）
- 判定: 再現（c・d・e の 3 経路で、判定できない状態が合格に数えられる）

---

## 再現できなかった・実行しなかったこと
- なし（3 件とも実行した）。I4-ci-02・04〜06・08〜17 は段2 の対象外

## 付録: repro.sh（scratchpad で実行したものと同じ内容）
```bash
#!/bin/bash
# 段2 I4-ci 再現。使い方: bash repro.sh <kit のルート>
# 使い捨てリポジトリは scratchpad 配下に作る。グローバル git 設定は読まない（GIT_CONFIG_GLOBAL=/dev/null）。
set -u
KIT="$1"
BASE="$(cd "$(dirname "$0")" && pwd)/work"
mv "$BASE" "$BASE.old.$$" 2>/dev/null
mkdir -p "$BASE"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
FB_PATH=/usr/bin:/bin   # gitleaks を外したフォールバック経路
P1=sk-ant; P2=api03
FAKE_ANT="${P1}-${P2}-AAAAbbbbCCCCddddEEEEffff0123456789"

newrepo() { # $1=dir
  git init -q -b main "$1"; git -C "$1" config user.email t@example.invalid; git -C "$1" config user.name t
  mkdir -p "$1/scripts"
  cp "$KIT/02_共通/ツール/pre-commit" "$KIT/02_共通/ツール/pre-commit-ui-gate.sh" "$KIT/02_共通/ツール/ui-hash.py" "$1/scripts/"
  echo init > "$1/README"; git -C "$1" add README scripts; git -C "$1" commit -q -m init --no-verify
}

echo "=== R1 worktree 配線 ==="
R=$BASE/r1; newrepo $R
git -C $R worktree add -q $BASE/r1-wt -b wtb
OUT=$(bash "$KIT/00_導入/02_プロジェクト配布/install-git-hooks.sh" $BASE/r1-wt 2>&1 | grep 配線しました); echo "installer: $OUT"
echo "git-dir        : $(git -C $BASE/r1-wt rev-parse --git-dir)"
echo "git-common-dir : $(git -C $BASE/r1-wt rev-parse --git-common-dir)"
echo "git-path hook  : $(git -C $BASE/r1-wt rev-parse --git-path hooks/pre-commit)"
ls -l $R/.git/hooks/pre-commit 2>/dev/null || echo "common hooks/pre-commit: 無し"
echo "k = \"$FAKE_ANT\"" > $BASE/r1-wt/leak.py
git -C $BASE/r1-wt add leak.py
PATH=$FB_PATH git -C $BASE/r1-wt commit -q -m leak >/dev/null 2>&1 && echo "worktree commit: 通過（漏れ）" || echo "worktree commit: 拒否"
echo "-- 対照: 本体に配線して同じ commit"
bash "$KIT/00_導入/02_プロジェクト配布/install-git-hooks.sh" $R >/dev/null 2>&1
echo "k = \"$FAKE_ANT\"" > $R/leak.py; git -C $R add leak.py
PATH=$FB_PATH git -C $R commit -q -m leak >/dev/null 2>&1 && echo "main commit: 通過" || echo "main commit: 拒否（hook 動作）"
echo "k2 = \"$FAKE_ANT\"" > $BASE/r1-wt/leak2.py; git -C $BASE/r1-wt add leak2.py
PATH=$FB_PATH git -C $BASE/r1-wt commit -q -m leak2 >/dev/null 2>&1 && echo "本体配線後の worktree commit: 通過" || echo "本体配線後の worktree commit: 拒否（共通 hooks が効く）"

echo "=== R2 フォールバック秘密検査の取りこぼし（gitleaks あり/なし比較）==="
R=$BASE/r2; newrepo $R
cd $R
case_run() { # $1=名前 $2=ファイル名 $3=内容
  printf '%s\n' "$3" > "$2"; git add "$2"
  if PATH=$FB_PATH bash scripts/pre-commit >/dev/null 2>&1; then fb="漏れ"; else fb="検出"; fi
  if gitleaks protect --staged --no-banner >/dev/null 2>&1; then gl="漏れ"; else gl="検出"; fi
  git rm -q --cached "$2"; mv "$2" "$BASE/trash-$RANDOM"
  printf '%-28s fallback=%s gitleaks=%s\n' "$1" "$fb" "$gl"
}
OA="sk-""proj-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_ABCDEFGHIJKLmnopqrstuv"
case_run "OpenAI sk-proj-"        a.py "OPENAI = \"$OA\""
case_run "Google AIza"            b.js "const k = \"AIza""SyA1b2C3d4E5f6G7h8I9j0KlMnOpQrStUvW\";"
case_run "Stripe sk_live_"        c.py "s = \"sk_""live_51HxYzAbCdEfGhIjKlMnOpQr\""
case_run "Slack webhook"          d.txt "https://hooks.slack.com/services/T0""1ABCDEF/B01ABCDEF/AbCdEfGhIjKlMnOpQrStUvWx"
case_run "YAML 引用符なし api_key" e.yml "api_key: <検査用ダミー鍵>"
case_run "export 引用符なし"       f.sh "export OPENAI_API_KEY=<検査用ダミー鍵>"
case_run "postgres 接続文字列"     g.py "DB = \"postgres://admin:<検査用ダミー>@db.internal:5432/app\""
case_run "Example を含む password" h.py "password = \"Example-<検査用ダミー>\""
case_run "対照: sk-ant-"           i.py "k = \"$FAKE_ANT\""
case_run "対照: 引用符付き代入"     j.py "api_key = \"<検査用ダミー鍵>\""
cd - >/dev/null

echo "=== R3 UI ゲート fail-open ==="
R=$BASE/r3; newrepo $R; cd $R
ui_try() { # $1=名前
  echo "<p>$RANDOM</p>" >> index.html; git add index.html
  if bash scripts/pre-commit-ui-gate.sh > "$BASE/r3-$2.log" 2>&1; then r="通過"; else r="拒否"; fi
  git rm -q --cached index.html 2>/dev/null; printf '%-40s %s | %s\n' "$1" "$r" "$(grep -E 'PASS|WARN|BLOCKED' "$BASE/r3-$2.log" | head -2 | tr '\n' ' ')"
}
H=$(git rev-parse HEAD); NOW=$(date -Iseconds)
rm -f .ui-verified 2>/dev/null; ui_try "a 対照: マーカー無し" a
printf '%s %s %s\n' "$H" deadbeef "$NOW" > .ui-verified; ui_try "b 対照: hash 不一致 (ui-hash.py あり)" b
mv scripts/ui-hash.py "$BASE/ui-hash.py.moved"; ui_try "c ui-hash.py 無し + hash deadbeef" c
mv "$BASE/ui-hash.py.moved" scripts/ui-hash.py
printf '%s %s %s\n' "$H" deadbeef "2099-01-01T00:00:00+09:00" > .ui-verified
mv scripts/ui-hash.py "$BASE/ui-hash.py.moved"; ui_try "d 未来時刻 2099 + ui-hash.py 無し" d
mv "$BASE/ui-hash.py.moved" scripts/ui-hash.py
printf 'import sys; sys.exit(3)\n' > "$BASE/broken.py"; cp scripts/ui-hash.py "$BASE/ui-hash.orig"; cp "$BASE/broken.py" scripts/ui-hash.py
printf '%s %s %s\n' "$H" deadbeef "$NOW" > .ui-verified; ui_try "e ui-hash.py が異常終了 + hash deadbeef" e
cp "$BASE/ui-hash.orig" scripts/ui-hash.py
printf '%s %s %s\n' "$H" deadbeef "2099-01-01T00:00:00+09:00" > .ui-verified; ui_try "f 未来時刻 2099 (ui-hash.py あり)" f
cd - >/dev/null
```

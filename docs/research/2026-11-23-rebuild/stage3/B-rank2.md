# 段3 反証 B: 順位 2「守りが黙って外れる」

- 対象コミット: 3ef90fd（origin/main）。作業場所は ROOT（git worktree）
- 方法: 根拠の行を現物で読み直し、使い捨て環境（`mktemp -d` の一時ディレクトリ・一時 HOME）で再現。実環境の ~/.claude・実リポジトリには触れていない。pytest・make test・CI は実行していない
- 11/21 以降の関連コミット（`git log --since=2026-11-21 --oneline`）:
  - 42f5ffc fix: ステータスラインの進捗行を表示しない（statusline.py の 1 行のみ）
  - 2114f37 docs: 11/21 調査そのもの（コード変更なし）
  - 3ef90fd merge #135
  - `git diff --stat 2114f37 3ef90fd -- 03_ClaudeCode 00_導入 .claude-plugin` は statusline.py 1 ファイルだけ。対象 8 件の根拠は 11/21 のまま現物に残っている（修正済みの件は無い）
- 環境: python3 は 3.12.13（/opt/homebrew/bin。PATH 先頭）。`/usr/bin/python3` は 3.9.6 で、実行できたので実測した

## D1-distribution-01
- 結果: 維持（発見は正しい。ただし発動条件の限定あり）
- 根拠:
  - 実測: `/usr/bin/python3`（3.9.6）で、有効な入力を stdin に与えて block-ci.py・block-destructive.py・block-phase.py を起動 → 3 本とも `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`・exit=1（block-gates.py は exit=0 で正常）
  - 原因の行: block-ci.py:28 `def reason_for(tool: str, tool_input: dict) -> str | None:`。`from __future__ import annotations` が無く、3.9 では定義時に評価されて落ちる
  - ここが分かれ目だった点: 例外は deny に倒されず、モジュール読み込み時に落ちて exit=1。hooks 文書の分類では exit 1 は非ブロッキング（処理は続行）で、止めるのは exit 2。よって「全停止」ではなく「素通り」になる。11/21 の主張どおり
  - 動かしていない部分: Claude Code 本体がこの exit=1 を実際に素通りとして扱うことは、文書の記述に依拠している。本体での通し確認はしていない（未確認）
- 反証できた限定:
  - 発動するのは PATH 上の python3 が 3.9 のときだけ。この開発機は PATH 先頭が 3.12 なので起きない。素の macOS（Xcode CLT の python3 = 3.9.6）の利用者では起きる
  - 必要版数の明記・版の確認（`sys.version_info` を見る処理）は install.sh・.sh 群に見当たらない（`git grep sys.version_info -- 03_ClaudeCode 00_導入` は 0 件）。README・利用ガイドの版数の記載は確かめ切れていない（未確認）
- 深刻度の見直し: Critical は「素の macOS を使う他者への配布」を前提にする場合だけ成り立つ。自分の開発機だけなら High。順位 2 の Critical の根拠はこの 1 件のみ

## S1-cc-hooks-01
- 結果: 維持
- 同時に見た I8-install-02 の再現が通ったので、install.sh:77-86 の挙動は現物で確認済み（下記）
- 根拠: `install.sh:77-82` は settings.json が既存だと警告を出して cp しない。自動で入れるのは `install_guard.py` の GUARDS（tool-timer・instruction-guard・prompt-priority・reply-language）だけ。block-destructive・block-ci・block-gates・block-phase・pre-read-guard・block-deps 等は配線されない
- 反証の試み: 「黙って」という点は誇張。install 実行時に「⚠ settings.json が既存。hooks / statusLine … を手動でマージしてください」と出る（実測の出力あり）。ただし利用者が従わなければ外れたまま、かつ導入後に外れていることを知らせる点検は無い
- 実環境の ~/.claude/settings.json の確認（grep block-destructive）は今回していない。11/21 の記述を引用するのみ（未確認）
- 深刻度の見直し: High のまま（警告が出る分 Critical ではない）

## I8-install-02
- 結果: 維持
- 再現（一時 HOME・使い捨て）: 手順どおり `{"model":"x"}` だけの settings.json を置いて install.sh を実行 → rc=0。出力「✅ settings.json に配線: tool-timer.py, tool-timer.py, tool-timer.py, instruction-guard.py, prompt-priority.py, reply-language.py（既存を .bak に退避して merge）」。マージ後の settings.json の hook 名は instruction-guard・prompt-priority・reply-language・tool-timer の 4 種だけ
- 手順の妥当性: 既存 settings.json がある利用者は、Claude Code を一度でも使った人のほぼ全員。導入経路（install.sh 実行）そのもので起きる。妥当
- 深刻度の見直し: High のまま。配線されるのは指示優先の 4 種で、阻止系（破壊操作・ゲート・CI・工程）は外れる。ただし install の出力に警告があるため Critical にはならない

## I3-tests-02
- 結果: 維持（事実）／深刻度は下げる
- 実測（3.12・一時ディレクトリが cwd）: 入力 `""`（空）と `{broken` で block-gates・block-ci・block-phase は exit=0・出力なし（許可）。`null` と `[]` では exit=1（AttributeError・非ブロッキング。これも素通り）
- 根拠の行: block-gates.py:27-30、block-ci.py:44-47、block-phase.py:55-62 の `except (json.JSONDecodeError, ValueError): return 0`。現物で同じ
- 反証の試み: block-destructive は同じ入力で exit=0 だった。ただし私は stdout を捨てたので deny の JSON が出たかは今回確かめていない（11/21 の記述 block-destructive.py:502-503 の fail-closed は未再現）
- 深刻度の見直し: High → Medium。理由: この 3 本が止めるのは「ゲート実行・CI 起動・工程の承認違反」で、秘密情報・破壊操作ではない。また Claude Code が壊れた JSON を hook へ渡す場面は想定しにくい（実際にあり得るかは未確認）。A-14 との不一致は実在するので、直す対象には残す

## R4-note-02
- 結果: 維持（I3-tests-02 と同じ事実。同じ実測で確認）／深刻度は下げる
- 根拠: 上記と同一（block-gates:29-30、block-ci:46-47、block-phase:60-61・74-75）。block-phase.py:74-75 の `return 0` は入力欠落以外の分岐にも掛かるが、今回は読んだだけで実行していない
- 深刻度の見直し: High → Medium（理由は I3-tests-02 と同じ。I3-tests-02 と R4-note-02 は同一欠陥の 2 つの記述）

## I4-ci-01
- 結果: 維持
- 再現（使い捨てリポジトリ proj と、その worktree wt。ゲートスクリプトは中身が `exit 0` のダミー）:
  - `install-git-hooks.sh <wt>` → 「✅ …/proj/.git/worktrees/wt/hooks/pre-commit に配線しました」
  - 実際に git が読む場所 `git -C <wt> rev-parse --git-path hooks/pre-commit` → `…/proj/.git/hooks/pre-commit`（共通ディレクトリ）。配線先と異なる
  - `proj/.git/hooks/pre-commit` は無い
- 動かしていない部分: 実際に commit して通過することまでは再現していない（配線先が git の読む場所と違うことまで）。11/21 は commit 通過まで実証としている。配線先が一致しない以上、結論は変わらない
- 深刻度の見直し: High のまま。別名で worktree を多用する運用（このキットの作業様式）では実害が大きい
- 同時判定: I4-ci-02 — 維持。使い捨てリポジトリに `git config core.hooksPath .husky` を設定して配線 → 「✅ …/.git/hooks/pre-commit に配線しました」と出るが、`git rev-parse --git-path hooks/pre-commit` は `.husky/pre-commit` を返し、`.husky` は存在しない。成功表示だが無効。核心は同じ（`install-git-hooks.sh` に `common-dir`・`hooksPath`・`git-path` の語が無いことも確認）

## S2-cc-plugins-02
- 結果: 維持（実装の事実のみ確認。影響は未再現）
- 根拠: `.claude-plugin/hooks.json` は constitution-gate.py（pre・stop）・reply-language.py・instruction-guard.py を無条件に登録している（hooks.json を JSON として読み出して確認）。plugin の CLAUDE.md が読み込まれない件は公式文書と `plugin validate` の警告に依拠。今回は再実行していない（未確認）
- 反証の試み: 「全部入る」は正しい（PreToolUse・Stop 等の約 28 エントリ）。ただし書式を強制する Stop の reply-language が plugin 利用者に deny を出すかは未再現のまま
- 深刻度の見直し: High → Medium。理由: 守りが「外れる」のではなく「要らない守りが余分に入る」＝摩擦の問題で、順位 2 の「守りが黙って外れる」とは向きが逆

## E6-agent-safety-01
- 結果: 維持
- 根拠（`git grep -nE "ALLOW_CONFIG_EDIT|settings\.json" 03_ClaudeCode/hooks/*.py`）:
  - hook 実装に `AIDD_ALLOW_CONFIG_EDIT` は 0 件。この語は absolute-rules.md:21（A-14）と Codex の複製にしか無く、規約に書かれた逃がし口に実装が無い
  - config-snapshot.py:28-29 は settings.json・CLAUDE.md を記録するだけで、変更を止めない（検出）。instruction-guard.py:23 は「止めたいときは settings.json から外す」と、改変可能を前提にしている
  - block-destructive.py:16・437・466 が止めるのは `.git/config`・`.git/hooks/` の書き込みと `core.hooksPath` の変更。`~/.claude/settings.json`・`~/.claude/hooks/` の書き換えは対象外
  - pre-write-check.sh・block-deps.py の読み込み範囲にも、設定・hook の保護は見当たらない
- 反証の試み: Edit/Write で settings.json を変える操作を止める別の仕組み（permissions の deny など）は私は確認していない。設定側（~/.claude/settings.json の permissions）は読んでおらず、未確認
- 深刻度の見直し: High のまま

## 結論: 順位 2 を Critical のままにしてよいか
- Critical の根拠として成立するのは D1-distribution-01 だけ（3.9.6 で block-ci・block-destructive・block-phase が exit=1 で素通りになることを実測）。条件は「PATH 上の python3 が 3.9」で、この開発機では起きない
- 残りは High 以下。I3-tests-02・R4-note-02 は Medium、S2-cc-plugins-02 は Medium に下げる（理由は各節）。順位 2 全体を Critical とするなら、「素の macOS 利用者へ配る」前提を明示するのが条件
- 推奨: 順位 2 は「Critical（D1-01 のみ。他者配布時）、その他は High〜Medium」と書き分ける

## 集計

| ID | 結果 | 深刻度 |
|---|---|---|
| D1-distribution-01 | 維持 | Critical（他者配布時）／High（自分の機のみ） |
| S1-cc-hooks-01 | 維持 | High |
| I8-install-02 | 維持 | High |
| I3-tests-02 | 維持 | High → Medium |
| R4-note-02 | 維持 | High → Medium |
| I4-ci-01 | 維持 | High |
| S2-cc-plugins-02 | 維持 | High → Medium |
| E6-agent-safety-01 | 維持 | High |
| I4-ci-02（同時判定） | 維持 | High |

主対象 8 件・同時判定 1 件。反証された件は 0 件（深刻度の引き下げ 3 件、限定条件の付与 1 件）。

## 未確認
- 実環境の ~/.claude/settings.json に block-destructive が無いこと（11/21 の記述の引用のみ）
- Claude Code 本体が exit=1 の hook を実際に素通りさせること（文書の記述に依拠。本体での通しは未実施）
- block-destructive が壊れた入力で deny の JSON を返すか（stdout を捨てたので exit=0 しか見ていない）
- worktree・hooksPath で実際に commit が通ること（配線先の不一致までの確認）
- README・利用ガイドが Python の必要版数を書いているか
- plugin の `plugin validate` 警告の再実行、plugin 利用者で deny が起きるか
- permissions の deny など、設定改変を止める別の仕組みの有無

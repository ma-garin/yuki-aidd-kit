# R4-note 運用記録: note 記事とキットの主張の突合（段1・広域）

- 対象: 作者の note（https://note.com/yuki_magari）全記事と、yuki-aidd-kit（origin/main の worktree `research-20261121`）の README・`02_共通/rules`・`03_ClaudeCode/hooks`・`00_導入/02_プロジェクト配布`・`02_共通/ツール`
- 調べた方法:
  - 一覧 API `https://note.com/api/v2/creators/yuki_magari/contents?kind=note&page=1..9`（page 9 で isLastPage=true、totalCount=52）→ 52 件のキー（重複 0）
  - 本文 API `https://note.com/api/v3/notes/<key>` で 52 件すべて取得（取得日 2026-11-21）。HTML を除去してテキスト化し、キーワード（hook・CLAUDE.md・ゲート・スキル・数値）で絞った
  - キットの主張に触れる 19 件（Claude Code 活用メモ 1〜12・番外 2 件、AIDD x QA メモ 1/5〜5/5）を主張行の抽出で読み、うち 3 件（活用メモ 3・9・10）は全文を読んだ。残り 33 件（生成AI x QA メモ・QA 仕事術・パワポ等）はキーワード検索のみ（キットの機能の主張は見つからなかった）
  - キット側は grep・wc・hook の静的読み。**hook・スクリプトは実行していない**
  - 一次資料の確認: arXiv 2310.01798v2（HTML 版の表）・arXiv 2510.20270（abstract）を curl で取得。手元の Claude Code バイナリ（2.1.330）を文字列検索
- 調べた件数/全件数: 本文取得 52/52、主張の突合 19/52（全文精読 3/52）

## 突合の前提（実証）

- 記事はキット名・リポジトリ URL を一度も出さない: `grep -l -i 'yuki-aidd-kit\|aidd-kit\|キット' body/*.txt` → 0 件。記事中の github.com は `mattpocock/skills` のみ
- キット側は URL では参照しない（`grep -rn note.com` → バックログ Q-17 の 1 件のみ）が、連載名で出所を書いている: `02_共通/rules/quality-decision.md:11`・`02_共通/rules/evidence-citation.md:8`（「出所: 作者 note 連載『AI駆動開発(AIDD) x QAメモ』」）、`CHANGELOG.md:35`（連載 1〜5 の提案を組み込み）
- `quality-decision.md` は「hook の時間切れ・想定外エラーは素通りしうる…確認が動かなかったときは止める側に倒す」と記事 5/5 の主張を規則にしている。R4-note-02・03 はキット自身の規則との矛盾でもある
- 突合は「記事が説く規律・機能」と「キットが実装している規律・機能」の内容比較になる

## 発見

### R4-note-01 テスト弱体化の検査は AI 自身が書ける `weaken-ok` コメントで許可され、記事の「別に承認」と矛盾する
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - キット: `02_共通/ツール/test-weaken-check.py:6`「差分の近く（±3 行）に `weaken-ok: <理由>` のコメントを**この差分で書き足せば**その件を許可する（理由は 8 字以上）」、同 `:31-33`（テストファイルの削除も `weaken-ok: <ファイル名> <理由>` で許可）
  - 記事: AIDD x QA メモ 4/5（n38f5dfe971d1）「テストを削除したり、スキップに変えたりした変更は、通常のレビューとは別に承認を取る」「テストの変更を含む変更は、別の承認が取れるまで取り込みません」、5/5（nbc2d78bcd809）「テストを消す、スキップする、期待値を書き換える変更は…別に承認するようにします」
  - キット自身の規約「AI は approver 欄を埋めない」（CLAUDE.md の記述）とも整合しない。テストを弱めた本人（AI）が同じ差分で 8 字の理由を書けば通る
- 状態: 実証（ソースの静的確認。実行はしていない）
- 改善の方向: `weaken-ok` を人間の承認記録（`check-approval.sh` 系の approver 付き記録）への参照に置き換え、AI が書いた理由コメントだけでは許可しない

### R4-note-02 阻止系 hook のうち block-gates / block-ci / block-phase は入力が読めないと素通り（fail-open）
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - `03_ClaudeCode/hooks/block-gates.py:29-30` `except (json.JSONDecodeError, ValueError): return 0`
  - `03_ClaudeCode/hooks/block-ci.py:46-47` 同上
  - `03_ClaudeCode/hooks/block-phase.py:60-61`・`:74-75` `return 0`
  - 対して `block-destructive.py:502-503`・`block-deps.py:163-164`・`pre-read-guard.py:158-159` は「読めないので止めた（fail-closed）」で deny。キット内で方針が揃っていない
  - 記事: 5/5「確認が動かなかったときは止める側に倒す」。キットの規約 A-14「判定不能は deny（合格に数えない）」
- 状態: 実証（ソースの静的確認。壊れた入力を与えての実行はしていない）
- 改善の方向: 3 本を block-destructive と同じ fail-closed（deny＋理由文）に揃え、回帰テストに壊れた入力のケースを足す

### R4-note-03 hook の時間切れは素通りになると記事は警告するが、キットの阻止系 hook に時間切れの補償が見当たらない
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - 記事: 2/5（n2ada5739f7b6）「時間切れになったフックは原則としてツールの実行を止めない」（出典 https://code.claude.com/docs/en/hooks ）、5/5「時間切れや失敗で、ゲートが素通りしうる」
  - キット: `03_ClaudeCode/hooks/settings.json:21,31,40,49,59` に `"timeout": 5`（阻止系 hook を含む）。`grep -rn 'fail-open\|fail-closed\|素通り' hooks/*.py` で時間切れ後の検出・記録の仕組みは見つからなかった
- 状態: 主張（公式文書の記述。時間切れの挙動はキット上で再現していない）
- 改善の方向: 阻止系 hook の実行記録（開始・判定）を残し、PostToolUse 側で「判定記録の無いツール実行」を検出して警告する

### R4-note-04 テスト改変の防止がコミット時（git hook）だけで、作業中にテストを書き換えさせない保護が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - 記事: 活用メモ 10（ne3eb8d0f86ed）「テストコードを触らせない」（ImpossibleBench を引用）、`/goal` の停止条件に「tests/ 配下を変更・削除していないこと」
  - キット: テスト弱体化の検査は `00_導入/02_プロジェクト配布/install-git-hooks.sh:13,42,110-120` の pre-commit のみで、しかも `scripts/test-weaken-check.py` が配布先に「あれば」配線（`HAS_WEAKEN`）。Claude Code の PreToolUse（`settings.json`）には tests/ への Edit/Write を止める hook が無い（hook 一覧: constitution-gate・block-deps・tool-timer・block-ci・instruction-guard・pre-write-check・block-phase・pre-read-guard・block-explore・block-destructive・block-gates・filter-output）
- 状態: 実証（settings.json の hook 一覧を python で列挙、grep）
- 改善の方向: 実装工程中は tests/・期待値ファイルへの Edit/Write を PreToolUse で止める（テスト作成工程だけ解除）選択肢を設計する

### R4-note-05 記事は「CLAUDE.md は短く。200 行超で遵守率が下がる」と説くが、キットは常時読み込みの規約が大きい
- 種別: 矛盾
- 深刻度: Medium
- 根拠:
  - 記事: 活用メモ 4（n7122b4f8d169）「200行を超えるファイルはコンテキストを消費し、指示の遵守率を下げる可能性がある」（出典リンク https://docs.anthropic.com/en/docs/claude-code/memory ）、活用メモ 9「CLAUDE.mdは減らす…増やすと全部が薄まります」
  - キット: `wc -c 02_共通/rules/*.md` 合計 33,724 バイト（`wc -l` 合計 280 行だが 1 行が非常に長い。`absolute-rules.md` は 24 行で表 1 行が数百字）。paths 無しの規約は毎セッション載る
- 状態: 実証（wc）。遵守率への影響は未確認
- 改善の方向: 常時載る規約の字数上限（行数でなく字数・トークン）を検査スクリプトに持たせ、記事の主張と同じ尺度で自己点検する

### R4-note-06 記事が紹介する `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` をキットは使っておらず、委譲本数の上限は撤廃済み
- 種別: 機会
- 深刻度: Medium
- 根拠:
  - 記事: 活用メモ 10「Claude Code v2.1.212 で CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION が追加されました。既定200です」
  - 手元バイナリ: `claude --version` → 2.1.330、`grep -a -o 'CLAUDE_CODE_MAX_SUBAGENTS[A-Z_]*' claude.exe` → `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` が 3 件（実在は確認。追加版・既定 200 は未確認）
  - キット: `grep -rn MAX_SUBAGENTS`（docs/research 除く）→ 0 件。利用者規約は「委譲の本数に上限は設けない（2026-10-25 撤廃。hook は記録のみ）」
- 状態: 実証（変数の実在）／未確認（追加版・既定値）
- 改善の方向: 暴走ループの最終防壁として、配布 settings にこの変数でセッション上限（規約の 30 本と整合する値）を置くか検討する

### R4-note-07 記事の Huang ら（ICLR 2024）の数値に取り違えがある
- 種別: 欠陥（記事側）
- 深刻度: Medium
- 根拠: arXiv 2310.01798v2 HTML の Table（取得日 2026-11-21）
  - 記事「常識問題…75.8点が38.1点まで落ちました。GPT-4でも95.5点が89.0点です」→ 表では 38.1 は round 1 で round 2 は 41.8（「まで落ちた」は最終値ではない）。95.5 は GPT-4 の **GSM8K（算数）**で、GPT-4 の CommonSenseQA は 82.0。文脈上、常識問題の数値に読める
  - 算数 75.9→75.1→74.7、Oracle 84.3／89.7 は表と一致
  - 内訳「変えなかった74.7%・正解→不正解8.8%・不正解→正解7.6%」は HTML 本文テキストに見つからない（図の中の値の可能性。未確認）
- 状態: 実証（表との照合）
- 改善の方向: 記事の該当文を「GSM8K の GPT-4 95.5→89.0」「CSQA は round 1 で 38.1」と条件ごとに書き直す。キットで引用する場合も同様

### R4-note-08 ImpossibleBench「テストを隠すか読み取り専用にすると率がほぼゼロ」は abstract では確認できない
- 種別: 未確認の主張
- 深刻度: Low
- 根拠: arXiv 2510.20270 abstract は「prompt, test access and feedback loop affect cheating rates」まで。「ほぼゼロ」の数値は abstract に無い（本文は読んでいない）
- 状態: 未確認
- 改善の方向: 本文の該当表（条件・モデル・n・率）を確認してから、キットの設計根拠（R4-note-04）に使う

### R4-note-09 記事の「サブエージェント起動は最大 1 体まで」とキットの「上限 30 本で並列委譲」が逆向き
- 種別: 矛盾
- 深刻度: Low
- 根拠:
  - 記事: 活用メモ 3（nba11398d3e7e）「『サブエージェントの起動は最大1体まで』とロックをかけておきます」（2026/8/16 時点と明記）
  - キット: `02_共通/rules/model-routing.md:13`「並列で委譲する（上限 30 本）」、`02_共通/rules/speed-harness.md:24`
- 状態: 主張（両文書の記述。記事は時点を明記しており、キットが後で方針を変えた可能性が高いが経緯の記録は未確認）
- 改善の方向: 方針転換の理由（モデル指定つき委譲で倍々消費を抑えた等）を lessons に 1 行残し、記事の読者が古い規則を写さないよう追記を検討

### R4-note-10 記事の「編集ごとに PostToolUse で npm test」とキットの「ゲートは要求時のみ」が逆向き
- 種別: 矛盾
- 深刻度: Low
- 根拠:
  - 記事: 活用メモ 9（n127bb651d9ac）の settings.json 例 `PostToolUse` / `matcher: Edit|Write` / `command: npm test`、「お願いは忘れられますが、フックは必ず動きます」
  - キット: `03_ClaudeCode/hooks/settings.json` の PostToolUse は tool-timer・observe・post-write-html・injection-guard のみ。`block-gates.py` がゲート実行を要求時（`GATES_REQUESTED=1`）に限る
- 状態: 実証（settings.json の列挙）
- 改善の方向: 「速度のためにゲートを要求時にする」設計判断と、記事の「終了基準を自己申告に預けない」の両立方法（完了宣言時だけ自動で走らせる等）を明文化する

### R4-note-11 記事の数値のうち出典リンクが付いていないもの
- 種別: 欠落
- 深刻度: Low
- 根拠（本文 HTML の該当語 ±600〜900 字の href を抽出）:
  - 活用メモ 2（n72b21c5a2b99）: Qiita「並列2スレッド×ultracodeで30分放置…Max 5xの5時間枠が消滅」→ href 0 件。「Sonnet 5＋Fable 5 アドバイザーで単体の10%以内・63%程度の価格」（ベンダー数値）→ href 0 件
  - 活用メモ 10: 「v2.1.212 で追加・既定200」→ 近傍の href は ImpossibleBench の arXiv のみ。「74.7%/8.8%/7.6%」→ href 0 件（論文リンクは上方にあるが値は表で確認できず。R4-note-07）
  - 活用メモ 5（n7f131d7fb6a3）: 「日本企業の生成AI活用・推進率87%」「9%」「米国38%・英国32%」→ href 0 件（帝国データバンク・Qiita・Zenn・料金ページには href あり）
  - 活用メモ 3: 「Max 5x の 58%」「20体近いサブエージェント」→ 個人体験で計測ログの提示なし
- 状態: 実証（href 抽出）
- 改善の方向: 出典の無い数値はキットへ引き写さない一覧（「引用してはいけない数値」）に入れる

### R4-note-12 記事の「ゲートに止められた回数の急減を見る」に対応する集計がキットに見当たらない
- 種別: 欠落
- 深刻度: Low
- 根拠: 記事 5/5「ゲートに止められた回数が急に減ったときは…ゲートを通らない経路ができたのかを確かめます」。キット: `grep -rln -E '止めた回数|deny.*件数|ブロック回数|deny 率|denies' 03_ClaudeCode 02_共通` → 0 件。block-destructive・pre-read-guard には deny の記録（B12）がある
- 状態: 未確認（記録はあるが、推移を見る集計の有無は grep 語彙の範囲でしか確かめていない）
- 改善の方向: deny 記録を日次で数え、急減を表示する点検スクリプトを検討（定時実行はしない。手動起動）

### R4-note-13 出所は連載名だけで記事単位の対応が無く、Claude Code 活用メモ側はキットから辿れない
- 種別: 機会
- 深刻度: Low
- 根拠: 前提の節。記事側にキットへの言及 0 件。キット側は「AIDD x QAメモ」連載名のみで記事 URL・記事番号が無い。活用メモ 1〜12（ハーネス・ループ・ガードレール）に由来する規律（sleep 禁止・停止条件など）には出所の記載が見つからない（`grep -E 'note 連載|QAメモ'` で 5 件、すべて AIDD x QA 連載）
- 状態: 実証（grep）
- 改善の方向: キットの `docs/` に「記事の主張 → キットの実装箇所」の対応表を置き、記事更新時に差分を見られるようにする（note への自動走査は Q-17 の方針どおり入れない）

## 整合していた主張（参考）

- 新しい依存は人が承認（記事 5/5）↔ `block-deps.py`（PreToolUse に配線、fail-closed `:163-164`）
- pass^k で見る（記事 5/5）↔ `02_共通/ツール/passk.py` が存在
- テストの削除・skip・assert 削除の検知（記事 4/5・5/5）↔ `test-weaken-check.py`（ただし許可の仕方は R4-note-01）
- バックグラウンド・sleep ポーリング禁止（記事 3）↔ 規約「バックグラウンド実行・sleep によるポーリング禁止」、`block-ci.py`

## 調べられなかったこと

- 33 件（生成AI x QA メモ 1〜25 等）はキーワード検索のみで全文は読んでいない。キットの機能に触れる記述を見落とした可能性がある
- note の有料部分: 本文 API の返り値が有料記事の全文か無料部分のみかは確認していない（活用メモ 2・3・5 に「ここから先は」の区切りがある）
- ImpossibleBench・METR・arXiv 2308.02828 の本文数値（abstract／記事の記述のみ）
- `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` の追加版と既定値
- hook の実行による再現（R4-note-02・03 は静的読み）
- 規約の字数と遵守率の関係（R4-note-05）

# D1-distribution 配布: 導入経路と摩擦（段1・広域）

- 対象: origin/main の worktree（commit 7e80b79、VERSION 8.7.0）。README.md（204 行）・README.en.md（20 行）・`00_導入/` の 3 ディレクトリ 20 ファイル・`.claude-plugin/`（marketplace.json・plugin.json・hooks.json）・`01_利用者向け資料/01_利用ガイド.html` の導入章（328〜470 行）
- 調べた方法: 初めて使う人として README の「30秒で試す」→「導入」→ 利用ガイド導入 A の順に読んだ。静的に読んだ（grep・sed）ほか、次の 3 つを実際に動かした。いずれも本物の `~/.claude` は使っていない
  1. `HOME=<scratchpad>/d1/home3 bash 00_導入/01_インストール/install.sh` を 3 回（同じ HOME に対して）
  2. `HOME=<scratchpad>/d1/home3 bash verify.sh`
  3. hook 3 本（block-ci / block-destructive / tool-timer）を macOS 標準の `/usr/bin/python3`（3.9.6）で、作業用の空ディレクトリから起動
  - Python 3.9 互換性は、自作の ast 走査（`scratchpad/d1/py39check.py`）で hooks・ツール・導入スクリプト全件を調べた
  - plugin 経由の導入（`/plugin install`）は実際には行っていない
- 調べた件数/全件数: 導入経路は 3/3（plugin・install.sh・export-project.sh）。ただし export-project.sh は静的に読んだだけ。Python ファイルは導入系とツール系をすべて走査した（hooks 30 本中 .py 全件 ＋ 02_共通/ツール ＋ 00_導入 の .py）
- 外部の根拠: Claude Code hooks 文書 https://code.claude.com/docs/en/hooks （取得日 2026-11-21。冒頭 10 万字まで読んだ）

---

## D1-distribution-01 / 対応 Python 3.9 だと hook が例外で落ち、守りが黙って外れる
- 種別: 欠陥
- 深刻度: Critical
- 根拠:
  - 3.9 で関数の定義時に TypeError になる `X | None` 注釈を、`from __future__ import annotations` を書かずに使っている hook が 12 本ある。走査結果: block-ci.py:28、block-destructive.py:200、block-phase.py:42、config-snapshot.py:32、constitution-gate.py:72、filter-output.py:55、instruction-guard.py:102、pre-read-guard.py:69、reply-language.py:56、session-context.py:52、statusline.py:75、tool-timer.py:113
  - 実際に動かした結果: `/usr/bin/python3`（Python 3.9.6）で block-ci / block-destructive / tool-timer を起動すると、3 本とも `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'` を出して exit=1 になった
  - 製品文書: exit 1 は「Non-blocking error ... The action goes ahead」で、ポリシーを強制するなら exit 2 を使うよう書かれている（hooks 文書の Exit codes 節）。つまり `rm -rf` などを止めるはずの hook が、3.9 の環境では何も止めずに素通りさせる
  - hooks.json と settings.json は `python3` を名前で呼んでいる。macOS の Xcode CLT に入っている python3 は 3.9.6（`/usr/bin/python3 --version` で確かめた）
  - キット自身の規約 A-14「判定不能は deny」とも合わない
- 状態: 実証
- 改善の方向: 全 hook の先頭に `from __future__ import annotations` を入れて 3.9 で回帰テストする。あるいは起動時に版を確かめ、満たさなければ exit 2 で理由を出す。plugin 側では `onFailure: block` も検討する

## D1-distribution-02 / install.sh を 2 回目に実行すると、利用者の元の CLAUDE.md・AGENTS.md の退避が上書きされて消える
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - install.sh:33-37・39-43 は `cp CLAUDE.md CLAUDE.md.bak` の後に、テンプレートで上書きする。退避先の名前が固定なので、2 回目には 1 回目に置いたキットのテンプレートが .bak を上書きする
  - 実際に動かした結果: 隔離した HOME に `MY ORIGINAL CLAUDE.md` を置いて 2 回実行した。2 回目の後、`head CLAUDE.md.bak` は `@AGENTS.md`（キットのテンプレート）になり、元の内容はどこにも残っていなかった
  - 利用ガイド 01_利用ガイド.html の導入 A は「自分の CLAUDE.md は消さず CLAUDE.md.bak に退避」と書き、更新は「同じフォルダで git pull」と案内している。つまり案内どおりに更新して再導入すると、元の内容が消える
- 状態: 実証
- 改善の方向: 退避名に日時を付ける（`.bak.<日時>`）。既にキットのテンプレートと同じ中身なら退避しない

## D1-distribution-03 / 既存のキット同名スキル・コマンド・hook・エージェントを、退避なしで上書きする
- 種別: 欠陥
- 深刻度: High
- 根拠:
  - install.sh:47・58・69・73・77 は `cp -r` / `cp` で上書きする。退避するのはリンクのときだけ（50-57 行）
  - 実際に動かした結果: 隔離した HOME の `skills/done-gate/SKILL.md` に `my done-gate` と書いてから再導入すると、キット版に置き換わった。`ls skills | grep bak` は 0 件
- 状態: 実証
- 改善の方向: 上書きする前に差分があるファイルだけ日時付きで退避し、退避した一覧を出す

## D1-distribution-04 / settings.json が既にあると守りの大半が配線されないのに、README は「install-guard.sh だけでも入る」と書き、verify.sh は全件 OK を返す
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - README.md:86-89 の表は `git add -A`・`rm -rf` の deny を挙げ、「これらは install-guard.sh だけでも入る」と書いている
  - 一方、install_guard.py が配線するのは GUARDS の 6 項目（tool-timer×3・instruction-guard・prompt-priority・reply-language）だけで、block-destructive は含まない（install_guard.py の GUARDS 定義）
  - install.sh:79-80 は、settings.json が既にあると「手動でマージしてください」と出すだけ
  - 実際に動かした結果: 既存の settings.json がある隔離 HOME に導入すると、`grep -o block-destructive settings.json` は 0 件だった（配線は 6 項目だけ）
  - 同じ状態で verify.sh を実行すると exit=0、`結果: OK=106 / NG=0` になり、`✅ block-destructive.py` と `✅ ~/.claude/settings.json: 問題なし` を表示した。verify.sh はファイルがあるかを見ているだけで、配線されているかは見ていない
  - Claude Code を使っている人はふつう settings.json を既に持っているので、大多数の利用者がこの経路に入ると考えられる（推測。利用者の分布は未確認）
- 状態: 実証
- 改善の方向: install_guard と同じ「既存設定への merge」を全 hook に広げる。verify.sh に「settings.json に配線されているか」の検査を足す。README の記述を実態に合わせる

## D1-distribution-05 / plugin 導入では保守者向けの「憲法ゲート」が全プロジェクトに入り、一度止まると利用者側に分かりにくい解除手順を求める
- 種別: 過剰
- 深刻度: High
- 根拠:
  - .claude-plugin/hooks.json は PreToolUse の先頭に `constitution-gate.py pre` を全ツールに対して配線している
  - constitution-gate.py の 1〜30 行と環境変数の grep を見た限り、適用範囲を絞る条件（プロジェクト名・opt-in の設定）は見当たらない。冒頭のコメントには「解除の環境変数は作らない」とある
  - 解除の条件は 2 つ: 保守者が自分の端末で停止ファイルを消すこと（223・292 行）と、インシデント記録を書くこと（73 行で `06_保守者向け/学んだこと.md`・`docs/lessons.md`・`.claude/lessons.md` を探す。301 行）。キットの外のプロジェクトでは「保守者」が誰を指すのか、どこに何を書けばよいのかが説明されていない
  - README の 30 秒導入（README.md:14-19）はこのゲートの存在に触れていない。README.md:92-93 の「8.7.0 で足したもの」で初めて説明される
  - 今回の依頼の中で、利用者本人が「誤判定で停止」したため手動で解除した、と報告している（主張。誤判定かどうかは未検証）
- 状態: 実証（配線と解除の条件は静的に読んで確かめた）。誤検知の頻度は未確認
- 改善の方向: plugin では opt-in（プロジェクトに印があるときだけ有効）にする。解除手順を、利用者が読める文書として 30 秒導入の横に置く

## D1-distribution-06 / アンインストール手順と、導入したファイルの一覧（manifest）が無い
- 種別: 欠落
- 深刻度: High
- 根拠:
  - `grep -rniE "uninstall|アンインストール|削除手順"` を README・INDEX・00_導入・利用者向け資料に対して実行した。当たったのは install-git-hooks.sh の `--uninstall`（git hook のみ）だけ
  - install.sh が書き込む先は少なくとも次のとおりで、どれを置いたかの記録は残らない（install.sh:30・62・89・108・116・121）
    - `~/.claude/` の skills・commands・agents・hooks・scripts・rules/aidd-kit・docs/aidd-kit・templates・CLAUDE.md・AGENTS.md・KIT_VERSION・settings.json
    - `~/.agents/skills/`（71 本）
    - `~/.codex/AGENTS.md`（シンボリックリンク）
- 状態: 実証
- 改善の方向: 導入時に配置したファイルの一覧を `~/.claude/aidd-kit.manifest` に記録し、uninstall.sh で一覧のファイルを退避し、.bak を戻す。plugin の場合は `/plugin uninstall` を README に 1 行書く

## D1-distribution-07 / 更新手順が README に無く、利用ガイドの記述は不完全
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - README.md には更新の節が無い（「更新」「git.pull」「plugin update」を grep して README は 0 件）
  - 利用ガイドの導入 A は「あとで更新するときも同じフォルダで git pull するだけ」と書くが、install.sh を再実行する必要には触れていない（コピーで配置しているので、pull しただけでは導入先に反映されない。install.sh:47-77）
  - plugin 経由の更新（marketplace の更新）には触れていない
  - 再実行すると 02・03 の問題も起きる
- 状態: 実証（文書を grep して確かめた）
- 改善の方向: README に「更新」節を作り、経路ごと（clone 経路は pull ＋ install.sh ＋ verify.sh、plugin 経路は marketplace の更新）に書く

## D1-distribution-08 / plugin と install.sh を両方入れると hook が二重に動くが、それについての注意書きが無い
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - 製品文書: 「When a plugin is enabled, its hooks merge with your user and project hooks」（hooks 文書）
  - README.md:14-27 は plugin と clone ＋ install.sh を続けて案内している
  - CLAUDE.md（キット）は plugin 導入を、install.sh はグローバル導入を勧めている
  - 両方入れると tool-timer・instruction-guard などが ~/.claude/settings.json と plugin の hooks.json の 2 か所から呼ばれる
  - README を `重複|二重` で grep すると、注意書きは 0 件
  - 二重に動いたときに計測値がどうずれるかは確かめていない
- 状態: 主張（製品文書と静的な読み）。二重に動いたときの影響は未確認
- 改善の方向: 「どちらか一方」と明記し、install.sh と verify.sh で plugin が有効か検出して警告する（verify.sh は plugin を grep しても 0 件で、検出していない）

## D1-distribution-09 / plugin 導入だけでは、工程承認ゲートと statusline の部品が足りない。その違いは 1 文で済まされている
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - block-phase.py:28・47 は、判定スクリプトを `scripts/` か `~/.claude/scripts/check_approval.py` に探す。plugin はこれを置かない（plugin.json に scripts の配布は無い）
  - statusline.py:42-46 は `~/.claude/statusline.sh` を前提にしている
  - README.md:21 は「スクリプト一式まで入れるなら clone して」と 1 文書くだけで、plugin だけで入れたときに何が効かないかの一覧が無い
  - plugin が入れる hook には block-phase が含まれる（hooks.json）
- 状態: 主張（静的に読んだ。plugin で実際に入れて試してはいない）
- 改善の方向: README に経路ごとの機能比較の表を置く（plugin で効くもの・効かないもの）。block-phase は `${CLAUDE_PLUGIN_ROOT}/02_共通/ツール` も探すようにする

## D1-distribution-10 / 英語圏の利用者には導入できる情報が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - README.en.md は全 20 行で、空でない行は 14 行。clone 先は `git clone <this repository>` という仮置きの文字列のまま（README.en.md:17）で、plugin 経路の記載も無い
  - 導入スクリプトのパスは日本語のディレクトリ名（`./00_導入/01_インストール/install.sh`）なので、英語キーボードでは補完頼みになる
  - install.sh・verify.sh の出力、hook の deny 理由はすべて日本語（install.sh:24・35・80、constitution-gate.py:223 など）。英語の利用者は止められた理由を読めない
  - CONTRIBUTING.md も本文は日本語（先頭 5 行で確認）
- 状態: 実証（ファイルを読んで確かめた）
- 改善の方向: README.en.md に実在の URL・plugin 経路・前提・解除手順を書く。ASCII だけの入口（例: ルートの `install.sh` から呼ぶ）を用意する。deny 理由に英語の 1 行を併記するかは段 2 で判断する

## D1-distribution-11 / 前提となる Python の版の記述が文書ごとに違う
- 種別: 矛盾
- 深刻度: Medium
- 根拠:
  - 利用ガイド 01_利用ガイド.html:336 は「Python 3.10 以上」
  - doctor.py:7 は「Python 3.9 互換」
  - README.md には版の記述が無い（`python ?3\.[0-9]+` を grep して 0 件）
  - 実態は 01 のとおりで、3.9 では hook が壊れる
- 状態: 実証
- 改善の方向: README の冒頭に前提（OS・python3 ≥ 3.10・bash・git）を 1 行で置く。install.sh の冒頭で版を確かめ、満たさなければ止める

## D1-distribution-12 / 利用ガイドの導入例が古い（6.3.0 の出力、Codex のリンクを手で張る手順）
- 種別: 矛盾
- 深刻度: Low
- 根拠:
  - 01_利用ガイド.html:361・366・375 に `版: 6.3.0` の出力例がある。現行は 8.7.0
  - 出力例の個数（スキル 26・Hooks 7・OK=48）は実数（スキル 27・コマンド 25・hook 30 本・verify OK=106）と合わない
  - 368 行目は `ln -s ~/.claude/AGENTS.md ~/.codex/AGENTS.md` を手で張るよう案内しているが、現行の install.sh:44 は自動で張る（隔離 HOME で `.codex/AGENTS.md -> ../.claude/AGENTS.md` ができることを確かめた）
- 状態: 実証
- 改善の方向: 出力例を現行版で撮り直す。check-docs に版の文字列の検査を足す

## D1-distribution-13 / 利用ガイドの任意手順が「配布しない」保守者用ディレクトリを指している
- 種別: 矛盾
- 深刻度: Low
- 根拠:
  - 01_利用ガイド.html（導入 A の「任意」の手順）は `./06_保守者向け/03_回帰テスト/test-hooks.sh` と `test-install.sh` を案内している
  - 一方、README.md:31・177 は `06_保守者向け/` を「保守者専用。配布しない」としている
  - install で `~/.claude/docs/aidd-kit/` にコピーされたガイドから見ると、この相対パスは存在しない
- 状態: 実証（文書を読んで確かめた）
- 改善の方向: 利用者向けの自己診断は `00_導入/03_点検/doctor.py` か verify.sh に寄せ、ガイドからはそれを案内する

## D1-distribution-14 / Windows 向けの案内とスクリプトの実態が合わない
- 種別: 矛盾
- 深刻度: Low
- 根拠:
  - 01_利用ガイド.html:278 は Windows の PowerShell・WSL を、前提表は「Windows は WSL か Git Bash」を挙げている
  - 一方、導入スクリプトは bash だけ（`ls 00_導入/01_インストール | grep -iE "ps1|bat|cmd"` は 0 件）
  - doctor.py:4・18 は「Codex の Windows 環境（git/bash 無し）」を前提にしている
  - Git Bash で install.sh が通るかは確かめていない
- 状態: 未確認（Windows では実行していない）
- 改善の方向: 対応 OS を明記する（macOS・Linux・WSL のみ、など）。Windows ネイティブは「対象外」と書く

## D1-distribution-15 / plugin の状態ファイルを plugin のインストール先に置くため、更新で消える可能性がある
- 種別: 欠陥
- 深刻度: Low
- 根拠:
  - constitution-gate.py:174 は計測の状態を `HERE.parent / "tool-time.json"` に置く。plugin 経由なら `${CLAUDE_PLUGIN_ROOT}/03_ClaudeCode/` の下になる
  - 製品文書は、更新をまたいで残すべき状態には `${CLAUDE_PLUGIN_DATA}` を使うよう書いている（hooks 文書）
  - hooks 配下を `grep -rl CLAUDE_PLUGIN_DATA` すると 0 件
  - plugin を更新したときに実際に消えるかは確かめていない
- 状態: 主張（静的に読んだのと製品文書）。消えるかどうかは未確認
- 改善の方向: 状態ファイルの置き場を、`CLAUDE_PLUGIN_DATA` があればそれを使い、無ければ `~/.claude` を使うよう統一する

## D1-distribution-16 / 30 秒導入のつもりが、clone 経路では実際の手順がずっと多い
- 種別: 機会
- 深刻度: Low
- 根拠:
  - README の「30秒で試す」は 2 コマンド（plugin）、または 3 コマンド（clone・install・verify）
  - 実際に clone 経路で全部入れるには、settings.json を手で merge し（install.sh:80）、CLAUDE.md・AGENTS.md の .bak を手で merge する（install.sh:35・41）必要がある
  - 利用ガイドの前提確認は 4 コマンド（328 行〜）
  - 隔離 HOME での install.sh 1 回の所要時間は今回測っていない（未計測）
- 状態: 実証（手順の数え上げ）
- 改善の方向: 手で merge する部分を自動 merge に置き換え、README には「最短の経路」と「全機能の経路」の手順数を正直に書く

## 調べられなかったこと
- plugin 経由の実際の導入（`/plugin marketplace add` → `/plugin install`）。実環境に入れない制約のため。CLAUDE_PLUGIN_ROOT の実際のパスや、日本語のディレクトリ名が正しく扱われるかは未確認
- Linux・WSL・Git Bash での install.sh の挙動（未確認）
- export-project.sh（プロジェクト配布）の実際の実行。静的にも詳しくは読んでいない
- plugin と install.sh を併用したときに計測値が二重に数えられるか（未確認）
- 憲法ゲートの誤検知の頻度（hook-decisions.log は今回の範囲外で、読んでいない）
- hooks 文書は冒頭 10 万字だけ読んだ（残りの 19 万字は読んでいない）
- 他の Claude Code 設定キット（導入手順の比較対象）の調査は、段 1 の範囲外として行っていない

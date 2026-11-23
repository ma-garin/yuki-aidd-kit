# S2-cc-plugins 段2（深掘り）: Claude Code plugin・marketplace

- 入力: `docs/research/2026-11-21/stage1/S2-cc-plugins.md`（High 3 件・Medium 5 件・Low 6 件）
- 選定: High は 3 件だけなので全件
  1. S2-cc-plugins-01（版が固定で更新が届かない。必須指定）
  2. S2-cc-plugins-02（plugin では憲法・rules が載らないのに hook は全部入る。必須指定）
  3. S2-cc-plugins-03（plugin と install.sh の併用で全 hook が二重発火）
  - 選ばなかった High: なし（High は上記 3 件のみ）
- 実行環境: worktree `kit-audit`（ブランチ research/audit-rebuild-20261123）。読み取りのみ。`claude plugin install` は実行していない。`claude plugin list`・`claude plugin validate .` は読み取り。CLI は段1 と同じ claude 2.1.330 系（版の再確認はしていない）
- 実行日時: 2026-11-23（Asia/Tokyo）
- 対象コミット: 3ef90fd（origin/main）

---

## S2-cc-plugins-01 版が固定のまま変更が plugin 利用者に届かない
- 確かめたコマンドと出力の要点:
  - `cat .claude-plugin/plugin.json` → `"version": "8.7.0"`。`.claude-plugin/marketplace.json` の plugins[0] には version 無し（name・source "./"・description のみ）。`cat VERSION` → 8.7.0
  - `git log -n3 -- .claude-plugin/plugin.json` → 最後の更新は 1d9f163（2026-11-10「Ver.8.7.0 の版・CHANGELOG…」）。VERSION も同じコミットが最後
  - `git log --oneline 1d9f163..HEAD | wc -l` → 26（段1 の 23 は 7e80b79 時点。`7e80b79..HEAD` = 3、`1d9f163..7e80b79` = 23 で整合）
  - `git diff --stat 1d9f163..HEAD -- 03_ClaudeCode/hooks .claude-plugin 03_ClaudeCode/skills` → 21 ファイル・+589/-160。plugin が配る hook・skill の中身は版を上げずに変わっている
  - hook の変更コミット（1d9f163 以降、`git log -- 03_ClaudeCode/hooks`）: 42f5ffc・7ab4d19・b1b49a8・e4c3334・52da673・9d37011 の 6 件（statusline・constitution-gate・見積書式）
  - `06_保守者向け/03_回帰テスト/test-plugin-manifest.sh:25` は `plugin.json の version == VERSION` だけを検査（コミット数との乖離は見ない）
  - README.md:15-19 の plugin 導入手順に `/plugin marketplace update`・auto-update に関する記述なし（`grep -n "marketplace update\|auto-update" README.md` は 18 行目の install のみ）
- 引き継ぎ情報（安全 hook の修正が plugin に届かない可能性）との関係:
  - 安全 hook の最終変更コミットを `git log -1 -- <file>` と `1d9f163..HEAD` で数えた。block-destructive.py: 最終 ed3695d（2026-11-03）・1d9f163 以降 0 件。pre-read-guard.py: 最終 ed3695d・以降 0 件。constitution-gate.py: 全 4 件のうち 1d9f163 以降が 2 件（e4c3334・b1b49a8、2026-11-14）
  - 判定: block-destructive・pre-read-guard の直近修正は 8.7.0（11-10）より前なので、8.7.0 を取り込んだ利用者には届いている。「届かない」と言えるのは constitution-gate の 11-14 の 2 修正（無報告ゲートの下限 60 秒・見積書式の合わせ込み）で、これは 8.7.0 に載っていない。さらに 8.7.0 より前の版（例 8.6 系）で止まっている利用者には、固定版のため 11-03 の修正も届かない
  - つまり引き継ぎの懸念は「構造として成立」（版固定が原因）。ただし安全 hook のうち破壊操作・秘密読み取りの 2 本は現行版で未反映の修正が無い。未反映なのは憲法ゲートの 2 件
- 判定: 版固定とコミット数の乖離は実証。「利用者が古いキャッシュに留まる」挙動そのものは公式文書の記述に依存（動いているバイナリでの再現は未確認。手元は plugin 未導入で、導入は実環境を変えるため行わない）
- 壊れていない可能性: 版を明示するのは意図的な安定運用の選択肢であり、リリース時にまとめて上げる運用なら仕様どおり。ただし README に更新手順がなく、利用者が更新できると知る手段が無い点は欠落として残る
- 状態の変更: 実証（コミット数・版の値・安全 hook の反映状況）／主張（更新が届かない挙動）。段1 から: 「23」を現 HEAD の 26 に更新、引き継ぎ情報との関係（安全 2 本は 8.7.0 に反映済み、未反映は constitution-gate の 2 件）を追加。深刻度は High のまま（届かない対象が憲法ゲートの修正を含むため）

---

## S2-cc-plugins-02 plugin では憲法・rules が載らないのに、前提とする hook は全部入る
- 確かめたコマンドと出力の要点:
  - `claude plugin validate .` → 「⚠ root: CLAUDE.md at the plugin root is not loaded as project context. To ship context with your plugin, use a skill」（警告 1 件）。plugin.json の宣言キーは skills・commands・agents・hooks・outputStyles のみで、rules・CLAUDE.md に当たるキーが無い
  - README.md:22「スクリプト一式（statusline・rules・…）まで入れるなら clone して」と、plugin に rules が入らないことは書かれている
  - `.claude-plugin/hooks.json`: constitution-gate.py（pre・stop）・reply-language.py・instruction-guard.py・block-ci.py ほか 29 登録を無条件で登録（`python3 -I` で数えた: hooks.json 29 登録・スクリプト 25 本）
  - `constitution-gate.py`（読めた。段1 では未読）: 適用の可否を決める opt-in 条件なし。`pre` は全ツールが対象（READ_ONLY は 3 回まで無条件、以降は見積が無ければ違反）。違反時は `.claude/constitution-stop` を作業ディレクトリに書き（:67-68, :216-217）、以後のツールを deny（:289-292）。解除は保守者の端末のみ、かつ事後記録を `06_保守者向け/学んだこと.md`・`docs/lessons.md`・`.claude/lessons.md` のどれかに要求（:73, :301）
  - deny の文面は違反種別と停止 file を示すが、「見積もり：N分（HH:MM）」の書式の本文は rules（absolute-rules.md A-2）側にあり、plugin には載らない（rules は同梱されない）
- 判定: 構造としては成立。plugin だけの利用者は、規約（見積を先に出す・中間報告の間隔）を知らないまま、見積を出さない最初の読み取り 4 回目以降で憲法ゲートに止められ得る。止まると停止 file を消すまで全ツールが deny
- 壊れていない可能性: skills（27 本）に書式の本文が含まれていれば利用者は書式を知り得る。`work-metering` スキルは書式を持つ（`03_ClaudeCode/skills/work-metering/SKILL.md`）。ただし plugin 利用者に A-2 を強制する前提の周知は無く、スキルが自動で読まれる保証もない
- 状態の変更: 実証（validate の警告・hooks.json の無条件登録・gate に opt-in 条件が無いこと）／未確認（plugin 利用者のセッションで実際に deny が起きるか。hook の入力形式・transcript の位置が plugin 経由でも同じかは動かして確かめていない）。段1 から: constitution-gate の適用範囲を確認（全プロジェクト・無条件）。状態は「実証（構造）／未再現（実機の deny）」

---

## S2-cc-plugins-03 plugin と install.sh を両方入れると全 hook が二重に発火する
- 確かめたコマンドと出力の要点:
  - `python3 -I` で `.claude-plugin/hooks.json` と `03_ClaudeCode/hooks/settings.json` の (event, matcher, script) を比較 → 29 / 29・集合一致 True・スクリプト 25 本。コマンド文字列は `python3 ~/.claude/hooks/constitution-gate.py pre`（settings）と `python3 "${CLAUDE_PLUGIN_ROOT}"/03_ClaudeCode/hooks/constitution-gate.py pre`（plugin）で別
  - `grep -n "二重\|両方" README.md` → 該当なし。README.md:15-27 は 2 つの導入を並べるだけで排他の注意なし
  - plugin 側 hook の中に plugin 経由か判定する処理は無い（`grep -n plugin 03_ClaudeCode/hooks/*.py` はコメントのみ）
- 判定: 両方入れると、同じイベントに別コマンド文字列で 2 回登録される構造は実証。Claude Code が別パスのコマンドを重複排除するかは動いているバイナリでの確認が要る（文字列が異なるため排除されない可能性が高いが未確認）
- 壊れていない可能性: 二重実行が冪等な hook（読み取り判定のみ）なら実害は小さい。しかし tool-timer・constitution-gate は状態を書くため、2 回目の pre が区間を二重に開く等の副作用は未確認
- 状態の変更: 実証（登録の一致・README に注意が無いこと）／主張（二重発火の実害）。段1 の「主張」から変更なし。深刻度は据え置くが、再現は両方を導入した別環境が要る（今回は実環境を守るため行わない）

---

## 引き継ぎ情報との総括
- 「プラグイン配布・更新経路で安全 hook の修正が届かない可能性」: 版固定（01）で裏付けられる。ただし安全 2 本（block-destructive・pre-read-guard）の直近修正は 8.7.0 に含まれ、未反映は constitution-gate の 2 件（2026-11-14）。実機の更新挙動は未再現

## 未確認
- 動いているバイナリでの plugin 更新挙動（auto-update 既定・キャッシュ固定）。公式文書の記述のみ
- plugin 利用者のセッションで constitution-gate が実際に deny するか
- 別パスの二重登録を Claude Code が重複排除するか、二重実行時の状態 file の副作用
- 手元の `~/.claude/settings.json` に `constitution-gate` の文字列が 0 件だった理由（読んだだけで原因は調べていない）

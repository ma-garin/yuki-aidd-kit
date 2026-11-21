# D2-adoption 普及: 発見されやすさと利用の実態（段1・広域）

- 対象: ma-garin/yuki-aidd-kit（origin/main の worktree、VERSION 8.7.0）と類似キット 3 本（obra/superpowers・affaan-m/ECC（everything-claude-code）・github/spec-kit）
- 調べた方法: `gh repo view`（stars・forks・watchers・description・topics・license・homepage）、`gh api .../traffic/{views,clones,popular/referrers,popular/paths}`、`gh api .../tags`・`/releases`、README.md・README.en.md・llms.txt・.claude-plugin/{plugin.json,marketplace.json,hooks.json}・ルート CLAUDE.md の静的な読み取り。比較キットは scratchpad/clones に `git clone --depth 1` して README を読んだ（スクリプト・ビルドは実行していない）
- 調べた件数/全件数: 自キットのメタデータ 6 項目/6、traffic 4 エンドポイント/4、配布の入口ファイル 7/7（README.md・README.en.md・llms.txt・plugin.json・marketplace.json・hooks.json・CLAUDE.md）、比較キット 3/3（指定分）。WebSearch・WebFetch は使っていない
- 取得日: 2026-11-21

## 実測値（要約）

| 項目 | yuki-aidd-kit | superpowers | ECC | spec-kit |
|---|---|---|---|---|
| stars | 0 | 323,015 | 307,988 | 150,858 |
| forks | 0 | 28,679 | 45,322 | 13,549 |
| topics | なし（null） | 8 個 | 8 個 | 7 個 |
| description | 空 | あり | あり | あり |

- yuki: watchers 0、license MIT、homepage 空、created 2026-06-23、pushed 2026-11-15
- traffic（直近 14 日）: views 7 / uniques 2、clones 242 / uniques 115、referrer は github.com の 1 件だけ
- tags 0、releases 0（`gh api repos/ma-garin/yuki-aidd-kit/tags --jq length` → 0、`/releases` → 0）

## 発見

### D2-adoption-01 GitHub 上の発見手段（description・topics・homepage）が全部空
- 種別: 欠落
- 深刻度: High
- 根拠: `gh repo view ma-garin/yuki-aidd-kit --json description,repositoryTopics,homepageUrl` → `"description":""`, `"repositoryTopics":null`, `"homepageUrl":""`。比較 3 本は全て description と topics 7〜8 個（superpowers: ai,skills,subagent-driven-development 等／ECC: claude-code,anthropic,mcp 等／spec-kit: spec-driven,prd 等）
- 状態: 実証
- 改善の方向: description（英語 1 文）と topics（claude-code・claude-code-plugin・qa・hooks・spec-driven・istqb 等）を設定する

### D2-adoption-02 ほぼ誰にも見られていない（views 7/uniques 2、外部流入 0）
- 種別: 欠陥（普及の実態）
- 深刻度: High
- 根拠: `gh api repos/ma-garin/yuki-aidd-kit/traffic/views` → count 7 / uniques 2（2026-11-10 に 6、11-13 に 1）。`popular/referrers` → `[{"referrer":"github.com","count":1,"uniques":1}]`。stars 0・forks 0・watchers 0
- 状態: 実証
- 改善の方向: 外部の導線（README 英語化・公式マーケットプレイス・記事）を作るまで「普及」は 0 と扱い、観測は traffic で週次に取る

### D2-adoption-03 clones 242/uniques 115 は views と釣り合わず、利用者数の指標にならない
- 種別: 矛盾
- 深刻度: Medium
- 根拠: 同 14 日間で views uniques 2 に対し clones uniques 115（`traffic/clones`）。ブラウザで見ずに clone するのはプラグインの `/plugin marketplace add`・CI・自動化・ボットが考えられるが、出所は特定していない
- 状態: 実証（数値）／出所は未確認
- 改善の方向: clone 数を普及の根拠に使わない。.github/workflows/kit-ci.yml や自分の端末の自動更新が clone しているかを切り分ける

### D2-adoption-04 プラグインを入れた第三者にも「憲法ゲート」（全ツール停止・保守者の手での解除）が全ツールに掛かる
- 種別: 過剰
- 深刻度: High
- 根拠: `.claude-plugin/hooks.json:8` が PreToolUse（matcher なし＝全ツール）で `03_ClaudeCode/hooks/constitution-gate.py pre` を呼び、`:235` が Stop でも呼ぶ。ルート `CLAUDE.md:7-9` は「違反 1 回で全ツールが deny。解除は保守者が自分の端末で file を消し、`06_保守者向け/学んだこと.md` にインシデントを書くまで再開不可。解除の環境変数は無い」と書く。今回の依頼文でも利用者が「誤判定で停止」を手で解除している（利用者の発言＝主張）。hook 本体の解除条件の実装は読めていない（読み取りが権限で拒否された）
- 状態: 主張（配線は実証、停止条件と第三者環境での挙動は未確認）
- 改善の方向: 保守者専用の hook（constitution-gate・日本時間・応答の口調判定など）をプラグイン既定から外し、opt-in にする

### D2-adoption-05 英語 README が 20 行の抜粋で、プラグインでの導入手順が無く、clone URL も仮置き
- 種別: 欠落
- 深刻度: High
- 根拠: `wc -l README.en.md` → 20。`README.en.md:3` "Full documentation is in Japanese"、`README.en.md:17` `git clone <this repository>`（README.md:22 は実 URL）。README.md:15-18 の `/plugin marketplace add ma-garin/yuki-aidd-kit` が英語版には無い。比較: ECC は 17 言語の README、spec-kit は英・中・日・韓の 4 言語、superpowers は英語のみだが本文 400 行
- 状態: 実証
- 改善の方向: 英語版を正にして、冒頭 30 行（何をするか・30 秒導入・何が止まるか）を日本語版と同期させる

### D2-adoption-06 版の約束（git tag vX.Y.Z）が守られておらず、リリースも 0
- 種別: 矛盾
- 深刻度: Medium
- 根拠: README.md の「版」段落が「`VERSION` ファイルと git tag（`vX.Y.Z`）に対応」と書くが、`gh api repos/ma-garin/yuki-aidd-kit/tags --jq length` → 0、`/releases` → 0。VERSION と plugin.json は 8.7.0。spec-kit は README 冒頭に最新リリースのバッジを置く
- 状態: 実証
- 改善の方向: タグと GitHub Release を版ごとに打つ（CHANGELOG から本文を作る）か、README の記述を実態に合わせる

### D2-adoption-07 llms.txt が古い（ルールの数と委譲方針が本体と違う）
- 種別: 矛盾
- 深刻度: Medium
- 根拠: `llms.txt:48` は absolute-rules を「A-1〜A-10」と説明するが、`02_共通/rules/absolute-rules.md` の表は A-1〜A-14（A-2a・A-11〜A-14 を含む）。`llms.txt:50` は model-routing を「委譲は隔離目的のみ」と書くが、`02_共通/rules/model-routing.md:13` は「独立単位が 2 つ以上あれば並列で委譲（上限 30 本）」。llms.txt は INDEX.md から生成すると冒頭に書いてあるので、生成元の INDEX.md も古い可能性がある（INDEX.md は未確認）
- 状態: 実証（llms.txt と rules の食い違い）
- 改善の方向: llms-txt.py を CI で再生成して差分を検出する。説明文を生成元の frontmatter から取る

### D2-adoption-08 README 冒頭に「誰向けか」と「自分の作業がどう変わるか」の具体例が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠: README.md:1-10 は機能 4 点（tool-timer.py / est.py / check-approval / phase-hash / check_design.py / token_report.py）をスクリプト名で並べる。比較: superpowers は冒頭の "How it works" で利用者体験を時系列の物語で書く（README:36-45）。spec-kit は「What you need / Process / Outcome」の表で入口を選ばせる（README:24-31）。ECC は hero 画像と 36 件の画像・バッジ。yuki は画像・バッジ・デモ 0 件（`grep -cE '!\[|<img|shields|\.gif|demo'` で 0）。ただし superpowers も画像 0 件で普及しており、デモ画像の有無は決定要因ではない（相関の根拠は無い）
- 状態: 実証（各 README の構成）／普及への効き目は未確認
- 改善の方向: 冒頭に「導入前／導入後」の会話例（見積が注入され、完了報告に実測が無いと差し戻される場面）を 1 つ置く

### D2-adoption-09 導入の面積が大きく、外し方が書かれていない
- 種別: 欠落
- 深刻度: Medium
- 根拠: hooks.json の command 58 件（重複除く hook スクリプト 25 本）、skills 27・commands 25・hooks 32 ファイル（`ls | wc -l`）。README の導入は「① グローバル ② プロジェクト配布、併用が前提」（README.md:35）で、install.sh は `~/.codex/AGENTS.md` を退避してシンボリックリンクに置き換える（README.md:46）。README に uninstall／アンインストールの語は無い（`grep -E 'uninstall|アンインストール' README.md` 一致なし）
- 状態: 実証
- 改善の方向: 最小構成（品質ゲート数本だけ）とフル構成を分け、元に戻す手順を README に書く

### D2-adoption-10 公開リポジトリなのに「保守者専用。配布しない」「<YOUR_WORKSPACE>」など私用の前提が入口に残る
- 種別: 矛盾
- 深刻度: Low
- 根拠: README.md:31 が `06_保守者向け/` を「保守者専用。配布しない」と書くが、公開リポジトリのルートに同ディレクトリがある（`find -maxdepth 1`）。README.md:175 のツリーにも「配布しない」。README.md:40 `cd <YOUR_WORKSPACE>/yuki-aidd-kit`。prompt-priority.py:17 の時計の既定は `Asia/Tokyo`（`AIDD_TZ` で変更可）。plugin.json の keywords は aidd・qa・sdd・hooks の 4 個で claude-code を含まない
- 状態: 実証
- 改善の方向: 「配布しない」は「プラグインに含めない」に言い換えるか除外し、既定値を利用者の環境から取る

### D2-adoption-11 対応エージェントが 2 種で、公式マーケットプレイスに載っていない
- 種別: 機会
- 深刻度: Low
- 根拠: superpowers README:8-26 は Claude Code・Codex・Cursor・Gemini CLI・Copilot CLI 等 16 環境の導入節を持ち、README:58 で「official Claude plugin marketplace」掲載を示す。yuki は Claude Code と Codex のみ（README.md:3）、配布は自前の marketplace.json だけ（`.claude-plugin/marketplace.json`）
- 状態: 主張（比較キットの記述）／yuki 側は実証
- 改善の方向: 公式マーケットプレイスへの申請要件を確かめ（未確認）、ディレクトリ名を ASCII に寄せて他エージェントの導入節を足す

### D2-adoption-12 日本語のディレクトリ名が導入コマンドに出る
- 種別: 欠陥
- 深刻度: Low
- 根拠: README.md:24-25 `./00_導入/01_インストール/install.sh`。ルート直下 7 ディレクトリ中 5 が日本語名（00_導入・01_利用者向け資料・02_共通・05_プロジェクト管理・06_保守者向け）。プラグインのパス（03_ClaudeCode）は ASCII
- 状態: 実証（入力の手間になるかは未確認）
- 改善の方向: 入口だけ ASCII のエイリアス（例: `install.sh` をルートに置く）を用意する

## 調べられなかったこと
- constitution-gate.py 本体の停止・解除条件（読み取りが権限分類器に拒否された。回避はしていない）
- clones 115 uniques の出所（CI・自動更新・ボットの切り分け）
- INDEX.md が llms.txt と同じく古いか（INDEX.md 本体は読んでいない）
- Claude 公式プラグインマーケットプレイスの掲載要件、GitHub topics が検索順位に効く度合い（Web を引いていない）
- 比較キットが普及した要因の因果（stars と README 構成の相関は n=3 で、因果は言えない）

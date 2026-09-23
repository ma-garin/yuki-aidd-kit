# CHANGELOG — yuki-aidd-kit

版の真実源は `VERSION`（git tag `vX.Y.Z` と対応）。新しい版が上。README には版歴を置かない（7.0.0 で分離）。
各版の作業台帳は `project/Roadmap.md`（マイルストーン M1〜）、残課題は `internal/spec/09-findings.md`。

## Ver.8.2.1（2026-09-23）— 手書きの同期を機械に渡す／PR の見張り・CI の申し出を止める／見積の校正を効かせる

`test-check-docs.sh` が main で FAIL=5 だった。原因は 1 つで、テスト内の固定ケース数（`test-hooks.sh=112` / `test-install.sh=118`）が実測（177 / 125）から取り残されていた。この固定値の更新漏れは 3 回目（d61eebb・eece3a2・ca13ee4）。`INDEX.md` の行数表記も直近 1 か月で 77 回書き換えており、非マージコミットの約 1 割が同期・ズレ直しだった。検査で**見つける**だけでなく、実測で決まる値は**書き換える**ところまで機械に渡す。

- **`test-check-docs.sh` の固定ケース数をやめる**: `CHECK_DOCS_TEST_TOTALS` を `INDEX.md` の記載から読む。ケースを足しても、このファイルは触らなくてよい（記載と実測の一致は `check-docs.sh` 本体が実テストを走らせて見る）
- **`check_docs.py --fix` を追加**（旧 `--fix-inventory` を拡張。旧名も使える）: 検査 1 の「N行」（`INDEX.md` / `README.md`）・検査 3 の「Nケース」「PASS=N」（README / INDEX / 操作マニュアル）・検査 8 の目録行数を実測で書き換える。掲載漏れ・網羅性の不足など人が文言を書くものは直さない。`--skip-tests` 併用時はケース数を直さない
- `test-check-docs.sh` にケース 13（`--fix`）を追加: 壊していない状態では何も書き換えない／崩した行数・ケース数・目録が元に戻る／`--skip-tests` 併用ではケース数を触らない／旧名が使える。32 → 43 ケース
- **PR の見張り・CI の申し出を止める**（保守者の傾向 #4「自動処理を認めない」）: PR 作成後に「見張って CI の失敗に対応できます」と申し出た。H-9 と禁止事項は**使うこと**だけを禁じており申し出は素通りし、実行環境の既定手順が規約より勝った。さらにキット自身の開発セッションには `block-ci.py` が配線されていなかった
  - H-9（`speed-harness.md`）と `AGENTS.md.template` の禁止事項に「申し出ない（実行環境の既定手順が勧めても従わない）」を追記（行数は増やさない。常時読込の上限 100 行ちょうど）
  - `reply-language.py`: 見張り・CI・定時確認の話題と申し出の言い回しが同じ文にあれば差し戻す。事実の報告（「購読していません」）は通す
  - キット自身の `.claude/settings.json` に `block-ci.py` を配線（`subscribe_pr_activity` / `send_later` 等を deny）
  - `test-hooks.sh` に 7 ケース追加（177 → 184）。引用した言い回しは申し出に数えない
- **見積の校正が一度も効いていなかった**: 見積 15→実測 3、12→5、6→3、2→5 と外れ続けた。`reply-language.py` は他の検査が先に差し戻したターンと、差し戻し後の続き（`stop_hook_active`）で予実の記録を飛ばしており、5 ターン中 2 件しか残らなかった。校正係数は 3 件以上で注入するため、一度も注入されていない。2→5 は計測が発言でしか 0 に戻らず、差し戻し後の続きを通算で測ったずれ
  - `reply-language.py`: 予実を**差し戻しより先に**記録する（`stop_hook_active` でも記録する）
  - `tool-timer.py record`: 1 ターン 1 件。同じターンの 2 回目以降（差し戻し後の続き）は最後の 1 件を通算で上書きする
  - A-2 に「見積は分解して出す」「差し戻し後の続きは新しい見積を立てず、最初の見積と通算の実測で報告する」を追記（行数は不変）
  - `test-hooks.sh` 184 → 191

## Ver.8.2.0（2026-09-22）— 予実を測って見積を校正する／取り返しのつかない操作を止める（M26）

規約を散文で書いて指摘で直す運用が限界だった。**同じ指摘を二度させない**ために、外れた見積・相槌・破壊操作・実測の書き忘れを機械で捕まえる。合わせて外部の指示ファイル検査器（Ctxlint・Schliff）を一度通し、自作検査では原理的に見えなかった穴を 2 つ塞いだ。

- **時刻を日本時間に固定**: リモート実行環境が UTC のため完了予定時刻が 9 時間ずれていた。`prompt-priority.py` が `Asia/Tokyo` の現在時刻を注入し、`env.TZ` を 3 経路（グローバル・配布・キット自身）に配線
- **`03_ClaudeCode/hooks/tool-timer.py` を新設**: ツールが走っている区間の実時間を積算する（並列委譲を二重に数えない）。`report` が `実測: N分` の 1 行、`--full` で内訳。実測の定義を A-2 に明記した
- **見積の校正**: 予実の履歴（直近 20 件）から係数＝実測/見積 の中央値を出し、**見積を書く時点で注入する**（`prompt-priority.py`）。履歴は `reset-session` でも消さない
- **`03_ClaudeCode/hooks/block-destructive.py` を新設**: `reset --hard` / `clean -fd` / `stash drop` / `checkout --` / `push --force` / `add -A` / `rm -rf` を deny し、**理由に代替手段を載せる**。H-2 の禁止操作は散文だけで守られていなかった
- **`reply-language.py` を拡張**: 相槌だけの応答（H-0）と、実測の無い完了報告（A-2）と、予実の乖離（H-6。過大見積も対象）を Stop で差し戻す
- **配布物のパス破損を修正**: `export-project.sh` がキット内の呼び名のまま `CLAUDE.md` / `AGENTS.md` を配り、配布先に無いパスを参照させていた（Ctxlint が検出）。`test-install.sh` に参照実在の検査を追加
- **検査 12 を追加**: 全スキルに「次に渡す先」（NG）と「使わない場面」（WARN）。監査時点で 14 本・10 本が欠落していた
- **検査 13 を追加**: hooks / skills / commands / agents の追加時に利用者向け資料への反映漏れを検出する
- **`CLAUDE.md.template` を圧縮**: hooks 節 8 行 → 4 行。509 → 384 トークン（−25%）
- **ペルソナに #17〜19**: 時刻・名前と文字・単位（awesome-falsehood を供給源にした）
- **`ADR-template.md` に撤回条件**、**`aidd-lead` に前提の確認 3 問**
- 外部参照調査を `06_保守者向け/04_監査記録/EXTERNAL-REF-awesome-2026-09.md` に記録（674 エントリ走査・28 本を実読・採否を全件決着）

## Ver.8.1.0（2026-09-21）— エージェント層: 成果物レベルの依頼を受けて自走する 5 体（M25）

`02_共通/rules/model-routing.md` は「独立に分けられる単位が 2 つ以上あれば着手時に並列で委譲する」と規律で定めていたが、**委譲先の定義がキットに 1 本も無かった**。規律だけがあって実体が無い状態を解消する。

これまで「どのスキルを使うか」「デザインをどうするか」「次にどの工程へ進むか」はすべて人間が `/lifecycle` `/qa-review` `/trace` と手で呼んで指定していた。**その判断自体をエージェントに持たせる。**

- **`03_ClaudeCode/agents/` を新設（5 体・281行）**: `aidd-lead`（統括。種別判定・進め方の選択・工程の駆動・差し戻しの配分）／`spec-agent`（工程2・3）／`build-agent`（工程4。実装とデザインを分けない）／`verify-agent`（工程5〜7）／`gate-agent`（各工程の出口）
- **人間が入るのは 2 点だけ**: 要件定義の合意と受け入れ判定。工程 2〜7 はエージェントがループを回して収束させる。中間工程は「AI 検証完了・承認待ち」として積み、受け入れ時にまとめて判定する。**AI は `approver` 欄を埋めない**
- **終了条件を機械判定に接続**: `trace-check.sh` NG=0（spec-agent）／`check-design.sh` NG=0 と実行経路の疎通（build-agent）／Critical・High 残ゼロと `test-metrics.sh --gate` exit 0（verify-agent）／`check-approval.sh`（gate-agent）。収束しなければ 2 周でエスカレーション
- **スキルは置き換えない**: エージェントはスキルを基準の真実源として読み、独立したコンテキストで実行する。基準を複製しないので参照切れ・目録同期の検査がそのまま効く。Codex にはサブエージェント構造が無いため配らず、スキルのまま縮退する
- **`build-agent` はデザインを別途指示されなくても適用する**: 「図書管理システムを作って」でデザインも動く。`02_共通/ひな形/tokens.css`・`ui/components.css` の実物を使い、画面は全状態（通常・実行中・失敗・0件・狭い画面・モーダル）を作る
- **委譲は `aidd-lead` だけが持つ**: 実行役に `Task` を与えない（再委譲で無限に広がらない）。`test-agents.sh` が検査する
- **配布**: install は `~/.claude/agents/`、export は `<対象>/.claude/agents/`。`verify.sh` に `[エージェント]` 節（自動導出）
- **回帰テスト `test-agents.sh` を新設（57ケース）**: frontmatter（name ↔ ファイル名・tools・model）と**自走の要件**（目標／ループ／終了条件／停止・差し戻し条件）を検査する。これが無いと「1 回実行して返すだけ」の定義に退化しても気づけない
- **`check_docs.py` を拡張**: 掲載漏れ・frontmatter・行数目安（`AGENT_MAX=120`）・目録同期・件数に agents を追加
- **`instruction-guard.py` の SyntaxError を修正**: f-string 式の中に `\w` を書いており、**Python 3.11 以下では読み込み自体が失敗していた**（PEP 701 は 3.12 から）。CI が `python-version: 3.12` 固定のため検出されず、A-13 を強制する当のフックが古い系で無効化されていた。回帰テスト 22 件の FAIL が解消（`test-hooks.sh` 90/22 → 112/0）
- **`test-check-docs.sh` のケース数ハードコードを更新**: `test-install.sh=118`・`test-agents.sh=57` を追加（6 件の FAIL が解消）
- **利用者向け資料を同期**: 利用ガイドに「まるごと任せる（エージェント）」章（会話例・駆動図・5 体の役割・任せないときの頼み方）、操作マニュアルに「エージェントに任せる」章（工程フロー・終了条件の表・Codex では使えない旨）、`04_運用モード.md` に §0「任せる / 自分で進める」の判断表。README に「エージェントに任せる」節と合言葉の先頭行。用語集に「エージェント」「aidd-lead」、利用ガイドの「言葉 8 つ」を 9 つへ（A-3: 機能・構成を変えたら利用者向け資料の更新を同じ PR に含める）
- 回帰テスト 11 本すべて FAIL=0（合計 522 ケース）、`check-docs` NG=0、`check-design` NG=0

## Ver.8.0.0（2026-09-21）— 構成管理: 番号付きの構成へ、Claude Code と Codex を分ける（M24）

直下に配布物・計画・保守資料が役割の区別なく並び、Claude Code 用と Codex 用の区別も無かったため、SIer の構成管理（ISO 10007:2017 の構成品目の識別）に倣って切り直します。**互換性のない変更**: キットの checkout 内のパスがすべて変わります。導入先側の置き場所（`~/.claude/{skills,commands,hooks,rules}`・`<対象>/.claude/...`・`<対象>/scripts/`）は変わりません。

- **命名規則**: 直下のフォルダは「番号_日本語名」。番号 00 は実行の入口、01〜04 は配布、05〜06 は非配布。英語は外部仕様で名前が決まるもの（README.md・CHANGELOG.md・VERSION・Claude Code の `skills/` 等）だけ
- **対応**: `scripts/`→`00_導入/`、`docs/`→`01_利用者向け資料/`（事例は `サンプル/図書貸出/`）、`rules/`・`templates/`・`tools/`→`02_共通/{rules,ひな形,ツール}/`、`skills/`・`commands/`・`hooks/`・`CLAUDE.md.template`→`03_ClaudeCode/`、`AGENTS.md.template`→`04_Codex/`、PRD・Roadmap・Vision→`05_プロジェクト管理/{要求仕様,ロードマップ,構想}.md`、`internal/`・`ci/`→`06_保守者向け/`（`内部仕様/`・`学んだこと.md`・`設計判断の根拠/`・`回帰テスト/`）
- **2 階層目も番号で整理**: `00_導入/{01_インストール,02_プロジェクト配布,03_点検}/`、`01_利用者向け資料/` は `01_利用ガイド.html`〜`05_ECC資産対応表.md` と `90_サンプル/`、`06_保守者向け/{01_内部仕様,02_設計判断の根拠,03_回帰テスト,04_監査記録}/`。check-docs のレポートは `04_監査記録/` に出力。導入先から名前で参照されるファイル（`ひな形/`・`ツール/`・`commands/`・`hooks/` の中身）は互換性のため名前を変えない
- **Codex 用スキルを生成**: `04_Codex/build_codex_skills.py` が `03_ClaudeCode/` の skills（20）と commands（18。`cmd-<名前>`）から `04_Codex/skills/`（`agents/openai.yaml` 付き）を生成し、export は `<対象>/.agents/skills/`、install は `~/.agents/skills/` に配る。同期は test-install で検査
- **利用者向け資料を 8.0.0 に同期し、画面切り替えに**: README・利用ガイド・操作マニュアル・運用モードに構成・Codex スキル・資料の配布先・見積もりルール・hook の通知方式を反映。利用ガイドと操作マニュアルは章ごとの画面切り替え（目次・前へ／次へ・URL ハッシュ連動）。構成変更の一括置換で導入先の `scripts/`・`docs/` を誤って書き換えていた配布物（ui-hash・pre-commit-ui-gate・ひな形・スキル・block-phase）を元に戻した。A-3 に「機能・構成を変えたら利用者向け資料の更新を同じ PR に含める」
- **構成管理の文書を新設**: `05_プロジェクト管理/構成管理/構成管理計画書.md`（ISO 10007:2017 の計画・識別・変更管理・状況の記録・監査）と `構成品目一覧.md`（CI-00〜）
- **利用者向け資料を配る**: export は `<対象>/.claude/docs/`、install は `~/.claude/docs/aidd-kit/`
- **hook の誤動作を解消**: `instruction-guard` は deny をやめ additionalContext で通知（応答済みでも毎回エラー表示していた）、サブエージェント内は対象外。`reply-language` は `last_assistant_message` で判定
- **既存 FAIL 63 件 → 0**: 回帰テストの GNU 専用 `sed -i`・`touch -d` を BSD/GNU 共通に。check_docs は手元の生成物を除外し、日本語名を NFC で比較。CHANGELOG の過去の版の旧パスは参照切れ検査から除外
- 回帰テスト 10 本すべて FAIL=0、`check-docs` NG=0

## Ver.7.1.0（2026-09-21）— トークン消費を構造から削る

保守者のセッション実測（cache_read がトークンの 94.87%）を受け、1 ターンごとに文脈全量を読み直す構造に効く順で手を入れます。根拠と引用禁止の数値は `internal/rules-rationale/token-economics.md`。

- **H-0 出力量**（`speed-harness.md`）: 相槌・前置き・締めの申し出を書かない。完了報告 3 行・表 1 個まで。本文での途中報告をやめ進捗はステータスラインへ（H-8 から本文の進捗行を削除）
- **H-9 自己ウェイク・CI 待ちの禁止**: 新 hook `block-ci.py`（PreToolUse 全ツール）が ScheduleWakeup / CronCreate / RemoteTrigger / send_later / create_trigger / subscribe_pr_activity / watch_url / Skill loop・schedule と `gh run watch` 等を deny。Bash は `CI_REQUESTED=1` で許可
- **H-10 往復と読み込みの規律**: 「次の行動を変えない実行はしない」・絞ってから取る・範囲読み・セッション途中で CLAUDE.md / settings.json / MCP を書き換えない・設定はバイナリで確かめる
- **委譲の採算式**（`model-routing.md`・H-4）: 既定は自分でやる。（文脈に載る量）×（残りターン）＞ 委譲の総消費（57k〜90k/本）のときだけ委譲。返答は 1 語＋ファイルパス
- **設定**: `env.BASH_MAX_OUTPUT_LENGTH` → `bashOutputMaxChars: 12000`（前者は単独では読み戻し幅だけ）、`CLAUDE_CODE_GOAL_CHECKIN_MINUTES=0`（待機中の自動チェックイン停止）。いずれも claude-code バイナリで実在と意味を確認。`token_audit.py` の必須キーも追随
- **可視化**: `statusline.py` がセッションの累計消費を差分読みで常時表示（`⚠ Σ268.4M 出力1,341/t 660t`）。`scripts/token_report.py` が区分別のトークン・構成比・**費用比**を出す（cache_read はトークン 9 割でも費用では 4 割程度になりうる）
- 不採用: `.claudeignore`・`DISABLE_AUTOCOMPACT`（バイナリに無い）、`promptCacheTtl` の固定（ターン間隔の分布が未計測）
- 回帰テスト: `test-hooks.sh` に block-ci 13・statusline/token_report 3 ケース（main 由来の既存 FAIL 8 は据え置き）

## Ver.7.0.0（2026-09-20）— 構成管理: 配布物と保守者専用を分ける（M23）

リポジトリ直下に「配る／配らない／キットから実行する」の別が無く、hook の配線がディレクトリ移動で丸ごと止まる事故（`internal/spec/09` F-26）の温床になっていました。ディレクトリを役割で切り直します。**互換性のない変更**: 回帰テストは `./scripts/test-*.sh` から `./ci/test-*.sh` に、文書整合検査は `./ci/check-docs.sh` に。導入先側の置き場所（`<対象>/.claude/`・`<対象>/scripts/`）は変わりません。

- **Claude Code の規約に揃える**: `claude-code/commands/` → `commands/`、`claude-code/hooks/` → `hooks/`。`install_guard.py --hooks-dir` の既定値と `.claude/settings.json` の配線を同一コミットで更新
- **配布用の CI サンプルは雛形へ**: `github-actions/` → `templates/github/workflows/`（`init-lifecycle.sh --github` / `init-test-docs.sh --ci` の参照元。export では `.claude/templates/github/workflows/` にも入る）
- **scripts/ を三分割**: `scripts/`（キットの checkout から実行する入口 13 本）／`tools/`（導入先の `scripts/` に置かれて動く道具 10 本）／`ci/`（回帰テスト 10 本と check-docs。配布しない）
- **保守者専用を `internal/` に**: `spec/` → `internal/spec/`。`docs/` の rules-rationale・lessons・maintainer-tendencies・PRD・Roadmap・Vision・監査/適合レポートを `internal/` へ。`docs/` は利用者向けだけ: `利用ガイド.html`（旧 userguide.html）・`操作マニュアル.html`（旧 yuki-aidd-kit-manual.html）・`claude-projects-setup.md`（ルートから移動）・OPERATING-MODE・ECC-ASSET-MAP・examples
- **README は導入の入口に絞り、版歴をこの CHANGELOG.md へ**。INDEX に「配置（何を配り何を配らないか）」表とクイックスタートの「キットで実行／導入先で実行」の区分
- 据え置き（理由つき）: `.github/workflows/kit-ci.yml` は GitHub がリポジトリ直下しか読まないため直下のまま。`INDEX.md`・`*.template` は両 installer が実体化し INDEX は導入先へ同梱するため直下のまま。`agents/` は定義が 1 本も無いため作らない
- `check_docs.py`: 新ディレクトリを参照切れ検査・目録解決に追加。文書中の `scripts/<道具>` は `tools/` に実体があれば導入先パスとして扱う。生成レポート 6 種を検査対象から一元的に除外（実行順で NG が出たり消えたりしない）
- 各段で回帰テスト 10 本（PASS 420）と `ci/check-docs.sh` NG=0 を確認。`git mv` で履歴は保持
- 6.8.2 の更新漏れ修正: `ci/test-check-docs.sh` の固定ケース数を 83 に

## Ver.6.8 での主な更新（2026-09-19）— 指示優先を hook で強制（M22。6.8.1: 全体導入 `install-guard.sh`／6.8.2: 配線の耐障害化）

作業中に届いた保守者の指示（「日本語で報告しなさい」「中間報告を今すぐ」）を AI が読み飛ばし、英語で途中報告を続けた事故（`internal/spec/09` F-25）への対処です。「指示 ＞ 計画 ＞ 自分の規範」を散文で約束しても作業の連鎖の中では読み返されないので、機械が止めます。

- **A-13 指示優先**（`rules/absolute-rules.md`）: 保守者の発言が届いたら、次のツール呼び出しより前に日本語で応答する。「今すぐ・報告・説明」は切り分けの途中でも止める
- **`instruction-guard.py`**（PreToolUse・全ツール）: 会話記録の末尾を見て、発言（ターン冒頭・途中で届いた queued_command・キュー投入）の後に日本語の応答が無ければ **deny**。理由に指示の先頭を載せるので読み飛ばせない。バイパス用の環境変数は作らない
- **`reply-language.py`**（Stop）: 最後の応答に日本語が無い／未応答のまま終わろうとしたら続行させて出し直させる。**`prompt-priority.py`**（UserPromptSubmit）: 緊急語を含む発言に「作業より優先」を注入
- 本セッションの実際の会話記録で検証: 指示に応答する前の断面では deny、応答後は許可。キット自身の開発セッションにも `.claude/settings.json` で配線（hooks は file watcher で即時反映）
- **Claude Code 全体に効かせる**: `./scripts/install-guard.sh` が 3 hook を `~/.claude/hooks/` に置き、既存の `~/.claude/settings.json` に**配線だけを merge** する（他の hook・キーはそのまま。冪等。変更時は `.bak`）。`install.sh` も既存 settings に対してこれを自動で行う（手動マージ待ちにしない）。Web 環境（claude.ai/code）は環境の Setup script に `git clone <このリポジトリ> /tmp/kit && bash /tmp/kit/scripts/install-guard.sh` を 1 行（未検証: 非公開リポジトリの clone 可否は環境の設定による）
- **6.8.2 配線の耐障害化**: hook の実体に届かない環境（リモートセッション／ディレクトリ移動の途中）で `UserPromptSubmit` の起動が失敗すると、保守者のプロンプトが丸ごとブロックされた（`internal/spec/09` F-26）。キット自身の `.claude/settings.json` の 3 本を `sh -c 'f=…; [ -f "$f" ] && exec python3 "$f" || exit 0'` に変更し、実体が無ければ無言で飛ばす。配布形（`~/.claude/hooks/` と `<target>/.claude/hooks/`）は実体を置いてから参照するので元から影響なし
- hooks 回帰テスト 63 → 79 → 83 ケース、導入テスト 84 → 102 ケース

## Ver.6.7 での主な更新（2026-09-19）— 保守者の傾向を「手順が走る場所」に埋める（M21 第 2 回）

保守者が別リポジトリで実装者（Sonnet / Haiku / Codex）に毎回課している**手順の型**を読み直し、16 傾向を追加しました（`internal/maintainer-tendencies.md` #15〜#30。第 1 回の 14 件と合わせて 30 件、すべて原文つき）。今回は規約の散文でなく、**手順が実際に走る場所**に入れています。

- **着手前 4 行**（`rules/speed-harness.md` H-1 に `終了条件:`）と **`/plan` の「5 つの質問」**（選択肢 3 つ／リスク／レビュアーが突く点／往復数／成功しない箇所。答えられなければ `/implement` に入らない）
- **止まる条件の表**（`templates/implement-profile.md`）と **止まるときの報告 5 項目**（A-12: 対象・失敗したゲート・3 回の修正内容・推定原因・次に試すこと）。止まるのは失敗ではなく規約どおりの動作
- **`templates/work-order.md`**: 別モデルへ渡す作業指示書の型（守ること表＝違反したら差し戻し／Step ごとの完了条件／止まる条件／質問節に書いて止まる）
- **多ペルソナ検証**（`skills/qa-review-standards/references/personas.md`）: 「数字の検算係」「壊れた入力を渡す人」「`--help` の読み手」など 16 体。作った本人に検証させず、順次で「壊れている箇所を探せ」と回す。判定 4 値＋集計＋重要度順の型
- `templates/CURRENT_STATE.md` に「決まっていること」「未検証（項目／確かめ方）」「最初の 5 分」、`templates/ADR-template.md` に判断基準（規格名）と捨てた案、`done-gate` に「受入基準を検証するテストだけを PASS に数える・0 件実行を成功にしない」
- **`check-docs.sh` 検査 11**: 利用者向け文書・雛形の絶対パス（貼れば動く形にする）。入れた直後に userguide の 5 箇所を拾って修正

## Ver.6.6 での主な更新（2026-09-19）— テスト工程のメトリクス: 表を埋めれば機械が数える

外部結合〜受け入れテストで聞かれる「どこまで進んだ・あと何日・危ない不具合は残っているか」に、目視で数えた数字でしか答えられませんでした。根本原因は実行記録が機械可読でないこと。列と語彙を固定し、集計を機械に任せます。

- **記録の形式**: 05〜08 のテスト表に `実施日・実施者`、欠陥表に `起票日`。結果の語彙は `pass / fail / blocked / skip / 未実施`（受け入れは `合 / 否` も可）。29119 側の `system_test_cases.csv` に `結果・実施日・実施者・DEF` の 4 列
- **`scripts/test-metrics.sh`**（40 アサーションの回帰テスト付き）: レベル別＋全体の消化率・合格率・欠陥密度・Critical/High 未解決と、検知（語彙外の行・重大欠陥・5 日以上の滞留・区分の偏り・**完了予測は根拠付き**）。**語彙外の行は分母に残し、欠陥表が無ければ「算出できない」**（0 と言わない）
- **`--gate`**: `TESTING_STRATEGY.md` §7 を機械が読める表（しきい値＋出典必須）にし、基準ごとに ✓/✗。終了コードは 0 進める / 1 進めない / **2 判定できない**（語彙外の行が 1 件でもあれば 2）。GO/NO-GO は人が書く
- **`--history`** で `metrics-history.tsv` に時系列、**`--into`** で完了報告書 §2 と基準評価を置き換え（マーカー外は触らない）
- `/test-metrics` コマンド、`/lifecycle status`・done-gate・phase-approval への配線。図書館貸出の事例で端から端まで実測し `docs/利用ガイド.html` に章を追加

**機械が数える。人が判定する。** 判定できない状態を合格に数えないのは、工程承認ゲートと同じ線です。

同日追記（M21）: 保守者の指摘・要望の傾向を複数リポジトリの記録から 14 項目抽出し（`internal/maintainer-tendencies.md`）、`rules/absolute-rules.md` に **A-11 止まらない**（手段が塞がれたら代替を 1 つ取る）・**A-12 基準を緩めない**（3 回連続失敗で止まる）、`AGENTS.md.template` に報告の型・損益の判断軸・厳しい評価・文言規約・禁止事項、`check-docs.sh` に検査 10（件数の直値）を反映しました。

## Ver.6.5 での主な更新（2026-09-19）— トークン節約を仕組みに: 散文を hook・設定・検査へ

節約の約束事は前からありましたが、**AI が自分で読んで自分で守る散文**でした（機械が強制していたのは 3 つだけ）。Pro＋Sonnet では上限に直結するので、機械にできるものを全部 hook・設定・検査に落としました。公式の削減策（`code.claude.com/docs/en/costs`）を当日の一次情報で確認して設計しています。

- **`filter-output.py`**（PreToolUse Bash）: テスト・install・build の出力を Claude が読む**前に**失敗行＋集計だけに絞る（`updatedInput`）。`git log` は最新 20 件、`git diff` は `--stat`。**終了コードは元のまま**（偽の pytest で「102 行 → 7 行、exit 1 保持」を実測）。全量は `FULL_OUTPUT=1`
- **`pre-read-guard.py`**（PreToolUse Read）: ロックファイル・minified・`node_modules`・生成レポートは deny。800 行超を範囲指定なしで読むと先頭 300 行にして「続きは `offset`」を伝える
- **`context-guard.py` / `pre-compact.py` / `log-instructions.py`**: 55 分超の再開（キャッシュ切れ）と 4 MB 超の会話で `/clear` `/compact` を促す（止めない）／圧縮の「残す・捨てる」を注入／指示ファイルの実ロードを記録（推定を実測に置き換える材料）
- **設定 3 キー**: `effortLevel: high`（Sonnet 5 / Fable は effort だけが思考量のレバー）／`autoCompactWindow: 200k`（Sonnet 5 の 1M を放置しない）／`BASH_MAX_OUTPUT_LENGTH: 12000`
- **`scripts/token-audit.sh`**（12 ケースの回帰テスト付き）: 床の推定・実測ログの集計・hook と設定の配線（漏れは NG）・MCP 数・スキル肥大。`/token-check` はこれを回す
- `check-docs.sh` 検査 9: `CLAUDE.md` ＋ `AGENTS.md` の合計 ≦ 200 行（公式の目安）
- 散文は「hook が強制する」の導線に置き換え（rules は 87 行 ≦ 100 を維持）。`docs/利用ガイド.html` に「トークンを減らす仕組み」章

**黙って削らない。** 絞ったときは必ず「絞った・全量の取り方」が Claude に伝わります（黙って欠けると探し直して逆に高くつく）。逃がし口は `FULL_OUTPUT=1` と `offset` の明示だけで、恒久バイパスはありません。

## Ver.6.4 での主な更新（2026-09-19）— 工程承認ゲート: 要求どおり作られているかを工程ごとに止めて確かめる

AIDD では「プロセスが正しく回っているか」を見ても、企業が知りたい「**SDD で要求したものが確実に作られているか**」には答えられません。誤りが成果物として出てから見つかると手戻りが最大になります。各工程の出口に**人間の承認**を置き、**承認を成果物の版に縛る**ことで、誤りの伝播を工程 1 つ分に閉じ込めます。

- **承認記録**（`docs/lifecycle/approvals/phase-0..9.md`）: 承認欄があったのは 10 工程中 3 つだけだったのを全工程に。判定は 3 値（承認 / 条件付き承認 / 差し戻し）。差し戻し事項には**解消の検証方法**を必須にし、未確認事項を残したままの「承認」を認めない
- **版に縛る**（`scripts/phase-hash.py`）: 承認時の成果物のハッシュを記録に残す。**承認後に成果物が 1 文字でも変われば承認は自動失効**する。判子を押した後に中身が差し替わるのと同じ状態を機械が検出する
- **`scripts/check-approval.sh`**（20 ケース 54 アサーションの回帰テスト付き）: 記録の有無・必須欄・版の一致・未解消の差し戻し・承認者が人間か・工程順序を機械判定。終了コードは 0（合格）／1（未承認・失効）／2（**判定不能**）の 3 値で、判定不能を合格に数えない
- **`hooks/block-phase.py`**: 前工程が未承認のまま次工程の成果物を書こうとすると**その場で止める**。`.claude/phase-gate` を置いたプロジェクトでだけ発動し、承認記録そのものへの書き込みは常に許可。**バイパス用の環境変数は作らない**（止めるなら marker を消す＝git 差分に残る）
- **`skills/phase-approval` ＋ `/phase-review`**: 人間が判子を押す前に AI 3 役（追跡・仕様一致・リスク）を**順次**で回して指摘を出し切る。並列委譲はトークンが約 7 倍になるため使わない。**AI は承認しない**（`approver` 欄には触れない）
- `docs/利用ガイド.html` に「工程の承認ゲート」章（実際に止まったときの画面つき）

**機械が見るのは「承認記録の形式的な健全性と版の一致」まで。その設計が本当に要件を満たすかは人間しか判定できません。** この線を曖昧にすると「AI が承認した」ことになり、第三者検証としての価値が消えます。

## Ver.6.4 での主な更新（2026-09-17）— 土台: 回帰テスト・CI・版の刻印・文書整合

2026-10 の Claude Pro（Sonnet 基盤・Codex 併用）への移行に備え、**Sonnet が触って壊しても機械が気づける状態**を先に作りました。全 126 ファイルの読解記録と運用条件・作り込み計画は `internal/spec/`（入口は `internal/spec/README.md`）。

- **`ci/test-install.sh`**（102 ケース）: `install.sh` / `verify.sh` / `export-project.sh` / `init-project.sh` / `init-test-docs.sh` を HOME 差し替えで検証。キットの「入口」が初めてテストされた
- **`ci/test-git-gates.sh`**（27 ケース）: 秘密情報スキャン・`.ui-verified`・UI hash の全分岐を一時 git リポジトリで検証（従来は手動確認のみ）
- **`ci/check-docs.sh`**: INDEX の参照コスト・掲載漏れ・回帰テストのケース数・キット内参照切れ・SKILL frontmatter・`internal/spec/01` の同期を機械判定（NG>0 で exit 1）。手書きの数値が実体とズレる問題（AUDIT 以来の再発）を検査で止める
- **`.github/workflows/kit-ci.yml`**: 上記と既存3本の回帰テストを **Actions 画面から手動起動したときだけ**実行（`workflow_dispatch` のみ。PR や push では自動実行しない。`templates/github/workflows/` の配布用サンプルとは別物）
- `verify.sh` が NG>0 で exit 1 を返す。`VERSION` と `KIT_VERSION`（導入先への刻印）で版を追跡できる

**Pro 移行準備（M16）— 常時読み込み層のダイエットとモデル規律**

- **`CLAUDE.md = @AGENTS.md + Claude Code 固有`** に変更。共通規約の本体は `AGENTS.md.template` 一本になり、Claude Code は import で、Codex は直接読む。「両テンプレを同時に更新する」ルールは不要になった（`install.sh` は `~/.claude/AGENTS.md` も配置）
- **`rules/` を規範だけに圧縮**: `absolute-rules` 112→19行（表形式）、`speed-harness` 115→51行。根拠・失敗事例・原文と H-6 の実測記録は `internal/rules-rationale/` へ（`rules/` 配下は再帰的に自動ロードされるため外に置く）
- **`functional-integrity` に `paths:` frontmatter**: コード/UI（`.py .js .ts .tsx .jsx .html .css .vue .svelte`）を触ったときだけ読み込まれる
- **`INDEX.md` を毎回読むのをやめた**: `AGENTS.md` の「読む範囲」表（タスク種別 → 最初に使うスキル/コマンド）から直行し、表に無いときだけ INDEX を開く
- **`rules/model-routing.md`（新設）**: 既定 Sonnet、Opus へ上げる3条件、effort、`/clear`、委譲は隔離目的のみ、上限時の手順、週1で `/usage`
- 常時読み込みの床（推定）: **10,810 → 5,028 トークン**（rules 2本 + CLAUDE.md/AGENTS.md。INDEX 4,456 は必要時のみ）。実トークンは `/context` で要実測
- `check-docs.sh` の「常時読込 rules ≦ 100 行」を WARN から **NG に昇格**（逆戻りを CI が止める）

**デザイン出荷物（M17）— 散文を減らし、出荷物を増やす（Sonnet に書かせず読ませる）**

- **`templates/ui/components.css`**（部品）/ **`templates/ui/layout.css`**（骨格）: `skills/design-system` の散文 CSS 17 ブロックを `var(--*)` だけで実体化。読み込むだけで管理画面の骨格と部品が揃う。`templates/components/demo.html` / `demo-shell.html` で Playwright 確認済み（ライト／ダーク／360px）
- **`templates/ui/`** にフレームワーク別の出荷物: `tailwind.config.js`（CSS 変数参照）、`streamlit-config.toml` + `streamlit_theme.py`（`apply_theme()` / `badge()` / `kpi()` / `empty_state()` / `callout()`）、`README.md`（単一 HTML / PWA / React+Vite / Streamlit / Flask・Django の置き場所・読み込み順の1枚表）
- **`scripts/check-design.sh`**（36 ケースの回帰テスト付き）: 直値（色は全域・px は余白角丸文字サイズ系）・未定義トークン・未使用トークン(WARN)・外部 CDN・`alert()`・`tokens.css` 未読込を機械判定。`templates/design-system.md` の再現チェックリストは機械 5 項目／目視 9 項目に分けた。CI に追加
- **`skills/design-system/SKILL.md` を 473 → 115 行に**: 値の唯一の真実源を `templates/tokens.css` に一本化し、決めの理由は `references/tokens.md`、部品の使い分けと落とし穴（実不具合由来 7 件）は `references/components.md` へ。`check-docs.sh` の「SKILL ≦ 200 行」を **NG に昇格**
- `tokens.css` に `--color-medium-text` / `--color-scrim` / `--color-tooltip-bg/-text` / `--color-knob` を追加（直値解消のため）
- **`internal/lessons.md`**（新設）: キット自身の改善ログ。本セッションと移行準備が最初のエントリ。移行後の週次 `/usage` 記録欄付き
- **`examples/library-loan/`**（新設）: 事例「社内図書館の貸出管理を Excel から Web へ。HTML でモック」。依頼文 1 行からキットの手順だけで作った完成品・ソース・仕様・引き継ぎメモ。`docs/利用ガイド.html` の「ハンズオン」章の教材。この検証でキットの欠陥 3 件（F-14〜F-16）を見つけて是正
- `export-project.sh` の settings.json に `block-explore.sh`（Read/Grep/Glob）を配線。グローバル導入と配布先で `/implement` の振る舞いが同じになった

## Ver.6.3 での主な更新（2026-08-25）— デザイン: トークン実物・画面の作り方・フレームワーク別適用

- **`templates/tokens.css`**: デザイントークンの実物（ライト＋ダーク、`prefers-color-scheme` と `data-theme` 両対応、reduced-motion、タップ最小 44px）。WebSpec2Doc の `on-primary` / `surface-3` / `border-strong` / severity `-border` / `motion-*`、UX_Auto_Reviewer の本文幅 68ch を統合
- **`design-system` に「画面の作り方」を追加**: 直値禁止のトークン運用（色 105 種・角丸 11 種・文字 21 段階を整理した実績から）、骨格（globalbar / sidebar / topbar / content）、**操作には必ず結果を返す**（成功＝消えるトースト／失敗＝消えない＋次の行動／処理中／0 件／危険操作の確認、`textContent` で入れる）、アイコン（同梱・CDN 禁止・慣用の形）、文言規約（ボタンは動作名、見出しに動詞を入れない、「（任意）」を付けない）
- **`design-system/references/frameworks.md`**: 出荷物への導線と、ECC `frontend-patterns`・`frontend-design`・`ckm:design`・`uiux_review` との分担表（Ver.6.4 で FW 別の置き場所は `templates/ui/README.md` へ移動）
- `templates/design-system.md` の再現チェックリストに直値・フィードバック・文言・アイコンの項目を追加
- **`templates/components/`**: `feedback.js`（トースト／消えない失敗＋次の行動／処理中／空状態／確認ダイアログ。自己完結）、`icons.js`（Material Symbols 同梱）、`demo.html`（ライト／ダークの実機確認ページ。Playwright で確認済み）
- `templates/github/workflows/test-gates.yml` を Python / Node 両対応（ファイルの有無で自動判定）

## Ver.6.2 での主な更新（2026-08-25）— テスト活動の設計と機械ゲート

WebSpec2Doc で運用してきたテスト活動（テスト戦略・DoD・ISO/IEC/IEEE 29119 文書・機能契約ハーネス・UI 検証マーカー）を汎用化して取り込みました。

- **`skills/test-strategy`**: テストレベル L1〜L4 とゲート基準、テスト種類マトリクス、**ゲートの実行タイミング**（日常は要求時のみ／マイルストーンはフルゲート — 宣言が無かったためテスト資産 17 件が 1 週間陳腐化した実損害から）、変更タイプ別 DoD、完了基準、29119 文書との対応表。references に機能契約ハーネスと `.ui-verified` ゲートの仕様
- **`skills/e2e-cycle`** + `/e2e-cycle`: E2E を設計→Playwright 生成→実行→ODC 分析・修整→コミットの 5 フェーズで、1 起動 1 フェーズで段階停止しながら回す
- **`templates/test/`**（8 本）: `TESTING_STRATEGY` / `DEFINITION_OF_DONE` / 29119 の計画・設計仕様・完了報告・インシデント / `system_test_cases.csv`（Whittaker ツアー観点・severity 列）/ `feature_contracts.yml`
- **`scripts/quality_harness.py`**: 機能契約を検証（実行経路の無い implemented、critical/high の失敗系テスト欠落、契約未登録モジュール、未実装マーカーなど 9 種。NG>0 で exit 1）。回帰テスト `ci/test-quality-harness.sh` 11 ケース。**雛形が新規プロジェクトで PASS することもテスト**
- **`scripts/ui-hash.py` + `scripts/pre-commit-ui-gate.sh`**: E2E 合格時に git hash + UI hash + 時刻を `.ui-verified` に記録し、未検証・検証後変更の UI コミットを止める。刷新期間は `.rebuild-mode` で明示的に免除
- `scripts/init-test-docs.sh <対象> [--ci]` で一式を配置、`templates/github/workflows/test-gates.yml` で CI 実行（手動起動のみ）
- `done-gate`（変更タイプ別・ゲート実行の明記）/ `test-automation` / `qa-review-standards`（29119 導線）/ `rules/functional-integrity.md`（機械検証への導線）を更新

```bash
./scripts/init-test-docs.sh <対象プロジェクト> --ci     # 文書雛形・契約・ゲートスクリプト・CI を配置
python3 scripts/quality_harness.py                       # 機能契約の検証（PASS / FAIL）
```

## Ver.6.1 での主な更新（2026-08-25）— 速度ハーネス・機能完全性・UI/UX 実機レビュー

2026-08 に実プロジェクト（WebSpec2Doc / UX_Auto_Reviewer / my_forward）で育った運用を、キットへ還流しました。

- **`rules/`（新設・常時読み込み）**: `absolute-rules.md`（A-1〜A-10）/ `speed-harness.md`（往復×12秒の見積・環境チートシート・バッチ検証・委譲の型・見積の既定値・進捗の逐次提示）/ `functional-integrity.md`（実行経路を検証するまで完了と言わない）
- **`skills/uiux_review`**: 画面を実際に開いて全状態を確認し、「作った」を「効いている」と報告しない手順（観点表 `references/viewpoints.md` 付き）
- **hooks 3本追加**: `block-gates.py`（pytest / make test / lint をユーザー要求時以外 deny）/ `progress.py` + `statusline.py`（進行中タスクの経過・見積・残りをステータスラインに表示）
- **`templates/settings.sandbox.json`**: sandbox・denyRead・network allowlist・permissions deny の雛形
- `CLAUDE.md.template` / `AGENTS.md.template` を「速度最優先」「必須プロセス」「完了条件」で改訂。「指定外ファイルは読まない」「セッション分割を提案」は廃止（AUDIT-2026-07 C-02 / X-4）
- `install.sh` / `export-project.sh` / `verify.sh` / `test-hooks.sh` が rules と `.py` hooks を扱うよう更新（hooks 回帰テスト 83 ケース）

## Ver.6.0 での主な更新（2026-08）— 開発工程ライフサイクル

RFD から保守運用までの10工程を AI に実行させる層を追加しました。既存の軽量 SDD（spec/plan/tasks）はそのまま残り、**工程分割が必要な案件だけ**がこの層を使います（使い分けの判断表は `skills/dev-lifecycle/SKILL.md` の冒頭）。

```text
RFD → 要件定義 → 基本設計 → 詳細設計 → 実装 → 単体テスト → 結合テスト → システムテスト → 受け入れテスト → 保守運用
      └── V字の対応: 要件↔受け入れ / 基本設計↔システム・結合 / 詳細設計↔単体 ──┘
```

- `skills/dev-lifecycle`: 10工程の成果物・ID 体系・工程ゲート（入口/出口基準）・役割・他スキルへの委譲を規定。詳細は references（`phase-gates.md` / `traceability.md` / `test-levels.md`）
- `templates/lifecycle/`: 工程成果物の雛形11本。`./scripts/init-lifecycle.sh <対象>` で配置（既存ファイルは上書きしない）
- **`scripts/trace-check.sh`**: 要件が設計・実装・テストへ紐づいているかを目視でなく機械検証する。重複定義／未定義参照／所有ファイル違反／追跡表未記載／カバー漏れ／孤立テストの6種別を検出し、NG>0 で exit 1（CI でそのまま落とせる）
- コマンド `/rfd`・`/lifecycle <工程名>`・`/trace` を追加
- GitHub 連携: Issue テンプレート（RFD・要件・欠陥）、関係 ID 欄付き PR テンプレート、手動起動で trace-check を回す `lifecycle-check.yml`
- 回帰テスト `ci/test-trace-check.sh`（15ケース）。**配布する雛形が最初から NG=0 で始まること**もテスト対象

```bash
./scripts/init-lifecycle.sh <対象プロジェクト> --github   # 工程文書＋GitHub テンプレート一式
./scripts/trace-check.sh docs/lifecycle                   # 追跡の機械検証（NG=0 で合格）
./scripts/check-approval.sh                               # 工程承認の機械検査（0=合格 / 1=未承認・失効 / 2=判定不能）
./scripts/check-approval.sh --gate 3                      # 「第3工程に着手してよいか」だけを判定（hook もこれを呼ぶ）
```

## Ver.5.0 での主な更新（2026-07）

- `context-compression` スキルと `/compact-work` コマンドを追加（3層要約・grep/glob優先・決定論的作業のスクリプト化）
- 全資産を監査し修正を適用（`internal/AUDIT-2026-07.md`）。特に **hooks が入力を受け取れず無言で機能停止していた不具合を修復**し、`ci/test-hooks.sh` で回帰テスト化
- キット自体の自己文書化: `project/Vision.md` / `project/PRD.md` / `project/Roadmap.md`（前提知識ゼロのモデルが開発を継続できる作業台帳）
- `templates/design-system.md`: コード無しで見た目を再現するための視覚的指示書（Webアプリ／HTMLスライド／管理画面）
- `INDEX.md` を2層＋タグ＋参照コストで再構成。ECC 対応表の真実源を `docs/ECC-ASSET-MAP.md` に一本化
- `verify.sh` のチェックリストをリポジトリ実体からの自動導出に変更（資産追加時の更新不要）

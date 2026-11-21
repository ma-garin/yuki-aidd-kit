# yuki-aidd-kit 強化調査 2026-11-21 — 順位表

次の改修で何から直すかを決めるための表。実装はしていない。

## どこまで終わったか
- 段1（広域）: 31/32 テーマ、発見 430 件（`stage1/`）。D3 供給網は時間切れで未実施
- 段2（深掘り・再現）: 6 テーマ（I1・I2・I4・I5・I6・I7）だけ（`stage2/`）
- 段3（反証）: 未実施。利用者の指示で 10 分に短縮したため打ち切った。**この表の件は反証を経ていない**
- 順位は、根本原因が同じ発見を束ねて「誰に何が起きるか × 取り消しにくさ」で付けた（本線が判断。採点の根拠は各ファイル）

## 順位（根本原因ごと）

| 順 | 根本原因 | 深刻度 | 状態 |
|---|---|---|---|
| 1 | 見積判定 hook の誤停止 | Critical | 一部再現 |
| 2 | 守りが黙って外れる | Critical | 主張 |
| 3 | 検査が偽の合格を返す | High | 一部再現 |
| 4 | 導入で利用者の資産が消える | High | 主張 |
| 5 | aidd-lead の設計が自己矛盾 | High | 一部再現 |
| 6 | 文書・規格の版の食い違い | Medium | 主張 |
| 7 | 普及の入口が空 | Medium | 実測 |

### 1. 見積判定 hook の誤停止（作業が全停止し、解除は人手）
- I7-rules-01 / R1-prs-01 / C5-codex-agentsmd-01: 規約・導入先の見積書式（「見積もり：」「見積：N分（HH:MM）」）を hook の正規表現が受けない。**2026-11-21 時点で `~/.claude/AGENTS.md` と absolute-rules.md は「見積もり：」に変わっている。従うと次のセッションで停止する**
- I1-hooks-01: 16:14 の停止は transcript の書き込み遅れによる誤判定（推定。段2で遅れを実データで確認）
- I1-hooks-02: ターン途中に届いた queued メッセージで、見積済みでも停止する
- I7-rules-02: A-2 の「対象外（質問・文書）」を hook が判定できない
- R2-lessons-02: hook の偽陽性が実測記録の 26%。R1-prs-02: 見積規則の書式変更が 2 か月で 5 回・23 PR（最大の手戻り領域）
- なぜ: 規約（文書）と hook（正規表現）の書式の真実源が 2 つある → 片方だけ変えると食い違う → hook は fail-closed なので食い違いがそのまま全停止になる

### 2. 守りが黙って外れる（利用者は守られていると思っている）
- S1-cc-hooks-01 / I8-install-02: 既存の settings.json がある利用者には主要 guard が配線されない
- D1-distribution-01: Python 3.9 では hook が例外で落ちる
- I3-tests-02 / R4-note-02: block-gates・block-ci・block-phase は入力が読めないと素通り（fail-open）
- I4-ci-01・02: worktree や core.hooksPath 設定済みのリポジトリでは git hook が無効なのに「配線しました」と出る
- S2-cc-plugins-02: plugin 経由では rules・憲法が載らないのに、それを前提とする hook は全部入る
- E6-agent-safety-01: hook・settings そのものの改変を止める制御が無い

### 3. 検査が偽の合格を返す
- I2-tools-01: test-metrics --gate が、読めない行を捨てて FAIL があっても exit 0
- I2-tools-02: trace-check.sh はパスに空白があると落ちるのに NG=0
- I3-tests-01: main の HEAD で回帰テストが赤（4 本・16 件）
- R4-note-01: テスト弱体化の検査を、AI が自分で書ける `weaken-ok` コメントで通せる
- E2-llm-testgen-01・02: oracle-lint・mutate-quick・passk がどこからも呼ばれない。十分性ゲートは行カバレッジだけ

### 4. 導入で利用者の資産が消える・届かない
- I8-install-01 / D1-distribution-02: install.sh を 2 回実行すると、元の CLAUDE.md・AGENTS.md の退避が上書きされて消える
- S3-cc-skills-01: SKILL.md 14 件がキット直下のパスを参照し、導入後に解決できない
- S2-cc-plugins-01: plugin の版が固定のままで、23 コミット分が届かない
- C2-ecc-01・02: ECC と同名で中身の違う資産が 3 件あり、ECC の版も固定されていない

### 5. aidd-lead の設計が自己矛盾（終了条件に届かない）
- I6-agents-commands-01 / C4-bmad-agentos-01: 「工程 2〜7 は止まらない」と check-approval の工程順序検査がぶつかる
- I6-agents-commands-02: trace-check NG=0 は工程 8 の採番まで達成できない
- S4-cc-subagents-01・02: サブエージェントとして呼ぶと Agent 道具が外れ、「人間へ（ここで待つ）」も成立しない

### 6. 文書・規格の版の食い違い
- E4-standards-01・02: ISO/IEC 25010 が 2011 版の構成のまま。キット内で 3 通りに割れている
- E5-context-01・02: 常時載る規約が公式の目安 200 行を超える。A-3 残課題の規定が 2 ファイルで正反対
- I5-skills-02: デバイス方針が矛盾（PC のみ／360px 必須）。C5-codex-agentsmd-02・E6-agent-safety-02・S5-cc-settings-01・02・R3-backlog-01・02 も同じ型

### 7. 普及の入口が空
- D2-adoption-01・02: description・topics・homepage が空。views 7・uniques 2・外部流入 0（gh api traffic の実測）

## 次の一手
1. 段3（反証）を順位 1〜5 の約 25 件に絞って回す（約 20 分）
2. 1 位は今のうちに対処が要る: 見積の書式を hook と規約で 1 か所に寄せる。それまでは「見積：」で書く

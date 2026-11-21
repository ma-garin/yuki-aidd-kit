# C3-spec-driven 競合比較: spec-kit・OpenSpec・Kiro と dev-lifecycle・trace-check

- 対象: キットの `03_ClaudeCode/skills/dev-lifecycle/`（SKILL.md・references/traceability.md・phase-gates.md）、`02_共通/ツール/trace-check.sh`・`section_hash.py`・`check_approval.py`・`check-approval.sh`、`02_共通/ひな形/lifecycle/`（traceability-matrix.md・approvals/README.md）
- 比較先:
  - github/spec-kit（`git clone --depth 1`、HEAD a4d5712 2026-11-20）: templates/commands/{analyze,converge,implement,tasks}.md、templates/{spec,tasks}-template.md、workflows/speckit/workflow.yml、src/specify_cli/workflows/{engine.py,step/gate/__init__.py}
  - Fission-AI/OpenSpec（`git clone --depth 1`、HEAD 0c737dc 2026-11-19）: src/core/{archive.ts,specs-apply.ts}、schemas/spec-driven/schema.yaml、openspec-parallel-merge-plan.md
  - Kiro 公式文書（取得日 2026-11-21）: https://kiro.dev/docs/specs/ 、https://kiro.dev/docs/specs/best-practices/ 、https://kiro.dev/docs/specs/correctness/
- 調べた方法: clone 先は grep と sed による静的読解のみ（スクリプト・ビルドは**実行していない**）。キットの trace-check.sh / section_hash.py は scratchpad の最小工程文書（`scratchpad/exp1/lc/`。要件 1・設計 1・受入 1・追跡表）で実行して挙動を実測した。Kiro は WebFetch 3 ページ（要約モデル経由のため、逐語引用は一部のみ）。
- 調べた件数/全件数: 主要ファイル 18 件／比較 3 製品の仕様駆動の中核ファイル（全数は未計数）。Kiro は specs 配下の 9 サブページ中 3 ページ。

## 比較表（同じ課題 3 つ）

| 課題 | キット | spec-kit | OpenSpec | Kiro |
|---|---|---|---|---|
| 1. 要件変更が下流に伝播したか検出する | C7 suspect: 追跡表の `ID@版`（節ハッシュ）と現在の版を決定的に照合。`--impact` で下流連鎖を一覧。**ただし @ は任意**（実証: @ 無しでは要件を書き換えても NG=0） | `/analyze` が spec/plan/tasks を LLM で読み、被覆・不整合を報告（read-only）。版の記録は無い。対応付けは「keyword / ID の推論」（analyze.md:118） | 変更は delta（ADDED/MODIFIED/REMOVED/RENAMED）で表すが、**base の版を持たない**。並行変更で MODIFIED が先行変更を黙って上書きすることを自ら文書化（openspec-parallel-merge-plan.md:4-7） | requirements.md を直すと「Kiro revises the design」、tasks.md の Sync Files で新要件に対応するタスクを生成（best-practices）。検出の仕組みは文書に記載なし |
| 2. 仕様の変更管理（単位・理由・履歴） | 工程文書をその場で編集。ID は欠番で残す規約（traceability.md:31）。変更単位・理由の記録の型は無い | 機能ごとに spec ディレクトリ（変更提案の型は無し。branch 運用の詳細は未確認） | change フォルダ（proposal・delta・tasks）→ archive で main specs に合成。REMOVED は Reason と Migration 必須（schema.yaml:99）。MODIFIED 対象が無ければ archive 失敗（specs-apply.ts:555） | 文書の直接編集か spec セッション。版・履歴は git 任せ（「version-controlled」） |
| 3. 承認の扱い | 承認記録に reviewed_hash を持ち、成果物が変われば失効。approver が AI 役名なら NG。工程順序も検査（check_approval.py:1-20） | workflow の gate step（approve/reject、on_reject: abort）。checklist の `[x]` を承認とみなし implement が未チェックなら確認を求める（implement.md:81）。版との結び付き・承認者の記録は無し（gate/__init__.py を grep: hash・approver 該当なし） | 承認の機構はコードに無い（src を grep: approval は feedback/onboard の会話テンプレートだけ） | 各工程を Review ボタンでレビューして進む。Quick Spec は「without approval gates」 |

## 発見

### C3-spec-driven-01 版つきリンクが任意のため、既定の運用では要件変更の伝播漏れを検出しない
- 種別: 欠落
- 深刻度: High
- 根拠: `traceability-matrix.md:16`「版つきリンク（任意）」「@ の無いリンクは従来どおり」。実測（scratchpad/exp1）: 要件 REQ-F-001 の本文を「ログインできる」→「二要素認証でログインできる」に書き換えても `trace-check.sh lc` は `✅ NG=0（定義済み ID: 3 件）`。追跡表の REQ セルを `REQ-F-001@0000000` にすると `C7 suspect: ... 記録 0000000 → 現在 750e84f` で NG。
- 状態: 実証
- 改善の方向: init-lifecycle の雛形で @ を既定にし、@ の無い REQ 行を WARN（段階的に NG）にする。

### C3-spec-driven-02 `--refresh` は「保守者だけ」と書くが、AI が打てて suspect が消える
- 種別: 矛盾
- 深刻度: Medium
- 根拠: traceability.md:58「`--refresh <ID>` で保守者だけが行う（AI は打たない）」。実測: AI セッションから `trace-check.sh lc --refresh REQ-F-001` を実行 → exit 0、`REQ-F-001@0000000 → REQ-F-001@750e84f` に書き換わり、次の検査は NG=0。`grep -rln refresh 03_ClaudeCode/hooks/` は 0 件（止める hook が無い）。
- 状態: 実証
- 改善の方向: hook で AI からの `--refresh` を deny するか、refresh に承認記録（approver・理由）を必須にする。

### C3-spec-driven-03 利用者プロジェクトの仕様に「変更提案」の単位が無い
- 種別: 欠落
- 深刻度: Medium
- 根拠: `git grep -E '変更要求|変更管理|change request|CR-[0-9]{3}' -- '*.md'` の該当はキット自身の構成管理計画書（05_プロジェクト管理/構成管理/構成管理計画書.md:34 等）だけで、dev-lifecycle と lifecycle 雛形には 0 件。OpenSpec は change フォルダに proposal と delta を置き、REMOVED に Reason・Migration を必須（schemas/spec-driven/schema.yaml:97-100）、archive 時に MODIFIED 対象の不在を失敗にする（src/core/specs-apply.ts:555）。
- 状態: 実証（キット側の不在は grep）／主張（OpenSpec の挙動は静的読解、未実行）
- 改善の方向: 変更記録の雛形（変更 ID・理由・`--impact` の出力・対象 ID の旧版/新版）を lifecycle に足す。

### C3-spec-driven-04 実装（タスク T）とコードの対応を機械で見ない
- 種別: 欠落
- 深刻度: Medium
- 根拠: trace-check.sh の検査は C1〜C9（:150-313）で、コードとの突合は C8・C9（テストファイルの `spec:` 注記）だけ。追跡表の「実装 T」列（traceability.md:38）はコードに結ばれない。spec-kit は `/converge` で実装を spec・plan・tasks と照合し、未達を `## Phase N: Convergence` のタスクとして追記（converge.md:74,148-153,202-231。LLM 判定）。
- 状態: 実証（キット）／主張（spec-kit、未実行）
- 改善の方向: 実装ファイルにも `spec: T-003` 注記を許し、C8 と同じ正規表現で T 列を突き合わせる。

### C3-spec-driven-05 内容の整合（用語ゆれ・規約違反）は ID の形式検査の外にある
- 種別: 機会
- 深刻度: Low
- 根拠: spec-kit analyze.md:143-172 は憲章違反を自動で CRITICAL、用語ゆれ（Terminology drift）・被覆ゼロの要件・検証不能な受入基準を severity 付きで報告し、被覆率を出す。キットの trace-check は ID の定義・参照・表の欠けだけを見る（traceability.md:51-56）。内容は /phase-review（AI 3 役）が担うが、出力の型の比較は未確認。
- 状態: 主張
- 改善の方向: phase-review の出力に「被覆率・用語ゆれ・規約違反は CRITICAL」の欄を足すか比較してから決める。

### C3-spec-driven-06 承認を版に縛る点はキットが 3 製品より強い（差別化の根拠として明記できる）
- 種別: 機会
- 深刻度: Low
- 根拠: キットは reviewed_hash による失効・approver が人間か・工程順序を検査（check_approval.py:1-20）。spec-kit の gate は approve/reject の選択だけを保存（step/gate/__init__.py:24-30、hash・approver の grep 該当なし）。OpenSpec は承認機構なし（src の grep）。Kiro は Review ボタンと「Quick Spec ... without approval gates」（kiro.dev/docs/specs/）。
- 状態: 主張（3 製品は静的読解と文書）
- 改善の方向: README の比較節に「承認は版に縛られ、AI は承認しない」を他社比較として書く。

### C3-spec-driven-07 OpenSpec の既知の欠陥（base 版なしの上書き）はキットの節ハッシュが答えにあたる
- 種別: 機会
- 深刻度: Low
- 根拠: openspec-parallel-merge-plan.md:4-7,20-23「Missing base fingerprint」「the second archive overwrites the first and silently drops scenarios」。`grep -rliE 'base.?fingerprint|authored.?against|baseHash' src` は 0 件（未実装）。キットの section_hash.py は ID 単位の正規化 sha256 を版として持つ。ただし 2 つの枝が同じ REQ 行を直してそれぞれ refresh した場合の検出は未確認。
- 状態: 主張（OpenSpec 側）／未確認（キットの並行編集時）
- 改善の方向: 並行ブランチで同一 ID を変えたときの C7 の挙動を検証ケースに足す。

### C3-spec-driven-08 要件から性質（property）を導くテストの型が無い
- 種別: 機会
- 深刻度: Low
- 根拠: Kiro は「extracts properties from your EARS-formatted requirements」し、性質から PBT を生成、要件・タスクへのリンクを UI で示す（kiro.dev/docs/specs/correctness/）。キットは欠陥記録に「不変条件」欄があるだけ（traceability.md:73）。req-lint.py は EARS 型を検査する（:2）ので入力は揃っている。
- 状態: 主張
- 改善の方向: 詳細設計の雛形に「性質（不変条件）→ テスト ID」の欄を足すか検討する。

### C3-spec-driven-09 上流の変更で下流工程の承認が失効しない
- 種別: 欠落
- 深刻度: Low
- 根拠: approvals/README.md:35-40「covers はその工程が所有する成果物だけ」。要件が変わると第 1 工程の承認は失効するが、第 2 工程以降の承認は自分の成果物が変わらない限り有効のまま。gate は「直前の着手済み工程だけを見る」（check_approval.py の docstring）。全工程モードで第 1 工程の失効が NG になるかは実行していないため未確認。
- 状態: 未確認
- 改善の方向: 承認記録に上流の reviewed_hash も持たせ、上流の失効を下流の「要再確認」として出す。

## 調べられなかったこと
- spec-kit・OpenSpec の CLI の実行（指示により実行せず、静的に読んだだけ）。spec-kit の create-new-feature によるブランチ運用の詳細。
- Kiro の残り 6 サブページ（feature-specs・analyze-requirements・plan 等）。Kiro の tasks.md が要件番号を参照する書式（文書では確認できず）。
- キットの /phase-review の出力の型と spec-kit analyze の比較、および並行ブランチでの C7 の挙動。
- 研究（論文）による効果の比較は対象外とした（製品文書とコードのみ）。

# リスク台帳（2026-11-23 再構築）

- 基準: 正本 `docs/research/2026-11-21/SUMMARY.md` の順位 1〜5 を、段3 の反証結果（`stage3/`）で更新した。順位 6・7 は反証していないので正本のまま
- 対象コミット: 3ef90fd（origin/main）。11/21 の調査時点から対象の hook・ツール・agent 定義に変更は無い（`stage3/A-rank1-rank5.md` 冒頭）
- 深刻度の「見直し」は反証担当の提案で、正本の値は書き換えていない。採否は保守者が決める
- 照合した基準: 深刻度は ISTQB の severity、リスクの書き方は ISO 31000 の「原因・事象・結果」

## 段3 の結果（主対象 27 件・同時判定 3 件）
| 結果 | 主対象 | 同時判定 |
|---|---|---|
| 維持 | 25 | 3 |
| 判定不能 | 2 | 0 |
| 反証された | 0 | 0 |

- 判定不能: I1-hooks-01（書き込み遅れの再現を組めなかった）、S4-cc-subagents-01（サブエージェント起動の実験は範囲外）
- 反証 0 件は「全て正しい」の証明ではない。27 件中 9 件は実行を伴わず読解だけで維持と判定している

## 順位別
### 順位 1 見積判定 hook の誤停止（正本 Critical）
- 維持: I7-rules-01、C5-codex-agentsmd-01、I1-hooks-02、I7-rules-02、R2-lessons-02、R1-prs-01（過去事象）
- 判定不能: I1-hooks-01
- 見直し案: I7-rules-01 は Critical→High（kit 内部の書式は一致済み。食い違いは導入先と Codex 側に残る）。R2-lessons-02 は High→Medium
- 実行で確かめた点: ターン途中の追加発言で、見積済みでも停止する（I1-hooks-02）。質問・文書だけの作業を対象外と判定できない（I7-rules-02）
- 下位原因（今回登録・未検証）: OPS-NEW-01・02・03（`ops-new.md`）。止まった後に復旧できない側の問題

### 順位 2 守りが黙って外れる（正本 Critical）
- 維持 8 件: S1-cc-hooks-01、I8-install-02、D1-distribution-01、I3-tests-02、R4-note-02、I4-ci-01、S2-cc-plugins-02、E6-agent-safety-01。同時判定 I4-ci-02 も維持
- Critical の根拠が成り立つのは D1-distribution-01 だけ（Python 3.9 で 3 本の hook が終了コード 1 で素通りになることを実測）。条件は「PATH 上の python3 が 3.9」で、他者へ配るときに効く
- 見直し案: I3-tests-02・R4-note-02・S2-cc-plugins-02 は High→Medium
- 段2 の追加（`stage2/S1-cc-hooks.md`）: S1-cc-hooks-02・03 は一部再現

### 順位 3 検査が偽の合格を返す（正本 High）
- 維持: I2-tools-01（High）、I2-tools-02（Medium へ見直し案）、R4-note-01（High）
- 順位 3 の原因に当たらない: I3-tests-01（偽の合格ではなく本物の不合格）、E2-llm-testgen-01（偽の合格ではなく網羅の欠落）。発見自体は維持
- I3-tests-01 は直すコミットが入っていないことまで確認。今も赤かは回帰テストを実行していないので未実施
- 維持すべき強み: `run-all.sh` の `RUN=FOUND` かつ `FAIL=0` の判定は働いている。弱点は下限（1 本以上）が無いこと（`stage2/I3-tests.md`。新規の指摘）

### 順位 4 導入で利用者の資産が消える・届かない（正本 High）
- 維持: I8-install-01 と D1-distribution-02（同じ事象。High）、S3-cc-skills-01、S2-cc-plugins-01
- 見直し案: S3-cc-skills-01・S2-cc-plugins-01 は High→Medium
- S2-cc-plugins-01 の更新: 安全 hook 2 本の直近修正は現行版に載っている。載っていないのは憲法ゲートの 11/14 の 2 修正（`stage2/S2-cc-plugins.md`）

### 順位 5 aidd-lead の設計が自己矛盾（正本 High）
- 維持: I6-agents-commands-01（Critical）、C4-bmad-agentos-01、I6-agents-commands-02、S4-cc-subagents-02
- 判定不能: S4-cc-subagents-01
- 見直し案: I6-agents-commands-02 は High→Medium

## 今回新しく登録したリスク
| 番号 | 内容 | 深刻度 | 状態 |
|---|---|---|---|
| D3-supply-chain-01 | 外部スキル 15 件が版固定なしで導入される | High | 段1 のみ |
| S4-cc-subagents-08 | 計測ファイルが共有でロック無し | High | 段2 で再現 |
| S4-cc-subagents-03 | 委譲先に見積・進捗の規律が届かない | High | 一部再現 |
| OPS-NEW-01〜03 | 停止後に復旧できない | 未評価 | 仕組みのみ実証 |

- S4-cc-subagents-08 の再現は並列 40〜60 の条件。運用上限の 30 本以下での頻度は未確認
- S4-cc-subagents-03 は引き継ぎ H-01 と同じ内容（agents 6 本と起動時の注入文に見積・進捗の規律が無いことは実測）
- OPS-NEW の深刻度は事象の実物が無いため付けていない

## 残存リスク
- 段3 は発見 441 件中 30 件。残りは `unverified.md`
- 順位 6・7 と、順位 1〜5 に載らない 21 テーマの段2 は未実施
- Claude Code 本体の挙動に依存する点（終了コード 1 の hook の扱い、plugin の更新、サブエージェントの道具）は文書の記述に依拠し、本体での通しは未実施
- 回帰テスト・CI は実行していない（保守者の要求時のみの決まり）。HEAD が今も赤かは未確認

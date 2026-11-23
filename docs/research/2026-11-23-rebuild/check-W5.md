# check-W5: 機械的な照合（段1・段3・参照・作業範囲）

ROOT は scratchpad/kit-audit（worktree）。N=docs/research/2026-11-23-rebuild、O=docs/research/2026-11-21。内容の評価はしない。照合のみ。

## 項目 1 段3 の対象 ID の実在

- コマンド: stage3 の `## <ID>` 見出しと `同時判定: <ID>` を抽出し、重複を除いて `grep -lE "^#{2,3} <ID>" O/stage1/*.md` で照合
- 結果: 固有 ID 30 件（主対象 27 + 同時判定 3 に相当）。stage1 の見出しに実在しない ID は 0 件
- 不一致: 0 件
- 注: 段3 の A 集計表は C5-codex-agentsmd-01・C4-bmad-agentos-01 を「同時」と表示しているが、本文は主対象 10 件に数えている。項目 2 で扱う

## 項目 2 段3 の件数

- 見出し数（`## ID`）: A 8・B 8・C 9 = 25。A の C5-01・C4-01 は見出しでなく本文の併記
- 集計表の行数: A 12（主 8＋同時 4）・B 9（主 8＋同時 1）・C 9（主 9）
- 計画の固定対象との比較: 計画は 主 27（A10・B8・C9）＋同時 3
  - 本文の数え方（A の主対象 10 を採る）では 主 27・同時 3 で一致
  - 集計表のラベルどおりに数えると 主 25・同時 5。C5-01 と C4-01 の 2 件がずれる
- 結果の語（主対象 27 件、本文の数え方による）: 維持 25・判定不能 2（I1-hooks-01・S4-cc-subagents-01）・反証された 0
- 結果の語（集計表ラベルによる主 25 件）: 維持 23・判定不能 2・反証された 0
- 同時判定 3 件: R1-prs-01 維持・S4-cc-subagents-02 維持・I4-ci-02 維持
- 不一致: 2 件（C5-codex-agentsmd-01・C4-bmad-agentos-01 のラベル表記）

## 項目 3 段1 の発見件数

- コマンド: `grep -cE "^#{2,3} [A-Z][0-9]-[a-z0-9-]+-[0-9]+" O/stage1/*.md` の合計
- 合計 429 件（期待値 429 と一致）。ファイル別: C1 10・C2 12・C3 9・C4 15・C5 14・C6 12・D1 16・D2 12・E1 10・E2 11・E3 14・E4 14・E5 13・E6 13・I1 15・I2 16・I3 13・I4 17・I5 14・I6 16・I7 14・I8 20・R1 14・R2 14・R3 14・R4 13・S1 16・S2 14・S3 16・S4 17・S5 11
- SUMMARY.md 6 行目は「発見 430 件」。`grep -n "430\|件"` で見た範囲に、テーマ別件数の表は無い
- 1 件のずれは、どのテーマかを特定できず
- 不一致: 1 件（合計 429 対 430）

## 項目 4 新規の D3

- コマンド: `grep -cE "^## D3-supply-chain-[0-9]+" stage1/D3-supply-chain.md` と、「既存 ID … と同じ」を含む行の照合
- 見出し数 12
- 見出しに「既存 ID … と同じ」を含むもの 2 件（D3-supply-chain-11・D3-supply-chain-12）
- 該当語を含む行は 3 行（見出し 2 行と、D3-12 の根拠行 1 行）
- 不一致: 0 件（見出し単位では 12 件中 2 件）

## 項目 5 参照の実在

- コマンド: N 配下の全 .md（PLAN.md・review-W2-plan.md を除く）からバッククォート内の `パス:行番号` を抽出
- 拾った件数 37（うち `~/`・絶対パス・`.claude/` 始まりの除外 2）。調べた件数 35（重複 1 行を含む）
- 行番号超過 0 件
- 不在 20 件（全件 NOFILE。ROOT 直下のパスとして解決できない）:

| # | 出所 | 参照 |
|---|---|---|
| 1 | handoff-10.md | build_codex_skills.py:135 |
| 2 | ops-new-01-02.md | tool-timer.py:42 |
| 3 | ops-new-01-02.md | metering.py:24 |
| 4 | ops-new-01-02.md | constitution-gate.py:45 |
| 5 | ops-new-03.md | constitution-gate.py:4 |
| 6 | ops-new-03.md | constitution-gate.md:11 |
| 7 | ops-new-03.md | constitution-gate.md:25 |
| 8 | ops-new-03.md | ロードマップ.md:323 |
| 9 | stage1/S4 | agents/aidd-lead.md:4 |
| 10 | stage1/S4 | constitution-gate.py:174 |
| 11 | stage1/S4 | constitution-gate.py:174（重複） |
| 12 | stage1/S4 | tool-timer.py:192 |
| 13 | stage3/A | constitution-gate.py:37 |
| 14 | stage3/A | instruction-guard.py:43 |
| 15 | stage3/A | constitution-gate.py:306 |
| 16 | stage3/A | gate-agent.md:22 |
| 17 | stage3/A | aidd-lead.md:69 |
| 18 | stage3/A | aidd-lead.md:4 |
| 19 | stage3/C | done-gate/SKILL.md:15 |
| 20 | stage3/C | SKILL.md:15 |

- 補足: 20 件のうち 18 件はディレクトリ部分の無い裸のファイル名で、パスとしては一意に解決できない。ROOT 配下を名前で探せば見つかる可能性があるが、この担当では探していない（未確認）
- 不一致: 20 件

## 項目 6 作業範囲

コマンド: `git -C ROOT status --short` および `git -C ROOT diff --stat origin/main -- docs/research/2026-11-21/` の出力

```
 M docs/research/2026-11-21/SUMMARY.md
?? docs/research/2026-11-23-rebuild/
```

```
 docs/research/2026-11-21/SUMMARY.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

- 正本（docs/research/2026-11-21/）の SUMMARY.md に、origin/main との差分が 1 行（1 挿入・1 削除）ある。この担当は書き換えていない。差分の出所は未確認
- 不一致: 1 件（正本の差分）

## 不一致の合計

| 項目 | 不一致 |
|---|---|
| 1 ID 実在 | 0 |
| 2 件数 | 2 |
| 3 段1 件数 | 1 |
| 4 D3 | 0 |
| 5 参照 | 20 |
| 6 作業範囲 | 1 |
| 合計 | 24 |

不一致の合計 24 件

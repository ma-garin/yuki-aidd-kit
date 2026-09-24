# lessons.md — AIDDプロセス改善ログ

> 成果物でなく「AIDDの進め方」の知見を蓄積する。ADR（技術判断）・CURRENT_STATE（進捗）とは別物。
> 1エントリ3-5行。retroスキルで追記する。
> 特定のファイルで効く学びには `**適用パス**:` の下に glob を 1 行 1 つ書く。`adr-to-rules.py` がその項目だけを
> paths 付き rules に書き出し、該当ファイルを扱うときに AI が読む（適用パスの無い項目は書き出さない）。

---

## YYYY-MM-DD [プロジェクト名 or 横断]

**適用パス**（任意。glob を 1 行 1 つ `- ` で並べる）:

**Keep**（再利用したいやり方）
-

**Problem**（詰まった点）
-

**Try**（次に試す / キットへの反映候補）
- [ ]

---

<!-- 記入例
## 2026-06-13 business_agent

**適用パス**:
- `src/modules/**`

**Keep**
- /sdd-start で spec→tasks を一気に作ると実装の手戻りが減った

**Problem**
- 16モジュール全体をAIが読もうとしてトークンを浪費した
- design-systemスキルが発火せず、UIの色がばらついた

**Try**
- [x] CLAUDE.mdに「対象モジュールのみ読む」を明記 → 反映済み
- [ ] design-systemのdescriptionに「Streamlitのテーマ」を追加
-->

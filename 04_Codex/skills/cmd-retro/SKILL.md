---
name: cmd-retro
description: "/retro — レトロと学びの蓄積"
---
<!-- 生成物: 04_Codex/build_codex_skills.py が 03_ClaudeCode/・02_共通/rules/ から生成する。直接編集しない -->
コマンド `/retro` の Codex 版。引数は、呼び出し時にユーザーが続けて書いた文を `$ARGUMENTS` として読む。

# /retro — レトロと学びの蓄積

引数: $ARGUMENTS（プロジェクト名 or 空＝横断レトロ）

## 実行内容

retroスキルに従い振り返りを行う。

1. 対象セッション/プロジェクトの作業を Keep / Problem / Try で整理
2. CURRENT_STATE.md・直近のコミット・evalスコア推移があれば参照して材料にする
3. lessons.md への追記内容を生成（templates/lessons.md形式、3-5行）
4. 学び 1 件ごとに**編集先ファイル**（rules／スキル／hook／コマンド）を決め、一回きりの出来事は除外する（retro スキルの「直す場所に結び付ける」、`references/lesson-to-target.md`）
5. 判断／発散／道具の 3 視点を別々のサブエージェントでレビューし、統合者が採用／却下／保留に仕分ける（`references/review-viewpoints.md`）
6. キット反映候補を提示（承認を得てから編集する）:
   - 発火しなかったスキル → description追加案
   - 繰り返した手作業 → コマンド化案
   - 繰り返したミス → hook / done-gate項目追加案
7. `python3 scripts/adr-to-rules.py <ADR のディレクトリ> <lessons.md> --out .claude/rules` を実行し、採用済み ADR・適用パスのある lessons を paths 付き rules に書き出す

引数が空なら直近の作業を対象にする。

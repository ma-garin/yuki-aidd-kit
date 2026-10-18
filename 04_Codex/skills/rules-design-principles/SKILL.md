---
name: rules-design-principles
description: "設計原則（短い 5 つ）。Claude Code のrules（規約） `design-principles` の Codex 版"
---
<!-- 生成物: 04_Codex/build_codex_skills.py が 03_ClaudeCode/・02_共通/rules/ から生成する。直接編集しない -->
Claude Code のrules（規約） `design-principles` の Codex 版。対象ファイルの範囲（Claude Code の paths）: `**/*.{py,js,ts,tsx,jsx,md}`。該当するファイルを扱うときに従う。Claude Code 専用の hook・コマンドは、Codex で対応機能を確認できた場合だけ適用する。

# 設計原則（短い 5 つ）

1. **前提を疑う**: 依頼文の前提（原因・手段・制約）を実物で確かめてから設計する。誤った前提の上の丁寧な実装は全部捨てになる
2. **根本原因を直す**: 症状の側にパッチを足さない。原因が別の層にあるなら、そこを直すか、直せない理由を残す
3. **冪等にする**: 同じ操作を 2 回走らせても結果が同じ。再実行・リトライ・中断再開で壊れない作りを先に選ぶ
4. **減らしてから足す**: 新機能の前に、既存の何を消せば済むかを探す。足すのは最後
5. **旧 API は呼び出し側を移して削除する**: 互換層を残して二重化しない。全呼び出し側を新へ移し、旧を消す（参照: plugins/pstack principle-*）

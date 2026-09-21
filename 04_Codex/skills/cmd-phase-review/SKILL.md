---
name: cmd-phase-review
description: "/phase-review — 工程の出口で AI 3 役を順次レビューし、人間の承認に渡す"
---
<!-- 生成物: 04_Codex/build_codex_skills.py が 03_ClaudeCode/ から生成する。直接編集しない -->
コマンド `/phase-review` の Codex 版。引数は、呼び出し時にユーザーが続けて書いた文を `$ARGUMENTS` として読む。

# /phase-review — 工程の出口で AI 3 役を順次レビューし、人間の承認に渡す

引数: $ARGUMENTS（工程番号 0〜9。例: `2`）

## 実行内容

`phase-approval` スキルに従う。**AI は承認しない。**承認欄は人間が埋める。

1. **現状を確認する**: `./scripts/check-approval.sh --phase $ARGUMENTS`
   - 既に承認済み（exit 0）なら、再レビューが必要か人間に確認してから進む
2. **判定基準を引く**: `skills/dev-lifecycle/references/phase-gates.md` 第 N 工程の出口基準（複製しない）
3. **3 役を順次実行する**（並列委譲しない。トークンが約 7 倍になる）
   - 役1 追跡担当: `./scripts/trace-check.sh docs/lifecycle` ＋ 追跡表。紐づいていない ID を列挙
   - 役2 仕様一致担当: **上流工程の成果物と当該工程の成果物だけ**を読む（実装コードを読まない）
   - 役3 リスク担当: 異常系・境界値・非機能の抜け。`qa-review-standards` の severity を付ける
4. **`docs/lifecycle/approvals/phase-N-ai.md` へ追記する**（上書きしない。形式はスキル参照）
   - 差し戻し事項は `R-N-<連番>`。**解消の検証方法が書けない指摘は差し戻さない**
   - 判定できなかった項目は「未確認事項」に残す。空欄にして合格にしない
5. **報告する**: ①各役の申し送り判定 ②差し戻し事項の件数と ID ③未確認事項 ④`check-approval.sh --phase N` の結果
   ⑤**「承認欄は空のままです。承認は人間が行ってください」**

## 制約

- 再レビューは**差し戻した役だけ**。全役をやり直さない
- **最大 2 ラウンド**。収束しなければ人間へエスカレーションする（工程の粒度が合っていない兆候）
- `approver` / `approved_at` / `reviewed_hash` には触れない（人間が埋める欄）

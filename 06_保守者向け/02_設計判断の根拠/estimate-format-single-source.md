# 見積・計測表示の真実源を A-2 に一本化（2026-11-03）

## 事実
- 「見積」の規約が 12 ファイルに重複し、書式が 3 系統に分かれていた
  - A: `見積: N分（HH:MM 完了予定）` ＋ 末尾 `見積: N分 / 実測: M分 / CP往復: X→Y`。ツールを使う作業すべてが対象（prompt-priority.py・instruction-guard.py の注入文、運用モード.md、保守者の会話設定 2026-09-27）
  - B: `見積：N分` 単独行 ＋ 末尾【見積:N分 | 実測:M分 | 開始:HH:MM | 終了:HH:MM | 作業時間記録:成功/失敗】。コーディングを含む作業のみ（absolute-rules A-2・AGENTS.md.template・work-metering。2026-10-18 保守者指示）
  - C: 【見積：N分 | 開始 | 終了 | タスク数】の計測 3 行（A-2a・work-metering）
- hook は A の文言を注入し、規約本文は B を定めていた。AI は毎回どちらかに違反する状態だった

## 決定
- 保守者が 2026-11-03 01:19 に **B** を選択（2026-10-18 の指示が最新。選択肢 A/B を提示して確認済み）
- 真実源は `02_共通/rules/absolute-rules.md` の A-2（見積行・完了行）と A-2a（計測行）。他は参照のみ。同じ規約を 2 か所に書かない
- C は A-2a として B の内部に含める（開始・中間・終了の計測行）
- 中間行は「3 分以上の無報告を作らない」。speed-harness H-0 の「ツール実行の合間に本文で途中報告しない」は A-2a と矛盾していたため、「中間行以外の途中報告は書かない」に改めた（2026-11-03 のインシデント: 無報告 7〜11 分）

## 変更した参照元
- 文書: speed-harness H-0・H-1・H-6・H-8、AGENTS.md.template、work-metering/SKILL.md、01_利用者向け資料/04_運用モード.md、INDEX.md
- hook: prompt-priority.py（注入文を B に。完了予定の計算指示を削除）、instruction-guard.py（通知文を B に）、reply-language.py（末尾行の判定 FINAL_EST_RE を【見積:N分 | 実測:M分】にも対応。差し戻し文言を B に）
- 互換: 旧 A の末尾行 `見積: N分 / 実測: M分` は当面読める（過去の transcript と回帰テストのため）。注入・差し戻しの文言は B のみ

## 参照の向き
hook・スキル・テンプレート → `rules/absolute-rules.md` A-2 / A-2a。逆方向の定義は置かない。

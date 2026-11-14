# 検証結果 2026-11-14

- REQ-UI-001/002/004: test-ui-catalog.py 5テスト合格。5用途・5例・0件・表示制限・不明ID・不正台帳6条件・ハッシュ・移設・読み取り専用を確認。
- REQ-UI-003: test-install.sh PASS=206 / FAIL=0。隔離HOMEのinstall.shと隔離プロジェクトexport-project.shを実行し、同梱カタログを取得。
- 実ブラウザ: 1366x660と補助の360x660、5部品ずつ指定10/検査10合格。再試行・条件変更・処理終了・確認の実行/取消/Escapeを確認。
- 前提発見: feedback.jsのダイアログは共通box-sizing:border-boxが必要。既存UIを変更せず台帳の前提へ記載。
- PC操作を既定とする設計指針を原本とCodex生成物へ反映。
- ISO/IEC 25010自己レビュー: 機能適合は上記証拠、保守性は共通台帳、互換性は既存API維持、安全性は範囲外参照拒否と読み取り専用で確認。品質認証を意味しない。
- 未検証: AI開発課題の旧方式との速度・修正往復比較、人間の受入合格。速度改善は主張しない。

再実行: python3 06_保守者向け/03_回帰テスト/test-ui-catalog.py
ブラウザ: ui-catalog-browser-code.pyの標準出力をPlaywright browser_run_code_unsafeのcodeへ渡す。
生成物: python3 04_Codex/build_codex_skills.py --check

# /security-audit — セキュリティ監査（security-audit スキルを呼ぶ）

引数: $ARGUMENTS（任意: 対象ディレクトリと範囲 quick / diff / full。既定は `.` と diff）

## 実行内容

`skills/security-audit/SKILL.md` の手順で監査する（明示の依頼だけで使う。`ecc-daily-router` からは自動で振らない）。
マイルストーンのフルゲートの一部（`skills/test-strategy/SKILL.md`）。

1. **範囲を決める**（quick・diff・full）。範囲の外は「見ていない」と書く
2. **`./02_共通/ツール/security-scan.sh <対象ディレクトリ>` を実行する**（配布先では `./scripts/security-scan.sh`）
   - 依存: pip-audit / osv-scanner / npm audit / trivy fs（導入済みのものだけ）
   - 危険なコード: semgrep（ローカル規則がある場合のみ）/ bandit。**どちらも無ければ grep シグネチャで簡易代替**し、結果に「簡易」と印を付ける
   - 秘密: gitleaks detect
   - 許容済みの既知の指摘がある場合だけ `--baseline <ファイル>`（件数は減る方向だけ・理由と期限。`skills/done-gate/SKILL.md`）
   - 全件は `security-report.md` に書き出される
3. **未検査の一覧を出す**（未導入・解析失敗の走査器。合格に数えない）
4. **スタックの観点を足す**: スキルの表から該当する references を 1 つ選び、3〜5 行だけを手で見る
5. **`security-report.md` の末尾に「手動監査」節を追記する**（file:line の根拠付き・重大度順）
6. **会話には要旨だけを 10 行以内で出す**
   - 指摘の `file:line`（重大度順、多くても先頭 10 件）
   - **未検査の一覧**（合格に数えていないことを明記する）
   - 次の一手（どの指摘から直すか。直すコードの提案はしてよい）

## 注意

- **AI は修正を提案するだけ**。指摘の抑制（`# nosec` 等の ignore コメント・除外設定・基準線への追加）は保守者が判断する。AI が抑制を書き込まない
- exit 2（判定不能）のときは「指摘なし」と言わない。走査器を導入していないだけであることを明記する
- 秘密の指摘が出た場合、値そのものを会話に貼らない（`file:line` と規則名だけ）
- 走査器の追加導入（`pip install` 等）はしない。導入は利用者の判断

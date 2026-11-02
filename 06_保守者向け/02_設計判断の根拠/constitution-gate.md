# 憲法ゲート（constitution-gate.py）— 見積・中間報告・番の終わり方を制御で止める（2026-11-03）

## 事故
- 2026-11-03 23:50〜01:25 の 1 セッション（クラウド。kit の hook 未導入）で、見積行の欠落 3 回、無報告 7〜11 分が 2 回、再発 3 分が 1 回。保守者が「最悪のインシデント」「二度と起こしてはいけない」と判定
- 「気をつける」「規約に書く」は効かなかった。記事 5/5 の区別で言えば全部「指示」だった

## 決定: 指示でなく制御
| 制御 | 動作 |
|---|---|
| 停止 file | 違反 1 回で `.claude/constitution-stop` を書く。存在する間は PreToolUse が全ツール deny。猶予・回数の閾値は設けない |
| 解除は保守者のみ | file の rm/mv/上書き・Write/Edit を本 hook が deny。解除の環境変数は作らない。保守者が自分の端末で消す |
| 事後分析の必須化 | `.claude/constitution-stop.last` の時刻より `06_保守者向け/学んだこと.md` が古ければ deny。振り返りを書くまで再開できない |
| 見積ゲート | コーディング指示の後、このターンに `見積：N分` 行が無ければ deny（読み取り専用ツールは 3 回まで許可） |
| 報告ゲート | 最後の見積行／中間行／完了行から 180 秒超（`AIDD_REPORT_INTERVAL_SEC`）で deny。時刻は hook の壁時計 |
| 離席ゲート（Stop） | 委譲先の走行中・計測区間が未了なら block |
| fail-closed | 入力不正・例外・transcript 不読は deny（A-14） |
| 監査 | 違反は `hook-decisions.log` と `.claude/constitution-violations.jsonl` に残す。`report` で状態表示。`evidence.py` に件数を載せる（次版） |

## 配線（PreToolUse は配列の**先頭**）
```json
"PreToolUse": [ { "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/constitution-gate.py pre", "timeout": 5 } ] }, … ],
"Stop":       [ { "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/constitution-gate.py stop", "timeout": 5 } ] }, … ]
```
キット自身の `.claude/settings.json` と plugin の `hooks.json` も同じ位置に置く（パス表記は各 file の流儀）。

## 解除手順（保守者）
1. 自分の端末で `rm .claude/constitution-stop`
2. `06_保守者向け/学んだこと.md` に Problem / Try を書く（mtime が停止時刻より新しくなる）
3. 次のツール呼び出しから再開

## 担保できない範囲
- hook が入らない環境（クラウドセッション等）。`CLAUDE.md` で「未導入なら宣言するまでツール不可・違反時は自ら停止」を規約化し、plugin 導入で塞ぐ

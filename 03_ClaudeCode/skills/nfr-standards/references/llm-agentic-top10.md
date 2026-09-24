# LLM・エージェントの点検表（OWASP LLM Top 10 ／ Agentic Top 10）

1 行 1 リスク。**2 つの対象に当てる**: (a) 利用者のアプリ（`streamlit-rag-app` の RAG・LLM API を呼ぶ単一 HTML 等）、
(b) キット自身（`03_ClaudeCode/skills/` のスキル・`03_ClaudeCode/agents/` のエージェント・hooks・導入する MCP）。
新しい道具は作らない。「確認方法」は既存の検査・テスト・grep で確かめる手順。適用しない行は「対象外（理由）」と書く。

出典: OWASP Top 10 for LLM Applications 2025、OWASP Top 10 for Agentic Applications（2026 年版）
（OWASP GenAI Security Project。CC BY-SA 4.0）。項目名は原題、説明は要約（公式の日本語訳ではない）。
この表は外部アクセスなしで作った。**版と項目名は保守者が公式ページで確かめてから確定する**。

## LLM Top 10（2025）

| 項目 | キットの対策 | 未対応 | 確認方法 |
|---|---|---|---|
| LLM01 Prompt Injection | `injection-guard.py`（取り込んだ内容の指示の形の文を警告）、`skill-scan.py`（注入の文言・不可視文字）、`check_docs.py` 検査14 | (a) RAG の取り込み文書・利用者入力の注入を止める仕組みは無い | (a) 注入文を含む文書を入れて出力が変わらないかを `agent-eval` の評価に足す (b) `test-hooks.sh` |
| LLM02 Sensitive Information Disclosure | `pre-read-guard.py`（秘密ファイルを読まない）、`pre-write-check.sh`・`pre-commit`（秘密値）、`security-scan.sh` の gitleaks | (a) 応答に他テナントの文書・個人情報が混ざる経路 | (a) テナント越境の単体テスト（`nfr-standards` マルチテナント） (b) `test-hooks.sh` |
| LLM03 Supply Chain | `skill-scan.py`（導入前の静的検査）、`verify.sh` の設定の監査（MCP が取得して実行する未知のパッケージ）、`security-scan.sh`（依存） | モデルの版の固定・出所の記録 | 設定にモデル ID を版まで書いているか grep。導入前に skill-scan を流したか |
| LLM04 Data and Model Poisoning | なし | (a) 取り込む文書の出所の管理・承認 | 取り込み元の一覧と、誰が足したかの記録があるか |
| LLM05 Improper Output Handling | `nfr-standards`（innerHTML を避ける）、`security-scan.sh` の簡易シグネチャ | (a) LLM の出力が SQL・シェル・HTML・動的評価に入る経路 | LLM ラッパーの戻り値を受ける所を grep し、描画・実行の前に検証があるか見る |
| LLM06 Excessive Agency | hooks（`block-destructive.py`・`block-protected.py`・`block-gates.py`・`block-ci.py`）、`verify.sh`（すべての Bash を許す allow と、許可確認を飛ばす既定モードを NG） | (b) 5 エージェントの tools が全員 Bash・Write・Edit を持つ（検証役の書き込みを絞る余地）。(a) ツール呼び出しの権限 | `grep -n '^tools:' 03_ClaudeCode/agents/*.md`、`verify.sh` の「設定の監査」 |
| LLM07 System Prompt Leakage | なし | システムプロンプトに秘密・内部 URL を書かない規約が無い | プロンプトの定義ファイルを grep（キー・URL・社内名） |
| LLM08 Vector and Embedding Weaknesses | `nfr-standards`（テナント ID を全クエリの第一キーに） | (a) ベクトル検索の filter にテナント条件があるか | 検索呼び出しの引数を grep。越境の単体テスト |
| LLM09 Misinformation | `agent-eval`（Faithfulness・ハルシネーション）、`done-gate`（AI を含む場合の追加項目） | 出典の表示を必須にする規約 | `agent-eval` のベースラインを下回らないか |
| LLM10 Unbounded Consumption | (b) `context-guard.py`・`block-ci.py`（待機と起き直しの反復を止める）、トークン監査 | (a) 利用者ごとの回数・トークンの上限 | LLM ラッパーに max_tokens と回数の上限があるか |

## Agentic Top 10（ASI01〜ASI10）

| 項目 | キットの対策 | 未対応 | 確認方法 |
|---|---|---|---|
| ASI01 Agent Goal Hijack | `injection-guard.py`、`subagent-context.py`（取り込んだ内容の指示に従わない規約を委譲先に注入）、`prompt-priority.py` | 取り込み内容の遮断（警告だけで止めない） | 注入文を含むページを読ませて作業が逸れないか（手動） |
| ASI02 Tool Misuse and Exploitation | `block-destructive.py`・`block-gates.py`・`filter-output.py`、`verify.sh` の設定の監査 | MCP ツールごとの許可の点検 | `test-hooks.sh`、`verify.sh` |
| ASI03 Identity and Privilege Abuse | `block-protected.py`（設定・hook・git hook の書き換えを止める）、承認は人（approver 欄を AI が埋めない・`check_approval.py`） | 秘密を扱う操作の本人確認 | `test-git-gates.sh`・`test-check-approval.sh` |
| ASI04 Agentic Supply Chain Vulnerabilities | `skill-scan.py`（install.sh・install-guard が導入前に流す）、`verify.sh`（MCP の定義） | 導入後の更新（版の変化）の再走査 | 取り込むたびに `python3 02_共通/ツール/skill-scan.py <パス>` |
| ASI05 Unexpected Code Execution | `skill-scan.py`（取得物をシェルへ流す形・動的評価）、`verify.sh`（hook の curl … sh を NG）、`block-destructive.py` | (a) LLM の出力をコードとして実行する経路 | 出力を実行する所を grep（LLM05 と同じ） |
| ASI06 Memory and Context Poisoning | `pre-compact.py`（圧縮で残すものを指定）、rules は採用済み ADR からだけ作る（`adr-to-rules.py`） | CURRENT_STATE.md・lessons の書き込みを人が読む仕組み | 差分を保守者が読むか（`retro`） |
| ASI07 Insecure Inter-Agent Communication | `subagent-context.py`（委譲の規約）、エージェント定義の「越えない線」 | エージェント間の受け渡しの検証（同じ利用者の手元で動く前提） | 対象外にするなら理由を書く（単一利用者・ローカル） |
| ASI08 Cascading Failures | `done-gate`・`gate-agent`（完了の判定を実装役と分ける） | 失敗の連鎖を止める上限（再試行の回数） | エージェント定義の終了条件・差し戻しの節 |
| ASI09 Human-Agent Trust Exploitation | 承認は人、`done-gate`（「動くはず」を書かない・未検証の表） | 報告の根拠の自動検査 | 報告に file:line・実行結果があるか |
| ASI10 Rogue Agents | `block-ci.py`（自己ウェイクを止める）、`log-instructions.py`（読み込んだ指示の記録）、`tool-timer.py` | 目標から外れた行動の検知 | 記録を `retro` で見直す |

# 機能契約ハーネス（feature contracts）

`rules/functional-integrity.md` の「UI → API → backend → 出力 → 永続化 → エラー → 証跡」を、**人の注意力でなくスクリプトで**検証する仕組み。
出所: WebSpec2Doc `scripts/quality_harness.py`（53 機能で運用）。2026-07-19 に「機能を足したが契約に登録し忘れ、ハーネスが素通しで PASS」が実際に起きたため、未登録モジュールの検出を含む。

## ファイル

| ファイル | 役割 |
|---|---|
| `quality/feature_contracts.yml` | 機能ごとの契約（JSON 互換 YAML）。雛形: `templates/test/feature_contracts.yml` |
| `scripts/quality_harness.py` | 契約を検証し PASS/FAIL を返す（NG>0 で exit 1。CI でそのまま落とせる） |
| `scripts/test-quality-harness.sh` | ハーネス自身の回帰テスト（キット側） |

## 契約の項目

```json
{
  "feature_id": "user_feedback",
  "name": "利用者フィードバック送信",
  "risk_level": "high",                 // critical | high | medium | low
  "status": "implemented",              // implemented | partial | planned（ui-only は禁止）
  "ui_files": ["templates/feedback.html", "static/js/feedback.js"],
  "route_files": ["web/routes/feedback.py"],
  "core_files": ["web/services/feedback_store.py"],
  "symbols": ["append_feedback", "FeedbackError"],   // core_files 内に実在すること
  "outputs": ["送信結果メッセージ", "/api/feedback JSON"],
  "persistence": ["instance/feedback.jsonl"],
  "failure_modes": ["empty_message_rejected", "write_failure_reported_not_silently_dropped"],
  "required_tests": ["happy_path", "error_path", "evidence"]
}
```

## 検証内容

| # | 検出するもの | 規則 |
|---|---|---|
| 1 | 統制文書の欠落 | `harness.required_docs` が全て存在する |
| 2 | 無効な risk_level / status | 上記の列挙値のみ。`ui-only` は禁止 |
| 3 | 参照パスの欠落 | `ui_files` / `route_files` / `core_files` が全て実在する |
| 4 | 実行経路の無い implemented | `implemented` は `route_files` か `core_files` を持つ |
| 5 | 失敗系の無い高リスク機能 | `critical` / `high` は `failure_modes` と `required_tests` が必須 |
| 6 | 存在しないシンボル | `symbols` が `core_files` のどれかに文字列として現れる |
| 7 | **契約未登録の新モジュール** | `harness.source_roots` 配下の `.py` は、いずれかの契約か `unregistered_allowlist`（理由付き）に現れる |
| 8 | 未実装の利用者経路 | `harness.scan_roots` の `.py/.js/.html` に "UI only" / "not implemented" / "stub endpoint" 等が無い |

## 運用

- 機能を追加したら契約を同じ PR で追加する。ハーネスが #7 で止めてくれる。
- 基盤部品（設定・認証・型定義など）は `unregistered_allowlist` に **「なぜ機能ではないか」の理由付き**で登録する。
- 実行はマイルストーンとユーザー要求時（`rules/speed-harness.md` H-7）。CI では `github-actions/test-gates.yml`。
- `python3 scripts/quality_harness.py --root . --contract quality/feature_contracts.yml`

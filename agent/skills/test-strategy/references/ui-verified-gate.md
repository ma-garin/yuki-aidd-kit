# UI 検証マーカー（.ui-verified）と pre-commit ゲート

「UI を変えたのに E2E を回していないコミット」と「E2E を回した後に UI を変えたコミット」を機械的に止める。
出所: WebSpec2Doc `.githooks/pre-commit` v2（`touch` による偽造と、検証後の変更を hash で検出）。

## 仕組み

```text
make verify-ui（L3 E2E 全 PASS）
  → .ui-verified に「git HEAD hash / UI コンテンツ hash / ISO 時刻」を 1 行書く
git commit（UI ファイルが staged）
  → pre-commit-ui-gate.sh がマーカーを確認:
     存在しない            → BLOCKED（make verify-ui を実行）
     時刻が 2 時間より古い  → BLOCKED
     UI hash が現在と不一致 → BLOCKED（検証後に UI が変更された）
     一致                  → PASS（「ブラウザ目視確認も実施しましたか？」と WARN）
```

- UI hash は `scripts/ui-hash.py disk`（git 管理対象の `.html/.js/.css` 全体）。staged 差分ではなく disk 全体で照合する（部分コミットで必ず不一致になるのを避ける）。
- `docs/` 配下の HTML/JS/CSS は設計モックとして対象外（誤検出で pytest 全件を完走してから BLOCK していた実績）。

## 刷新モード（`.rebuild-mode`）

UI を作り替えている期間は毎コミットの E2E を要求しない。**免除ではなく「マイルストーンでまとめて実行」に切り替える。**

```bash
echo "ダッシュボード刷新（〜8/30）" > .rebuild-mode   # 有効化（理由必須）
rm .rebuild-mode                                     # 解除。必ず make verify-ui を通してから
```

有効中は毎コミットに「E2E は未実行。未検証であり問題なしではない」と表示する。

## 配置

```bash
./scripts/init-test-docs.sh <対象>        # ui-hash.py / pre-commit-ui-gate.sh を <対象>/scripts/ に置く
# <対象>/.git/hooks/pre-commit から呼ぶ（秘密情報スキャンの scripts/pre-commit と併用）:
#   bash scripts/pre-commit-ui-gate.sh || exit 1
```

verify-ui 側（Makefile / npm script）で E2E PASS 後にマーカーを書く:

```bash
printf "%s %s %s\n" "$(git rev-parse HEAD)" "$(python3 scripts/ui-hash.py disk)" "$(date -Iseconds)" > .ui-verified
```

# ECC Asset Map for AIDD

最終更新: 2026-10-12

`<APP_WORKSPACE>` の実プロジェクト群に対して、ECC の資産を DAILY / LIBRARY に分けた対応表です。

## STACK

スキャン結果の要点:

- Python: QA document generator、QA portal、storage-manager、旧 API test tool
- JavaScript / HTML: UX audit tool、JSTQB学習アプリ、単一HTML/静的ツール
- React / Vite: React finance PWA、iOS wrapper project、investment hypothesis PWA
- Playwright: QA document generator、UX audit tool、playwright-sample、QA portal smoke
- Django: QA portal portal
- Swift / Xcode: iOS wrapper project の wrapper のみ
- ドキュメント / QA資産: README、AGENTS、CONTEXT、strategy、requirements が多い

## DAILY

| ECC path | 種別 | 根拠 | 使い方 |
|---|---|---|---|
| `skills/e2e-testing` | skill | Playwright 利用が複数プロジェクトに存在 | E2E、smoke、ブラウザ確認 |
| `skills/browser-qa` | skill | UX監査・Web仕様抽出が中心 | 画面フロー、スクショ、表示崩れ確認 |
| `skills/accessibility` | skill | UX audit tool が alt / label / heading を扱う | WCAG / a11y 観点の補強 |
| `skills/frontend-patterns` | skill | HTML / JS / CSS / React が多数 | UI変更時の基本規約 |
| `skills/react-patterns` | skill | React finance PWA / investment hypothesis PWA が React | React component / state / localStorage |
| `skills/vite-patterns` | skill | React + Vite + GitHub Pages | build / base path / Pages 配信 |
| `skills/python-patterns` | skill | Pythonファイルが多い | Flask / CLI / ロジック整理 |
| `skills/python-testing` | skill | pytest / pyproject / ruff / mypy | テスト、型、lint |
| `skills/django-patterns` | skill | QA portal portal が Django | Django app / view / tests |
| `skills/backend-patterns` | skill | QA portal / API系のサーバサイド実装 | API設計、バックエンド規約 |
| `skills/tdd-workflow` | skill | 既存AGENTSでテスト重視 | 実装前のRED/GREEN/REFACTOR |
| `skills/verification-loop` | skill | UI変更で検証漏れを避けたい | 完了前の検証ストーリー |
| `skills/security-review` | skill | APIキー、localStorage、Web取得が多い | 秘密情報、XSS、入力検証 |
| `skills/deep-research` | skill | QA技術・OSS評価・競合調査 | ソース付き調査 |
| `skills/eval-harness` | skill | AI/RAG/LLM評価の構想がある | ゴールデンデータ、judge、回帰 |

## LIBRARY

| ECC path | 理由 |
|---|---|
| `rules/swift/*` / Swift skills | iOS wrapper project の Swift wrapper に触る時だけ使う |
| Go / Java / Kotlin / Rust / PHP / Laravel 系 | 現在の主プロジェクト群では日常利用なし |
| Blockchain / DeFi / prediction market 系 | 現在のプロジェクト目的から遠い |
| 大規模 orchestration / multi-agent 系 | 使う前に目的・運用コストを確認 |

## Project Mapping

### QA document generator

DAILY:

- `python-patterns`
- `python-testing`
- `e2e-testing`
- `browser-qa`
- `verification-loop`
- `security-review`

Kit:

- `test-automation`
- `qa-review-standards`
- `done-gate`
- `sdd-ecc-workflow`

### UX_Auto_Reviewer

DAILY:

- `browser-qa`
- `accessibility`
- `frontend-patterns`
- `e2e-testing`
- `security-review`

Kit:

- `qa-review-standards`
- `design-system`
- `test-automation`

### React finance PWA / iOS wrapper project

DAILY:

- `react-patterns`
- `vite-patterns`
- `frontend-patterns`
- `security-review`
- `verification-loop`

LIBRARY:

- Swift / iOS skills for `iOS wrapper project/ios/*`

Kit:

- `personal-pwa`
- `nfr-standards`
- `done-gate`

### QA repository research tool

DAILY:

- `deep-research`
- `eval-harness`
- `typescript` / frontend-related skills as needed
- `security-review`

Kit:

- `agent-eval`
- `code-doc-search`
- `sdd-ecc-workflow`

### sandbox/QA portal

DAILY:

- `django-patterns`
- `python-testing`
- `backend-patterns`
- `security-review`
- `verification-loop`

Kit:

- `streamlit-rag-app` when AI module work is involved
- `qa-review-standards`
- `agent-eval`

## Kit 側の追加資産（2026-09-21 以降）

ECC とは別に、kit 自身が提供する資産です。上の「Kit:」に載せた既存スキルはすべて現存を確認済みです。

| 資産 | 種別 | 使い方 |
|---|---|---|
| `aidd-lead` | agent | 成果物レベルの依頼（「〇〇システムを作って」）を受ける統括。種別・進め方・デザインを人間に聞かない |
| `spec-agent` / `build-agent` / `verify-agent` | agent | 工程 2〜3（設計）／工程 4（実装＋デザイン）／工程 5〜7（テスト）を `aidd-lead` の下で回す |
| `gate-agent` | agent | 各工程の出口で機械判定と 3 役レビューを行い、差し戻す。承認欄は空のまま人間へ渡す |
| `advisor`（skill / agent） | skill / agent | 大きな判断の前・詰まったとき・完了の前に別の強いモデルへ相談する。助言は参考で、最終判断は自分と利用者 |
| `security-audit`（`/security-audit`） | skill / command | 導入済みの無料走査器でセキュリティ監査。明示の依頼のみ。未検査は合格に数えない |
| `ai-trend-research` | skill | AI・LLM・開発ツールの最新動向を公開 API・RSS・GitHub・Web から調べる（読み取り専用） |
| `agent-ready`（`/agent-ready`） | skill / command | プロジェクトが AI エージェントで開発しやすいかを 100 点で採点する（対象は変更しない） |
| `skill-guide` | skill | やりたいことから使うスキル・コマンドを案内する。利用者が呼ぶ専用 |

## Install Guidance

ECC を使う場合、いきなり full profile ではなく、対象プロジェクトごとに DAILY だけを選びます。

例:

```bash
# QA document generator 系
ecc plan --target claude-project --skills python-patterns,python-testing,e2e-testing,browser-qa,verification-loop,security-review

# React/Vite PWA 系
ecc plan --target claude-project --skills react-patterns,vite-patterns,frontend-patterns,security-review,verification-loop
```

実際にコピーする前に `plan` で差分を確認します。


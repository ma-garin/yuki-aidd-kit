# 03 — スキル詳細（19件）

各スキルの「目的 / 発火語 / 中身の要点 / 委譲・被参照 / 行数」。
**値や基準そのものは本体が真実源**。ここは構造と要点の索引として使う。

---

# DAILY 層（12件）

## dev-lifecycle（105行 + references 274行）

- **目的**: 工程を分けずに実装へ飛ぶと AI は「動くが要求を満たさないもの」を高速に量産する。**成果物・ID・ゲート**の3点を固定して各工程の完了を機械判定可能にする
- **発火語**: RFD / 要件定義 / 基本設計 / 詳細設計 / 単体テスト / 結合テスト / システムテスト / 受け入れテスト / UAT / 保守運用 / 工程 / V字 / トレーサビリティ / 設計書を作って / テスト仕様書
- **適用判断（冒頭・最重要）**:
  | 進め方 | 適用条件 |
  |---|---|
  | 軽量 SDD（spec/plan/tasks） | 個人PWA・単一HTMLツール・PoC。工程分割のコストが回収できない規模 |
  | 工程ライフサイクル | 他者に納品/引き継ぐ・要件の合意が必要・テスト分割が必要・保守運用が続く |
  両者は排他でなく**入れ子**（`01-requirements`↔`spec.md` / `02-basic-design`↔`plan.md` / `04-implementation`↔`tasks.md`）
- **10工程と ID**: RFD-001 / REQ-F-001・REQ-N-001 / BD-001 / DD-001 / T-001 / UT-001 / IT-001 / ST-001 / UAT-001 / OPS-001 / DEF-001
- **V字**: REQ↔UAT / BD↔ST・IT / DD↔UT。**テストを書く時は先に「左側のどの ID を検証するか」を書く**
- **共通の出口基準3つ**: TBD 残ゼロ / trace-check.sh NG=0 / qa-review-standards で自己レビュー（Critical・High 残ゼロ）
- **役割**: Coordinator（進行とゲート判定のみ）/ Implementor（指定 ID の範囲のみ）/ Verifier（実装と独立に evidence-only）/ **承認者（人間）— RFD の決定・要件定義の確定・UAT 合格の3点。AI は承認しない**
- **references**: `phase-gates.md`（工程0〜9の入口/出口チェックリスト＋差し戻し規則3条）/ `traceability.md`（ID 書式・定義と参照・追跡表・検出6種別・GitHub 連携）/ `test-levels.md`（UT/IT/ST/UAT の技法と規律）

## test-strategy（105行 + references 96行）

- **目的**: テスト活動全体（レベル・ゲート・種類・完了基準・実行タイミング・29119 文書・機械ゲート）の設計。`test-automation`（書き方）・`done-gate`（完了判定）・`dev-lifecycle`（工程）・`e2e-cycle`（回し方）と対
- **出所**: WebSpec2Doc の運用実測（2026-06〜08）。**テスト資産 17 件が 1 週間陳腐化した事故と是正を含む**
- **原則**: 「pytest が全 PASS であることは『完了』ではない。それは L1/L2 の『コードが壊れていない』確認にすぎない」
- **レベル**:
  | | 対象 | ゲート | 証跡 |
  |---|---|---|---|
  | L1 単体 | 関数・純ロジック | FAIL 0・行カバレッジ80%+ | テスト結果 |
  | L2 統合 | API・結合・状態遷移 | FAIL 0 | テスト結果 |
  | L3 システム(E2E) | ブラウザ上の実フロー | FAIL 0 → `.ui-verified` 生成。無ければ UI 変更をコミット不可 | スクショ 1280×800 + 1366×768 |
  | L4 受け入れ | ユーザーストーリー・非機能 | **依頼者(PO)が承認。AI は承認しない**。ISTQB FL 相当が初見・マニュアルなしで実施 | スクショ + コメント |
- **ゲートの実行タイミング（最優先で宣言する）**: 日常のコミット＝実行しない（H-7）／**マイルストーン＝フルゲート**／ユーザー要求時＝要求されたもの。*これが書かれていなかったため H-7 運用でゲートが1週間実行されず陳腐化した（2026-08-23 実損害）。迷ったらマイルストーンとして実行する*
- **変更タイプ別 DoD**: A バックエンド / **B フロントエンド★**（L3 全 PASS + `.ui-verified` + 実操作 1920×1080・1366×768 + コンソールエラーなし）/ C ドキュメント
- **references**: `feature-contracts.md`（契約項目と検証8種）/ `ui-verified-gate.md`（BLOCKED 条件・`.rebuild-mode`）

## e2e-cycle（95行）

- **目的**: E2E を5フェーズに分割し、**1回の起動で1フェーズだけ実行して必ず停止**する
- **絶対原則3つ**: ①1サイクル1停止 ②**待機・監視の完全禁止**（`sleep`・ポーリング・バックグラウンド `&`）③実行と状態管理の分離（フォアグラウンドで1回だけ発行）
- **フェーズ**: 1 テスト設計（CSV 出力）→ 2 Playwright スクリプト生成（実行しない）→ 3 安全な実行（件数概要のみ報告）→ 4 ODC 分析・**1〜2個だけ修整**→対象のみ再テスト→停止 → 5 ドキュメント同期と `git add` パス明示でコミット
- **自動判定**: 引数省略時は成果物の有無（CSV→スクリプト→結果 JSON→残 Fail）で次フェーズを決め、1行で宣言してから実行
- **既定パス**: `docs/system_test_cases.csv` / `playwright.config.ts` / `e2e/artifacts/` / `e2e/results/results.json` / `docs/odc_analysis.md`
- **ステップ4 の分類**: 製品欠陥 / テスト陳腐化 / 環境・データ依存 / flaky を判定し、`iso29119-incident-report.md` 形式で記録

## context-compression（56行）

- **目的**: トークンを「推論」に使い「作業ログ・生データの垂れ流し」に使わない
- **原則1 — 3層要約**: 結論(1-3行) / 根拠(5-10行・ファイル名:行番号つき) / 詳細(**会話に出さずファイルへ**)。30行を超えそうな出力に適用
- **原則2 — grep/glob で絞る**: 「まず全ファイルを読んで把握」を禁止。読む前に「grep 1回で取れないか」を自問
- **原則3 — 決定論的作業はスクリプト化**: 集計・検索・変換・カウント・整形をモデルの手作業でやらない。3回以上繰り返す操作は使い捨てスクリプトに
- **出力**: 結論→根拠の要約 / 詳細のファイルパス / 使用スクリプト（再実行可能な形）

## ecc-daily-router（57行）

- **目的**: ECC を全部読まず、対象プロジェクトに合う資産だけを DAILY / LIBRARY / OFF に分類
- **最初に見る証拠**: AGENTS.md/CLAUDE.md → README → manifest → tests/playwright.config → 変更対象の近傍。`node_modules` `venv` `dist` `output` `test-results` は読まない
- **プリセットを持たない**: 真実源は `docs/ECC-ASSET-MAP.md` の Project Mapping（AUDIT A-03 で全文削除）。該当が無ければスタックから選び **MAP への追記案を出す**
- **出力**: `STACK / DAILY / LIBRARY / NEXT` の4ブロック
- **注意**: `ecc plan` や install の前にまず分類だけ出す。秘密情報・localStorage・外部URL取得が絡むときは `security-review` を DAILY へ昇格

## sdd-ecc-workflow（55行 + references 56行）

- **目的**: 仕様ファイルを単一の真実とし、実装と検証を分離
- **10ステップ**: spec → plan → tasks → 実装ループ → 検証 → implement.md → documentation.md → AGENTS/CLAUDE 更新 → レビュー → 次イテレーション
- **ガバナンス3パターン**: spec-first（小規模・個人PWA）/ spec-anchored（社内ツール・PoC。実装後に逆同期）/ spec-as-source（顧客納品・規制要件。spec が常に正）
- **役割分離**: Coordinator / Implementor / Verifier（evidence-only）
- **トークン規律**: spec に禁止操作・対象外ファイルを明記／1タスク1セッション／思考トークン上限（Claude Code では `MAX_THINKING_TOKENS=10000`）／大きい仕様は口頭でなくファイルで
- **dev-lifecycle との関係**: 工程分割が要る案件は `dev-lifecycle` へ。本スキルはその**中に入れ子**で収まる

## qa-review-standards（46行）

- **目的**: 第三者検証の品質基準を AI レビューに注入。判定は常に **evidence-only**（根拠を提示できない指摘は出力しない）
- **ISO/IEC 25010 の5カテゴリ運用**: 使用性 / 性能効率性 / 信頼性 / セキュリティ / 保守性 を 0〜100＋根拠。**総合点は単純平均にせず重み付けを明示**
- **ISTQB severity**: Critical（データ損失・セキュリティ侵害・主要機能停止）/ High（主要ユースケース阻害・回避策困難）/ Medium（回避策あり）/ Low（軽微）。**severity と priority を混同しない**
- **Whittaker ツアー8種**: Guidebook / Money / Landmark / Intellectual / FedEx / Saboteur / Back Alley / All-Nighter
- **報告フォーマット**: `{id, category(25010), severity(ISTQB), evidence, 再現手順, 改善案}`（Jira CSV / GitHub Issues へエクスポート可能なフラット構造）

## atarimae-quality-audit（71行 + scan.sh 77行）

- **目的**: 当たり前品質（Kano の must-be）＝**満たされても満足は生まれないが、欠けると強い不満を生む**要素を、発見者として先回りで潰す
- **発火語**: 徹底的に / 洗い出して / 品質を上げて / 似たようなものが大量にある / まだ○○がおかしい / exhaustive review / quality audit
- **作法4条**: ①追認者でなく発見者になる（指摘1点は症状。裏の**欠陥クラスを自分で全列挙**してから着手）②机上で満足しない（**実機の描画を必ず目視**）③虚偽の断定をしない（verified / 未verified を区別）④系統的な欠陥は共通基盤で一括修正
- **手順**: 1. `scan.sh` で候補列挙（**ヒットは候補であって結論ではない**）→ 2. 実機で描画を目視（CSS 変更後は必ずキャッシュ破棄／狭幅でも確認）→ 3. 共通基盤で直し再検証
- **欠陥カタログ11型**: インライン塗りバグ（span に width → inline は寸法無視）/ チャートの識別不能 / 時間軸の張り付き / 二重送信・無反応（`disabled` は値欠落で不可、`aria-busy`）/ 破壊的操作の確認欠如 / 内部表現の露出 / ページネーション欠如 / オートフィル暴発 / 桁区切りなし / 時刻非依存の挨拶 / 空・エラー・読込状態の欠落
- **Gotchas**: CSS が反映されない＝ブラウザキャッシュ / Playwright 永続プロファイルの残タブ汚染 / `--reuse-db` のフレーク / **エージェントの禁止事項**（パスワード入力・アカウント作成・権限変更・恒久的削除）

## test-automation（55行 + references 95行）

- **目的**: 「動いた」を主観でなくテスト実行で判定する
- **種別別**: PWA/単一HTML → Playwright(Python) `tests/test_smoke.py` / Streamlit → pytest + AppTest / 純 Python → pytest
- **Playwright 最小スモーク観点**: console.error ゼロ / 主要操作 / localStorage 永続化（reload 後） / 360px で崩れない / offline で動く
- **Streamlit 観点**: 例外なく起動 / session_state キー衝突なし / LLM ラッパーをモック / **マルチテナント越境データが出ない**
- **責務分離**: LLM 出力の品質は本スキルでなく `agent-eval`。レベル定義・実行タイミングは `test-strategy`
- **規律**: テストは実装と独立に書く（Verifier 原則）。flaky は `expect`/`wait_for` で明示的に待つ。**`time.sleep` 禁止**

## done-gate（56行）

- **目的**: 「動いた」と「完了」は別物。クローズ前に機械的に確認
- **全種別共通8項目**: spec の FR 検証基準 / 自己レビュー Critical・High 残ゼロ / **テストが pass**（人力の「動作確認した」を置換）/ 秘密情報なし / CURRENT_STATE 更新 / implement.md 追記 / コミット済み / `quality_harness.py` PASS
- **変更タイプ別**: Type B（HTML/JS/CSS）は L3 全 PASS + `.ui-verified` 更新 + 実操作 + コンソールエラーなし + `uiux_review` 全状態。**pytest PASS だけで完了としない**
- **工程ライフサイクル併用時**: 出口基準充足 / `trace-check.sh` NG=0 / TBD 残ゼロ / **人間の承認3点を取得済み**
- **追加項目**: AI/LLM（agent-eval がベースライン以上・Faithfulness ゲート）/ PWA（360px・export/import・SW キャッシュ版・オフライン・Lighthouse 80+）/ 単一HTML / Streamlit
- **出力**: 未達があれば「未完了。残り N 項目」。**全達成時のみ「完了基準を満たしている」と判定**

## uiux_review（199行 + viewpoints 849行）

- **目的**: 「**作った**」を「**効いている**」として報告する失敗を防ぐ
- **根拠（実際に起きたこと・すべて利用者から指摘）**: テスト537件・スモーク5件が通る状態で結果ページが読めなかった（スクロール不可）／部品を作ったが画面に1つも適用せず「対応しました」と報告／ステップ1だけ見て「画面を確認した」と報告／同じ画面に単位の違う「件」が3種類
- **手順**:
  1. **現物を開く（省略禁止）** — 全状態＝通常（全ステップ）/ 実行中 / 失敗 / **0件** / **狭い画面（縦660px）** / ホバー・フォーカス / モーダル。1つでも欠けたら「一部のみ確認」と書く。**目視で「同じ」と判断せず `getBoundingClientRect` で実測**
  2. **観点で照合** — `references/viewpoints.md` の74観点。照合していない観点は「未検査」と書く
  3. **部品でなく画面に適用されているか数える** — `grep -c "Feedback\." target.html` が 0 なら「作った」であって「対応した」ではない
  4. **報告** — 状態の網羅 / 適用の実数 / 実測値 / 未対応 の4つが揃わなければ報告しない
- **直すときの決めごと**: 操作には必ず結果を返す / 文言（ボタンは動作名・見出しに動詞を入れない・「（任意）」を付けない）/ **数字（同じ画面に単位の違う数字を混ぜない）** / 骨格 / トークン（直値を書かない）/ アイコン（外部CDN禁止）
- **やってはいけないこと5つ**: テスト通過を理由に完了報告 / 1状態だけ見て「確認した」/ 部品を作って「対応した」/ 指摘外の改善を始める / 「良い設計とは」を語る
- **サーバ起動時の落とし穴**: 古いプロセスが残ると新プロセスが EADDRINUSE で静かに落ち、**古いコードの応答が返り続ける**。`lsof -ti:PORT` で確認
- **references/viewpoints.md（74観点）**: 8分類 — 操作の到達性13 / 操作の手応え11 / 内容の分かりやすさ19 / 表示の一貫性10 / 設定の扱いやすさ6 / 壊れにくさ6 / 資産の移管性6 / 検証の進め方3。各観点は 条件・確認方法・期待結果・**不合格の例（実際に発生したこと）**・優先度（TestRail）・25010 副特性 を持つ

## retro（38行）

- **目的**: 成果物でなく「AIDD の進め方」を改善する
- **3層の記録（混同しない）**: `CURRENT_STATE.md`（進捗）/ ADR（技術判断）/ **`lessons.md`（プロセス改善）← 本スキルの対象**
- **トリガー**: プロジェクト完了時（必須）/ 大きくつまずいた時（その場で）/ 月1の定期
- **観点（KPT 変形）**: Keep（再利用したいやり方）/ Problem（詰まった点）/ Try（キットへの反映候補）
- **キットへのフィードバック**: 発火しなかったスキル→description に言い回し追加 / 繰り返した手作業→コマンド化 / 繰り返したミス→hook or done-gate 項目 / 有効だったプロンプト→スキル本文に定着
- **現況**: `templates/lessons.md` はエントリ0件。このループは未稼働（`spec/09-findings.md` F-05）

---

# LIBRARY 層（7件）

## design-system（465行 + references 47行）★ 最大のスキル

- **目的**: AIDD ツール群のビジュアルを統一する。**値の真実源は本ファイル**、実物は `templates/tokens.css`、FW 別適用は `references/frameworks.md`
- **構成**:
  1. カラーパレット（CSS 変数）— primary `#1976D2` / surface 3段 / border・divider / text 3段 / **status（ISTQB severity 対応）** critical#D32F2F・high#F57C00・medium#FBC02D・low#388E3C・info#0288D1 ＋各 `-bg`
  2. ダークテーマ — **変数名は変えず `prefers-color-scheme` と `data-theme` で上書きのみ**。色相は変えず明度だけ上げる／背景は `rgba(色,.18〜.20)`／純黒・純白を使わない
  3. タイポグラフィ — `--text-xs`〜`--text-2xl`（7段）、行間3段
  4. スペーシング・形状 — `--space-1`〜`--space-12`（4px 倍数）、`--radius-sm/md/lg/xl/full`、`--shadow-sm/md/lg`
  5. レイアウトパターン — **永続サイドバー＋折りたたみ（既定）**：ヘッダーをサイドバーの上に横断させない／旧2ペイン（軽量ツール向け）／カードグリッド
  6. コンポーネント11種 — バッジ / スコアカード / **情報ツールチップ**（画面端はみ出し対策 `.edge-left` の実不具合あり）/ 列フィルタ＋ページネーション / トグル・セグメント / **モーダル**（開閉3経路・破壊的操作は対象名を動的に埋める）/ 通知ポップオーバー（右揃え）/ **空状態**（フィルタ0件 と 新規ユーザー で文言とボタンを変える）/ フォームエラー（**バナー＋フィールド直下の2段構え**）
  7. 折りたたみ端末レスポンシブ（360px / 768px）＋タッチターゲット 44px
  8. フォント読み込み方針 — **既定はシステムフォントスタック**。CDN は「オフライン要件がなく常時オンラインと確定している場合」の任意強化に格下げ（single-html-tool / nfr-standards との矛盾解消）
  9. **画面の作り方**（2026-08 追加）— 直値禁止（*整理開始時点で色105種・角丸11種・文字21種あった*）/ 骨格（globalbar / sidebar / topbar / content）/ **操作には必ず結果を返す**（成功＝消えるトースト、失敗＝**消えない**＋次の行動、処理中、0件、危険操作の確認。`textContent` で入れる）/ アイコン（同梱・CDN 禁止・慣用の形）/ 文言規約6条
- **references/frameworks.md**: 分担表（値＝本スキル / 実装規約＝ECC / 独創的 UI 生成＝`frontend-design` に**起動時トークンを渡す** / ブランド起こし＝`ckm:design` / 検証＝`uiux_review`）＋ 単一HTML / React+Vite（Tailwind は `theme.extend` に CSS 変数参照で登録）/ Streamlit（`config.toml` + `ui/theme.py` 集約）/ Flask・Django ＋ 検証手順（直値の残数を grep で数えて 0 を目標）
- **注**: PRD の非機能「1スキル ≦ 200行」を大きく超過（`spec/09-findings.md` F-04）

## nfr-standards（89行）

- **目的**: プロジェクト種別ごとの非機能既定値を `spec.md` へそのまま転記できる形で提供
- **PWA**: 初回ロード3G相当3秒 / Lighthouse 80+ / **カバー画面 360×820・メイン 768×1812・iPhone13Pro 390×844** / タッチ44px / SW cache-first / localStorage 全機能オフライン / **iOS の evict 対策に手動 export/import 必須** / WCAG 2.1 AA / APIキーは localStorage のみ / スキーマ version + マイグレーション
- **単一HTMLツール**: Chrome/Edge 最新 / ファイル1つで送れる / ビルド不要 / 圧縮不可 / AI 処理にローディング必須 / `innerHTML` 直接代入を避ける
- **Streamlit**: 初期表示3秒（LLM 除く）/ RAG 5秒 / **テナントIDを全DBクエリの第一キーに強制フィルタ** / 1モジュール1責務（16モジュール維持）/ `session_state` は `{module}_{name}` / LLM 呼び出しは1ラッパーに集約 / `.env` は `.gitignore`

## agent-eval（67行 + references 184行）

- **目的**: LLM 出力は非決定性なので pass/fail の単体テストでは測れない。**トレース＋データセット＋スコアラー＋回帰ゲート**の4点で評価（Weave 相当を無料スタックで）
- **スタック**: DeepEval（pytest-native, MIT）/ Langfuse セルフホスト（MIT）/ judge は**業務＝OpenAI GPT-4o系（精度重視）・個人PWA＝Gemini 無料枠 or Ollama（課金ゼロ）**
- **システム別スコアラー**: 意思決定支援（判定正確性の混同行列・**FN が業務上 Critical**／根拠の妥当性 G-Eval／JSON 妥当性）/ RAG（**Faithfulness** が主軸・Contextual Precision/Recall・引用提示率）/ マルチエージェント（層別正確性・Tool Correctness・ハンドオフ整合性）
- **運用フロー**: ゴールデンデータセット（**実運用ログから** 20-50件）→ スコアラー定義 → ベースライン記録 → 回帰ゲート → トレース常時記録
- **閾値**: FN が Critical な指標は recall 優先（例 0.95）/ ハルシネーションは faithfulness 0.9 以上を必須ゲート / **根拠を ADR に記録（恣意的に決めない）**
- **注意**: ベースライン比較は必ず同一 judge で / judge の非決定性は temperature=0 / **eval 自体の eval**（初期に数件を目視突合）/ コストは回帰 eval を CI 限定に

## code-doc-search（55行）

- **目的**: 検索ツール（Claude Code では WebSearch）を技術情報向けに最適化。追加コストゼロ
- **クエリパターン**: 公式ドキュメント / GitHub / npm / PyPI / API リファレンス / 変更履歴 / エラー解決 の7型
- **手順**: キーワードを3〜5語に絞る / バージョンが重要なら年を含める / 公式が見つかればページ取得ツールで全文 / 並列は最大3クエリ
- **出力**: ソース（公式/GitHub/その他を明記）・バージョン・要点3〜5行・コード例・注意点。**確認できなかった仕様は「未確認」と明記**

## single-html-tool（36行）

- **絶対制約**: **CSS/JS の外部分割禁止**（`<style>` `<script>` をインライン）/ 外部依存は CDN(cdnjs) のみ・オフライン要件があれば CDN も不可 / 行数が増えたら全体再生成でなく部分編集 / 実装後は必ずブラウザ確認手順を提示
- **機能パターン**: localStorage（キー `{appName}:{dataType}`・スキーマ version）/ APIキーは設定モーダル＋localStorage / AI 応答は JSON 強制＋```json フェンス除去フォールバック / エクスポート（Jira CSV / GitHub Issues / Markdown / `@media print`）/ イテレーション delta 比較

## personal-pwa（30行）

- **前提**: ゼロランニングコスト。サーバレス・無料枠のみ
- **構成**: GitHub Pages / index.html + manifest.json + sw.js の最小3ファイル / SW は cache-first＋バージョン文字列 / localStorage に version と export/import
- **AI 連携**: 既定は Gemini API 無料枠。レート制限を UI 側で抑制（debounce・手動実行ボタン）
- **デバイス**: メインは折りたたみ Android。検証基準は**キット統一値 360×820 / 768×1812**（実機カバーが約344px の機種を使う場合は追加確認）

## streamlit-rag-app（32行）

- **前提（冒頭に明記）**: 特定の業務プロジェクト（VeriRAG 基盤・16モジュール構成）が対象。**一般 Streamlit アプリへは「実装規律」節のみ流用可**（AUDIT の備考対応）
- **アーキテクチャ**: 16モジュール（1モジュール1責務）/ RAG は検索→根拠提示→回答の順を崩さない（**根拠なし回答を返さない**）/ マルチテナントはクエリ層で強制フィルタ
- **3機能**: 意思決定支援（ルール閾値→AI 判断の2段構え）/ 成果物支援（引用元を必ず表示）/ 教育支援（左:作業 右:AIレビュー）
- **実装規律**: LLM 呼び出しを1ラッパーへ集約 / プロンプトは定数モジュールか外部ファイル / `session_state` は `{module}_{name}` / **改修時は対象モジュールのみ読む**

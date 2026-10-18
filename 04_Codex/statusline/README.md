# Codex CLI の4行ステータスライン

Claudeの1〜3行目に合わせて、tmuxが端末下部に4行を確保する。Codex本体・config.tomlは変更しない。Codex Desktop / IDE拡張の画面には適用されない。

```text
gpt-6.1-sol low | project | 手動承認 | cache 12.3k | API換算 $0.03（¥5） 直近+$0.01（¥2）
current ●●●○○○○○○○ 30% ↻10/19 01:53
weekly  ●○○○○○○○○○ 10% ↻10/25 20:53
並列作業 2件 ｜ review_sources 2分10秒 ｜ agent_statusline 0分45秒
```

## 導入・起動

macOS、Python 3.11以降、tmux 3.3以降が必要。Codex CLI 0.163.0で起動を確認。

```sh
brew install tmux
bash 04_Codex/statusline/install.sh
rehash
codex
```

`~/.local/bin` をPATHの先頭に置く。導入先は `~/.local/share/codex-statusline/`、起動用リンクは `~/.local/bin/codex`。元の実行ファイルは `/opt/homebrew/bin/codex`。別の配置の場合は `CODEX_STATUS_BACKEND` に元の絶対パスを指定する（ラッパー自身を指定しない）。

起動時の選択メニューは表示せず、初期値はフルアクセス。実際にCodexへ渡す起動引数から承認モードを取得し、最初のステータス表示から反映する。起動時にモードを変更したい場合は、次のように直接指定できる。

```sh
codex --status-access manual
codex --status-access auto
codex --status-access full
codex --status-access manual resume --last
```

| モード | Codexへの指定 |
|---|---|
| 手動承認 | `-a on-request -s workspace-write -c 'approvals_reviewer="user"'` |
| 代理承認 | `--approve-for-me`（workspace-writeで自動審査） |
| フルアクセス | `--dangerously-bypass-approvals-and-sandbox`（承認とサンドボックスを無効化） |

元の `--sandbox` などを直接指定した場合は、その指定を使う。`--status-access` と直接指定の併用は拒否する。非TTY・`exec`・`login`・`--help`・`--version` などは本体にそのまま渡す。リモート接続は表示補助の対象外で、本体に渡す。

起動中は入力欄に `/permissions` と入力してEnter、↑↓で選択してEnter。実際のCLI 0.163.0の選択肢は `Ask for approval`（手動承認）、`Approve for me`（代理承認）、`Full Access`（フルアクセス）。`(current)` が現在のモード。フルアクセスでは続けて `Enable full access?` が出るので、適用する場合は `Yes, continue anyway` を選んでEnter。変更はそのセッションに適用され、次回起動時はフルアクセス、または明示した起動引数に従う。

tmux内でCodexを `--no-daemon` で起動する。CLIプロセス群が実際に開いたrolloutファイルだけを監視し、別プロジェクト・同時起動の会話とは混ぜない。履歴を再開すると、その履歴の料金を再集計する。`Ctrl-C` はCodexへ渡す。tmuxからdetachすると補助画面とそのCodexは終了する。上へスクロールするときはマウスホイール、または `Ctrl-b [`、戻るときは `q`。

## データと限界

- 2・3行目：公式App Serverの `account/rateLimits/read` を起動時と60秒ごとに読み取る。モデルへの依頼は行わない。rollout内の更新も反映する。実際の時間幅が300分／10080分の枠を表示し、未取得は `(n/a)`。リセット日時は日本時間。
- 承認モードは左から3番目に表示。設定・起動引数から初期化し、取得できたセッション情報で更新する。未取得は `承認モード未取得`。
- 1行目：モデル・推論強度・フォルダは設定から初期化し、rolloutの `turn_context` で更新。キャッシュは直近のキャッシュ読出トークン数（千単位）。文字色は灰色・左余白2桁でClaudeの表示に合わせる。Claudeのcache有効期限に相当する情報は取得できない。
- 料金はAPIトークン料金の概算。サブスクの請求額・クレジット消費ではない。キャッシュ読出、書込、出力を分けて集計し、reasoningを出力へ二重加算しない。ツール料金・地域追加料金・サブエージェント分は含まない。
- 2026-10-18確認の `gpt-6.1-sol` のみ換算する。Standardは入力$2、キャッシュ読出$0.10、書込$2.50、出力$10 / 100万トークン。入力272K超では入力・キャッシュ2倍、出力1.5倍、Fastは2倍。未知モデル・未知ティアは金額を推測せず `＋未換算あり`。円表示はClaudeと同じ固定160円/USD。model/tier変更を含む履歴の単価は現在の表を使う。
- Codex専用 `~/.codex/progress.json` があり、タスク実行中なら進捗を1行目の先頭に追加する。形式は `{"task":"作業名","step":"実装","started":1792324800,"estimate_sec":300}`。Claudeの進捗ファイルは流用しない。
- 幅を超えた1行目はtmuxが切り詰める。料金まで見たい場合は端末を広げる。
- 設定プロフィールの初期表示は従来の `[profiles.<name>]` に対応。プロジェクト別設定などがある場合、開始後の `turn_context` を正とする。

標準設定へ一時的に戻す：

```sh
CODEX_STATUS_DISABLE=1 codex
# または
/opt/homebrew/bin/codex
```

常時解除する場合は `~/.local/bin/codex` のリンクを外す。設定ファイルの復元は不要。

## 確認

```sh
cd 04_Codex/statusline
python3 -m unittest -v test_status.py
```

公式仕様：

- https://learn.chatgpt.com/docs/config-file/config-reference (`tui.status_line`)
- https://learn.chatgpt.com/docs/app-server (`account/rateLimits/read`)
- https://developers.openai.com/api/docs/models/gpt-6.1-sol （料金）

## 4行目のサブエージェント

実行中の子・孫だけを `並列作業 2件 ｜ review_sources 2分10秒 ｜ agent_statusline 0分45秒` と表示する。完了・中断した担当は消え、実行中が0件なら空行になる。状態ログを読めない場合だけ取得エラーを表示する。

担当名はJSONLのagent_path、経過時間はtask_startedのtimestampを使用し、再開時は新しい開始時刻から計る。ログだけではプロセスの異常終了を断定できないため、最終イベントの状態を使用する。

ファイルの発見は既存の表示更新中に10秒間隔で行い、本文は差分読みする。追加の常駐処理、定時実行、LLM/API呼び出しは作らない。幅を超える部分はtmuxが切り詰める。Codex Desktop / IDE拡張には適用されない。

### 起動済みCLIへの4行目追加

旧3行ラッパーで動作中のセッションには、再起動せず次の単発レンダラーをtmuxの `status-format[3]` へ指定できる。既存の `status-format[0]` 〜 `[2]` は維持し、`status` を `4` に変更する。

```sh
python3 codex_status.py --internal-agents <親セッションID> <現在のステータス保存先>/agents.json
```

レンダラー呼出時だけ動作し、子ログの読取位置と状態をJSONキャッシュへ保存する。次回は追記だけを読み、キャッシュ破損時はログから再構築する。並行呼出はファイルロックで直列化し、一意な一時ファイルから原子的に保存する。親セッションIDと保存先は現在のtmuxセッションに対応するものを指定する。

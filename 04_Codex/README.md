# 04_Codex — Codex 用の配布物

- `aidd-kit`: kit 全体の原本へ到達する Codex 用統合スキル。`$aidd-kit` で呼び出す。専門スキルの原文・付属資料を保持し、工程と検証へ案内する。
- `native-skills/`: Codex 固有スキルの真実源。生成器は共通スキル・コマンドに加えてこのディレクトリを取り込む。同名衝突はエラーとなり、既存出力を保持する。
- 全件台帳: `python3 04_Codex/native-skills/aidd-kit/scripts/kit_catalog.py inventory --output /tmp/kit-inventory.json`。非秘密ファイルの全文機械読込・ハッシュ・見出しを記録する。精読・動作検証とは区別する。`search` と `read` で原本を参照できる。

- [4行ステータスライン](statusline/README.md): Claudeの1〜3行目に合わせるCodex CLI用補助ツール。4行目にサブエージェントの担当・状態・経過時間を表示する。

- `AGENTS.md.template`: 規約本体。export で `<対象>/AGENTS.md`、グローバルは `~/.codex/AGENTS.md` に置く（Claude Code も `CLAUDE.md` の `@AGENTS.md` で同じ本体を読む）
- Codex は `~/.codex/AGENTS.md`、次にプロジェクトルートから作業ディレクトリまでの各階層の `AGENTS.md` を連結して読む（出典: https://learn.chatgpt.com/codex/agent-configuration/agents-md）
- スキル: Codex は `$REPO_ROOT/.agents/skills/<名前>/SKILL.md` と `$HOME/.agents/skills/` を読む（出典: https://learn.chatgpt.com/codex/build-skills）。形式は `03_ClaudeCode/skills/` と同じ。export で `<対象>/.agents/skills/`、install で `~/.agents/skills/` に配る
- 未確認: カスタムプロンプトと `config.toml` の配置・項目。公式ドキュメントで確認してから、ここに置く
- **スキル（Codex 用）**: `skills/` は `build_codex_skills.py` が `03_ClaudeCode/skills/`、`commands/`（`cmd-<名前>` として）、`03_ClaudeCode/agents/`（`agent-<名前>`。tools・model は落とし、他エージェントの起動は `$agent-<名前>` に読み替える）、`02_共通/rules/`（`rules-<名前>`。暗黙呼び出しは absolute-rules・speed-harness だけ）、出力スタイル（`03_ClaudeCode/output-styles/` があれば `style-<名前>`）、`native-skills/` から生成する。生成名の重複と native-skills との衝突はエラー。各スキルに `agents/openai.yaml` の `interface`（display_name・short_description）と `policy`（allow_implicit_invocation）を付ける。`$名前` で呼び出せる。直接編集せず、元を直して再生成する。同期は回帰テスト（test-install）で検査。`skills-manifest.json` にスキルごとのファイル数と sha256 を書き、`--check` が照合する（生成元の無い配布先ではマニフェストとの照合だけ）。`disable-model-invocation: true` のスキルは `policy.allow_implicit_invocation: false`。
- **hooks（Codex 用）**: [hooks/README.md](hooks/README.md)。破壊操作・ゲートの無断実行・実装モード中の再探索を Codex hook で止める（`hooks/install.sh`）

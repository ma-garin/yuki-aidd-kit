# 04_Codex — Codex 用の配布物

- `AGENTS.md.template`: 規約本体。export で `<対象>/AGENTS.md`、グローバルは `~/.codex/AGENTS.md` に置く（Claude Code も `CLAUDE.md` の `@AGENTS.md` で同じ本体を読む）
- Codex は `~/.codex/AGENTS.md`、次にプロジェクトルートから作業ディレクトリまでの各階層の `AGENTS.md` を連結して読む（出典: https://learn.chatgpt.com/codex/agent-configuration/agents-md）
- スキル: Codex は `$REPO_ROOT/.agents/skills/<名前>/SKILL.md` と `$HOME/.agents/skills/` を読む（出典: https://learn.chatgpt.com/codex/build-skills）。形式は `03_ClaudeCode/skills/` と同じ。export で `<対象>/.agents/skills/`、install で `~/.agents/skills/` に配る
- 未確認: カスタムプロンプトと `config.toml` の配置・項目。公式ドキュメントで確認してから、ここに置く
- **スキル（Codex 用）**: `skills/` は `build_codex_skills.py` が `03_ClaudeCode/skills/`（21）と `commands/`（19。`cmd-<名前>` として）から生成する。各スキルに `agents/openai.yaml`（display_name・short_description・allow_implicit_invocation）を付ける。`$名前` で呼び出せる。直接編集せず、元を直して再生成する。同期は回帰テスト（test-install）で検査

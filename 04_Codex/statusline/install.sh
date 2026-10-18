#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
target_dir="$HOME/.local/share/codex-statusline"
launcher="$HOME/.local/bin/codex"
if [[ -e "$launcher" || -L "$launcher" ]]; then
  if [[ ! -L "$launcher" || "$(readlink "$launcher")" != "$target_dir/codex_status.py" ]]; then
    echo "既存の $launcher があるため停止しました。上書きしていません。" >&2
    exit 1
  fi
fi
command -v tmux >/dev/null || { echo '先に brew install tmux を実行してください。' >&2; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11以降が必要です"'
mkdir -p "$target_dir" "$HOME/.local/bin"
if [[ -f "$target_dir/codex_status.py" ]]; then
  cp -p "$target_dir/codex_status.py" "$target_dir/codex_status.py.previous"
fi
install -m 755 "$source_dir/codex_status.py" "$target_dir/codex_status.py"
install -m 644 "$source_dir/README.md" "$target_dir/README.md"
if [[ ! -L "$launcher" ]]; then
  ln -s "$target_dir/codex_status.py" "$launcher"
fi
echo "導入済み: $launcher"
echo '次の通常のターミナルで codex を実行してください（必要なら rehash）。'

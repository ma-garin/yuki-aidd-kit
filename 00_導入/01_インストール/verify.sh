#!/bin/bash
# verify.sh — インストール確認
# チェックリストはリポジトリ実体（03_ClaudeCode/ の skills/ commands/ agents/ hooks/）から自動導出する。
# 資産を追加してもこのファイルの更新は不要（Roadmap M6 で決定）。
# 末尾の [設定の監査]（B-24 B06）は merge 後の設定を読むだけで点検する（書き換えない）。対象は
# ~/.claude/settings(.local).json・~/.claude.json の mcpServers・プロジェクト（AIDD_VERIFY_PROJECT、既定はカレント）の
# .claude/settings(.local).json と .mcp.json。
#   NG（exit 1）: defaultMode の bypassPermissions ／ permissions.allow の Bash(*)（すべての Bash）／
#                 hook・MCP の command が取得物をシェルへ流す（curl … | sh の形）／ 既知形式の秘密値（secret_patterns の値パターン）
#   WARN        : allow の Bash(rm…)・Bash(sudo…)・Write(*) ／ hook がプロジェクトと ~/.claude の外のスクリプトを呼ぶ ／
#                 MCP の command が npx -y で @scope の無いパッケージ
#   秘密値は場所と型だけを出す（値は出さない）。会話履歴（~/.claude/projects 等）は読まない。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
OK=0; NG=0; AUDIT_NG=0; AUDIT_WARN=0

check() {
  if [ -e "$2" ]; then echo "  ✅ $1"; OK=$((OK+1)); else echo "  ❌ $1（未配置: $2）"; NG=$((NG+1)); fi
}

echo "=== AIDD Kit インストール確認 ==="
if [ -f "$CLAUDE_DIR/KIT_VERSION" ]; then echo "導入済みの版: $(cat "$CLAUDE_DIR/KIT_VERSION")"; fi
echo "リポジトリの版: $(cat "$KIT_DIR/VERSION" 2>/dev/null || echo unknown) $(git -C "$KIT_DIR" rev-parse --short HEAD 2>/dev/null || echo -)"
echo "[グローバル設定]"
check "CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
check "AGENTS.md（CLAUDE.md が @AGENTS.md で import）" "$CLAUDE_DIR/AGENTS.md"
check "settings.json" "$CLAUDE_DIR/settings.json"

echo "[スキル]"
for d in "$KIT_DIR/03_ClaudeCode/skills/"*/; do
  s=$(basename "$d")
  check "$s" "$CLAUDE_DIR/skills/$s/SKILL.md"
done

echo "[コマンド]"
for f in "$KIT_DIR/03_ClaudeCode/commands/"*.md; do
  c=$(basename "$f" .md)
  check "/$c" "$CLAUDE_DIR/commands/$c.md"
done

echo "[エージェント]"
for f in "$KIT_DIR/03_ClaudeCode/agents/"*.md; do
  a=$(basename "$f" .md)
  check "$a" "$CLAUDE_DIR/agents/$a.md"
done

echo "[Hooks]"
for f in "$KIT_DIR/03_ClaudeCode/hooks/"*.sh "$KIT_DIR/03_ClaudeCode/hooks/"*.py; do
  h=$(basename "$f")
  check "$h" "$CLAUDE_DIR/hooks/$h"
done

echo "[判定スクリプト]"
check "scripts/check_approval.py（工程承認ゲートの判定。block-phase.py の探索先）" "$CLAUDE_DIR/scripts/check_approval.py"
check "scripts/phase-hash.py（承認を版に縛る。check_approval.py が隣を参照する）" "$CLAUDE_DIR/scripts/phase-hash.py"

echo "[Rules]"
for f in "$KIT_DIR/02_共通/rules/"*.md; do
  n=$(basename "$f")
  if find "$CLAUDE_DIR/rules" -name "$n" 2>/dev/null | grep -q .; then
    echo "  ✅ rules/$n"; OK=$((OK+1))
  else
    echo "  ❌ rules/${n}（未配置: $CLAUDE_DIR/rules/**/${n}）"; NG=$((NG+1))
  fi
done

echo "[設定の監査（過大な許可・危険な hook・MCP 定義・平文の秘密値）]"
AUDIT_OUT=$(AIDD_VERIFY_PROJECT="${AIDD_VERIFY_PROJECT:-$PWD}" python3 - "$KIT_DIR/03_ClaudeCode/hooks" <<'PY'
import json, os, re, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
try:
    import secret_patterns as sp
except Exception:
    sp = None
home = Path(os.environ.get("HOME", str(Path.home())))
proj = Path(os.environ["AIDD_VERIFY_PROJECT"]).resolve()
claude = home / ".claude"
PIPE_SHELL = re.compile(
    r"\b(?:curl|wget)\s+[^|\s][^|\n]*\|\s*(?:sudo\s+(?:-\S+\s+)*)?(?:(?:ba|z|da|k)?sh|python[0-9.]*|node|perl)\b"
    r"|\b(?:ba|z|da|k)?sh\s+(?:-s\s+)?<\(\s*(?:curl|wget)\b|\b(?:ba|z|da|k)?sh\s+-c\s+[\"']?\$\(\s*(?:curl|wget)\b")
SCRIPT = re.compile(r"(?:~|\$\{?\w+\}?)?[\w./-]*\.(?:py|sh|js|mjs|cjs|ts|rb|pl)\b")
NPX = re.compile(r"\bnpx\s+(?:-y|--yes)\s+(?:-\S+\s+)*(\S+)")


def short(p):
    s = str(p)
    return "~" + s[len(str(home)):] if s.startswith(str(home) + "/") else s


def outside(path_s):
    """hook が呼ぶスクリプトがプロジェクトと ~/.claude の外か。変数で指す場所は分からないので外として扱う。"""
    t = path_s
    if t.startswith(("$CLAUDE_PROJECT_DIR", "${CLAUDE_PROJECT_DIR}")):
        return False
    for v in ("${HOME}", "$HOME", "~"):
        if t.startswith(v + "/"):
            t = str(home) + t[len(v):]
            break
    if t.startswith("$"):
        return True
    if not t.startswith("/"):
        return False   # 相対パス＝プロジェクトの中
    rp = Path(os.path.normpath(t))
    for base in (proj, claude, claude.resolve()):
        try:
            rp.relative_to(base)
            return False
        except ValueError:
            pass
    return True


def servers(d):
    out = []
    if isinstance(d, dict):
        if isinstance(d.get("mcpServers"), dict):
            out += [(n, v) for n, v in d["mcpServers"].items() if isinstance(v, dict)]
        if isinstance(d.get("projects"), dict):
            for pv in d["projects"].values():
                if isinstance(pv, dict) and isinstance(pv.get("mcpServers"), dict):
                    out += [(n, v) for n, v in pv["mcpServers"].items() if isinstance(v, dict)]
    return out


def audit(path, mcp_only=False):
    ng, warn = [], []
    try:
        raw = path.read_text(encoding="utf-8")
        d = json.loads(raw)
    except (OSError, ValueError) as e:
        return [f"JSON として読めない（{e.__class__.__name__}。判定不能は不合格）"], []
    if mcp_only:   # ~/.claude.json は MCP の定義だけを見る（履歴などは読まない）
        raw = json.dumps([v for _n, v in servers(d)], ensure_ascii=False, indent=1)
    if sp is None:
        ng.append("秘密値の検査部品 secret_patterns.py が無い（判定不能は不合格）")
    else:
        for name, _no in sp.find_secret_values(raw):
            ng.append(f"平文の秘密値（{name}）を含む。値は環境変数や鍵管理へ移す")
    if not mcp_only and isinstance(d, dict):
        perms = d.get("permissions") if isinstance(d.get("permissions"), dict) else {}
        if "bypassPermissions" in (perms.get("defaultMode"), d.get("defaultMode")):
            ng.append("defaultMode が bypassPermissions（許可確認を全部飛ばす）")
        for item in perms.get("allow") or []:
            if not isinstance(item, str):
                continue
            t = item.replace(" ", "")
            if t in ("Bash", "Bash(*)", "Bash(:*)"):
                ng.append(f"permissions.allow に {item}（すべての Bash を許す）")
            elif t.startswith(("Bash(rm", "Bash(sudo")) or t in ("Write", "Write(*)"):
                warn.append(f"permissions.allow に {item}（広い。範囲を絞る）")
        hooks = d.get("hooks") if isinstance(d.get("hooks"), dict) else {}
        for ev, entries in hooks.items():
            for e in entries if isinstance(entries, list) else []:
                for h in (e.get("hooks") or []) if isinstance(e, dict) else []:
                    cmd = str(h.get("command", "")) if isinstance(h, dict) else ""
                    if PIPE_SHELL.search(cmd):
                        ng.append(f"hooks.{ev} の command が取得物をシェルへ流す（curl … | sh の形）")
                    for m in SCRIPT.finditer(cmd):
                        if outside(m.group(0)):
                            warn.append(f"hooks.{ev} がプロジェクトと ~/.claude の外のスクリプトを呼ぶ（{m.group(0)}）")
    for n, v in servers(d):
        cmd = " ".join(str(x) for x in [v.get("command", "")] + list(v.get("args") or []) if x)
        if PIPE_SHELL.search(cmd):
            ng.append(f"MCP {n} の command が取得物をシェルへ流す")
        m = NPX.search(cmd)
        if m and not m.group(1).startswith("@"):
            warn.append(f"MCP {n} が npx -y で @scope の無いパッケージ（{m.group(1)}）を取得して実行（出所と版を確かめる）")
    return ng, warn


targets = [(claude / "settings.json", False), (claude / "settings.local.json", False), (home / ".claude.json", True),
           (proj / ".claude" / "settings.json", False), (proj / ".claude" / "settings.local.json", False),
           (proj / ".mcp.json", False)]
seen = set()
for p, mcp_only in targets:
    if not p.is_file() or p.resolve() in seen:
        continue
    seen.add(p.resolve())
    ng, warn = audit(p, mcp_only)
    label = short(p) + ("（mcpServers）" if mcp_only else "")
    for x in dict.fromkeys(ng):
        print(f"NG\t{label}: {x}")
    for x in dict.fromkeys(warn):
        print(f"WARN\t{label}: {x}")
    if not ng and not warn:
        print(f"OK\t{label}: 問題なし")
PY
)
AUDIT_RC=$?
if [ "$AUDIT_RC" -ne 0 ]; then
  echo "  ❌ 設定の監査を実行できない（python3 が exit $AUDIT_RC。判定不能は不合格）"; NG=$((NG+1)); AUDIT_NG=$((AUDIT_NG+1))
fi
while IFS=$'\t' read -r kind msg; do
  case "$kind" in
    NG)   echo "  ❌ $msg"; NG=$((NG+1)); AUDIT_NG=$((AUDIT_NG+1)) ;;
    WARN) echo "  ⚠ $msg"; AUDIT_WARN=$((AUDIT_WARN+1)) ;;
    OK)   echo "  ✅ $msg"; OK=$((OK+1)) ;;
  esac
done <<< "$AUDIT_OUT"

echo ""
echo "結果: OK=$OK / NG=$NG（うち設定の監査 $AUDIT_NG）／ 警告=$AUDIT_WARN"
if [ "$NG" -eq 0 ]; then echo "✅ 全て正常"; exit 0; fi
[ "$AUDIT_NG" -gt 0 ] && echo "⚠ 設定の監査で NG（bypassPermissions・Bash(*)・curl|sh の hook・平文の秘密値）。上の ❌ を直す（install.sh では直らない）"
[ "$NG" -gt "$AUDIT_NG" ] && echo "⚠ 未配置あり。install.shを再実行してください"
exit 1

#!/bin/bash
# test-plugin-manifest.sh — .claude-plugin/{plugin,marketplace,hooks}.json の回帰テスト
# JSON が妥当／必須キーがある／参照先パスが実在する／hooks の全 command が実在ファイルを指す、を確かめる。
# 仕様: https://code.claude.com/docs/en/plugins-reference ・ https://code.claude.com/docs/en/plugin-marketplaces
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }

OUT=$(python3 - "$KIT_DIR" <<'PY'
import json, os, re, sys
root = sys.argv[1]; cp = os.path.join(root, ".claude-plugin")
def r(ok, msg, why=""): print(("OK\t" if ok else "NG\t") + msg + "\t" + why)
def load(n):
    try: d = json.load(open(os.path.join(cp, n), encoding="utf-8")); r(True, f"{n} が JSON として妥当"); return d
    except Exception as e: r(False, f"{n} が JSON として妥当", str(e)); return None
def path_ok(label, p):
    if not isinstance(p, str) or not p.startswith("./"): return r(False, label, f"'./' 始まりでない: {p}")
    if ".." in p.split("/"): return r(False, label, f"'..' を含む: {p}")
    r(os.path.exists(os.path.join(root, p)), label, f"無い: {p}")
p = load("plugin.json"); m = load("marketplace.json"); h = load("hooks.json")
ver = open(os.path.join(root, "VERSION"), encoding="utf-8").read().strip()
if p:
    r(p.get("name") == "yuki-aidd-kit", "plugin.json の name が yuki-aidd-kit", str(p.get("name")))
    r(p.get("version") == ver, "plugin.json の version が VERSION と一致", f"{p.get('version')} != {ver}")
    for k in ("skills", "commands", "agents", "hooks", "outputStyles"):
        v = p.get(k)
        if v is None: r(False, f"plugin.json に {k} がある", "無い"); continue
        for x in (v if isinstance(v, list) else [v]): path_ok(f"plugin.json {k} の参照先が実在: {x}", x)
    for a in p.get("agents", []): r(a.endswith(".md"), f"agents は .md ファイル: {a}", a)
    sk = os.path.join(root, "03_ClaudeCode/skills")
    for d in sorted(os.listdir(sk)) if os.path.isdir(sk) else []:
        if os.path.isdir(os.path.join(sk, d)) and not d.startswith(("_", ".")):
            r(os.path.isfile(os.path.join(sk, d, "SKILL.md")), f"skill {d} に SKILL.md がある", d)
if m:
    for k in ("name", "owner", "plugins"): r(k in m, f"marketplace.json に {k} がある", "無い")
    r(isinstance(m.get("owner"), dict) and "name" in m["owner"], "marketplace.json の owner.name がある", "")
    for e in m.get("plugins", []):
        r("name" in e and "source" in e, f"plugins 要素に name・source がある: {e.get('name')}", "")
        if p: r(e.get("name") == p.get("name"), "エントリ名とマニフェスト名が一致", f"{e.get('name')} != {p.get('name')}")
        s = e.get("source")
        if isinstance(s, str): r(s.startswith("./") and ".." not in s and os.path.isdir(os.path.join(root, s)), f"source が実在ディレクトリ: {s}", s)
if h:
    r(isinstance(h.get("hooks"), dict), "hooks.json がトップレベル hooks で包まれている", "")
    n = 0
    for ev, groups in (h.get("hooks") or {}).items():
        for g in groups:
            for hk in g.get("hooks", []):
                c = hk.get("command", ""); n += 1
                r("~/.claude" not in c, f"{ev}: ~/.claude を参照しない: {c}", c)
                mm = re.search(r'"?\$\{CLAUDE_PLUGIN_ROOT\}"?(/\S+)', c)
                if not mm: r(False, f"{ev}: ${{CLAUDE_PLUGIN_ROOT}} を使う: {c}", c); continue
                f = mm.group(1).lstrip("/")
                r(os.path.isfile(os.path.join(root, f)), f"{ev}: command の実体が実在: {f}", f)
    r(n > 0, "hooks.json に command が 1 件以上ある", "0 件")
PY
)
while IFS=$'\t' read -r st msg why; do
  [ -z "$st" ] && continue
  [ "$st" = OK ] && ok "$msg" || ng "$msg" "$why"
done <<< "$OUT"
echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ]

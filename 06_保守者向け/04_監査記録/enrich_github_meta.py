#!/usr/bin/env python3
"""EXTERNAL-REF-github-*.csv の「★/最終更新」列を GitHub GraphQL で埋める（手元の PC で実行する）。

Claude Code on the web のセッションは GitHub API を自分のリポジトリにしか使えないため、ここでは取れない。
手元で `gh auth login` 済みなら 100 件ずつ問い合わせる（2 万件で約 210 回）。

  python3 enrich_github_meta.py EXTERNAL-REF-github-2026-09.csv            # 上書き
  python3 enrich_github_meta.py EXTERNAL-REF-github-2026-09.csv out.csv    # 別ファイルへ
"""
import csv, json, subprocess, sys

COL, KEY, BATCH = "★/最終更新", "リポジトリ", 100


def query(repos):
    parts = []
    for i, r in enumerate(repos):
        owner, _, name = r.partition("/")
        parts.append(f'r{i}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) '
                     "{ stargazerCount pushedAt isArchived }")
    q = "query {" + " ".join(parts) + "}"
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], capture_output=True, text=True)
    # 存在しないリポがあると errors 付きで返るが、data は他の分を含むので捨てない
    return (json.loads(out.stdout or "{}").get("data") or {})


def main():
    src = sys.argv[1]; dst = sys.argv[2] if len(sys.argv) > 2 else src
    with open(src, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh)); fields = list(rows[0].keys())
    todo = [r for r in rows if not r.get(COL)]
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        data = query([r[KEY] for r in chunk])
        for j, r in enumerate(chunk):
            d = data.get(f"r{j}")
            r[COL] = "取得不可（削除・改名・非公開）" if d is None else \
                f"★{d['stargazerCount']} / {(d['pushedAt'] or '')[:10]}" + (" / archived" if d["isArchived"] else "")
        print(f"{min(i + BATCH, len(todo))}/{len(todo)}", file=sys.stderr)
    with open(dst, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()

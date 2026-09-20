#!/usr/bin/env python3
"""skill_route_check.py — スキルの発火（ルーティング）を機械判定する。

出所: agent-skills（addyosmani）の evals Tier 2。スキルは frontmatter の description で発火するが、
「発火すべき依頼文で本当に上位に来るか」「他のスキルの依頼文で誤発火しないか」「description 同士が似すぎていないか」を
キットは検証できていなかった（spec/09-findings.md F-13）。本スクリプトは決定論的（LLM を呼ばない）に近似する:

  1. 構造    全スキルに evals/routing/<skill>.json があり、positive ≧ 3・negative ≧ 2（不足は NG）
  2. 発火    positive の依頼文が、その skill を top_k（既定 3）以内に置く（description との文字 n-gram TF-IDF 余弦）
  3. 誤発火  negative の依頼文で、その skill が 1 位にならない。owner を書いた場合は owner がその skill より上に来る
  4. 衝突    description 同士の余弦 ≧ 0.75 は NG、≧ 0.50 は WARN（似た description は互いに奪い合う）
  5. 床      --min-rank1 N: positive のうち 1 位に来た割合（%）が N 未満なら NG（下げない。上がったら床を上げる）

語彙の近似なので意味は判定できない。落ちたときに直すのは依頼文ではなく description（発火語が足りない／広すぎる）。
日本語は文字 2-gram＋3-gram、英数は単語で数える。

使い方:
  python3 scripts/skill_route_check.py [--root DIR] [--min-rank1 N] [--json] [--explain "<依頼文>"]
  exit 0 合格 / 1 NG / 2 判定不能（skills/ が無い）
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

COLLISION_WARN = 0.50
COLLISION_ERROR = 0.75
DEFAULT_TOP_K = 3
MIN_POSITIVE = 3
MIN_NEGATIVE = 2

CJK_RE = re.compile(r"[぀-ヿ一-鿿々ー]+")
ASCII_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./+-]*")
STOP = {"の", "を", "に", "が", "は", "で", "と", "て", "た", "し", "する", "ます", "です", "こと", "この", "その", "から", "まで", "たい", "して", "へ", "も", "な", "ない", "れ", "や", "か", "い", "う"}


def frontmatter_description(text: str) -> tuple[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return "", ""
    name = desc = ""
    for line in m.group(1).splitlines():
        if line.startswith("name:"):
            name = line[5:].strip().strip("'\"")
        elif line.startswith("description:"):
            desc = line[12:].strip().strip("'\"")
    return name, desc


def tokens(text: str) -> list[str]:
    text = text.lower()
    out: list[str] = []
    for w in ASCII_WORD_RE.findall(text):
        if len(w) >= 2:
            out.append(w)
    for run in CJK_RE.findall(text):
        for n in (2, 3):
            for i in range(len(run) - n + 1):
                g = run[i:i + n]
                if g in STOP:
                    continue
                out.append(g)
    return out


class Corpus:
    def __init__(self, docs: dict[str, str]) -> None:
        self.names = list(docs)
        self.tf = {n: Counter(tokens(t)) for n, t in docs.items()}
        df: Counter = Counter()
        for c in self.tf.values():
            df.update(set(c))
        n = len(docs)
        self.idf = {t: math.log((n + 1) / (d + 1)) + 1.0 for t, d in df.items()}
        self.vec = {n: self._vec(c) for n, c in self.tf.items()}

    def _vec(self, c: Counter) -> dict[str, float]:
        v = {t: (1 + math.log(f)) * self.idf.get(t, math.log(len(self.names) + 1) + 1.0) for t, f in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def rank(self, prompt: str) -> list[tuple[str, float]]:
        q = self._vec(Counter(tokens(prompt)))
        scores = []
        for n in self.names:
            v = self.vec[n]
            s = sum(w * v.get(t, 0.0) for t, w in q.items())
            scores.append((n, s))
        scores.sort(key=lambda x: (-x[1], x[0]))
        return scores

    def similarity(self, a: str, b: str) -> float:
        va, vb = self.vec[a], self.vec[b]
        return sum(w * vb.get(t, 0.0) for t, w in va.items())


def load_skills(root: Path) -> dict[str, str]:
    docs = {}
    for p in sorted((root / "skills").glob("*/SKILL.md")):
        name, desc = frontmatter_description(p.read_text(encoding="utf-8", errors="replace"))
        docs[p.parent.name] = f"{name} {desc}"
    return docs


def load_cases(root: Path) -> dict[str, dict]:
    cases = {}
    for p in sorted((root / "evals" / "routing").glob("*.json")):
        try:
            cases[p.stem] = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            cases[p.stem] = {"_error": f"JSON でない: {e}"}
    return cases


def run(root: Path, min_rank1: int) -> tuple[list[str], list[str], dict]:
    """(ng, warn, data)"""
    ng: list[str] = []
    warn: list[str] = []
    docs = load_skills(root)
    if not docs:
        return ["skills/ にスキルが無い"], [], {}
    corpus = Corpus(docs)
    cases = load_cases(root)
    # 1. 構造
    for skill in docs:
        c = cases.get(skill)
        if c is None:
            ng.append(f"構造 {skill}: evals/routing/{skill}.json が無い（positive ≧ {MIN_POSITIVE}・negative ≧ {MIN_NEGATIVE} を書く）")
            continue
        if "_error" in c:
            ng.append(f"構造 {skill}: {c['_error']}")
            continue
        if len(c.get("positive", [])) < MIN_POSITIVE:
            ng.append(f"構造 {skill}: positive が {len(c.get('positive', []))} 件（≧ {MIN_POSITIVE}）")
        if len(c.get("negative", [])) < MIN_NEGATIVE:
            ng.append(f"構造 {skill}: negative が {len(c.get('negative', []))} 件（≧ {MIN_NEGATIVE}）")
    for skill in cases:
        if skill not in docs:
            ng.append(f"構造 {skill}: ケースはあるがスキルが無い（skills/{skill}/SKILL.md）")
    # 2. 発火 / 3. 誤発火
    pos_total = pos_rank1 = 0
    results = []
    for skill, c in cases.items():
        if skill not in docs or "_error" in c:
            continue
        for t in c.get("positive", []):
            prompt, top_k = t["prompt"], int(t.get("top_k", DEFAULT_TOP_K))
            ranking = corpus.rank(prompt)
            idx = next(i for i, (n, _) in enumerate(ranking) if n == skill)
            score = ranking[idx][1]
            pos_total += 1
            if idx == 0 and score > 0:
                pos_rank1 += 1
            hit = idx < top_k and score > 0
            results.append({"skill": skill, "kind": "positive", "prompt": prompt, "rank": idx + 1, "score": round(score, 3), "ok": hit})
            if not hit:
                top = ", ".join(f"{n}({s:.2f})" for n, s in ranking[:3] if s > 0) or "（一致なし）"
                ng.append(f"発火 {skill}: 「{prompt}」が {idx + 1} 位（top {top_k} が必要）。上位: {top} → description に発火語を足す")
        for t in c.get("negative", []):
            prompt, owner = t["prompt"], t.get("owner")
            ranking = corpus.rank(prompt)
            self_idx = next(i for i, (n, _) in enumerate(ranking) if n == skill)
            ok = True
            if self_idx == 0 and ranking[0][1] > 0:
                ok = False
                ng.append(f"誤発火 {skill}: 「{prompt}」で 1 位になった（description が広すぎる）")
            if owner:
                if owner not in docs:
                    ok = False
                    ng.append(f"誤発火 {skill}: owner `{owner}` が存在しない")
                else:
                    o_idx = next(i for i, (n, _) in enumerate(ranking) if n == owner)
                    if ranking[o_idx][1] <= 0 or o_idx > self_idx:
                        ok = False
                        ng.append(f"誤発火 {skill}: 「{prompt}」で owner `{owner}`（{o_idx + 1} 位）が自分（{self_idx + 1} 位）より下 → owner の description に発火語を足す")
            results.append({"skill": skill, "kind": "negative", "prompt": prompt, "rank": self_idx + 1, "owner": owner, "ok": ok})
    # 4. 衝突
    names = corpus.names
    collisions = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            s = corpus.similarity(a, b)
            if s >= COLLISION_ERROR:
                ng.append(f"衝突 {a} ↔ {b}: description の類似 {s:.2f} ≧ {COLLISION_ERROR}（責務分離の一文を足す）")
            elif s >= COLLISION_WARN:
                warn.append(f"衝突 {a} ↔ {b}: description の類似 {s:.2f}（≧ {COLLISION_WARN}）")
            if s >= COLLISION_WARN:
                collisions.append({"a": a, "b": b, "similarity": round(s, 3)})
    # 5. 床
    rank1_rate = round(100.0 * pos_rank1 / pos_total, 1) if pos_total else 0.0
    if min_rank1 and rank1_rate < min_rank1:
        ng.append(f"床 rank-1 率 {rank1_rate}% < {min_rank1}%（下げずに description を直す）")
    data = {"skills": len(docs), "cases": len(cases), "positive": pos_total, "rank1": pos_rank1, "rank1_rate": rank1_rate,
            "collisions": collisions, "results": results}
    return ng, warn, data


def main() -> int:
    ap = argparse.ArgumentParser(description="スキル発火の機械判定")
    ap.add_argument("--root", default=".")
    ap.add_argument("--min-rank1", type=int, default=0, help="positive が 1 位に来る割合（%%）の床。下回れば NG")
    ap.add_argument("--explain", default=None, help="この依頼文の順位を表示して終わる（description の調整用）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if not (root / "skills").is_dir():
        print("skills/ が無い（--root を確認）")
        return 2
    if a.explain:
        corpus = Corpus(load_skills(root))
        for i, (n, s) in enumerate(corpus.rank(a.explain)[:5], 1):
            print(f"{i}. {n}  {s:.3f}")
        return 0
    ng, warn, data = run(root, a.min_rank1)
    code = 1 if ng else 0
    if a.json:
        env = {"ok": code == 0, "exit": code, "data": {"ng": ng, "warn": warn, **data}, "meta": {}}
        if code:
            env["error"] = {"type": "routing.failed", "message": f"NG={len(ng)}", "hint": "落ちた依頼文ではなく description を直す（発火語を足す／責務分離の一文を足す）。依頼文を description の写しにしない",
                            "retry_argv": ["./scripts/skill-route-check.sh"]}
        print(json.dumps(env, ensure_ascii=False))
        return code
    print(f"=== スキル発火検査: {root.name} ===")
    print(f"スキル {data.get('skills', 0)} / ケース {data.get('cases', 0)} / positive {data.get('positive', 0)} 件 → rank-1 率 {data.get('rank1_rate', 0)}%")
    if ng:
        print(f"❌ NG={len(ng)}")
        for x in ng[:10]:
            print(f"  - {x}")
        if len(ng) > 10:
            print(f"  ほか {len(ng) - 10} 件")
    else:
        print("✅ NG=0")
    for x in warn:
        print(f"⚠ {x}")
    return code


if __name__ == "__main__":
    sys.exit(main())

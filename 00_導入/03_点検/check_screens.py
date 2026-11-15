#!/usr/bin/env python3
"""check_screens.py — 画面方針（ライトのみ／PC のみ／ページ全体のスクロール禁止）を実ブラウザで判定する。

NG: S01 ページ縦スクロール / S02 ページ横スクロール / S03 タブ切替後のはみ出し / S04 コンソールエラー
WARN: W01 表・一覧・ログ以外の要素内スクロール（フォームを内部スクロールで逃がしている疑い）
除外: <meta name="aidd-screen-check" content="skip"> を持つページ
exit: NG>0 → 1、判定不能 → 2、それ以外 0
"""
import argparse
import re
import sys
from pathlib import Path

SKIP_RE = re.compile(
    r'<meta[^>]*name=["\']aidd-screen-check["\'][^>]*content=["\']skip["\']'
    r'|<meta[^>]*content=["\']skip["\'][^>]*name=["\']aidd-screen-check["\']', re.I)

MEASURE_JS = """() => {
  const se = document.scrollingElement || document.documentElement;
  return {sh: se.scrollHeight, sw: se.scrollWidth, ih: innerHeight, iw: innerWidth};
}"""

INNER_SCROLL_JS = r"""() => {
  const out = [];
  const allowed = el => {
    if (el.tagName === 'TABLE' || el.querySelector('table')) return true;
    const role = (el.getAttribute('role') || '').toLowerCase();
    if (role === 'list' || role === 'log') return true;
    const cls = typeof el.className === 'string' ? el.className : '';
    return /table-wrap|list|log/.test(cls);
  };
  const sel = el => {
    if (el.id) return '#' + el.id;
    const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).filter(Boolean) : [];
    const base = el.tagName.toLowerCase() + (cls.length ? '.' + cls.join('.') : '');
    const p = el.parentElement;
    return p && p !== document.body && p !== document.documentElement ? sel(p) + ' > ' + base : base;
  };
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    const y = /(auto|scroll)/.test(cs.overflowY) && el.scrollHeight > el.clientHeight + 1;
    const x = /(auto|scroll)/.test(cs.overflowX) && el.scrollWidth > el.clientWidth + 1;
    if ((y || x) && !allowed(el)) out.push(sel(el));
  }
  return out;
}"""



def _launch(p):
    """同梱 chromium → 端末の Chrome の順で起動する。どちらも無ければ例外（判定不能＝exit 2）。"""
    try:
        return p.chromium.launch()
    except Exception:
        return p.chromium.launch(channel="chrome")

def parse_args(argv):
    ap = argparse.ArgumentParser(description="画面方針の実ブラウザ検査")
    ap.add_argument("paths", nargs="*", help="HTML ファイルまたはディレクトリ（再帰で *.html）")
    ap.add_argument("--url", action="append", default=[], help="検査する URL（複数可）")
    ap.add_argument("--viewports", default="1366x768,1920x1080")
    ap.add_argument("--out", default="./screen-check")
    return ap.parse_args(argv)


def parse_viewports(text):
    vps = []
    for part in text.split(","):
        m = re.fullmatch(r"\s*(\d+)x(\d+)\s*", part)
        if not m:
            raise ValueError(f"幅の指定が読めない: {part}（例: 1366x768）")
        vps.append((int(m.group(1)), int(m.group(2))))
    return vps


def safe_name(text):
    return re.sub(r"[^\w.-]+", "_", text).strip("_") or "page"


def collect_targets(paths, urls):
    """戻り値: (targets[(name, url)], skipped[name], errors[str], specified 数)"""
    targets, skipped, errors = [], [], []
    files = []
    for p in map(Path, paths):
        if p.is_dir():
            files.extend(sorted(p.rglob("*.html")))
        elif p.is_file():
            files.append(p)
        else:
            errors.append(f"パスが無い: {p}")
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            errors.append(f"読めない: {f}（{e}）")
            continue
        name = str(f)
        if SKIP_RE.search(text):
            skipped.append(name)
        else:
            targets.append((name, f.resolve().as_uri()))
    targets.extend((u, u) for u in urls)
    return targets, skipped, errors, len(files) + len(urls) + len(errors)


def page_overflow(page):
    m = page.evaluate(MEASURE_JS)
    found = []
    if m["sh"] > m["ih"] + 1:
        found.append(("S01", f"scrollHeight={m['sh']} > innerHeight={m['ih']}"))
    if m["sw"] > m["iw"] + 1:
        found.append(("S02", f"scrollWidth={m['sw']} > innerWidth={m['iw']}"))
    return found


def check_tabs(page):
    found = []
    tabs = page.locator("[role=tab]")
    for i in range(tabs.count()):
        tab = tabs.nth(i)
        label = (tab.inner_text(timeout=2000) or "").strip()[:30] or f"#{i + 1}"
        try:
            tab.click(timeout=2000)
        except Exception as e:  # noqa: BLE001 クリック不能なタブは記録して続ける
            found.append(("S03", label, f"クリックできない: {type(e).__name__}"))
            continue
        page.wait_for_timeout(300)
        for sid, val in page_overflow(page):
            found.append(("S03", label, f"{sid} {val}"))
    return found


def check_one(browser, name, url, vp, out_dir):
    """1 ページ×1 幅。戻り値: (ng[dict], warn[dict], error 文字列 or None)"""
    w, h = vp
    ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme="light")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc).splitlines()[0][:200]))
    vp_s = f"{w}x{h}"
    rec = lambda sid, tab, val: {"id": sid, "page": name, "vp": vp_s, "tab": tab, "value": val}
    try:
        page.goto(url, wait_until="load", timeout=15000)
    except Exception as e:  # noqa: BLE001 開けないページは判定不能
        ctx.close()
        return [], [], f"{name} @ {vp_s}: 開けない（{type(e).__name__}）"
    page.wait_for_timeout(300)
    ng = [rec(sid, "-", val) for sid, val in page_overflow(page)]
    warn = [rec("W01", "-", s) for s in page.evaluate(INNER_SCROLL_JS)]
    page.screenshot(path=str(out_dir / f"{safe_name(name)}-{vp_s}.png"))
    ng += [rec(sid, tab, val) for sid, tab, val in check_tabs(page)]
    ng += [rec("S04", "-", msg) for msg in errors]
    ctx.close()
    return ng, warn, None


def write_report(path, summary, ng, warn, errs, skipped):
    lines = ["# 画面検査レポート（check-screens）", "", summary, ""]
    for title, rows in (("NG", ng), ("WARN", warn)):
        lines += [f"## {title}（{len(rows)} 件）", ""]
        if rows:
            lines += ["| ID | ページ | 幅 | タブ | 値 |", "|---|---|---|---|---|"]
            lines += [f"| {r['id']} | {r['page']} | {r['vp']} | {r['tab']} | {r['value']} |" for r in rows]
        lines.append("")
    lines += [f"## 判定不能（{len(errs)} 件）", ""] + [f"- {e}" for e in errs] + [""]
    lines += [f"## 除外（{len(skipped)} 件）", ""] + [f"- {s}" for s in skipped] + [""]
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args):
    try:
        vps = parse_viewports(args.viewports)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright が無い。導入: pip install playwright && playwright install chromium", file=sys.stderr)
        return 2
    targets, skipped, errs, specified = collect_targets(args.paths, args.url)
    if specified == 0:
        print("検査対象が指定されていない。HTML ファイル・ディレクトリか --url を渡す", file=sys.stderr)
        return 2
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ng, warn, checked = [], [], 0
    with sync_playwright() as p:
        browser = _launch(p)
        for name, url in targets:
            ok_all = True
            for vp in vps:
                n, w, err = check_one(browser, name, url, vp, out_dir)
                ng += n
                warn += w
                if err:
                    errs.append(err)
                    ok_all = False
            checked += ok_all
        browser.close()
    return report(args, out_dir, vps, targets, skipped, errs, specified, checked, ng, warn)


def report(args, out_dir, vps, targets, skipped, errs, specified, checked, ng, warn):
    summary = (f"対象: {len(targets)} ページ × {len(vps)} 幅"
               f"（検査 {checked} / 指定 {specified}、除外 {len(skipped)}）")
    print(summary)
    print(f"NG={len(ng)} / WARN={len(warn)} / 判定不能={len(errs)}")
    for r in ng:
        print(f"  {r['id']} {r['page']} {r['vp']} タブ={r['tab']} {r['value']}")
    for r in warn:
        print(f"  {r['id']}(WARN) {r['page']} {r['vp']} {r['value']}")
    for e in errs:
        print(f"  判定不能: {e}")
    rpt = out_dir / "check-screens-report.md"
    write_report(rpt, summary, ng, warn, errs, skipped)
    print(f"詳細: {rpt}")
    if errs:
        return 2
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(run(parse_args(sys.argv[1:])))

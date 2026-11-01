#!/usr/bin/env python3
"""予実計測ツール v3。見積秒・往復数・待ちの判定・比・系統判定をすべてここで計算し、Claude の暗算と自己申告を排除する。

運用（1依頼 = 1作業）:
  est.py t0                         新規依頼の最初のツール呼び出しで実行（中断中の作業が残っていれば拒否。abort で明示的に閉じる）
  est.py plan <種別> <予定X> [外部待ち秒] [--chars 字数] [--margin 秒]   1回のみ。見積秒をログから算出（往復単価の中央値 × 往復数補正 × X + 外部待ち）。完了予定を表示
  est.py tick                       1往復に1つ。クリティカルパス上の呼び出しに同梱（同時に投げた呼び出し・外部待ち中のポーリングは数えない）（t0 の呼び出しは1往復目として自動計上）。
                                    往復間隔が閾値（max(90秒, 単価×3)）を超えたら long_gap_s に記録（実測からは引かない）。
                                    その件は往復単価の算出から除外する
  est.py ext-begin / ext-end        CI・委譲など、外部待ちの開始と終了
  est.py reest <予定X> [外部待ち秒]   再見積（1回のみ）。完了予定 = 現在 + (再見積 − 経過) + 20秒
  est.py now                        経過・進捗%・70%到達
  est.py quote <種別> <X> [外部待ち秒]  選択肢比較用の試算（状態は変えない）。応答に書く時間見積は plan/reest/quote の値だけ（est-guard フックが照合）
  est.py pause / resume             ターン末に pause、次ターンの最初に resume（pause を忘れた場合、resume が前回の記録以降を返答待ちとして除外）
  est.py end / abort [--same]       完了 / 未完。T1 の呼び出しを1往復に数える（直前の tick と同じ呼び出しなら --same）。実測 = 作業区間 − ユーザー待ち（外部待ちは実測に含め、別列に記録）
  est.py stats                      往復単価（種別別）・往復数補正・直近10件の系統判定（Σ実測/Σ見積）・未完率
"""
import csv, fcntl, json, os, shutil, statistics as stt, sys, time
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
D = os.path.dirname(os.path.abspath(__file__))
ST, LOG = os.path.join(D, "state.json"), os.path.join(D, "log.csv")

# 見積行の表示義務（est-guard フックと連携）: plan/reest の結果を「未表示」として書き出す。
# フックは、この行が SendUserMessage か最終応答に出るまで、次のツール呼び出しと終了を止める。
PENDING = os.environ.get("EST_PENDING", os.path.expanduser("~/.claude/est-pending.json"))
QUOTES = os.environ.get("EST_QUOTES", os.path.expanduser("~/.claude/est-quotes.json"))
def announce(line):
    try:
        os.makedirs(os.path.dirname(PENDING), exist_ok=True)
        with open(PENDING, "w", encoding="utf-8") as f: json.dump({"line": line, "at": int(time.time())}, f, ensure_ascii=False)
    except OSError: pass
    print(f"表示義務: 次のツール呼び出しの前に、この行をそのまま応答に出す → {line}")
COLS = ["t0", "t1", "kind", "plan_x", "unit_s", "xcorr", "ext_plan_s", "gen_s", "margin_s", "est_s", "reest_s", "actual_x",
        "user_wait_s", "ext_wait_s", "long_gap_s", "actual_s", "ratio", "result", "unfinished"]
INIT_UNIT = {k: 10.2 for k in ("UI改修", "UI新規", "コード+CI", "調査", "文書・回答", "ブラウザ操作", "外部投稿")}  # 13件の交差検証で全件範囲内（比の中央値0.98）
LINE_S = 0.22  # 生成1行あたりの秒（同上）
REPORT_S = 20
SAME_ROUND_S = 3  # 前回 tick からこの秒数以内の tick は、同時に投げた同じ往復として数えない
KINDS = set(INIT_UNIT)
now = int(time.time())
hms = lambda t: datetime.fromtimestamp(t, JST).strftime("%H:%M:%S")


def die(m):
    sys.exit("エラー: " + m)


def rows():
    return list(csv.DictReader(open(LOG))) if os.path.exists(LOG) else []


def unit_and_corr(kind):
    done = [r for r in rows() if r["kind"] == kind and int(r["actual_x"] or 0) > 0 and int(r.get("long_gap_s") or 0) == 0]
    alln = [r for r in rows() if r["unfinished"] == "0" and int(r["actual_x"] or 0) > 0]
    per = lambda r: (int(r["actual_s"]) - int(r["ext_wait_s"])) / int(r["actual_x"])
    if len(done) >= 3:
        unit, src = stt.median(per(r) for r in done), f"{kind}の実測{len(done)}件"
    else:
        unit, src = INIT_UNIT.get(kind, 23), "初期値（暫定）"
    xs = [int(r["actual_x"]) / int(r["plan_x"]) for r in done if r["unfinished"] == "0" and int(r["plan_x"] or 0) > 0]
    corr = stt.median(xs) if len(xs) >= 3 else 1.0
    return unit, corr, src, len(alln)


def load():
    if not os.path.exists(ST):
        return None
    try:
        s = json.load(open(ST)); assert isinstance(s["t0"], int); return s
    except Exception:
        shutil.move(ST, ST + f".broken.{now}"); print("警告: 状態ファイルが壊れていたため退避しました"); return None


def save(s):
    json.dump(s, open(ST, "w"))


def union(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def measure(s):
    segs = s["segs"] + ([[s["open"], now]] if s["open"] is not None else [])
    total = sum(b - a for a, b in segs)
    ov = lambda iv: sum(max(0, min(b, y) - max(a, x)) for a, b in union(iv) for x, y in segs)
    ext = s["ext"] + ([[s["eb"], now]] if s["eb"] else [])
    uw, ew = ov(s["user"]), ov(ext)
    return total - uw, uw, ew


def compute_est(kind, x, ext):
    unit, corr, src, _ = unit_and_corr(kind)
    return round(x * corr * unit + ext), unit, corr, src


def close_and_log(s, unfinished):
    if s["eb"]:
        s["ext"].append([s["eb"], now]); s["eb"] = None
    if s["open"] is not None:
        s["segs"].append([s["open"], now]); s["open"] = None
    a, uw, ew = measure(s)
    est = s["est"]
    if a < 0:
        die(f"実測が負（{a}s）。状態を確認してください")
    if unfinished or not est:
        ratio, res, unfinished = "", "未完", True
    else:
        r = a / est; ratio = round(r, 2)
        res = ("合格" if 0.67 <= r <= 1.5 else "不合格") if a >= 300 else ("合格" if abs(a - est) <= 60 else "不合格")
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(COLS)
        w.writerow([datetime.fromtimestamp(s["t0"], JST).isoformat(), hms(now), s["kind"], s["x"], s["unit"], s["corr"],
                    s["extp"], s.get("gen", 0), s.get("margin", 0), est, s["reest"] or "", s["ticks"], uw, ew, s["long"], a, ratio, res, int(unfinished)])
    os.remove(ST)
    return a, uw, ew, ratio, res


cmd, args = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
_lock = open(os.path.join(D, ".lock"), "w"); fcntl.flock(_lock, fcntl.LOCK_EX)
s = load()
if cmd == "stats":
    rs = rows(); fin = [r for r in rs if r["unfinished"] == "0"]; last = rs[-10:]
    lf = [r for r in last if r["unfinished"] == "0"]
    sa, se = sum(int(r["actual_s"]) for r in lf), sum(int(r["est_s"]) for r in lf)
    print(f"記録{len(rs)}件（完了{len(fin)}・未完{len(rs) - len(fin)}）")
    if lf:
        sr = sa / se
        print(f"直近10件: Σ実測/Σ見積={sr:.2f} 未完率={100 * (len(last) - len(lf)) // len(last)}% 系統判定="
              + ("合格" if 0.9 <= sr <= 1.1 and (len(last) - len(lf)) / len(last) <= 0.2 else "不合格"))
    for k in sorted({r["kind"] for r in fin}):
        u, c, src, _ = unit_and_corr(k); print(f"  {k}: 往復単価={u:.1f}s（{src}） 往復数補正={c:.2f}")
    sys.exit()
if cmd == "quote":
    if len(args) < 2: die("quote <種別> <予定X> [外部待ち秒]  … 選択肢比較用。状態は変えない")
    kind, x, ext = args[0], int(args[1]), int(args[2]) if len(args) > 2 else 0
    if kind not in KINDS: die(f"種別は {'/'.join(sorted(KINDS))} のいずれか")
    est, *_ = compute_est(kind, x, ext); m = max(1, round(est / 60))
    try:
        qs = json.load(open(QUOTES, encoding="utf-8")) if os.path.exists(QUOTES) else []
    except (OSError, ValueError): qs = []
    qs = [v for v in qs if time.time() - v.get("at", 0) < 6 * 3600] + [{"min": m, "at": int(time.time())}]
    try:
        os.makedirs(os.path.dirname(QUOTES), exist_ok=True); json.dump(qs, open(QUOTES, "w", encoding="utf-8"))
    except OSError: pass
    print(f"試算={m}分（{est}s）  ※応答では「{m}分」と書く（「約」は付けない）"); sys.exit()
if cmd == "t0":
    if s:
        die("前の作業が残っています。resume してから end（完了）か abort（未完）を実行してください")
    save({"t0": now, "open": now, "segs": [], "user": [], "ext": [], "eb": None, "last": now, "ticks": 1, "long": 0, "ext_hold": False,
          "est": 0, "kind": "", "x": "", "unit": "", "corr": "", "extp": 0, "reest": 0})
    print(f"T0={hms(now)}"); sys.exit()
if not s:
    die("t0 が未実行です")
if cmd in ("plan", "reest"):
    if len(args) < 2 and cmd == "plan" or len(args) < 1:
        die("plan <種別> <予定X> [外部待ち秒] / reest <予定X> [外部待ち秒]")
    if cmd == "plan":
        if s["est"]: die("見積は確定済みです。変更は reest（1回のみ）で行ってください")
        opt = lambda k: int(args[args.index(k) + 1]) if k in args else 0
        margin, chars, lines = opt("--margin"), opt("--chars"), opt("--lines")
        pos = [a for i, a in enumerate(args) if a not in ("--margin", "--chars", "--lines") and (i == 0 or args[i - 1] not in ("--margin", "--chars", "--lines"))]
        kind, x, ext = pos[0], int(pos[1]), int(pos[2]) if len(pos) > 2 else 0
        if kind not in KINDS: die(f"種別は {'/'.join(sorted(KINDS))} のいずれか")
        if x < 1 or ext < 0: die("予定X は1以上、外部待ちは0以上")
        if now - s["last"] > SAME_ROUND_S: s["ticks"] += 1; s["last"] = now
        est, unit, corr, src = compute_est(kind, x, ext)
        gen = round(chars / 1000 * 60)  # 生成速度 初期値 1,000字/分（暫定）
        if margin > 0.25 * est or margin > 300: die("余裕は素の見積の25%と300秒の小さい方まで")
        est += round(lines * LINE_S) + margin  # 生成秒は T1 後の最終応答で書くため実測に入らない。完了予定の表示にだけ加える
        s.update(est=est, kind=kind, x=x, unit=round(unit, 1), corr=round(corr, 2), extp=ext, margin=margin, gen=gen); save(s)
        print(f"見積={max(1, round(est / 60))}分（{est}s = X{x}×補正{corr:.2f}×単価{unit:.1f}s[{src}]＋外部待ち{ext}s＋生成{gen}s＋余裕{margin}s） "
              f"完了予定={hms(s['t0'] + est + gen + REPORT_S)[:5]}")
        announce(f"見積: {max(1, round(est / 60))}分（{hms(s['t0'] + est + gen + REPORT_S)[:5]} 完了予定）")
    else:
        if not s["est"]: die("plan の前に再見積はできません")
        if s["reest"]: die("再見積は1回のみです")
        x, ext = int(args[0]), int(args[1]) if len(args) > 1 else 0
        if x < 1 or ext < 0: die("予定X は1以上、外部待ちは0以上")
        est, *_ = compute_est(s["kind"], x, ext); est += s.get("margin", 0); a, _, _ = measure(s)
        s["reest"] = est; save(s)
        print(f"再見積={max(1, round(est / 60))}分（{est}s） 完了予定={hms(now + max(0, est - a) + s.get("gen", 0) + REPORT_S)[:5]}")
        announce(f"再見積: {max(1, round(est / 60))}分（{hms(now + max(0, est - a) + s.get("gen", 0) + REPORT_S)[:5]} 完了予定）")
elif cmd == "tick":
    if s["open"] is None: die("中断中です。resume してください")
    gap = now - s["last"]
    thr = max(90, (float(s["unit"]) if s["unit"] else 30) * 3)
    if gap > 600 and s["eb"] is None:
        s["user"].append([s["last"], now])
        print(f"警告: 前回の記録から{gap}s 経過（pause/resume の記録漏れ）。この間隔をユーザー返答待ちとして除外します")
    elif gap > thr and s["eb"] is None:
        s["long"] += gap
        print(f"注意: 往復間隔{gap}s が閾値{int(thr)}s を超過（承認待ちか長い生成かを区別できないため実測には含め、long_gap_s に記録。この件は往復単価の算出から除外）")
    if s["eb"] is not None:
        print("外部待ち中のため往復に数えません（ポーリング）")
    elif gap <= SAME_ROUND_S and s["ticks"] > 0:
        print("同時に投げた呼び出しとして、同じ往復に数えます")
    else:
        s["ticks"] += 1
    s["last"] = now; save(s)
    a, uw, ew = measure(s); base = s["reest"] or s["est"]
    print(f"tick#{s['ticks']} {hms(now)} 経過={a}s" + (f" 進捗={100 * a // base}%" + (" ※70%到達" if a >= .7 * base else "") if base else ""))
elif cmd == "now":
    a, uw, ew = measure(s); base = s["reest"] or s["est"]
    print(f"経過={a}s 待ち=ユーザー{uw}s/外部{ew}s 往復={s['ticks']}" + (f" 進捗={100 * a // base}%" if base else " （見積未確定）")
          + ("（中断中）" if s["open"] is None else ""))
elif cmd == "ext-begin":
    if s["eb"]: die("外部待ちはすでに開始されています")
    if now - s["last"] > SAME_ROUND_S: s["ticks"] += 1
    s["eb"] = now; s["last"] = now; save(s); print(f"外部待ち開始={hms(now)}")
elif cmd == "ext-end":
    if not s["eb"]: die("外部待ちが開始されていません")
    s["ext"].append([s["eb"], now]); s["eb"] = None; s["ticks"] += 1; s["last"] = now; save(s); print(f"外部待ち={s['ext'][-1][1] - s['ext'][-1][0]}s")
elif cmd == "pause":
    if s["open"] is None: die("すでに中断中です")
    if s["eb"]: s["ext"].append([s["eb"], now]); s["eb"] = None; s["ext_hold"] = True
    s["segs"].append([s["open"], now]); s["open"] = None; save(s); print(f"中断={hms(now)}" + ("（外部待ちは resume で再開）" if s["ext_hold"] else ""))
elif cmd == "resume":
    if s["open"] is not None:
        s["user"].append([s["last"], now])
        print(f"警告: pause が記録されていなかったため、前回の記録（{hms(s['last'])}）から現在までの{now - s['last']}s をユーザー返答待ちとして除外します")
    if s["open"] is None: s["open"] = now
    s["last"] = now
    if s.get("ext_hold"): s["eb"] = now; s["ext_hold"] = False
    save(s); print(f"再開={hms(now)}")
elif cmd in ("end", "abort"):
    gap = now - s["last"]; thr = max(90, (float(s["unit"]) if s["unit"] else 30) * 3)
    if s["open"] is not None and gap > thr and s["eb"] is None:
        s["long"] += gap; print(f"注意: 最後の記録から{gap}s 経過。long_gap_s に記録し、この件は往復単価の算出から除外")
    if "--same" not in args and gap > SAME_ROUND_S: s["ticks"] += 1
    if cmd == "end" and not s["est"]: print("警告: 見積が未確定のため未完として記録します")
    a, uw, ew, r, res = close_and_log(s, cmd == "abort")
    print(f"T0={hms(s['t0'])} T1={hms(now)} 待ち=ユーザー{uw}s/外部{ew}s 実測={a}s 往復={s['ticks']} 比={r} {res}")
else:
    die(f"不明なコマンド: {cmd}")

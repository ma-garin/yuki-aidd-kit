# AIDD Kit

> Full documentation is in Japanese: [README.md](README.md)

**A Claude Code / Codex kit that brings the quality gates of a third-party QA engineer into AI-driven development.**

Rules are enforced and measured by hooks and scripts, not requested in prose. Four things other Claude Code config collections don't have:

1. **Estimate calibration against actuals** — `tool-timer.py` / `est.py` clock actual time, and a calibration factor (median of actual/estimate) is grown from history and injected into the next estimate
2. **Phase approval gate** — `check-approval` and `phase-hash` bind approval records to a content hash of the deliverables; without approval, or after post-approval edits, writes to the next phase are denied (`block-phase.py`)
3. **Design lint `check_design.py`** — mechanically checks raw values, undefined tokens, a11y (alt, labels, lang, contrast ratio) and AI-default styling (decorative gradients, emoji icons)
4. **Hook decision log** — every deny/warn is appended to `.claude/hook-decisions.log`; `token_report.py --hooks` counts overrides as a false-positive indicator

## Try it in 30 seconds

```bash
git clone <this repository> && cd yuki-aidd-kit
./00_導入/01_インストール/install.sh   # install into ~/.claude
./00_導入/01_インストール/verify.sh    # verify (exit 1 if NG > 0)
```

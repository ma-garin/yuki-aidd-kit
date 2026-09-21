"""streamlit_theme.py — AIDD Design System を Streamlit に当てる（見た目の追加は必ずここ1箇所に集約する）。

値の真実源: 02_共通/ひな形/tokens.css ／ 部品: 02_共通/ひな形/ui/components.css ／ 規律: skills/design-system/SKILL.md

配置:
    <project>/ui/streamlit_theme.py   ← このファイル
    <project>/ui/tokens.css           ← 02_共通/ひな形/tokens.css をコピー
    <project>/ui/components.css       ← 02_共通/ひな形/ui/components.css をコピー
    <project>/.streamlit/config.toml  ← 02_共通/ひな形/ui/streamlit-config.toml をコピー

使い方（各ページの最初に1回。Streamlit は再実行のたびに DOM を組み直すので毎回呼ぶ）:
    from ui.streamlit_theme import apply_theme, badge, empty_state, kpi, callout
    apply_theme()
    st.markdown(badge("high", "High"), unsafe_allow_html=True)
    st.markdown(kpi("今週のレビュー", "128", "+12 前週比", trend="up"), unsafe_allow_html=True)
    if not rows:
        st.markdown(empty_state("まだレビュー結果がありません", "URL を登録して最初のレビューを実行してください"), unsafe_allow_html=True)

規律: 各ページで st.markdown('<style>…') を散発させない。文字列は必ず html.escape を通す（サーバ由来の文言が混ざる）。
severity は列挙（critical / high / medium / low / info）。色名を引数に出さない。
"""
from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

_HERE = Path(__file__).resolve().parent
TOKENS_CSS = _HERE / "tokens.css"
COMPONENTS_CSS = _HERE / "components.css"
SEVERITIES = ("critical", "high", "medium", "low", "info")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def apply_theme(extra_css: str = "") -> None:
    """tokens.css と components.css を <style> として注入する。プロジェクト固有の追加 CSS は extra_css に渡す。"""
    css = "\n".join(s for s in (_read(TOKENS_CSS), _read(COMPONENTS_CSS), extra_css) if s)
    if not css:
        st.warning("ui/tokens.css が見つかりません。02_共通/ひな形/tokens.css をコピーしてください。")
        return
    # Streamlit 自身の部品にもトークンを効かせる最小セット（ボタン・入力・データフレームのヘッダ）
    css += """
    .stButton > button { border-radius: var(--radius-md); font-weight: 600; min-height: var(--tap-min); }
    .stButton > button[kind="primary"] { background: var(--color-primary); color: var(--color-on-primary); border-color: var(--color-primary); }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div { border-radius: var(--radius-sm); }
    """
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _sev(severity: str) -> str:
    s = severity.lower()
    if s not in SEVERITIES:
        raise ValueError(f"severity は {SEVERITIES} のいずれか: {severity!r}")
    return s


def badge(severity: str, text: str) -> str:
    """severity バッジ（ピル型）。"""
    return f'<span class="badge badge-{_sev(severity)}">{html.escape(text)}</span>'


def kpi(label: str, value: str, delta: str = "", trend: str = "") -> str:
    """KPI カード。trend は "up" / "down" / ""（良し悪しの色は trend だけで決める）。"""
    cls = {"up": " up", "down": " down"}.get(trend, "")
    delta_html = f'<span class="kpi-delta{cls}">{html.escape(delta)}</span>' if delta else ""
    return (f'<div class="card kpi"><span class="kpi-label">{html.escape(label)}</span>'
            f'<span class="kpi-value">{html.escape(value)}</span>{delta_html}</div>')


def empty_state(title: str, description: str = "") -> str:
    """0 件表示。枠だけ残さず、次にやることを文で示す。ボタンは st.button を直後に置く。"""
    desc = f"<p>{html.escape(description)}</p>" if description else ""
    return f'<div class="empty-state"><h4>{html.escape(title)}</h4>{desc}</div>'


def callout(severity: str, text: str) -> str:
    """本文内のエラー・注意（alert() や st.error の代わりに使うと見た目が揃う）。"""
    return f'<div class="callout callout--{_sev(severity)}"><span>{html.escape(text)}</span></div>'

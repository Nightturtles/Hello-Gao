"""Charts (spec section 11).  matplotlib, PNG, dpi 150.

Style: surface #fcfcfb, gridlines #e1e0d9 @ 0.5, spines #c3c2b7 (top/right removed), ink #0b0b0b / #52514e / #898781,
series colours blue #2a78d6 -> orange #eb6834 -> aqua #1baf7a in that order, lines ~1.2, dashed thresholds in muted
ink, legend whenever there are 2+ series, text never takes a series colour, a single y-scale per panel (no twin axes).
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import config  # noqa: E402

SURFACE, GRID, SPINE = "#fcfcfb", "#e1e0d9", "#c3c2b7"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
LW = 1.2

REGIME_LINES = [("2020-03-02", "COVID"), ("2022-01-03", "Post-COVID")]
THRESHOLDS = {  # rule -> list of (value, label)
    "coint_ols": [2.0, -2.0, 3.5, -3.5],
    "coint_kalman": [2.0, -2.0, 3.5, -3.5],
    "leadlag": [1.0, -1.0],
    "leadlag_rev": [1.0, -1.0],
    "rotation": [],
}
SIGNAL_LABEL = {
    "coint_ols": "z-score of log spread (60d)",
    "coint_kalman": "z-score of Kalman innovation (60d)",
    "leadlag": "leader k-day return z (z_x)",
    "leadlag_rev": "leader k-day return z (z_x)",
    "rotation": "20d return gap R_A - R_B",
}


def _style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(SPINE)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.xaxis.label.set_color(INK2)
    ax.yaxis.label.set_color(INK2)
    ax.xaxis.label.set_size(9)
    ax.yaxis.label.set_size(9)


def _legend_below(ax, ncol=3, y=-0.16):
    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, y), frameon=False, fontsize=8, ncol=ncol)
    for t in leg.get_texts():
        t.set_color(INK2)


def _regime_lines(ax, x0, x1, label_axes):
    """Thin vertical lines at the regime boundaries; small muted labels centred on each regime span."""
    bounds = [pd.Timestamp(config.REGIMES["pre"][0]), pd.Timestamp(config.REGIMES["covid"][0]),
              pd.Timestamp(config.REGIMES["post"][0]), x1]
    names = ["Pre-COVID", "COVID", "Post-COVID"]
    total = (x1 - x0).days
    for t in bounds[1:3]:
        if x0 < t < x1:
            ax.axvline(t, color=MUTED, linewidth=0.6)
    if label_axes:
        for name, s_, e_ in zip(names, bounds[:3], bounds[1:]):
            s_, e_ = max(s_, x0), min(e_, x1)
            if (e_ - s_).days / total < 0.14:
                continue                      # span too narrow to carry a label
            mid = s_ + (e_ - s_) / 2
            ax.text(mid, 1.0, name, transform=ax.get_xaxis_transform(), fontsize=7, color=MUTED, va="bottom",
                    ha="center")


def _fig(h):
    fig = plt.figure(figsize=(10, h), dpi=config_dpi(), facecolor=SURFACE)
    return fig


def config_dpi() -> int:
    return 150


def _dates(ax):
    loc = mdates.AutoDateLocator(minticks=5, maxticks=10)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))


def equity_chart(daily: pd.DataFrame, spy_ret: pd.Series, pair_id: str, rule: str, path) -> None:
    eq = daily["equity"] / daily["equity"].iloc[0] * 100.0
    # index both to 100 at the close before the first OOS return so the first day starts level
    spy = (1.0 + spy_ret.reindex(daily.index).fillna(0.0)).cumprod()
    spy = spy / spy.iloc[0] * 100.0
    fig = _fig(5.2)
    ax = fig.add_subplot(111)
    ax.plot(eq.index, eq.to_numpy(), color=BLUE, linewidth=LW, label=f"{pair_id} {rule} (net of costs)")
    ax.plot(spy.index, spy.to_numpy(), color=ORANGE, linewidth=LW, label="SPY buy-and-hold (total return)")
    _style(ax)
    _dates(ax)
    _regime_lines(ax, daily.index[0], daily.index[-1], True)
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity index (first OOS day = 100)")
    ax.set_title(f"{pair_id} | {rule}: strategy equity vs SPY", color=INK, fontsize=11, loc="left", pad=18)
    _legend_below(ax, ncol=2, y=-0.14)
    fig.tight_layout()
    fig.savefig(path, dpi=config_dpi(), facecolor=SURFACE)
    plt.close(fig)


def spread_z_chart(daily: pd.DataFrame, trades: pd.DataFrame, log_ratio: pd.Series, pair_id: str, rule: str,
                   path) -> None:
    """Two stacked panels sharing the x-axis: spread on top, signal below (never twin y-axes)."""
    fig = _fig(7.2)
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.12)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    coint = rule in ("coint_ols", "coint_kalman")
    if coint:
        top = daily["spread"]
        top_label = ("log spread  ln A - beta ln B  (beta in force)" if rule == "coint_ols"
                     else "Kalman innovation  ln A - beta(t-1) ln B - alpha(t-1)")
        top_name = "log spread" if rule == "coint_ols" else "Kalman spread"
    else:
        top = log_ratio.reindex(daily.index)
        top_label = "log price ratio  ln(A / B)"
        top_name = "ln(A/B)"
    ax1.plot(top.index, top.to_numpy(), color=BLUE, linewidth=LW, label=top_name)
    z = daily["z"]
    ax2.plot(z.index, z.to_numpy(), color=BLUE, linewidth=LW, label=SIGNAL_LABEL[rule])
    ax2.axhline(0.0, color=MUTED, linewidth=0.8)
    for v in THRESHOLDS[rule]:
        ax2.axhline(v, color=MUTED, linewidth=0.8, linestyle=(0, (4, 3)))
    # entries / exits at the fill dates
    if len(trades):
        ent = pd.to_datetime(trades["entry_date"])
        ext = pd.to_datetime(trades.loc[~trades["open_at_end"].astype(bool), "exit_date"])
        for ax, ser in ((ax1, top), (ax2, z)):
            ev = ser.reindex(ent).dropna()
            xv = ser.reindex(ext).dropna()
            ax.scatter(ev.index, ev.to_numpy(), s=16, marker="^", color=ORANGE, zorder=3, label="entry (fill day)")
            ax.scatter(xv.index, xv.to_numpy(), s=16, marker="v", color=AQUA, zorder=3, label="exit (fill day)")
    for ax in (ax1, ax2):
        _style(ax)
    plt.setp(ax1.get_xticklabels(), visible=False)
    _dates(ax2)
    _regime_lines(ax1, daily.index[0], daily.index[-1], True)
    _regime_lines(ax2, daily.index[0], daily.index[-1], False)
    ax1.set_ylabel(top_label if len(top_label) < 44 else top_name, fontsize=8)
    ax2.set_ylabel(SIGNAL_LABEL[rule].split(" (")[0] + (" (dashed: thresholds)" if THRESHOLDS[rule] else ""), fontsize=8)
    ax2.set_xlabel("Date")
    ax1.set_title(f"{pair_id} | {rule}: spread and signal", color=INK, fontsize=11, loc="left", pad=18)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    seen, hh, ll = set(), [], []
    for h, l in list(zip(h1, l1)) + list(zip(h2, l2)):
        if l not in seen:
            seen.add(l)
            hh.append(h)
            ll.append(l)
    leg = fig.legend(hh, ll, loc="lower center", ncol=4, frameon=False, fontsize=8)
    for t in leg.get_texts():
        t.set_color(INK2)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.93, bottom=0.12)
    fig.savefig(path, dpi=config_dpi(), facecolor=SURFACE)
    plt.close(fig)

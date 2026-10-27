"""Summary chart for the final research report: candidate pairs vs random pairs.

    .venv/bin/python -m backtest.final_charts   ->  reports/charts/candidates_vs_random.png
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .charts import BLUE, INK, INK2, MUTED, SURFACE, _legend_below, _style, plt

OUT_DIR = config.ROOT / "reports" / "charts"


def candidates_vs_random() -> None:
    m = pd.read_csv(config.RESULTS_DIR / "trials_metrics.csv")
    b = pd.read_csv(config.RESULTS_DIR / "baseline.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), dpi=150, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    bins = np.arange(-2.0, 2.05, 0.1)
    for ax, rule, title in ((axes[0], "coint_ols", "Spread mean reversion (coint_ols)"),
                            (axes[1], "rotation", "Flip-sides rotation (rotation)")):
        _style(ax)
        r = b.loc[b["rule"] == rule, "full_sharpe"].dropna().clip(-2, 2)
        c = m.loc[m["rule"] == rule, "full_sharpe"].dropna().clip(-2, 2)
        ax.hist(r, bins=bins, density=True, color="#c3c2b7", label=f"500 random pairs")
        ax.hist(c, bins=bins, density=True, histtype="step", linewidth=1.6, color=BLUE,
                label=f"{len(c)} scouted candidate pairs")
        for x, lab in ((1.0, "pass bar 1.0"), (1.75, "DSR-implied ~1.75")):
            ax.axvline(x, color=MUTED, linestyle="--", linewidth=0.9)
            ax.text(x, ax.get_ylim()[1] * 0.97, f" {lab}", color=INK2, fontsize=7, va="top")
        ax.set_title(title, color=INK, fontsize=9, loc="left")
        ax.set_xlabel("out-of-sample Sharpe, Oct 2016 - Oct 2026, net of costs")
        _legend_below(ax, ncol=2, y=-0.22)
    axes[0].set_ylabel("density")
    fig.suptitle("Scouted pairs do no better than random pairs; none come close to the bar", color=INK,
                 fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "candidates_vs_random.png", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    candidates_vs_random()

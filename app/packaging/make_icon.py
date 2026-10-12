#!/usr/bin/env python3
"""
Generate the application icon: the critical line with the first zeros on it.

Not decoration — it is the one picture that says what the app is. A vertical
line at sigma = 1/2 with marks at 14.13, 21.02, 25.01 … is the Riemann
hypothesis in a single glyph.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

ZEROS = [14.134725, 21.022040, 25.010858, 30.424876, 32.935062,
         37.586178, 40.918719, 43.327073]

BG = "#141414"
LINE = "#4fc3f7"
ZERO = "#ffd54f"


def render(path: Path, px: int = 256) -> Path:
    fig = plt.figure(figsize=(px / 100, px / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    lo, hi = 10.0, 46.0
    ax.set_xlim(0, 1)
    ax.set_ylim(lo, hi)
    ax.axis("off")

    # the strip
    ax.axvspan(0.30, 0.70, color="#1e1e1e")
    # sigma = 0 and 1 edges, faint
    for x in (0.30, 0.70):
        ax.plot([x, x], [lo, hi], color="#333", lw=px * 0.006, zorder=1)
    # the critical line
    ax.plot([0.5, 0.5], [lo, hi], color=LINE, lw=px * 0.016, zorder=2)

    # The zeros. Markers, not Circle patches: a patch radius is given in DATA
    # units, and here x spans 0..1 while y spans 36 — so a "circle" comes out as
    # a bar across the whole icon. Marker size is in points and is isotropic.
    ax.plot([0.5] * len(ZEROS), ZEROS, linestyle="none", marker="o",
            markersize=px * 0.055, markerfacecolor=ZERO,
            markeredgecolor=BG, markeredgewidth=px * 0.008, zorder=3)

    fig.savefig(path, dpi=100, facecolor=BG)
    plt.close(fig)
    return path


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "pse-riemann.png")
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    print(render(out, size))

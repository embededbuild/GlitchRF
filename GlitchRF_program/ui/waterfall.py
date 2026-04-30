from __future__ import annotations
from collections import deque
from typing import List

try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.animation import FuncAnimation
except ImportError:  # pragma: no cover
    plt = None
    np = None
    FuncAnimation = None


class WaterfallDisplay:
    """Display a simple waterfall visualization using matplotlib."""

    def __init__(self, width: int = 125, height: int = 64) -> None:
        self.available = plt is not None and np is not None and FuncAnimation is not None
        self.width = width
        self.height = height
        self.history: deque[List[float]] = deque(maxlen=height)

    def add_scan(self, values: List[int]) -> None:
        if not self.available:
            return
        self.history.append([float(value) for value in values])

    def render(self) -> None:
        if not self.available:
            print("Waterfall display requires matplotlib and numpy.")
            return
        if not self.history:
            print("No data to display.")
            return
        matrix = np.array(self.history)
        fig, ax = plt.subplots(figsize=(11, 6))
        image = ax.imshow(matrix, aspect="auto", origin="lower", cmap="inferno", vmin=0, vmax=1)
        ax.set_title("GlitchRF Waterfall")
        ax.set_ylabel("Scan sweep")
        ax.set_xlabel("Channel")
        ax.set_xticks([0, 25, 50, 75, 100, self.width - 1])
        ax.set_xticklabels(["2400", "2425", "2450", "2475", "2500", str(int(2400 + self.width - 1))])
        fig.colorbar(image, ax=ax, label="RSSI activity")
        plt.tight_layout()
        plt.show()

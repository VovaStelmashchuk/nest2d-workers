from polygone import DxfPolygon, process
import matplotlib.pyplot as plt
from typing import Iterable, List, Sequence, Dict
import sys
# --------------------------------------------------------------------------
# plotting ------------------------------------------------------------------
# --------------------------------------------------------------------------

def plot_items(items: List[DxfPolygon], title="DXF closed regions"):
    fig, ax = plt.subplots()
    ax.set_aspect("equal", "box")
    ax.set_title(title)
    ax.grid(True, zorder=0)
    for d in items:
        x, y = d.polygon.exterior.xy
        ax.plot(x, y, lw=1.2, zorder=1)
    plt.show()

# --------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python main.py <file.dxf>")
   
    filePath = sys.argv[1]
    fileStream = open(filePath, "r")

    result = process(fileStream)
    for res in result:
        print(res.polygon)
        print(res.entities)

    plot_items(result, title=sys.argv[1])


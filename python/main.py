from polygone import DxfPolygon, process
import matplotlib.pyplot as plt
from typing import Iterable, List, Sequence, Dict
import sys
import ezdxf
from svg_generator import create_svg_from_doc

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
    # fileStream = open(filePath, "r")

    # result = process(fileStream, 0.01)
    # for res in result:
    #     print(res.polygon)
    #     print(res.entities)

    # plot_items(result, title=sys.argv[1])

    # New: generate SVG from DXF and print
    doc = ezdxf.readfile(filePath)
    svg = create_svg_from_doc(doc)
    with open("output.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("SVG saved to output.svg")


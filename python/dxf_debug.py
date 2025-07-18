from __future__ import annotations

from polygonizer.main import close_polygon_from_dxf 
import ezdxf
from dxf_utils import read_dxf_file

if __name__ == "__main__":
    import json
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--dxf", help="Input DXF file")
    p.add_argument("-t", "--tol", type=float, default=0.05, help="snap tolerance in drawing units")
    p.add_argument("-o", "--out", default="polygons.json", help="output json")
    args = p.parse_args()
    
    doc = read_dxf_file(args.dxf)

    result = close_polygon_from_dxf(doc, args.tol)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump([{"points": poly.points, "handles": poly.handles} for poly in result], f, indent=2)
    print(f"Found {len(result)} polygons  ➜  {args.out}")
    
    import matplotlib.pyplot as plt
    import numpy as np

    if result:
        fig, ax = plt.subplots(figsize=(8, 8))
        colors = plt.colormaps["tab20"].resampled(len(result))
        for i, poly in enumerate(result):
            pts = np.array(poly.points)
            ax.fill(pts[:, 0], pts[:, 1], color=colors(i), alpha=0.5, label=f"Polygon {i+1}")
            ax.plot(pts[:, 0], pts[:, 1], color=colors(i), lw=1.5)
        ax.set_aspect("equal")
        ax.set_title(f"Polygons from {args.dxf}")
        ax.legend(loc="best", fontsize="small", ncol=2)
        plt.savefig("output.png")
    else:
        print("No polygons found to plot.")

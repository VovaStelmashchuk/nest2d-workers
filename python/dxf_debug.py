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
    print(f"Found {len(result)} polygons")
    
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Plot the polygons in result
    fig, ax = plt.subplots()
    for poly in result:
        xs = [p.x for p in poly.points]
        ys = [p.y for p in poly.points]
        ax.plot(xs, ys, marker='o')
        if hasattr(poly, "handles") and poly.handles:
            centroid_x = np.mean(xs)
            centroid_y = np.mean(ys)
            ax.text(centroid_x, centroid_y, ",".join(str(h) for h in poly.handles), fontsize=8)

    ax.set_aspect('equal')
    ax.set_title("Closed Polygons")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.show()


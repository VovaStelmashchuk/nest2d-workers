from polygone import DxfPolygon, process
import matplotlib.pyplot as plt
from typing import Iterable, List, Sequence, Dict
import sys
import ezdxf
from svg_generator import create_svg_from_doc
import os

def plot_items(items: List[DxfPolygon], title="DXF closed regions"):
    fig, ax = plt.subplots()
    ax.set_aspect("equal", "box")
    ax.set_title(title)
    ax.grid(True, zorder=0)
    for d in items:
        x, y = d.polygon.exterior.xy
        ax.plot(x, y, lw=1.2, zorder=1)
    plt.show()

# Recursively find all .dxf files in a directory
def find_dxf_files(root_dir):
    dxf_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith('.dxf'):
                dxf_files.append(os.path.join(dirpath, filename))
    return dxf_files

# Make sure the output directory exists
def ensure_dir_exists(path):
    os.makedirs(path, exist_ok=True)

# --------------------------------------------------------------------------
if __name__ == "__main__":
    dxf_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../prod-files'))
    svg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../svg-files'))

    dxf_files = find_dxf_files(dxf_root)
    print(f"Found {len(dxf_files)} DXF files.")

    ensure_dir_exists(svg_root)

    for idx, dxf_path in enumerate(dxf_files):
        svg_path = os.path.join(svg_root, f"{idx}.svg")
        try:
            doc = ezdxf.readfile(dxf_path)
            svg = create_svg_from_doc(doc)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg)
            print(f"[OK] {dxf_path} -> {svg_path}")
        except Exception as e:
            print(f"[FAIL] {dxf_path}: {e}")


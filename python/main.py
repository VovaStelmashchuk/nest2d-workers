#!/usr/bin/env python
"""
Extract every closed region from a DXF file and plot it.

• Closed LWPOLYLINE / POLYLINE are copied verbatim.
• CIRCLE, full‑angle ARC and closed ELLIPSE are sampled with ezdxf.flattening().
• Closed / periodic SPLINE is flattened with a distance tolerance (Hausdorff).
• Open entities are joined into edge‑loops with ezdxf.edgeminer
  and each loop becomes a polygon directly (no Shapely polygonize()).
"""

from __future__ import annotations
import sys
from typing import Iterable, List, Sequence

import ezdxf
from ezdxf.entities import DXFEntity
from ezdxf.edgeminer import Deposit, find_all_loops
from ezdxf.edgesmith import edges_from_entities_2d, is_closed_entity
from ezdxf.math import Vec3
from shapely.geometry import Polygon
import matplotlib.pyplot as plt

# --------------------------------------------------------------------------- #
# Tunables (can be overridden from CLI)                                       #
# --------------------------------------------------------------------------- #
GAP_TOL = 1       # for joining endpoints when building edge‑loops
SPLINE_TOL = 0.1    # max distance between a spline and its polyline approx.
ELIGIBLE = {
    "LINE", "ARC", "ELLIPSE", "SPLINE", "LWPOLYLINE", "POLYLINE", "CIRCLE",
}

# --------------------------------------------------------------------------- #
# Helpers for CLOSED entities                                                 #
# --------------------------------------------------------------------------- #


def _poly_from_lwpoly(entity) -> Polygon:
    pts = [tuple(p[:2]) for p in entity.get_points()]
    if pts and pts[0] != pts[-1]:
        pts.append(pts[0])
    return Polygon(pts)


def _poly_from_polyline(entity) -> Polygon:
    # same as LWPolyline but with .points()
    pts = [tuple(p[:2]) for p in entity.points()]
    if pts and pts[0] != pts[-1]:
        pts.append(pts[0])
    return Polygon(pts)


def _poly_from_circle_like(entity, tol: float = 0.1) -> Polygon:
    pts = [(v.x, v.y) for v in entity.flattening(tol)]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return Polygon(pts)


def _poly_from_spline(entity, tol: float = 0.1) -> Polygon:
    tool = entity.construction_tool()
    if not is_closed_entity(entity):
        raise ValueError("SPLINE is not closed")
    pts = [(v.x, v.y) for v in tool.flattening(distance=tol)]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return Polygon(pts)


def closed_entities_to_polygons(
    entities: Iterable[DXFEntity],
    spline_tol: float = SPLINE_TOL,
) -> List[Polygon]:
    polys: List[Polygon] = []
    for e in entities:
        try:
            dxftype = e.dxftype()
            if dxftype == "LWPOLYLINE":
                polys.append(_poly_from_lwpoly(e))
            elif dxftype == "POLYLINE":
                polys.append(_poly_from_polyline(e))
            elif dxftype in {"CIRCLE"}:
                polys.append(_poly_from_circle_like(e, tol=spline_tol))
            elif dxftype == "ARC":
                if abs(e.dxf.end_angle - e.dxf.start_angle) % 360 == 0:
                    polys.append(_poly_from_circle_like(e, tol=spline_tol))
                else:
                    print(f"⚠️  Skipping open ARC {e.dxf.handle}")
            elif dxftype == "ELLIPSE":
                if is_closed_entity(e):  # full ellipse
                    polys.append(_poly_from_circle_like(e, tol=spline_tol))
                else:
                    print(f"⚠️  Skipping open ELLIPSE {e.dxf.handle}")
            elif dxftype == "SPLINE":
                polys.append(_poly_from_spline(e, tol=spline_tol))
            else:
                print(f"⚠️  Closed entity {dxftype} not handled, skipped")
        except Exception as exc:
            print(f"Error converting {e.dxf.handle}: {exc}")
    return polys

# --------------------------------------------------------------------------- #
# Helpers for OPEN entities                                                   #
# --------------------------------------------------------------------------- #


def open_entities_to_polygons(
    entities: Iterable[DXFEntity],
    flatten_tol: float = 0.1,
) -> List[Polygon]:
    """Build polygons from *open* entities.

    1.  Every entity is flattened with the given tolerance → sequence of
        points in drawing order.
    2.  Consecutive point pairs are converted to individual Shapely
        ``LineString`` objects.
    3.  All segments are sent to ``shapely.ops.polygonize`` which stitches
        them together into as many closed polygons as can be found.

    Compared to the previous edge‑miner approach this handles arcs, bulge
    segments and splines transparently because they are already reduced to
    straight segments before polygonisation.
    """
    from shapely.geometry import LineString
    from shapely.ops import polygonize

    segments: list[LineString] = []

    for ent in entities:
        try:
            # ezdxf entities expose .flattening(tol) for geometric sampling
            pts = [(v.x, v.y) for v in ent.flattening(0.1)]
        except AttributeError:
            # fallback for entities without .flattening() (should be rare)
            if ent.dxftype() == "LINE":
                pts = [(ent.dxf.start.x, ent.dxf.start.y),
                       (ent.dxf.end.x, ent.dxf.end.y)]
            else:
                print(f"⚠️  Cannot flatten {ent.dxftype()} – skipped")
                continue
        # build segment list
        for p1, p2 in zip(pts, pts[1:]):
            if p1 != p2:
                segments.append(LineString([p1, p2]))

    print(f"Generated {len(segments)} straight segments from open entities")

    polys = [p for p in polygonize(segments) if p.is_valid and not p.is_empty]
    print(f"Polygonize() produced {len(polys)} polygon(s) from open entities")
    return polys

# --------------------------------------------------------------------------- #
# Plotting                                                                    #
# --------------------------------------------------------------------------- #


def plot_polygons(polys: List[Polygon], title="DXF polygons"):
    fig, ax = plt.subplots()
    ax.set_aspect("equal", "box")
    ax.set_title(title)
    ax.grid(True, zorder=0)
    for p in polys:
        x, y = p.exterior.xy
        ax.plot(x, y, lw=1.2, zorder=1)
    plt.show()

# --------------------------------------------------------------------------- #
# Main driver                                                                 #
# --------------------------------------------------------------------------- #


def process_dxf(path: str, gap_tol: float, spline_tol: float):
    print(f"Reading {path!r}")
    try:
        doc = ezdxf.readfile(path)
    except (IOError, ezdxf.DXFStructureError) as exc:
        sys.exit(f"❌  {exc}")

    msp = doc.modelspace()
    ents = [e for e in msp if e.dxftype() in ELIGIBLE]

    closed, open_ = [], []
    for e in ents:
        (closed if is_closed_entity(e) else open_).append(e)

    print(f"Total eligible entities : {len(ents)}")
    print(f"  closed entities       : {len(closed)}")
    print(f"  open entities         : {len(open_)}")

    polys = (
        closed_entities_to_polygons(closed, spline_tol=spline_tol) +
        open_entities_to_polygons(open_, flatten_tol=gap_tol)
    )

    print(f"Total polygons produced : {len(polys)}")
    plot_polygons(polys, "DXF closed regions")


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    if len(sys.argv) not in {2, 4}:
        sys.exit(
            "Usage:\n"
            "  python main.py <file.dxf> [gap_tol spline_tol]\n"
            "Example:\n"
            "  python main.py mamapapa.dxf 0.5 0.02"
        )

    if len(sys.argv) == 4:
        GAP_TOL = float(sys.argv[2])
        SPLINE_TOL = float(sys.argv[3])

    process_dxf(sys.argv[1], gap_tol=GAP_TOL, spline_tol=SPLINE_TOL)

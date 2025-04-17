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
from shapely.prepared import prep
from typing import List
import sys
from typing import Iterable, List, Sequence

import ezdxf
from ezdxf.disassemble import make_primitive, recursive_decompose
from ezdxf.entities import DXFEntity
from ezdxf.edgeminer import Deposit, find_all_loops
from ezdxf.edgesmith import edges_from_entities_2d, is_closed_entity
from ezdxf.math import Vec3
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
from typing import Iterable, List
from shapely.geometry import LineString, MultiLineString, Polygon, MultiPolygon
from shapely.ops import unary_union, polygonize
# --------------------------------------------------------------------------- #
# Tunables (can be overridden from CLI)                                       #
# --------------------------------------------------------------------------- #
GAP_TOL = 0.1       # for joining endpoints when building edge‑loops
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
    flatten_tol: float,
    snap_tol: float,
) -> List[Polygon]:
    """
    Build polygons from *open* entities.

    Parameters
    ----------
    entities     : iterable of DXFEntity
    flatten_tol  : sampling tolerance used when flattening curves
    snap_tol     : grid size for snapping vertices (defaults to 0.5 * flatten_tol)

    Returns
    -------
    list[Polygon]
        All polygons Shapely can form from the given geometry.
    """

    def snap(pt):
        """Snap point to grid of size `snap_tol`."""
        return (
            round(pt[0] / snap_tol) * snap_tol,
            round(pt[1] / snap_tol) * snap_tol,
        )

    segments: list[LineString] = []

    # ------------------------------------------------------------------ collect
    for ent in entities:
        prim = make_primitive(ent, flatten_tol)
        verts = list(prim.vertices())
        if len(verts) < 2:
            continue

        # build LineStrings between consecutive vertices
        for a, b in zip(verts, verts[1:]):
            pa = snap((a.x, a.y))
            pb = snap((b.x, b.y))
            if pa != pb:                       # avoid zero‑length artefacts
                segments.append(LineString([pa, pb]))

    if not segments:
        return []

    # --------------------------------------------------------- clean & polygonise
    merged = unary_union(segments)             # dissolve dups / overlaps
    if isinstance(merged, LineString):         # happens for single segment
        merged = MultiLineString([merged])

    polys = [
        p for p in polygonize(merged)
        if p.is_valid and not p.is_empty
    ]
    print(
        f"open_entities_to_polygons(): "
        f"{len(segments)} segments → {len(polys)} polygons "
        f"(flatten_tol={flatten_tol}, snap_tol={snap_tol})"
    )
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

def keep_only_outer(polys: List[Polygon]) -> List[Polygon]:
    """
    Return a new list that contains no polygon which is completely
    inside (or exactly equal to) another polygon from the same list.
    """
    # largest area first – makes the containment test cheap
    polys_sorted = sorted(polys, key=lambda p: p.area, reverse=True)

    outers: List[Polygon] = []
    prepared: List = []            # prepared geometries for fast 'covers'

    for poly in polys_sorted:
        # is poly completely covered by any already‑kept outer polygon?
        if any(pp.covers(poly) for pp in prepared):
            continue               # → it's a hole, skip
        outers.append(poly)
        prepared.append(prep(poly))  # cache prepared version for speed

    return outers

def merge_touching(polys: List[Polygon]) -> List[Polygon]:
    """
    Return a list in which any polygons that share an edge *or* overlap
    are merged into a single polygon.
    """
    merged = unary_union(polys)          # one big geometry

    # explode back into a flat list
    if isinstance(merged, Polygon):
        return [merged]
    elif isinstance(merged, MultiPolygon):
        return list(merged.geoms)
    else:                                # unlikely (e.g. GeometryCollection)
        return [g for g in merged.geoms if isinstance(g, Polygon)]


def process_dxf(path: str, gap_tol: float, spline_tol: float):
    print(f"Reading {path!r}")
    try:
        doc = ezdxf.readfile(path)
    except (IOError, ezdxf.DXFStructureError) as exc:
        sys.exit(f"❌  {exc}")

    msp = doc.modelspace()
    ents = [
        e for e in recursive_decompose(msp)
        if e.dxftype() in ELIGIBLE
    ]

    closed, open = [], []
    for e in ents:
        (closed if is_closed_entity(e) else open).append(e)

    print(f"Total eligible entities : {len(ents)}")
    print(f"  closed entities       : {len(closed)}")
    print(f"  open entities         : {len(open)}")

    polys = (
        closed_entities_to_polygons(closed, spline_tol=spline_tol) +
        open_entities_to_polygons(open, flatten_tol=gap_tol, snap_tol=gap_tol)
    )

    print(f"Total polygons produced : {len(polys)}")
    polys = keep_only_outer(polys)
    polys = merge_touching(polys)
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

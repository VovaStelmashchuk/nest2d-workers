#!/usr/bin/env python
"""
Extract every closed region from a DXF file, **keep track of which DXF
entities created every polygon**, merge polygons that belong together and
plot the result.

Output of the core pipeline is a list of dicts with two keys:

    {
        "polygon": <shapely.geometry.Polygon>,
        "entities": [<entity‑handle>, <entity‑handle>, ...]
    }

 so each face is linked back to the originating DXF entity handles.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Dict, TextIO

import ezdxf
from ezdxf import read
from ezdxf.disassemble import make_primitive, recursive_decompose
from ezdxf.entities import DXFEntity
from ezdxf.edgesmith import is_closed_entity
from shapely.geometry import Polygon, LineString, MultiLineString, MultiPolygon
from shapely.ops import unary_union, polygonize
from shapely.prepared import prep
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union, polygonize

@dataclass
class DxfPolygon:
    """A closed region extracted from a DXF drawing."""

    polygon: Polygon               # the geometry (2‑D)
    entities: list[DXFEntity]      # all DXF entities that produced it

    def __post_init__(self):
        if not self.polygon.is_valid or self.polygon.is_empty:
            raise ValueError("polygon must be a valid, non‑empty geometry")

# ‑‑‑ constants -------------------------------------------------------------
GAP_TOL     = 0.1   # sampling / snapping grid for open geometry
SPLINE_TOL  = 0.1   # flattening tol for splines / circles / ellipses
ELIGIBLE = {
    "LINE", "ARC", "ELLIPSE", "SPLINE", "LWPOLYLINE", "POLYLINE", "CIRCLE",
}

# --------------------------------------------------------------------------
# helpers for closed entities ----------------------------------------------
# --------------------------------------------------------------------------

def _poly_from_lwpoly(e):
    pts = [tuple(p[:2]) for p in e.get_points()]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return Polygon(pts)

def _poly_from_polyline(e):
    pts = [tuple(p[:2]) for p in e.points()]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return Polygon(pts)

def _poly_from_circle_like(e, tol=SPLINE_TOL):
    pts = [(v.x, v.y) for v in e.flattening(tol)]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return Polygon(pts)

def _poly_from_spline(e, tol=SPLINE_TOL):
    tool = e.construction_tool()
    if not is_closed_entity(e):
        raise ValueError("open spline")
    pts = [(v.x, v.y) for v in tool.flattening(tol)]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return Polygon(pts)

def closed_entities_to_polys_with_src(
    entities: Iterable[DXFEntity],
    spline_tol: float = SPLINE_TOL,
) -> List[DxfPolygon]:
    out: list[DxfPolygon] = []
    for e in entities:
        try:
            dxftype = e.dxftype()
            if dxftype == "LWPOLYLINE":
                p = _poly_from_lwpoly(e)
            elif dxftype == "POLYLINE":
                p = _poly_from_polyline(e)
            elif dxftype == "CIRCLE":
                p = _poly_from_circle_like(e, tol=spline_tol)
            elif dxftype == "ARC":
                if abs(e.dxf.end_angle - e.dxf.start_angle) % 360 != 0:
                    print(f"⚠️  Skipping open ARC {e.dxf.handle}")
                    continue
                p = _poly_from_circle_like(e, tol=spline_tol)
            elif dxftype == "ELLIPSE":
                if not is_closed_entity(e):
                    print(f"⚠️  Skipping open ELLIPSE {e.dxf.handle}")
                    continue
                p = _poly_from_circle_like(e, tol=spline_tol)
            elif dxftype == "SPLINE":
                p = _poly_from_spline(e, tol=spline_tol)
            else:
                print(f"⚠️  Closed entity {dxftype} not handled, skipped")
                continue
            out.append(DxfPolygon(polygon=p, entities=[e]))
        except Exception as exc:
            print(f"Error converting {e.dxf.handle}: {exc}")
    return out

# --------------------------------------------------------------------------- #
# Helpers for OPEN entities                                                   #
# --------------------------------------------------------------------------- #


def open_entities_to_polys_with_src(
    entities: Iterable[DXFEntity],
    flatten_tol: float = 0.1,
    snap_tol: float | None = None,
) -> List[DxfPolygon]:
    if snap_tol is None:
        snap_tol = 0.5 * flatten_tol

    def snap(pt):
        return (
            round(pt[0] / snap_tol) * snap_tol,
            round(pt[1] / snap_tol) * snap_tol,
        )

    seg2ent: list[tuple[LineString, DXFEntity]] = []

    for ent in entities:
        prim = make_primitive(ent, flatten_tol)
        verts = list(prim.vertices())
        if len(verts) < 2:
            continue
        for a, b in zip(verts, verts[1:]):
            pa, pb = snap((a.x, a.y)), snap((b.x, b.y))
            if pa != pb:
                seg2ent.append((LineString([pa, pb]), ent))

    if not seg2ent:
        return []

    # dissolve geometry only — keep mapping to entities separately
    segments = [s for s, _ in seg2ent]
    merged = unary_union(segments)
    if isinstance(merged, LineString):
        merged = MultiLineString([merged])

    result: list[DxfPolygon] = []
    for poly in polygonize(merged):
        if poly.is_valid and not poly.is_empty:
            touching_ents = [ent for seg, ent in seg2ent if seg.intersects(poly)]
            result.append(DxfPolygon(polygon=poly, entities=touching_ents))
    return result

# --------------------------------------------------------------------------- #
# Post‑processing helpers                                                     #
# --------------------------------------------------------------------------- #

from shapely.prepared import prep

def keep_only_outer(items: List[DxfPolygon]) -> List[DxfPolygon]:
    # sort by descending area
    items_sorted = sorted(items, key=lambda d: d.polygon.area, reverse=True)
    outers: list[DxfPolygon] = []
    prepared: list = []
    for item in items_sorted:
        if any(p.covers(item.polygon) for p in prepared):
            continue
        outers.append(item)
        prepared.append(prep(item.polygon))
    return outers


def merge_touching(items: List[DxfPolygon]) -> List[DxfPolygon]:
    # naive O(n²) merge of polygons that share any boundary
    merged: list[DxfPolygon] = []
    while items:
        base = items.pop()
        changed = True
        while changed:
            changed = False
            for other in list(items):
                if base.polygon.touches(other.polygon) or base.polygon.intersects(other.polygon):
                    # union geometries
                    base = DxfPolygon(
                        polygon=base.polygon.union(other.polygon),
                        entities=list({*base.entities, *other.entities}),
                    )
                    items.remove(other)
                    changed = True
        merged.append(base)
    return merged

# --------------------------------------------------------------------------- #
# Plotting (unchanged)                                                        #
# --------------------------------------------------------------------------- #

def plot_polygons(polys: List[DxfPolygon], title="DXF polygons"):
    fig, ax = plt.subplots()
    ax.set_aspect("equal", "box")
    ax.set_title(title)
    ax.grid(True, zorder=0)
    for item in polys:
        x, y = item.polygon.exterior.xy
        ax.plot(x, y, lw=1.2, zorder=1)
    plt.show()

# --------------------------------------------------------------------------- #
# Main processing routine (strongly typed)                                    #
# --------------------------------------------------------------------------- #

def process(dxf_stream: TextIO, tol: float = GAP_TOL) -> List[DxfPolygon]:
    """Read *dxf_stream* and extract outer polygons.

    Parameters
    ----------
    dxf_stream : TextIO
        File‑like object opened in text or binary mode pointing at a DXF file.
    tol        : float
        Sampling / snapping tolerance (model‑space units).

    Returns
    -------
    list[DxfPolygon]
        Outer, merged polygons with their source entities attached.
    """
    try:
        doc = ezdxf.read(dxf_stream)
    except ezdxf.DXFStructureError as e:
        raise ValueError(f"Invalid DXF file: {e}") from e

    msp = doc.modelspace()
    entities = [e for e in recursive_decompose(msp) if e.dxftype() in ELIGIBLE]

    closed_ents = [e for e in entities if is_closed_entity(e)]
    open_ents   = [e for e in entities if not is_closed_entity(e)]

    items: List[DxfPolygon] = (
        closed_entities_to_polys_with_src(closed_ents, spline_tol=tol) +
        open_entities_to_polys_with_src(open_ents, flatten_tol=tol)
    )

    items = keep_only_outer(items)
    items = merge_touching(items)

    return items

from __future__ import annotations

import ezdxf
import numpy as np
from shapely.geometry import Polygon
from shapely import contains, covers

from polygonizer.dto import ClosedPolygon, PolygonPart, Point

from utils.logger import setup_json_logger

logger = setup_json_logger("dxf_polygonizer")

def _vec2(v):
    """Return a plain (x, y) tuple from a Vec3 or any 3-component iterable."""
    return (float(v[0]), float(v[1]))  # works for Vec3, numpy rows, etc.

def _flatten_entity(e, tol: float):
    """
    Return Nx2 NumPy array of (x, y) vertices approximating *e*
    and its DXF handle.  All curve entities are tessellated with the
    user–supplied *tol* so the maximum sagitta ≤ tol.
    """
    h = e.dxf.handle
    kind = e.dxftype()

    if kind == "LINE":
        pts = np.array([_vec2(e.dxf.start), _vec2(e.dxf.end)])

    elif kind == "LWPOLYLINE":
        pts = np.array([_vec2(p) for p in e.get_points(format="xy")])
        if e.closed:
            pts = np.vstack([pts, pts[0]])

    elif kind == "POLYLINE":
        pts = np.array([_vec2(p) for p in e.points()])
        if getattr(e, "is_closed", False):
            pts = np.vstack([pts, pts[0]])

    elif kind == "ARC":
        pts = np.array([_vec2(p) for p in e.flattening(sagitta=tol)])   # adaptive tessellation :contentReference[oaicite:2]{index=2}

    elif kind == "CIRCLE":
        pts = np.array([_vec2(p) for p in e.flattening(sagitta=tol)])    # circle uses sagitta-based method :contentReference[oaicite:3]{index=3})

    elif kind == "ELLIPSE":
        pts = np.array([_vec2(p) for p in e.flattening(distance=tol)])   # ellipse flattening :contentReference[oaicite:4]{index=4}

    elif kind == "SPLINE":
        pts = np.array([_vec2(p) for p in e.flattening(distance=tol)])   # spline adaptive flattening :contentReference[oaicite:5]{index=5}

    else:
        pts = np.empty((0, 2))

    return pts, h


def polygon_parts_from_dxf(doc: ezdxf.Drawing, tol: float) -> list[PolygonPart]:
    msp = doc.modelspace()
    all_pts: list[PolygonPart] = []
    for e in msp:
        pts, handle = _flatten_entity(e, tol)
        if len(pts) >= 2:
            all_pts.append(
                PolygonPart(points=[Point(x=pt[0], y=pt[1]) for pt in pts], handles=[handle])
            )
    
    return all_pts


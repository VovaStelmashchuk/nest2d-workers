from operator import contains
from polygonizer.dto import PolygonPart, ClosedPolygon
from shapely.geometry import Polygon

def _combine_nested_polygons(polys: list[ClosedPolygon], tol: float) -> list[ClosedPolygon]:
    """
    Return a **new list** where every polygon that was strictly contained
    inside another has been merged into its parent:

        * Parent keeps its `points`
        * Parent's `handles` = union of its own + all children’s
        * Nested children are removed.

    `tol` – optional buffer used to compensate for floating‑point
    noise: parent.buffer(+tol).covers(child) allows boundary‑touching
    cases to count as 'inside'.
    """
    # Convert once to Shapely objects
    shp = []
    for p in polys:
        coords = [(pt.x, pt.y) for pt in p.points]
        shp.append(Polygon(coords))

    # Sort by descending area so big parents come first
    order = sorted(range(len(polys)), key=lambda i: shp[i].area, reverse=True)

    keep = [True] * len(polys)
    for i in order:
        if not keep[i]:
            continue
        parent = shp[i]
        for j in order:                                # check every *smaller* poly
            if i == j or not keep[j]:
                continue
            child = shp[j]

            # Strict inclusion test with numeric tolerance
            # - contains(...)  ensures child interior is strictly inside parent interior
            # - covers(...)    catches 'same boundary' degeneracies
            
            inside = (parent.contains(child) or
                      parent.buffer(+tol).covers(child))

            if inside:
                # merge handles
                polys[i].handles = sorted(set(polys[i].handles) |
                                          set(polys[j].handles))
                keep[j] = False                       # drop child

    # Build the cleaned list preserving original order
    return [p for p, k in zip(polys, keep) if k]

def combine_polygon_parts(
    open_parts: list[PolygonPart], 
    closed_parts: list[ClosedPolygon], 
    tol: float
) -> tuple[list[PolygonPart], list[ClosedPolygon]]:
    """
    Returns a tuple of (list of open polygons, list of closed polygons).
    """
    if len(open_parts) == 0 and len(closed_parts) == 0:
        raise ValueError("Open and closed parts are empty")
    
    if (len(open_parts) == 0):
        nested_closed_parts = _combine_nested_polygons(closed_parts, tol)
        return [], nested_closed_parts
    
    pass

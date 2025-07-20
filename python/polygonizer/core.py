from operator import contains

import shapely
from polygonizer.dto import PolygonPart, ClosedPolygon, Point
from shapely.geometry import Polygon
from utils.logger import setup_json_logger

logger = setup_json_logger("polygonizer")

def _combine_nested_polygons(polys: list[ClosedPolygon], tol: float) -> list[ClosedPolygon]:
    """
    Return a **new list** where every polygon that was strictly contained
    inside another has been merged into its parent:

        * Parent keeps its `points`
        * Parent's `handles` = union of its own + all children's
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
            # - For tolerance cases, we need to ensure the child is mostly inside the parent
            
            # First check if child is completely inside parent
            if parent.contains(child):
                inside = True
            else:
                # For boundary-touching cases, check if child is mostly inside parent
                # by buffering the parent slightly and checking coverage
                buffered_parent = parent.buffer(tol)
                if buffered_parent.covers(child):
                    # Additional check: ensure child area is significantly inside parent
                    # (not just touching at edges)
                    intersection_area = parent.intersection(child).area
                    child_area = child.area
                    # Child should be at least 90% inside parent to be considered nested
                    inside = intersection_area >= 0.9 * child_area
                else:
                    inside = False

            if inside:
                # merge handles
                polys[i].handles = sorted(set(polys[i].handles) |
                                          set(polys[j].handles))
                keep[j] = False                       # drop child

    # Build the cleaned list preserving original order
    return [p for p, k in zip(polys, keep) if k]

def _combine_intersecting_polygons(polys: list[ClosedPolygon], tol: float) -> list[ClosedPolygon]:
    """
    Return a **new list** where every polygon that intersects with another has been merged into its parent:
    
    * Intersecting polygons are combined into a single polygon
    * The resulting polygon's `handles` = union of all intersecting polygons' handles
    * The resulting polygon's `points` = union of the geometries including intersection points
    
    `tol` – optional buffer used to compensate for floating‑point
    noise: polygons that are within `tol` distance are considered intersecting.
    """
    if not polys:
        return []

    # Use a copy to avoid modifying the original list
    polys = polys[:]
    
    # Convert to Shapely objects
    shp = [Polygon([(pt.x, pt.y) for pt in p.points]) for p in polys]

    # Keep merging until no more intersections are found
    while True:
        merged_in_pass = False
        i = 0
        while i < len(polys):
            j = i + 1
            while j < len(polys):
                poly_i = shp[i]
                poly_j = shp[j]

                # Use a small buffer to handle floating point issues, but respect tol=0
                buffered_i = poly_i.buffer(tol) if tol > 0 else poly_i
                buffered_j = poly_j.buffer(tol) if tol > 0 else poly_j

                if buffered_i.intersects(buffered_j):
                    # Only merge if the intersection has an area (is a Polygon)
                    intersection = buffered_i.intersection(buffered_j)
                    if intersection.area > 1e-9:  # Use a small threshold for area
                        # Merge polygons
                        union_poly = poly_i.union(poly_j)
                        
                        # Create new combined polygon
                        if union_poly.geom_type == 'Polygon':
                            coords = list(union_poly.exterior.coords)
                            points = [Point(x, y) for x, y in coords]
                        elif union_poly.geom_type == 'MultiPolygon':
                            # For MultiPolygon, take the largest polygon
                            largest_poly = max(union_poly.geoms, key=lambda p: p.area)
                            coords = list(largest_poly.exterior.coords)
                            points = [Point(x, y) for x, y in coords]
                        else:
                            # Fallback
                            points = polys[i].points

                        # Combine handles
                        combined_handles = sorted(set(polys[i].handles) | set(polys[j].handles))
                        
                        # Replace the first polygon with the merged one
                        polys[i] = ClosedPolygon(points=points, handles=combined_handles)
                        shp[i] = Polygon([(p.x, p.y) for p in points])

                        # Remove the second polygon
                        polys.pop(j)
                        shp.pop(j)
                        
                        merged_in_pass = True
                        # Restart inner loop since list is modified
                        j = i + 1
                    else:
                        j += 1
                else:
                    j += 1
            i += 1
        
        if not merged_in_pass:
            break
            
    return polys

def is_open_part_inside_closed_part(open_part: PolygonPart, closed_part: ClosedPolygon) -> bool:
    """
    Return True if the open part is inside the closed part, False otherwise.
    """
    points = open_part.points
    shapely_closed_part = Polygon([(p.x, p.y) for p in closed_part.points])
    
    for i in range(len(points)):
        if not shapely_closed_part.contains(shapely.Point(points[i].x, points[i].y)):
            return False
    return True

def _combine_open_parts(part_a: PolygonPart, part_b: PolygonPart, tol: float) -> tuple[bool, PolygonPart]:
    """
    Return a tuple of (True if the parts are combined, the combined part).
    """
    
    a_start= part_a.points[0]
    a_end= part_a.points[-1]
    b_start= part_b.points[0]
    b_end= part_b.points[-1]
    
    if a_start.eq_to(b_start, tol):
        return True, PolygonPart(
            points=list(reversed(part_b.points)) + part_a.points[1:],
            handles=part_a.handles + part_b.handles
        )
    elif a_start.eq_to(b_end, tol):
        return True, PolygonPart(
            points=part_b.points + part_a.points[1:],
            handles=part_a.handles + part_b.handles
        )
    elif a_end.eq_to(b_start, tol):
        return True, PolygonPart(
            points=part_a.points + part_b.points[1:],
            handles=part_a.handles + part_b.handles
        )
    elif a_end.eq_to(b_end, tol):
        return True, PolygonPart(
            points=part_a.points[:-1] + list(reversed(part_b.points)),
            handles=part_a.handles + part_b.handles
        )
    
    return False, None

def combine_polygon_parts(
    open_parts: list[PolygonPart], 
    closed_parts: list[ClosedPolygon], 
    tol: float
) -> tuple[list[PolygonPart], list[ClosedPolygon]]:
    """
    Returns a tuple of (list of open polygons, list of closed polygons).
    """
    
    logger.info("combine_polygon_parts", extra={
        "count of open parts": len(open_parts),
        "count of closed parts": len(closed_parts)
    })
    
    if (len(open_parts) == 1):
        print(f"Open part: {open_parts[0].points}")
    
    if not open_parts and not closed_parts:
        raise ValueError("Open and closed parts are empty")
    
    closed_parts = _combine_nested_polygons(closed_parts, tol)
    closed_parts = _combine_intersecting_polygons(closed_parts, tol)
    
    for open_part in open_parts:
        if open_part.is_closed(tol):
            closed_parts.append(open_part)
            open_parts.remove(open_part)
            return combine_polygon_parts(open_parts, closed_parts, tol)

    if not open_parts or len(open_parts) == 0:
        return [], closed_parts
    
    n = len(open_parts)
    already_combined = set()
    combined_open_parts = []
    is_any_combined = False
    for i in range(n):
        for j in range(i + 1, n):
            combine, new_part = _combine_open_parts(open_parts[i], open_parts[j], tol)
            if combine:
                already_combined.add(i)
                already_combined.add(j)
                combined_open_parts.append(new_part)
                is_any_combined = True
   
    if is_any_combined:
        non_combined_open_parts = [part for i, part in enumerate(open_parts) if i not in already_combined]
        open_parts = non_combined_open_parts + combined_open_parts
        return combine_polygon_parts(open_parts, closed_parts, tol)
    
    for open_part in open_parts:
        for closed_part in closed_parts:
            if is_open_part_inside_closed_part(open_part, closed_part):
                closed_part.handles.extend(open_part.handles)
                open_parts.remove(open_part)
                return combine_polygon_parts(open_parts, closed_parts, tol)
   
    print("Open parts are not inside any closed parts")
    print(f"Open parts length: {len(open_parts)}")
    print(f"Open parts: {[part.handles for part in open_parts]}")
    print(f"Closed parts: {[part.handles for part in closed_parts]}")
   
    raise ValueError("Open parts are not inside any closed parts")
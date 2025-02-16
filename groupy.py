from shapely.geometry import LineString
from shapely.ops import polygonize
from shapely.geometry import Polygon

from dxf_utils import DXFEntityPrimitives

class DXFPolygonGroup:
    """
    Represents a polygon formed by a group of DXFEntityPrimitives.
    
    Attributes:
        polygon: A Shapely polygon formed by connected line segments.
        dxf_entities: A list of DXFEntityPrimitives instances that contributed to the polygon.
    """
    def __init__(self, polygon, dxf_entities):
        self.polygon = polygon
        self.dxf_entities: list[DXFEntityPrimitives] = dxf_entities

    def __repr__(self):
        return f"DXFPolygonGroup(polygon={self.polygon}, dxf_entities={self.dxf_entities})"

def line_contributes_to_polygon(line, polygon, tol=1e-6):
    """
    Determines if a given line (a Shapely LineString) should be associated
    with the polygon. It returns True if the line's midpoint is either very
    near the polygon's boundary or inside the polygon.
    
    Parameters:
        line (LineString): The line representation of a primitive.
        polygon (Polygon): A Shapely polygon.
        tol (float): Tolerance for considering a point as "on" the boundary.
    
    Returns:
        bool: True if the line is on or inside the polygon, else False.
    """
    midpoint = line.interpolate(0.5, normalized=True)
    on_boundary = polygon.exterior.distance(midpoint) < tol
    inside = polygon.contains(midpoint)
    return on_boundary or inside

def customRound(value):
    removed = value * 1000000 // 1 / 1000000
    return round(removed, 5)

def group_dxf_entities_into_polygons(entities, tol=1e-6) -> list[DXFPolygonGroup]:
    """
    Given a list of DXFEntityPrimitives objects, create polygon groups where each
    group contains a Shapely polygon and a list of the entities that contributed to
    that polygon (either by having primitives on the boundary or inside the polygon).
    
    This function uses each primitive's vertices() method to generate line segments.
    
    Parameters:
        entities (list): List of DXFEntityPrimitives instances.
        tol (float): Tolerance used for geometric comparisons.
    
    Returns:
        List of DXFPolygonGroup instances.
    """
    lines = []
    for entity in entities:
        for primitive in entity.primitives:
            verts = list(primitive.vertices())
            if len(verts) < 2:
                continue
            for i in range(len(verts) - 1):
                startX = customRound(verts[i][0])
                startY = customRound(verts[i][1])
                endX = customRound(verts[i+1][0])
                endY = customRound(verts[i+1][1])
                pt1 = (startX, startY)
                pt2 = (endX, endY)
                line = LineString([pt1, pt2])
                lines.append(line)

    polygons = list(polygonize(lines))
    # sort plogygons by area from biggest to smallest
    polygons.sort(key=lambda x: x.area, reverse=True)
    print(f"Extracted {len(polygons)} polygons.")
    
    polygon_groups : list[DXFPolygonGroup] = []
    pIndex = 0;
    for poly in polygons:
        pIndex += 1
        print(f"Processing polygon {pIndex} of {len(polygons)}")
        group_entities = set()
        for entity in entities:
            for primitive in entity.primitives:
                verts = list(primitive.vertices())
                if len(verts) < 2:
                    continue
                for i in range(len(verts) - 1):
                    pt1 = (verts[i][0], verts[i][1])
                    pt2 = (verts[i+1][0], verts[i+1][1])
                    line = LineString([pt1, pt2])
                    if line_contributes_to_polygon(line, poly, tol):
                        group_entities.add(entity)
                        break
                else:
                    continue
                break
        polygon_groups.append(DXFPolygonGroup(poly, list(group_entities)))

    print(f"Grouped into {len(polygon_groups)} polygon groups.")
    
    # Step 4: Detect nested polygons and merge entities
    # We will iterate over all pairs of polygons and check if one is within another.
    removed_indices = set()
    for i in range(len(polygon_groups)):
        if i in removed_indices:
            continue
        poly_i = Polygon(polygon_groups[i].polygon.exterior)
        
        for j in range(len(polygon_groups)):
            if i == j or j in removed_indices:
                continue

            poly_j = Polygon(polygon_groups[j].polygon.exterior)
            
            # Check if polygon i is within polygon j
            if poly_i.within(poly_j):
                # polygon i is inside polygon j
                # --> move i's entities to j
                polygon_groups[j].dxf_entities.extend(polygon_groups[i].dxf_entities)
                # mark i for removal
                removed_indices.add(i)
                break
            
            # OR check if polygon j is within polygon i
            elif poly_j.within(poly_i):
                # polygon j is inside polygon i
                # --> move j's entities to i
                polygon_groups[i].dxf_entities.extend(polygon_groups[j].dxf_entities)
                # mark j for removal
                removed_indices.add(j)

    print(f"Removed {len(removed_indices)} nested polygons.")
    
    # Step 5: Filter out removed polygon groups
    final_polygon_groups = [
        pg for idx, pg in enumerate(polygon_groups)
        if idx not in removed_indices
    ]

    return final_polygon_groups
    

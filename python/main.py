# /usr/bin/env python
"""
A DXF processing script that:
  - Reads a DXF file using ezdxf 1.4.0.
  - Extracts eligible entities (LINE, ARC, ELLIPSE, SPLINE, LWPOLYLINE, POLYLINE).
  - Separates entities that are already closed (e.g. closed LWPOLYLINEs) from open entities.
  - For open entities, it uses ezdxf.edgeminer and edgesmith to extract edges,
    builds edge loops, and polygonizes them.
  - Processes closed entities by extracting their vertex data.
  - Combines the results and plots the resulting polygons using matplotlib.
"""

import sys
from typing import Sequence, Iterable, List
import ezdxf
from ezdxf.edgeminer import Deposit, Edge, find_all_loops
from ezdxf.edgesmith import edges_from_entities_2d, is_closed_entity
from ezdxf.math import Vec3
from ezdxf.entities.dxfentity import DXFEntity
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize

# Global tolerance used for gap matching when processing edges.
GAP_TOL = 1.5


def process_closed_entity(entity: DXFEntity) -> Polygon:
    """
    Process a closed DXF entity (e.g. LWPOLYLINE or POLYLINE with closed flag) and return
    a Shapely Polygon.
    """
    etype = entity.dxftype()
    if etype in {'LWPOLYLINE', 'POLYLINE'}:
        pts = [tuple(pt[:2]) for pt in entity.get_points()]
        # Ensure the polyline loop is closed
        if pts and pts[0] != pts[-1]:
            pts.append(pts[0])
        poly = Polygon(pts)
        return poly
    else:
        # Extend here if you wish to support other closed entity types.
        raise ValueError(
            f"Entity type {etype} not supported as a closed entity.")


def process_closed_entities(entities: Iterable[DXFEntity]) -> List[Polygon]:
    """
    Processes all closed entities and returns a list of Shapely Polygons.
    """
    polygons = []
    for entity in entities:
        try:
            poly = process_closed_entity(entity)
            polygons.append(poly)
        except Exception as e:
            print(f"Error processing closed entity {entity.dxf.handle}: {e}")
    return polygons


def process_open_entities(entities: Iterable[DXFEntity]) -> List[Polygon]:
    """
    Processes open entities:
      - Extracts 2D edges from entities.
      - Deposits the edges and finds loops using ezdxf.edgeminer.
      - Converts the edge loops into Shapely LineStrings and then polygonizes them.
    Returns a list of Shapely Polygons.
    """
    edge_list = list(edges_from_entities_2d(entities, gap_tol=GAP_TOL))
    print(f"Extracted {len(edge_list)} edges from open entities.")

    deposit = Deposit(edge_list, gap_tol=GAP_TOL)
    loops: Sequence[Sequence[Edge]] = find_all_loops(deposit)
    print(f"Found {len(loops)} loops from open entities.")

    # Convert each edge of every loop into a Shapely LineString.
    line_segments = []
    for loop in loops:
        print(f"Processing a loop with {len(loop)} edges.")
        for edge in loop:
            start: Vec3 = edge.start
            end: Vec3 = edge.end
            print(f"  Edge from {start} to {end}")
            pt1 = (start.x, start.y)
            pt2 = (end.x, end.y)
            line = LineString([pt1, pt2])
            line_segments.append(line)

    # Use Shapely's polygonize to merge connected lines into polygons.
    polygons = list(polygonize(line_segments))
    return polygons


def plot_polygons(polygons: List[Polygon], title: str = "DXF Polygons") -> None:
    """
    Plots a list of polygons using matplotlib.
    """
    fig, ax = plt.subplots()
    ax.set_aspect('equal', 'box')
    ax.set_title(title)
    ax.set_xlabel('X-axis')
    ax.set_ylabel('Y-axis')
    ax.grid(True)
    ax.set_axisbelow(True)

    # Optionally, you could compute bounds from the polygons; here we use default limits.
    for poly in polygons:
        if not poly.is_empty and poly.exterior:
            x, y = poly.exterior.xy
            ax.plot(x, y, color='blue', linewidth=2)

    plt.show()


def do_file(file_path: str) -> None:
    """
    Processes the specified DXF file:
      - Reads the file.
      - Separates closed and open eligible entities.
      - Processes each group and plots the final polygons.
    """
    print("Processing DXF file:", file_path)
    try:
        doc = ezdxf.readfile(file_path)
    except IOError:
        print("Not a DXF file or a generic I/O error.")
        sys.exit(1)
    except ezdxf.DXFStructureError:
        print("Invalid or corrupted DXF file.")
        sys.exit(2)

    msp = doc.modelspace()
    eligible_types = {'LINE', 'ARC', 'ELLIPSE',
                      'SPLINE', 'LWPOLYLINE', 'POLYLINE'}
    entities = [e for e in msp if e.dxftype() in eligible_types]

    closed_entities = []
    open_entities = []
    for entity in entities:
        if is_closed_entity(entity):
            closed_entities.append(entity)
        else:
            open_entities.append(entity)

    print(f"Total eligible entities: {len(entities)}")
    print(f"Closed entities: {len(closed_entities)}")
    print(f"Open entities: {len(open_entities)}")

    closed_polys = process_closed_entities(closed_entities)
    print(f"Processed {len(closed_polys)} polygons from closed entities.")

    open_polys = process_open_entities(open_entities)
    print(f"Processed {len(open_polys)} polygons from open entities.")

    # Combine all resulting polygons.
    all_polygons = closed_polys + open_polys

    plot_polygons(all_polygons, "DXF Loops and Closed Entities")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <DXF_FILE_PATH>")
        sys.exit(1)
    do_file(sys.argv[1])


if __name__ == "__main__":
    main()

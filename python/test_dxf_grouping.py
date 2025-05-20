import argparse

import ezdxf
from polygone import find_closed_polygons
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString


def main():
    parser = argparse.ArgumentParser(description="Find closed polygons in a DXF file.")
    parser.add_argument("dxf_path", type=str, help="Path to the DXF file.")
    parser.add_argument("--tolerance", type=float, default=0.01, help="Gap tolerance for edge joining (default: 0.01)")
    args = parser.parse_args()
    
    try:
        with open(args.dxf_path, 'r', encoding='utf-8') as f:
            doc = ezdxf.read(f)
        msp = doc.modelspace()
        # Filter out TEXT and MTEXT entities
        entities = [e for e in msp if e.dxftype() in ("LINE", "ARC", "ELLIPSE", "SPLINE", "LWPOLYLINE", "POLYLINE", "CIRCLE") 
                   and e.dxftype() not in ("TEXT", "MTEXT")]
        print(f"Found {len(entities)} entities in DXF file (excluding text)")
        print("Entity handles:")
        for ent in entities:
            print(f"  {ent.dxftype()}: {ent.dxf.handle}")
    except Exception as e:
        print(f"Error reading DXF file: {e}")
        return

    try:
        results = find_closed_polygons(args.dxf_path, args.tolerance)
    except Exception as e:
        print(f"Error: {e}")
        return

    print(f"Found {len(results)} closed polygons.")
    for i, poly in enumerate(results):
        print(f"\nPolygon {i+1}:")
        print(f"  Vertices: {poly['vertices']}")
        print(f"  Handles: {[getattr(e, 'dxf', getattr(e, 'handle', str(e))).handle if hasattr(getattr(e, 'dxf', getattr(e, 'handle', e)), 'handle') else getattr(e, 'handle', str(e)) for e in poly['entities']]}")
        print(f"  Contained handles: {poly.get('contained_handles', [])}")
        
    # Get all unique handles from both sources
    all_handles = set()
    for poly in results:
        # Add handles from entities
        for ent in poly['entities']:
            handle = getattr(ent, 'dxf', getattr(ent, 'handle', str(ent))).handle if hasattr(getattr(ent, 'dxf', getattr(ent, 'handle', ent)), 'handle') else getattr(ent, 'handle', str(ent))
            all_handles.add(handle)
        # Add contained handles
        all_handles.update(poly.get('contained_handles', []))
        
    # Get all handles from original DXF entities
    original_handles = {ent.dxf.handle for ent in entities}
    
    # Find handles that exist in original DXF but not in all_handles
    missing_handles = original_handles - all_handles
    
    if missing_handles:
        print("\nHandles in original DXF but not included in any polygon:")
        for handle in sorted(missing_handles):
            print(f"  {handle}")
    else:
        print("\nAll handles from original DXF are included in polygons.")
    
    # Plot all polygons
    plt.figure(figsize=(8, 8))
    for poly in results:
        verts = poly['vertices']
        if len(verts) > 1:
            xs, ys = zip(*verts)
            plt.plot(xs, ys, marker='o')
    plt.title('Closed Polygons from DXF')
    plt.gca().set_aspect('equal', adjustable='box')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.grid(True)
    plt.show()

    print("\n--- Debugging missing entities ---")
    for ent in entities:
        if ent.dxf.handle in missing_handles:
            print(f"\nEntity handle: {ent.dxf.handle}")
            print(f"  Type: {ent.dxftype()}")
            # Try to extract geometry
            try:
                if ent.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                    pts = [tuple(p[:2]) for p in getattr(ent, 'get_points', lambda: getattr(ent, 'points', lambda: [])())()]
                    print(f"  Points: {pts}")
                    print(f"  Closed: {getattr(ent, 'closed', None)}")
                    if len(pts) > 2:
                        geom = Polygon(pts)
                    elif len(pts) > 1:
                        geom = LineString(pts)
                    else:
                        geom = None
                elif ent.dxftype() == "LINE":
                    pts = [(ent.dxf.start[0], ent.dxf.start[1]), (ent.dxf.end[0], ent.dxf.end[1])]
                    print(f"  Points: {pts}")
                    geom = LineString(pts)
                else:
                    print("  (Geometry extraction not implemented for this type)")
                    continue
                # Check relation to polygons
                if geom is not None:
                    for i, poly in enumerate(results):
                        poly_geom = Polygon(poly['vertices'])
                        print(f"    Polygon {i+1}:")
                        print(f"      within: {geom.within(poly_geom)}")
                        print(f"      intersects: {geom.intersects(poly_geom)}")
                        print(f"      touches: {geom.touches(poly_geom)}")
            except Exception as e:
                print(f"  [Error extracting geometry: {e}]")


if __name__ == "__main__":
    main() 
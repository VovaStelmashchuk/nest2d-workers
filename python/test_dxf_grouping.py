import argparse
from polygone import find_closed_polygons


def main():
    parser = argparse.ArgumentParser(description="Find closed polygons in a DXF file.")
    parser.add_argument("dxf_path", type=str, help="Path to the DXF file.")
    parser.add_argument("--tolerance", type=float, default=0.01, help="Gap tolerance for edge joining (default: 0.01)")
    args = parser.parse_args()

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


if __name__ == "__main__":
    main() 
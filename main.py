#!/usr/bin/env python
import sys
import matplotlib.pyplot as plt

from dxf_utils import get_entity_primitives
from groupy import group_dxf_entities_into_polygons, DXFPolygonGroup
from dxf_utils import DXFEntityPrimitives

import io
import ezdxf


def main():
    if len(sys.argv) < 2:
        print("Usage: python dxf_to_paths.py <dxf_file>")
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, 'r') as f:
        fileStrContent = f.read()

    stream = io.StringIO(fileStrContent)

    dxf_entities: list[DXFEntityPrimitives] = get_entity_primitives(stream)

    paths = []
    for entity in dxf_entities:
        paths.extend(entity.get_paths())
    print(f"Extracted {len(paths)} path objects.")

    polygon_groups: list[DXFPolygonGroup] = group_dxf_entities_into_polygons(
        dxf_entities
    )

    print(f"Grouped into {len(polygon_groups)} polygon groups.")

    for i in range(len(polygon_groups)):
        print(f"Group {i} has {len(polygon_groups[i].dxf_entities)} entities")
        doc = ezdxf.new("R2010", setup=True)
        msp = doc.modelspace()
        pGroup: DXFPolygonGroup = polygon_groups[i]
        for dxf_entity_primitives in pGroup.dxf_entities:
            print(type(dxf_entity_primitives))
            copy = dxf_entity_primitives.entity.copy()
            msp.add_entity(copy)

        doc.saveas(f"output/group_{i}.dxf")

    fig, ax = plt.subplots(figsize=(10, 8))

    for group in polygon_groups:
        poly = group.polygon
        if poly.is_empty:
            continue
        x, y = poly.exterior.xy
        ax.plot(x, y, 'r-', linewidth=1)  # Draw polygon boundary in red.
        ax.fill(x, y, alpha=0.3, fc='r', ec='none')

    ax.set_title("DXF Paths and Grouped Polygons")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_aspect('equal', adjustable='box')
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()

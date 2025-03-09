from dxf_utils import get_entity_primitives, DXFEntityPrimitives
from groupy import group_dxf_entities_into_polygons, DXFPolygonGroup


def create_svg(dxf_stream):
    print("Creating SVG from DXF")

    dxf_entities: list[DXFEntityPrimitives] = get_entity_primitives(dxf_stream)

    paths = []
    for entity in dxf_entities:
        paths.extend(entity.get_paths())

    print(f"Extracted {len(paths)} path objects.")

    polygon_groups: list[DXFPolygonGroup] = group_dxf_entities_into_polygons(
        dxf_entities
    )

    all_x = []
    all_y = []
    for group in polygon_groups:
        poly = group.polygon
        if poly.is_empty:
            continue
        xs, ys = poly.exterior.xy
        all_x.extend(xs)
        all_y.extend(ys)
    if all_x and all_y:
        min_x = min(all_x)
        max_x = max(all_x)
        min_y = min(all_y)
        max_y = max(all_y)
    else:
        min_x, max_x, min_y, max_y = 0, 100, 0, 100

    width = max_x - min_x
    height = max_y - min_y

    svg_parts = []
    svg_parts.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="{min_x} {min_y} {width} {height}">')

    for group in polygon_groups:
        poly = group.polygon
        if poly.is_empty:
            continue
        xs, ys = poly.exterior.xy
        points = " ".join(f"{x},{y}" for x, y in zip(xs, ys))
        svg_parts.append(
            f'<polygon points="{points}" fill="none" stroke="black" stroke-width="0.5" />')

    svg_parts.append("</svg>")

    svg_content = "\n".join(svg_parts)

    return svg_content


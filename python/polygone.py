#!/usr/bin/env python
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ezdxf.entities import DXFEntity
from gridfs import GridOut
from shapely import Point
from shapely.geometry import Polygon
from dxf_utils import read_dxf
from polygonizer.dto import ClosedPolygon
from polygonizer.main import close_polygon_from_dxf
from typing import Tuple
from ezdxf.document import Drawing

@dataclass
class DxfPolygon:
    polygon: Polygon
    entities: list[DXFEntity]

def _find_entity(doc: Drawing, handle: str) -> DXFEntity:
    for entity in doc.modelspace():
        if entity.dxf.handle == handle:
            return entity
    return None

def _polygone_to_shapely(polygon: ClosedPolygon) -> Polygon:
    points = [Point(point.x, point.y) for point in polygon.points]
    return Polygon(points)

def find_closed_polygons(dxf_stream: GridOut, tolerance: float) -> List[DxfPolygon]:
    """
    Loads a DXF file, finds all closed polygons, and returns their vertices and all associated entities (used, within, touching, or intersecting).

    Args:
        dxf_path (str): Path to the DXF file.
        tolerance (float): Gap tolerance for edge joining and flattening.

    Returns:
        List[Dict]: Each dict contains:
            - 'vertices': ordered list of 2D points (tuples)
            - 'entities': list of original DXF entity references (used, within, touching, or intersecting the polygon)
    """
    doc = read_dxf(dxf_stream)
    msp = doc.modelspace()
    
    layers_info = {}
    for layer in doc.layers:
        layers_info[layer.dxf.name] = {
            'name': layer.dxf.name,
            'color': layer.dxf.color,
        }
        
    color_map: dict[str, int] = {}
    
    for entity in msp:
        if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'layer'):
            layer_name = entity.dxf.layer
            if layer_name in layers_info:
                color = layers_info[layer_name]['color']
                entity.dxf.color = color 
                print(entity.dxf.get("handle"))
                color_map[entity.dxf.handle] = color 
    
    closed_polygons = close_polygon_from_dxf(doc, tolerance, "dxf_polygonizer")
                
    result = []
    for polygon in closed_polygons:
        result.append(
            DxfPolygon(
                polygon=_polygone_to_shapely(polygon),
                entities=[_find_entity(doc, handle) for handle in polygon.handles]
            )
        )
    return result
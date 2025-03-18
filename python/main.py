#!/usr/bin/env python
from re import I
import sys

import io

import ezdxf
from mongo import userDxfBucket
from nest import NestPolygone, NestRequest, NestRequest, NestResult, nest
from dxf_utils import get_entity_primitives
from groupy import group_dxf_entities_into_polygons


def main():
    if len(sys.argv) < 2:
        print("Usage: python dxf_to_paths.py <dxf_file>")
        sys.exit(1)

    fileSlug = sys.argv[1]

    binary_stream = userDxfBucket.open_download_stream_by_name(fileSlug)
    dxf_stream = io.TextIOWrapper(binary_stream, encoding="utf-8")
    dxf_entities = get_entity_primitives(dxf_stream)
    polygon_groups = group_dxf_entities_into_polygons(dxf_entities)

    nest_polygones = []
    for group in polygon_groups:
        nest_polygones.append(NestPolygone(group, 2))

    res: NestResult = nest(NestRequest(nest_polygones, 200, 200, 1.5))
    doc = ezdxf.new('R2000')
    msp = doc.modelspace()
    for entity in res.dxf_entities:
        msp.add_entity(entity)
    doc.saveas(f"{fileSlug}_nested.dxf")
    print(res)


if __name__ == '__main__':
    main()

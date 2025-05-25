import base64
import io
import argparse
from mongo import db, nestDxfBucket
from svg_generator import create_svg_from_doc
import ezdxf
import sys
from dxf_utils import read_dxf
from mongo import tmpBucket

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SVG from DXF file or last finished nesting job.")
    parser.add_argument("dxf_path", type=str, nargs="?", help="Path to the DXF file. If not provided, loads from last finished nesting job in DB.")
    args = parser.parse_args()
    
    # save dxf to tmp bucket
    with open(args.dxf_path, 'rb') as f:
        tmpBucket.upload_from_stream('test.dxf', f)

    # read dxf from tmp bucket
    grid_out = tmpBucket.find_one({"filename": "test.dxf"})
    doc = read_dxf(grid_out)

    # Generate SVG
    svg_string = create_svg_from_doc(doc)
    print(svg_string) 
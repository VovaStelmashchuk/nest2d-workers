import argparse
import json
from mongo import db, nestDxfBucket
from svg_generator import create_svg_from_doc
import ezdxf
from dxf_utils import read_dxf
from mongo import tmpBucket
from ezdxf.addons.drawing import RenderContext, Frontend, layout, config
from ezdxf.addons.drawing.json import CustomJSONBackend

def dxf_to_json(doc):
    """
    Convert DXF to GeoJSON format using ezdxf's GeoJSONBackend
    """
    msp = doc.modelspace()
    
    # Create rendering context and backend
    context = RenderContext(doc)
    backend = CustomJSONBackend()
    
    # Configure rendering
    cfg = config.Configuration(
        background_policy=config.BackgroundPolicy.OFF,
        color_policy=config.ColorPolicy.BLACK,
        max_flattening_distance=0.01,
        lineweight_policy=config.LineweightPolicy.ABSOLUTE,
        lineweight_scaling=1.0
    )
    
    # Create frontend and render
    frontend = Frontend(context, backend, cfg)
    frontend.draw_layout(msp, finalize=True)
    
    # Get GeoJSON data
    json_data = backend.get_json_data()
    
    return json_data
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SVG from DXF file or last finished nesting job.")
    parser.add_argument("dxf_path", type=str, nargs="?", help="Path to the DXF file. If not provided, loads from last finished nesting job in DB.")
    args = parser.parse_args()
    
    # save dxf to tmp bucket
    with open(args.dxf_path, 'rb') as f:
        tmpBucket.upload_from_stream('test.dxf', f)

    # read dxf from tmp bucket
    grid_out = tmpBucket.open_download_stream_by_name("test.dxf")
    doc = read_dxf(grid_out)

    # Generate SVG
    svg_string = create_svg_from_doc(doc)
    # print(svg_string) 
    
    # Generate GeoJSON
    json_data = dxf_to_json(doc)
    print(json_data)
    
    # save geojson to file 
    with open("test.json", "w") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    # save svg to file 
    with open("test.svg", "w") as f:
        f.write(svg_string)
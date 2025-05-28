import sys
from dxf_utils import read_dxf

from mongo import tmpBucket

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python python/dxf_debug.py <path to dxf file>")
        sys.exit(1)
    path = sys.argv[1]
    

    with open(path, 'rb') as f:
        file_id = tmpBucket.upload_from_stream('test.dxf', f)
        print(f"File uploaded with ID: {file_id}")
    
    try:
        grid_out = tmpBucket.open_download_stream(file_id=file_id)
        doc = read_dxf(grid_out)
        msp = doc.modelspace()
        units = doc.header.get('$INSUNITS', 0)
        print(f"Units: {units}")
        print(f"Loaded DXF file: {path}")
        print(f"Number of entities in modelspace: {len(list(msp))}")
    except Exception as e:
        print(f"Error loading DXF: {e}")
        sys.exit(1)

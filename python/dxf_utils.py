import tempfile
import ezdxf
from ezdxf.document import Drawing
from gridfs.synchronous.grid_file import GridOut

def read_dxf(dxf_stream: GridOut) -> Drawing:
    """
    Reads a DXF stream and returns the modelspace without entities TEXT and MTEXT.

    Parameters:
        dxf_stream: The DXF string to process.

    Returns:
        Modelspace: The modelspace of the DXF document.
    """
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(dxf_stream.read())
        temp_file_path = temp_file.name

    doc = ezdxf.readfile(temp_file_path)
    msp = doc.modelspace()

    text_entities = [entity for entity in msp if entity.dxftype()
                     in ("TEXT", "MTEXT")]

    for entity in text_entities:
        msp.delete_entity(entity)

    return doc

def read_dxf_file(dxf_path: str) -> Drawing:
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    text_entities = [entity for entity in msp if entity.dxftype()
                     in ("TEXT", "MTEXT")]

    for entity in text_entities:
        msp.delete_entity(entity)

    return doc
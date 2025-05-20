import ezdxf
from typing import TextIO
from ezdxf.document import Drawing

def read_dxf(dxf_stream: TextIO) -> Drawing:
    """
    Reads a DXF stream and returns the modelspace without entities TEXT and MTEXT.

    Parameters:
        dxf_stream: The DXF string to process.

    Returns:
        Modelspace: The modelspace of the DXF document.
    """
    doc = ezdxf.read(dxf_stream)
    msp = doc.modelspace()

    text_entities = [entity for entity in msp if entity.dxftype()
                     in ("TEXT", "MTEXT")]

    for entity in text_entities:
        msp.delete_entity(entity)

    return doc

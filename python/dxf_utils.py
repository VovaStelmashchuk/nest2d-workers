import io
import ezdxf

from ezdxf.disassemble import (
    Primitive,
    to_paths,
    recursive_decompose,
    to_primitives
)
from ezdxf.entities.dxfentity import DXFEntity


class DXFEntityPrimitives:
    """
    Stores a DXF entity and the list of primitives generated from that entity.

    Attributes:
        entity: The source DXF entity.
        primitives: A list of primitive objects generated from this entity.
    """

    def __init__(self, entity):
        self.entity: DXFEntity = entity
        # List to store the associated primitives
        self.primitives: list[Primitive] = []

    def add_primitive(self, primitive: Primitive):
        """Add a primitive to the list."""
        self.primitives.append(primitive)

    def get_paths(self):
        return to_paths(self.primitives)


def extract_entity_primitives(msp, max_flattening_distance=0.01) -> list[DXFEntityPrimitives]:
    """
    Decomposes the DXF modelspace and converts the resulting entities into primitives.
    Primitives are grouped by their source DXF entity.

    Parameters:
        msp: The DXF modelspace.
        max_flattening_distance: The maximum flattening distance for curve approximation.

    Returns:
        List[DXFEntityPrimitives]: A list of DXFEntityPrimitives objects.
    """
    # Recursively decompose nested block references and complex entities:
    flat_entities = list(recursive_decompose(msp))

    # Convert the flat entities into primitives:
    primitives: list[Primitive] = list(to_primitives(
        flat_entities, max_flattening_distance=max_flattening_distance))

    # Group primitives by their source DXF entity:
    entity_dict = {}  # Key: DXF handle, Value: DXFEntityPrimitives instance
    for prim in primitives:
        # Only consider primitives that provide a valid path representation.
        if prim.path is None:
            continue
        try:
            handle = prim.entity.dxf.handle
        except AttributeError:
            continue  # Skip if no DXF handle is available.

        if handle not in entity_dict:
            entity_dict[handle] = DXFEntityPrimitives(prim.entity)
        entity_dict[handle].add_primitive(prim)

    return list(entity_dict.values())


def get_entity_primitives(dxf_stream, max_flattening_distance=0.01) -> list[DXFEntityPrimitives]:
    """
    Reads a DXF string and extracts DXF entity primitives.

    Parameters:
        dxf_stream: The DXF string to process.
        max_flattening_distance: Maximum flattening distance for curve approximation.

    Returns:
        List[DXFEntityPrimitives]: A list of DXFEntityPrimitives objects extracted from the DXF.
    """
    doc = ezdxf.read(dxf_stream)
    msp = doc.modelspace()
    return extract_entity_primitives(msp, max_flattening_distance=max_flattening_distance)

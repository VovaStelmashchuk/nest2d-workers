import os
import ezdxf


def main():
    print("Hello, World!")
    
    filepath = os.path.expanduser('~/Downloads/pavlo_file_colors.dxf')
    
    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()
    
    color_counts = {}
    for entity in msp:
        color = entity.dxf.color
        color_counts[color] = color_counts.get(color, 0) + 1
    
    print("Color counts:")
    for color, count in color_counts.items():
        print(f"  Color {color}: {count} entities")
    # Get layer information for each entity
    print("\nEntity layer information:")
    for entity in msp:
        layer_name = entity.dxf.layer
        layer = doc.layers.get(layer_name)
        print(f"  Entity: {entity.dxftype()}")
        print(f"    Layer: {layer_name}")
        print(f"    Layer color: {layer.dxf.color}")
        print()
        
    # Get all layers
    layers = doc.layers
    print("\nAll layers in the DXF file:")
    for layer in layers:
        print(f"  Layer: {layer}")
        print(f"    Color: {layer.dxf.color}")
        print()

if __name__ == "__main__":
    main() 
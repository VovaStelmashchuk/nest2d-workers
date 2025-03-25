from ezdxf import bbox
from ezdxf.addons.drawing import RenderContext, Frontend, layout
from ezdxf.addons.drawing import svg
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout, config


def create_svg_from_modelspace(doc, max_flattening_distance=0.01):
    msp = doc.modelspace()
    # get overall bounding box
    doc_bbox = bbox.extents(msp)

    # Calculate width and height from the bounding box.
    drawing_width = doc_bbox.extmax[0] - doc_bbox.extmin[0]
    drawing_height = doc_bbox.extmax[1] - doc_bbox.extmin[1]

    # 2. Set up the rendering: create the context, backend, and frontend.
    context = RenderContext(doc)
    backend = svg.SVGBackend()

    cfg = config.Configuration(
        background_policy=config.BackgroundPolicy.OFF,
        color_policy=config.ColorPolicy.BLACK,
        max_flattening_distance=max_flattening_distance,
    )
    frontend = Frontend(context, backend, cfg)

    frontend.draw_layout(msp, finalize=True)

    page = layout.Page(drawing_width, drawing_height,
                       layout.Units.mm, margins=layout.Margins.all(8))

    # 5. Get the SVG string using the computed page dimensions.
    svg_string = backend.get_string(page)
    return svg_string

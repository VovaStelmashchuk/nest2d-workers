from ezdxf import bbox
from ezdxf.addons.drawing import RenderContext, Frontend, layout
from ezdxf.addons.drawing import svg
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout, config


def create_svg_from_doc(doc, max_flattening_distance=0.01):
    msp = doc.modelspace()
    doc_bbox = bbox.extents(msp)

    drawing_width = doc_bbox.extmax[0] - doc_bbox.extmin[0]
    drawing_height = doc_bbox.extmax[1] - doc_bbox.extmin[1]

    context = RenderContext(doc)
    backend = svg.SVGBackend()

    cfg = config.Configuration(
        background_policy=config.BackgroundPolicy.OFF,
        color_policy=config.ColorPolicy.BLACK,
        max_flattening_distance=max_flattening_distance,
        lineweight_policy=config.LineweightPolicy.ABSOLUTE,
        lineweight_scaling=2.0
    )
    frontend = Frontend(context, backend, cfg)

    frontend.draw_layout(msp, finalize=True)

    page = layout.Page(drawing_width, drawing_height,
                       layout.Units.mm, margins=layout.Margins.all(8))

    svg_string = backend.get_string(page)
    return svg_string

from ezdxf.addons.drawing import svg, layout
from xml.etree import ElementTree as ET

class SVGRenderBackendWithHandle(svg.SVGRenderBackend):
    def add_strokes(self, d: str, properties):
        if not d:
            return
        element = ET.SubElement(self.entities, "path", d=d)
        stroke_width = self.resolve_stroke_width(properties.lineweight)
        stroke_color, stroke_opacity = self.resolve_color(properties.color)
        cls = self.styles.get_class(
            stroke=stroke_color,
            stroke_width=stroke_width,
            stroke_opacity=stroke_opacity,
        )
        element.set("class", cls)
        if hasattr(properties, 'handle') and properties.handle:
            element.set("data-dxf-handle", properties.handle)

    def add_filling(self, d: str, properties):
        if not d:
            return
        element = ET.SubElement(self.entities, "path", d=d)
        fill_color, fill_opacity = self.resolve_color(properties.color)
        cls = self.styles.get_class(fill=fill_color, fill_opacity=fill_opacity)
        element.set("class", cls)
        if hasattr(properties, 'handle') and properties.handle:
            element.set("data-dxf-handle", properties.handle)

class SVGBackendWithHandle(svg.SVGBackend):
    @staticmethod
    def make_backend(page: layout.Page, settings: layout.Settings):
        return SVGRenderBackendWithHandle(page, settings) 
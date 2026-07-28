"""
SVG version of the Pillow visualizer.

Simple SVG generation that matches the PIL interface.
Serge Beaumont / Claude, 2025
"""

from arena.engine.objects.objectinspace import Point
from arena.engine.reporting.visualize import COLORS, Colors

BACKGROUND_COLOR = Colors.Black


class SVGVisualizer:
    """SVG equivalent of the PIL Visualizer."""
    
    @classmethod
    def boundaries(cls, pts, padding=1):
        """Same as PIL version."""
        min_x = min([p[0] for p in pts])
        max_x = max([p[0] for p in pts])
        min_y = min([p[1] for p in pts])
        max_y = max([p[1] for p in pts])
        return min_x - padding, min_y - padding, max_x + padding, max_y + padding

    def __init__(self, boundaries, scale=1, flip_vertical=True, initial_viewport=None):
        self.scale = scale
        self.flip_vertical = flip_vertical
        x1, y1, x2, y2 = boundaries
        self.b_min = self._scale_point(Point(x1, y1))
        self.b_max = self._scale_point(Point(x2, y2))
        self.width = abs(round(self.b_max.x - self.b_min.x))
        self.height = abs(round(self.b_max.y - self.b_min.y))
        self.elements = []
        self.initial_viewport = initial_viewport

    def _scale_point(self, p: Point) -> Point:
        return Point(round(p.x * self.scale), round(p.y * self.scale))

    def _to_image_coords(self, point: Point) -> Point:
        p = self._scale_point(point)
        p = Point(p.x - self.b_min.x, p.y - self.b_min.y)
        if self.flip_vertical:
            p = Point(p.x, self.height - p.y)
        return p

    def draw_point(self, point, color=COLORS[Colors.White], size=1):
        p = self._to_image_coords(point)
        self.elements.append(f'<circle cx="{p.x}" cy="{p.y}" r="{size}" fill="{color.as_svg_color()}" vector-effect="non-scaling-stroke"/>')

    def draw_square(self, point, color=COLORS[Colors.White], size=1):
        p = self._to_image_coords(point)
        self.elements.append(f'<rect x="{p.x-size}" y="{p.y-size}" width="{size*2}" height="{size*2}" fill="{color.as_svg_color()}" vector-effect="non-scaling-stroke"/>')

    def draw_circle(self, point, color=COLORS[Colors.White], size=5):
        p = self._to_image_coords(point)
        self.elements.append(f'<circle cx="{p.x}" cy="{p.y}" r="{size}" fill="{color.as_svg_color()}" vector-effect="non-scaling-stroke"/>')

    def draw_points(self, points, color=COLORS[Colors.White], size=1):
        for point in points:
            self.draw_point(point, color, size)

    def draw_line(self, line, color=COLORS[Colors.White], width=1):
        p1 = self._to_image_coords(line[0])
        p2 = self._to_image_coords(line[1])
        self.elements.append(f'<line x1="{p1.x}" y1="{p1.y}" x2="{p2.x}" y2="{p2.y}" stroke="{color.as_svg_color()}" stroke-width="{width}" vector-effect="non-scaling-stroke"/>')

    def draw_lines(self, lines, color=COLORS[Colors.White], width=1):
        for line in lines:
            self.draw_line(line, color, width=width)

    def draw_polyline(self, points, color=COLORS[Colors.White], width=1):
        for i in range(1, len(points)):
            self.draw_line((points[i-1], points[i]), color, width)

    def text(self, point, msg):
        p = self._to_image_coords(point)
        text = msg.replace('\n', ' ')
        self.elements.append(f'<text x="{p.x}" y="{p.y}" fill="white" font-family="monospace" font-size="4">{text}</text>')

    def to_svg(self):
        """Generate clean SVG content."""
        # Create viewBox based on actual content dimensions
        initial_viewbox = f"0 0 {self.width} {self.height}"
        svg = f'<svg viewBox="{initial_viewbox}" xmlns="http://www.w3.org/2000/svg"'
        
        # Add initial viewport as data attribute if provided
        if self.initial_viewport:
            x1, y1, x2, y2 = self.initial_viewport
            # Convert to image coordinates
            p1 = self._to_image_coords(Point(x1, y1))
            p2 = self._to_image_coords(Point(x2, y2))
            svg += f' data-initial-viewport="{p1.x},{p1.y},{p2.x},{p2.y}"'
        
        svg += '>\n'
        svg += f'<rect width="100%" height="100%" fill="{COLORS[BACKGROUND_COLOR].as_svg_color()}"/>\n'
        for element in self.elements:
            svg += element + '\n'
        svg += '</svg>'
        return svg

    def save(self, file_name):
        """Save as SVG file."""
        with open(file_name, 'w') as f:
            f.write(self.to_svg())
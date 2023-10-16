"""
Utility library to easily create visualizations, wrapping the Pillow library.

Originally created for code challenges (Advent Of Code!!!), although there have been some changes since and this
version is by now unique to the game.

Serge Beaumont, december 2019
"""

from PIL import Image, ImageDraw
from collections import namedtuple
from ois.objectinspace import Point
from enum import Enum, auto

Color = namedtuple('Color', 'R G B')


class Colors(Enum):
    Black  = auto()
    Blue   = auto()
    Green  = auto()
    Red    = auto()
    Yellow = auto()
    White  = auto()


COLORS = {
    Colors.Black: Color(R=0, G=0, B=0),
    Colors.Blue: Color(R=0, G=0, B=255),
    Colors.Green: Color(R=0, G=255, B=0),
    Colors.Red: Color(R=255, G=0, B=0),
    Colors.Yellow: Color(R=255, G=255, B=0),
    Colors.White: Color(R=255, G=255, B=255)
}

BACKGROUND_COLOR = Colors.Black
BLOCK = '\u2588'


class Visualizer(object):
    """Convenience wrapper around the Pillow library to draw graphics."""
    @classmethod
    def boundaries(cls, pts, padding=1):
        """Convenience function to calculate boundaries that will nicely fit all points to be drawn.
        Only useful if all points are known before drawing."""
        min_x = min([p[0] for p in pts])
        max_x = max([p[0] for p in pts])
        min_y = min([p[1] for p in pts])
        max_y = max([p[1] for p in pts])
        return min_x - padding, min_y - padding, max_x + padding, max_y + padding

    def __init__(self, boundaries, scale=1, flip_vertical=True):
        """boundaries allows you to set x and y boundaries that correspond to the puzzle values.
        This class will then calculate how this maps onto the image.
        Note that scale only scales coordinates, not line widths. Set those separately."""
        self.scale = scale
        self.flip_vertical = flip_vertical
        x1, y1, x2, y2 = boundaries
        self.b_min = self._scale_point(Point(x1, y1))
        self.b_max = self._scale_point(Point(x2, y2))
        self.im = Image.new('RGB',
                            (abs(round(self.b_max.x - self.b_min.x)),
                             abs(round(self.b_max.y - self.b_min.y))),
                            BACKGROUND_COLOR.value)
        self.draw = ImageDraw.Draw(self.im)

    def _scale_point(self, p: Point) -> Point:
        assert isinstance(p, Point)
        return Point(round(p.x * self.scale), round(p.y * self.scale))

    def _to_image_coords(self, point: Point) -> Point:
        assert isinstance(point, Point)
        # To create larger images of small coordinate spaces in a puzzle
        p = self._scale_point(point)
        # To deal with x and y values that are negative in the puzzle. Shift to positive image coordinates.
        p = Point(p.x - self.b_min.x, p.y - self.b_min.y)
        # Image origin is top left, needs to be bottom left.
        if self.flip_vertical:
            p = Point(p.x, self.im.height - p.y)
        return p

    def draw_point(self, point, color=COLORS[Colors.White], size=1):
        p = self._to_image_coords(point)
        self.draw.ellipse((p.x - size, p.y - size, p.x + size, p.y + size), fill=color)

    def draw_square(self, point, color=COLORS[Colors.White], size=1):
        p = self._to_image_coords(point)
        self.draw.rectangle((p.x - size, p.y - size, p.x + size, p.y + size), fill=color)

    def draw_circle(self, point, color=COLORS[Colors.White], size=5):
        p = self._to_image_coords(point)
        self.draw.ellipse((p.x - size, p.y - size, p.x + size, p.y + size), fill=color)

    def draw_points(self, points, color=COLORS[Colors.White], size=1):
        for point in points:
            self.draw_point(point, color, size)

    def draw_line(self, line, color=COLORS[Colors.White], width=1):
        x1, y1 = self._to_image_coords(line[0]).as_tuple
        x2, y2 = self._to_image_coords(line[1]).as_tuple
        self.draw.line((x1, y1, x2, y2), color, width=width)

    def draw_lines(self, lines, color=Colors.White.value, width=1):
        for line in lines:
            self.draw_line(line, color, width=width)

    def draw_polyline(self, points, color=Colors.White.value, width=1):
        for i in range(1, len(points)):
            self.draw_line((points[i-1], points[i]), color, width)

    def text(self, point, msg):
        self.draw.text(self._to_image_coords(point).as_tuple, msg)

    def show(self):
        self.im.show()

    def save(self, file_name):
        self.im.save(file_name, 'png')

import pyray as pr
from .colors import DIM

class VUMeter:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.level = 0.0  # 0.0 -> 1.0

    def set_level(self, value):
        self.level = max(0.0, min(1.0, value))

    def draw(self):
        pr.draw_rectangle_lines(self.x, self.y, self.w, self.h, DIM)

        for i in range(int(self.w * self.level)):
            t = i / self.w  # 0.0 -> 1.0
            r = int(255 * t)
            g = int(255 * (1 - t))
            b = 0
            pr.draw_rectangle(self.x + i, self.y, 1, self.h, (r, g, b, 255))


import pyray as pr
from .colors import BG, DIM
from .main_config import WINDOW_HEIGHT

class Panel:
    def __init__(self, w):
        self.w = w
        self.x = -w
        self.target = -w
        self.open = False

    def toggle(self):
        self.open = not self.open
        self.target = 0 if self.open else -self.w

    def update(self):
        self.x += (self.target - self.x) * 0.2
        if abs(self.x - self.target) < 1:
            self.x = self.target

    def draw(self):
        x = int(self.x)
        pr.draw_rectangle(x, 0, self.w, WINDOW_HEIGHT, BG)
        pr.draw_line(x + self.w, 0, x + self.w, WINDOW_HEIGHT, DIM)

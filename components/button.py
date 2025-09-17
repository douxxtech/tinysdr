import pyray as pr
from .colors import FG, DIM, ACCENT

class Button:
    def __init__(self, x, y, w, h, text, callback):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.text = text
        self.callback = callback
        self.hover = False

    def draw(self):
        color = ACCENT if self.hover else DIM
        pr.draw_rectangle_lines(self.x, self.y, self.w, self.h, color)
        
        tw = pr.measure_text(self.text.encode(), 16)
        tx = self.x + (self.w - tw) // 2
        ty = self.y + (self.h - 16) // 2
        pr.draw_text(self.text.encode(), tx, ty, 16, FG)

    def update(self):
        mouse = pr.get_mouse_position()
        self.hover = (self.x <= mouse.x <= self.x + self.w and 
                      self.y <= mouse.y <= self.y + self.h)
        
        if pr.is_mouse_button_pressed(pr.MOUSE_LEFT_BUTTON) and self.hover:
            self.callback()

import pyray as pr
from .colors import FG, DIM, ACCENT

class Input:
    def __init__(self, x, y, w, value, callback=None, realtime=False):
        self.x, self.y, self.w = x, y, w
        self.value = str(value)
        self.active = False
        self.cursor = len(self.value)
        self.callback = callback
        self.realtime = realtime
        self.blink = 0

    def draw(self):
        color = ACCENT if self.active else DIM
        pr.draw_rectangle_lines(self.x, self.y, self.w, 20, color)
        pr.draw_text(self.value.encode(), self.x + 4, self.y + 2, 16, FG)
        
        if self.active and (self.blink // 30) % 2:
            cx = self.x + 4 + pr.measure_text(self.value[:self.cursor].encode(), 16)
            pr.draw_line(cx, self.y + 2, cx, self.y + 18, ACCENT)
        self.blink += 1

    def update(self):
        mouse = pr.get_mouse_position()
        if pr.is_mouse_button_pressed(pr.MOUSE_LEFT_BUTTON):
            self.active = (self.x <= mouse.x <= self.x + self.w and 
                           self.y <= mouse.y <= self.y + 20)
        
        if self.active:
            value_changed = False
            
            key = pr.get_char_pressed()
            while key > 0:
                if 32 <= key <= 126:
                    self.value = self.value[:self.cursor] + chr(key) + self.value[self.cursor:]
                    self.cursor += 1
                    value_changed = True
                key = pr.get_char_pressed()
            
            if pr.is_key_pressed(pr.KEY_BACKSPACE) and self.cursor > 0:
                self.value = self.value[:self.cursor-1] + self.value[self.cursor:]
                self.cursor -= 1
                value_changed = True
            
            if pr.is_key_pressed(pr.KEY_LEFT) and self.cursor > 0:
                self.cursor -= 1
            if pr.is_key_pressed(pr.KEY_RIGHT) and self.cursor < len(self.value):
                self.cursor += 1
            
            if self.callback:
                if self.realtime and value_changed:
                    self.callback(self.value)
                elif not self.realtime and pr.is_key_pressed(pr.KEY_ENTER):
                    self.callback(self.value)
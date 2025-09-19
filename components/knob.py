import pyray as pr
import math
from .colors import *

class Knob:
    def __init__(self, x, y, r, mode, value=100.0, callback=None):
        self.x, self.y, self.r = x, y, r
        self.value = value
        self.callback = callback
        self.dragging = False
        self.min_freq = 88.0
        self.max_freq = 108.0

        value_normalized = (self.value - self.min_freq) / (self.max_freq - self.min_freq)  # 0..1
        self.angle = (value_normalized - 0.5) * 2 * math.pi

        self.colors = get_current_colors(mode)

    def draw(self):
        pr.draw_circle(self.x, self.y, self.r, self.colors["accent"])

        self.draw_frequency_scale()

        # indicator
        dx = math.cos(self.angle)
        dy = math.sin(self.angle)

        start_x = self.x + int(dx * self.r)
        start_y = self.y + int(dy * self.r)

        end_x = self.x + int(dx * (self.r * 0.3))
        end_y = self.y + int(dy * (self.r * 0.3))

        pr.draw_line_ex(pr.Vector2(start_x, start_y),
                        pr.Vector2(end_x, end_y),
                        3,
                        self.colors["bg"])

    def draw_frequency_scale(self):

        frequencies = [92, 96, 100, 104, 108]
        
        for freq in frequencies:

            freq_normalized = (freq - self.min_freq) / (self.max_freq - self.min_freq)
            mark_angle = (freq_normalized - 0.5) * 2 * math.pi
            
            text_radius = self.r + 15
            text_x = self.x + int(math.cos(mark_angle) * text_radius)
            text_y = self.y + int(math.sin(mark_angle) * text_radius)
            
            freq_text = f"{freq}"
            text_width = pr.measure_text(freq_text.encode(), 13)
            
            text_x -= text_width // 2
            text_y -= 5
            
            pr.draw_text(freq_text.encode(), text_x, text_y, 13, self.colors["accent"])

    def update(self):
        mouse = pr.get_mouse_position()
        dx = mouse.x - self.x
        dy = mouse.y - self.y
        dist = math.sqrt(dx*dx + dy*dy)

        if pr.is_mouse_button_pressed(pr.MOUSE_LEFT_BUTTON) and dist < self.r:
            self.dragging = True
        if pr.is_mouse_button_released(pr.MOUSE_LEFT_BUTTON):
            self.dragging = False

        if self.dragging:
            self.angle = math.atan2(dy, dx)
            # map angle (-pi..pi) to frequency range
            freq = 98 + (self.angle / math.pi) * 10
            self.value = max(self.min_freq, min(self.max_freq, freq))
            if self.callback:
                self.callback(self.value)
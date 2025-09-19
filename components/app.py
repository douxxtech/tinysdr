import pyray as pr
import json
import os
from .main_config import *
from radlive import LiveFMPlayer
from .knob import Knob
from .button import Button
from .panel import Panel
from .input_box import Input
from .colors import BG, FG, GREEN, RED, DIM
from .vu import VUMeter


class App:
    def __init__(self):
        # load cfg
        self.config = self.load_config()
        
        self.player = LiveFMPlayer(self.config['host'], self.config['port'])

        self.freq_knob = Knob(WINDOW_WIDTH - 100, WINDOW_HEIGHT // 2 - 20, 60, self.config['frequency'], self.set_frequency)
        self.panel = Panel(160)
        self.connect_btn = Button(20, WINDOW_HEIGHT - 100, 100, 30, "Connect", self.toggle_connect)
        self.menu_btn = Button(20, 10, 60, 25, "Host", self.panel.toggle)
        self.vu_meter = VUMeter(20, WINDOW_HEIGHT - 50, 200, 20)

        self.host_input = Input(20, 45, 120, self.config['host'], self.set_host, True)
        self.port_input = Input(20, 85, 120, str(self.config['port']), self.set_port, True)
        self.apply_btn = Button(20, 200, 120, 30, "APPLY", self.apply_settings)


    def load_config(self):
        cfg_file = "config.json"
        default_config = {
            'host': DEFAULT_HOST,
            'port': DEFAULT_PORT,
            'frequency': DEFAULT_FREQ
        }
        
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, 'r') as f:
                    loaded_config = json.load(f)
                    config = {**default_config, **loaded_config}
                    return config
            except (json.JSONDecodeError, FileNotFoundError):
                print("Config file corrupted, using defaults")
                return default_config
        else:
            self.save_config_to_file(default_config)
            return default_config

    def save_config_to_file(self, config=None):
        if config is None:
            config = self.config
            
        try:
            with open("config.json", 'w') as f:
                json.dump(config, f, indent=4)
            print("Configuration saved successfully")
        except Exception as e:
            print(f"Failed to save config: {e}")

    def update_config(self, key, value):
        self.config[key] = value
        self.save_config_to_file()

    # callbacks
    def set_host(self, value):
        self.player.set_host(value)
        self.config['host'] = value
        print(f"Host updated to: {value}")

    def set_port(self, value):
        try:
            port_int = int(value)
            self.player.set_port(port_int)
            self.config['port'] = port_int
            print(f"Port updated to: {port_int}")
        except ValueError:
            print(f"Invalid port value: {value}")


    def apply_settings(self):
        if self.player.rtl.connected:
            self.player.initialize_sdr()
        # auto save cfg
        self.save_config_to_file()

    def set_frequency(self, value):
        self.player.set_frequency(value)
        self.update_config('frequency', value)

    def toggle_connect(self):
        if self.player.rtl.connected:
            self.player.stop()
            self.player.disconnect()
            self.connect_btn.text = "Connect"
        else:
            if self.player.connect():
                self.player.start()
                self.connect_btn.text = "Disconnect"

    def update_panel_widgets(self):
        base_x = int(self.panel.x) + 20
        self.host_input.x = base_x
        self.port_input.x = base_x
        self.apply_btn.x = base_x

    def is_click_outside_panel(self, mouse_pos):
        if not self.panel.open:
            return False
        
        panel_right = int(self.panel.x) + self.panel.w
        return mouse_pos.x > panel_right

    def run(self):
        pr.init_window(WINDOW_WIDTH, WINDOW_HEIGHT, "Tiny SDR")
        pr.set_target_fps(FPS)

        while not pr.window_should_close():
            if pr.is_mouse_button_pressed(pr.MOUSE_LEFT_BUTTON):
                mouse_pos = pr.get_mouse_position()
                if self.is_click_outside_panel(mouse_pos):
                    self.panel.toggle()
            
            # updates
            self.freq_knob.update()
            self.connect_btn.update()
            self.menu_btn.update()
            self.panel.update()
            self.update_panel_widgets()

            if self.panel.open:
                self.host_input.update()
                self.port_input.update()
                self.apply_btn.update()

            self.vu_meter.set_level(self.player.rms_level)

            pr.begin_drawing()
            pr.clear_background(BG)

            pr.draw_text("TINY SDR", 20, 50, 20, FG)
            status = "CONNECTED" if self.player.rtl.connected else "OFFLINE"
            color = GREEN if self.player.rtl.connected else RED
            pr.draw_text(status.encode(), 20, 80, 16, color)

            self.freq_knob.draw()
            self.connect_btn.draw()
            self.menu_btn.draw()

            self.vu_meter.draw()
            pr.draw_text("VU", 230, WINDOW_HEIGHT - 45, 14, FG)

            # knob value
            pr.draw_text(f"{self.freq_knob.value:.2f} MHz", WINDOW_WIDTH - 100, WINDOW_HEIGHT - 45, 18, FG)

            # pnl
            self.panel.draw()
            if self.panel.x > -self.panel.w + 10:
                panel_x = int(self.panel.x)
                pr.draw_text("SETTINGS", panel_x + 20, 20, 16, FG)

                pr.draw_text("Host:", panel_x + 20, 33, 12, DIM)
                self.host_input.draw()

                pr.draw_text("Port:", panel_x + 20, 73, 12, DIM)
                self.port_input.draw()
                self.apply_btn.draw()

            pr.end_drawing()

        # save cfg on exit, dont work if ^C, but just dont ^C
        self.save_config_to_file()
        
        # cleanup
        self.player.stop()
        self.player.disconnect()
        pr.close_window()
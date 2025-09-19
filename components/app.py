import pyray as pr
import json
import os
from .main_config import *
from .knob import Knob
from .button import Button
from .panel import Panel
from .input_box import Input
from .colors import *
from .vu import VUMeter

try:
    from radlive import LiveFMPlayer
except ImportError:
    LiveFMPlayer = None
    print("LiveFMPlayer not available")

try:
    from piwave import PiWave
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    PiWave = None
    print("PiWave not available")

class App:
    def __init__(self):
        self.mode = "RX"  # start w/ rx
        self.swipe_start_y = 0
        self.is_swiping = False
        self.is_pi = self.is_raspberry_pi()
        self.is_root_user = self.is_root() if self.is_pi else False
        
        # Load config
        self.config = self.load_config()
        
        self.rx_player = None
        self.tx_player = None
        self.selected_filepath = None
        
        if LiveFMPlayer:
            self.rx_player = LiveFMPlayer(self.config['host'], self.config['port'])

        if not self.is_pi or not self.is_root_user:
            print("WARNING: TX mode requires a Raspberry Pi and root privileges. TX will be disabled.")
        
        if PiWave and self.is_pi and self.is_root_user:
            self.tx_player = PiWave(
                self.config["frequency"],
                self.config["name"],
                self.config["description"],
                loop=False
            )
            self.root = tk.Tk()
            self.root.withdraw()
        else:
            self.tx_player = None

        
        # specific ui elements
        self.init_ui_elements()

    def is_raspberry_pi(self): # needs to be a pi to use piwave
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                return 'Raspberry Pi' in cpuinfo
        except Exception:
            return False

    def is_root(self):
        return os.geteuid() == 0


    def init_ui_elements(self):
        if self.mode == "RX":
            self.freq_knob = Knob(WINDOW_WIDTH - 100, WINDOW_HEIGHT // 2 - 20, 60, self.mode, self.config['frequency'], self.set_frequency)
            self.panel = Panel(160, self.mode)
            self.menu_btn = Button(20, 10, 60, 25, "CFG", self.panel.toggle, self.mode)
            self.connect_btn = Button(20, WINDOW_HEIGHT - 100, 100, 30, "Connect", self.toggle_connect, self.mode)
            self.vu_meter = VUMeter(20, WINDOW_HEIGHT - 50, 200, 20)
            # rx settings
            self.host_input = Input(20, 50, 120, self.config.get('host', DEFAULT_HOST), self.mode, self.set_host, True)
            self.port_input = Input(20, 90, 120, str(self.config.get('port', DEFAULT_PORT)), self.mode, self.set_port, True)
        else:  # TX mode
            self.freq_knob = Knob(WINDOW_WIDTH - 100, WINDOW_HEIGHT // 2 - 20, 60, self.mode, self.config['frequency'], self.set_frequency)
            self.panel = Panel(160, self.mode)
            self.menu_btn = Button(20, 10, 60, 25, "CFG", self.panel.toggle, self.mode)
            self.connect_btn = Button(20, WINDOW_HEIGHT - 100, 100, 30, "Send", self.toggle_send, self.mode)
            self.file_btn = Button(130, WINDOW_HEIGHT - 100, 120, 30, "Select File", self.select_file, self.mode)
            # tx settings
            self.name_input = Input(20, 50, 120, self.config.get('name', DEFAULT_NAME), self.mode, self.set_name, True)
            self.desc_input = Input(20, 90, 120, self.config.get('description', DEFAULT_DESC), self.mode, self.set_desc, True)
        
        self.apply_btn = Button(20, 200, 120, 30, "APPLY", self.apply_settings)

    def load_config(self):
        cfg_file = "config.json"
        default_config = {
            'host': DEFAULT_HOST,
            'port': DEFAULT_PORT,
            'frequency': DEFAULT_FREQ,
            'name': DEFAULT_NAME,
            'description': DEFAULT_DESC
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

    def switch_mode(self):
        if self.mode == "RX" and self.rx_player:
            if hasattr(self.rx_player, 'rtl') and self.rx_player.rtl.connected:
                self.rx_player.stop()
                self.rx_player.disconnect()
        elif self.mode == "TX" and self.tx_player:
            if self.tx_player.get_status()["is_playing"]:
                self.tx_player.stop()

        self.mode = "TX" if self.mode == "RX" else "RX"
        self.init_ui_elements()

        # warn if tx not usable
        if self.mode == "TX" and (not self.is_pi or not self.is_root_user):
            print(
                "TX MODE UNAVAILABLE: "
                f"{'Not a Raspberry Pi' if not self.is_pi else ''}"
                f"{' and ' if not self.is_pi and not self.is_root_user else ''}"
                f"{'Not running as root' if not self.is_root_user else ''}."
            )

        print(f"Switched to {self.mode} mode")


    def handle_swipe_input(self):
        mouse_pos = pr.get_mouse_position()
        
        if pr.is_mouse_button_pressed(pr.MOUSE_LEFT_BUTTON):
            self.swipe_start_y = mouse_pos.y
            self.is_swiping = True
        
        if pr.is_mouse_button_released(pr.MOUSE_LEFT_BUTTON) and self.is_swiping:
            swipe_distance = mouse_pos.y - self.swipe_start_y
            
            # 200 px to change
            if abs(swipe_distance) > 200:
                if (swipe_distance < 0 and self.mode == "RX") or (swipe_distance > 0 and self.mode == "TX"):
                    self.switch_mode()
            
            self.is_swiping = False

    def set_host(self, value):
        if self.rx_player:
            self.rx_player.set_host(value)
        self.config['host'] = value
        print(f"Host updated to: {value}")

    def set_port(self, value):
        try:
            port_int = int(value)
            if self.rx_player:
                self.rx_player.set_port(port_int)
            self.config['port'] = port_int
            print(f"Port updated to: {port_int}")
        except ValueError:
            print(f"Invalid port value: {value}")

    def toggle_connect(self):
        if not self.rx_player:
            print("RX Player not available")
            return
            
        if self.rx_player.rtl.connected:
            self.rx_player.stop()
            self.rx_player.disconnect()
            self.connect_btn.text = "Connect"
        else:
            if self.rx_player.connect():
                self.rx_player.start()
                self.connect_btn.text = "Disconnect"

    def set_name(self, value):
        self.config['name'] = value
        print(f"Name updated to: {value}")

    def set_desc(self, value):
        self.config['description'] = value
        print(f"Description updated to: {value}")

    def select_file(self):
        if not PiWave:
            print("TX functionality not available")
            return
            
        filetypes = [
            ("Audio files", "*.wav *.mp3"),
            ("WAV files", "*.wav"),
            ("MP3 files", "*.mp3"),
            ("All files", "*.*")
        ]
        
        if self.selected_filepath and os.path.exists(self.selected_filepath):
            initial_dir = os.path.dirname(self.selected_filepath)
        else:
            initial_dir = os.getcwd()
        
        filename = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=filetypes,
            initialdir=initial_dir
        )
        
        if filename:
            self.selected_filepath = filename
            self.file_btn.text = os.path.basename(filename)
            print(f"Selected file: {filename}")

    def toggle_send(self):
        if not self.tx_player:
            print("TX Player not available (check Raspberry Pi/root requirements)")
            return
            
        if self.tx_player.get_status()["is_playing"]:
            self.tx_player.stop()
            self.connect_btn.text = "Send"
        else:
            if isinstance(self.selected_filepath, str) and os.path.exists(self.selected_filepath):
                self.tx_player.play([self.selected_filepath])
                self.connect_btn.text = "Stop"
            else:
                print("No valid file selected! Please select a file first.")

    def set_frequency(self, value):
        if self.mode == "RX" and self.rx_player:
            self.rx_player.set_frequency(value)
        elif self.mode == "TX" and self.tx_player:
            self.tx_player.set_frequency(value)
        self.update_config('frequency', value)

    def apply_settings(self):
        if self.mode == "RX" and self.rx_player:
            if hasattr(self.rx_player, 'rtl') and self.rx_player.rtl.connected:
                self.rx_player.initialize_sdr()
        elif self.mode == "TX" and self.tx_player:
            self.tx_player.stop()
            self.tx_player.cleanup()
            self.tx_player = PiWave(self.config["frequency"], self.config["name"], self.config["description"], loop=False)
        
        self.save_config_to_file()

    def update_panel_widgets(self):
        base_x = int(self.panel.x) + 20
        if self.mode == "RX":
            self.host_input.x = base_x
            self.port_input.x = base_x
        else:
            self.name_input.x = base_x
            self.desc_input.x = base_x
        self.apply_btn.x = base_x

    def is_click_outside_panel(self, mouse_pos):
        if not self.panel.open:
            return False
        
        panel_right = int(self.panel.x) + self.panel.w
        return mouse_pos.x > panel_right


    def run(self):
        pr.init_window(WINDOW_WIDTH, WINDOW_HEIGHT, "TinySDR - Unified")
        pr.set_target_fps(FPS)

        while not pr.window_should_close():
            
            if pr.is_mouse_button_pressed(pr.MOUSE_LEFT_BUTTON) and not self.is_swiping:
                mouse_pos = pr.get_mouse_position()
                if self.is_click_outside_panel(mouse_pos):
                    self.panel.toggle()

            self.handle_swipe_input()
            
            self.freq_knob.update()
            self.connect_btn.update()
            self.menu_btn.update()
            self.panel.update()
            self.update_panel_widgets()

            if self.panel.open:
                if self.mode == "RX":
                    self.host_input.update()
                    self.port_input.update()
                else:
                    self.name_input.update()
                    self.desc_input.update()
                self.apply_btn.update()

            if self.mode == "RX" and hasattr(self, 'vu_meter') and self.rx_player:
                self.vu_meter.set_level(self.rx_player.rms_level)
            elif self.mode == "TX" and hasattr(self, 'file_btn'):
                self.file_btn.update()

            # Drawing
            pr.begin_drawing()
            colors = get_current_colors(self.mode)
            pr.clear_background(colors['bg'])

            title = f"TINY SDR - {self.mode}"
            pr.draw_text(title.encode(), 20, 50, 20, colors['fg'])
            
            if self.mode == "RX":
                status = "CONNECTED" if (self.rx_player and hasattr(self.rx_player, 'rtl') and self.rx_player.rtl.connected) else "OFFLINE"
                color = colors['green'] if (self.rx_player and hasattr(self.rx_player, 'rtl') and self.rx_player.rtl.connected) else colors['red']
            else:
                status = "PLAYING" if (self.tx_player and self.tx_player.get_status()["is_playing"]) else "IDLE"
                color = colors['green'] if (self.tx_player and self.tx_player.get_status()["is_playing"]) else colors['red']
            
            pr.draw_text(status.encode(), 20, 80, 16, color)

            self.freq_knob.draw()
            self.connect_btn.draw()
            self.menu_btn.draw()

            if self.mode == "RX" and hasattr(self, 'vu_meter'):
                self.vu_meter.draw()
                pr.draw_text("VU", 230, WINDOW_HEIGHT - 45, 14, colors['fg'])
            elif self.mode == "TX":
                if hasattr(self, 'file_btn'):
                    self.file_btn.draw()
                
                if self.tx_player:
                    if self.tx_player.get_status()['current_file']:
                        current_file = os.path.basename(self.tx_player.get_status()['current_file'])
                        pr.draw_text(f"Playing: {current_file}", 20, WINDOW_HEIGHT - 40, 16, colors['fg'])
                    else:
                        pr.draw_text("Not playing anything :[", 20, WINDOW_HEIGHT - 45, 18, colors['fg'])
                    
                else:
                    pr.draw_text("TX unavalible (check Raspberry Pi/root\nrequirements)", 20, WINDOW_HEIGHT - 45, 18, TX_RED)


            # freq
            pr.draw_text(f"{self.freq_knob.value:.2f} MHz", WINDOW_WIDTH - 100, WINDOW_HEIGHT - 45, 18, colors['fg'])

            # pnl
            self.panel.draw()
            if self.panel.x > -self.panel.w + 10:
                panel_x = int(self.panel.x)
                pr.draw_text("SETTINGS", panel_x + 20, 20, 16, colors['fg'])

                if self.mode == "RX":
                    pr.draw_text("Host:", panel_x + 20, 38, 12, colors['dim'])
                    self.host_input.draw()
                    pr.draw_text("Port:", panel_x + 20, 78, 12, colors['dim'])
                    self.port_input.draw()
                else:
                    pr.draw_text("Name:", panel_x + 20, 38, 12, colors['dim'])
                    self.name_input.draw()
                    pr.draw_text("Description:", panel_x + 20, 78, 12, colors['dim'])
                    self.desc_input.draw()
                
                self.apply_btn.draw()

            pr.end_drawing()

        # Cleanup
        self.save_config_to_file()
        
        if self.rx_player:
            self.rx_player.stop()
            self.rx_player.disconnect()
        
        if self.tx_player:
            self.tx_player.stop()
            self.tx_player.cleanup()
        
        pr.close_window()
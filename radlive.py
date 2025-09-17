#!/usr/bin/env python3
"""
RadLive - FM Radio Player Module
Inspired from radback.douxx.tech's software
"""
import socket
import struct
import numpy as np
import threading
import time
from scipy import signal
from scipy.signal import resample_poly
import pyaudio
from collections import deque
import sys

DEFAULT_SAMPLE_RATE = 1.024e6 
DEFAULT_AUDIO_RATE = 48000
DEFAULT_BUFFER_SIZE = 65536
DEFAULT_CHUNK_SIZE = 1024

RTL_TCP_SET_FREQ = 0x01
RTL_TCP_SET_SAMPLE_RATE = 0x02
RTL_TCP_SET_GAIN_MODE = 0x03  # 0 = AGC, 1 = manual gain
RTL_TCP_SET_GAIN = 0x04
RTL_TCP_SET_FREQ_CORRECTION = 0x05

class Log:
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'underline': '\033[4m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'bright_red': '\033[91m',
        'bright_green': '\033[92m',
        'bright_yellow': '\033[93m',
        'bright_blue': '\033[94m',
        'bright_magenta': '\033[95m',
        'bright_cyan': '\033[96m',
        'bright_white': '\033[97m',
    }

    ICONS = {
        'success': 'OK',
        'error': 'ERR',
        'warning': 'WARN',
        'info': 'INFO',
        'client': 'CLIENT',
        'server': 'SERVER',
        'broadcast': 'BCAST',
    }

    SILENT = False

    @classmethod
    def config(cls, silent: bool = False):
        cls.SILENT = silent

    @classmethod
    def print(cls, message: str, style: str = '', icon: str = '', end: str = '\n'):
        if cls.SILENT: return
        color = cls.COLORS.get(style, '')
        icon_char = cls.ICONS.get(icon, '')
        if icon_char:
            if color:
                print(f"{color}[{icon_char}]\033[0m {message}", end=end)
            else:
                print(f"[{icon_char}] {message}", end=end)
        else:
            if color:
                print(f"{color}{message}\033[0m", end=end)
            else:
                print(f"{message}", end=end)
        sys.stdout.flush()

    @classmethod
    def info(cls, message: str):
        cls.print(message, 'bright_cyan', 'info')

    @classmethod
    def success(cls, message: str):
        cls.print(message, 'bright_green', 'success')

    @classmethod
    def warning(cls, message: str):
        cls.print(message, 'bright_yellow', 'warning')

    @classmethod
    def error(cls, message: str):
        cls.print(message, 'bright_red', 'error')

    @classmethod
    def broadcast_message(cls, message: str):
        cls.print(message, 'bright_magenta', 'broadcast')


class RTLTCPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.agc_enabled = False
        self.current_gain = 0.0

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            self.connected = True
            Log.success(f"Connected to RTL-TCP at {self.host}:{self.port}")
            return True
        except Exception as e:
            Log.error(f"Connection failed: {e}")
            return False

    def send_command(self, command, value):
        if not self.connected:
            Log.warning("Cannot send command, not connected")
            return False
        try:
            if command == RTL_TCP_SET_FREQ_CORRECTION:
                data = struct.pack('>Bi', command, int(value))
            else:
                data = struct.pack('>BI', command, int(value))
            self.socket.send(data)
            return True
        except Exception as e:
            Log.error(f"Command failed: {e}")
            return False

    def set_frequency(self, freq_hz):
        return self.send_command(RTL_TCP_SET_FREQ, freq_hz)

    def set_sample_rate(self, rate_hz):
        return self.send_command(RTL_TCP_SET_SAMPLE_RATE, rate_hz)

    def set_gain_mode(self, manual=True):
        success = self.send_command(RTL_TCP_SET_GAIN_MODE, 1 if manual else 0)
        if success:
            self.agc_enabled = not manual
            mode = "hardware AGC" if not manual else "manual gain"
            Log.info(f"Gain mode set to {mode}")
        return success

    def set_gain(self, gain_db):
        if self.agc_enabled:
            Log.warning("Cannot set manual gain while AGC is enabled")
            return False
        success = self.send_command(RTL_TCP_SET_GAIN, int(gain_db * 10))
        if success:
            self.current_gain = gain_db
            Log.info(f"Manual gain set to {gain_db} dB")
        return success

    def set_freq_correction(self, ppm):
        return self.send_command(RTL_TCP_SET_FREQ_CORRECTION, ppm)

    def enable_hardware_agc(self):
        return self.set_gain_mode(manual=False)

    def disable_hardware_agc(self):
        return self.set_gain_mode(manual=True)

    def read_samples(self, num_samples):
        if not self.connected:
            return None
        try:
            bytes_needed = num_samples * 2
            data = b''
            while len(data) < bytes_needed:
                chunk = self.socket.recv(min(DEFAULT_BUFFER_SIZE, bytes_needed - len(data)))
                if not chunk:
                    break
                data += chunk
            if len(data) < bytes_needed:
                return None
            raw_samples = np.frombuffer(data, dtype=np.uint8)
            i_samples = (raw_samples[0::2] - 127.5) / 127.5
            q_samples = (raw_samples[1::2] - 127.5) / 127.5
            return i_samples + 1j * q_samples
        except Exception as e:
            Log.error(f"Read error: {e}")
            return None

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.connected = False
            Log.info("Disconnected from RTL-TCP")


class FMDemodulator:
    def __init__(self):
        self.dc_accum = 0

    def demodulate(self, samples): # yes, claude made that, its one of the only things i swear
        if len(samples) < 2:
            return np.array([])
        phase = np.angle(samples)
        phase_diff = np.diff(phase)
        phase_diff = np.mod(phase_diff + np.pi, 2*np.pi) - np.pi
        alpha = 0.99
        for i in range(len(phase_diff)):
            self.dc_accum = alpha * self.dc_accum + (1 - alpha) * phase_diff[i]
            phase_diff[i] -= self.dc_accum
        return phase_diff


class AudioPlayer:
    def __init__(self, sample_rate=48000):
        self.sample_rate = sample_rate
        self.pyaudio = None
        self.stream = None
        self.running = False
        self.buffer = deque(maxlen=20)
        self.buffer_lock = threading.Lock()

    def start(self):
        if self.running:
            return False

        try:
            self.pyaudio = pyaudio.PyAudio()
            
            def callback(in_data, frame_count, time_info, status):
                with self.buffer_lock:
                    if not self.buffer:
                        return (np.zeros(frame_count, dtype=np.float32).tobytes(), pyaudio.paContinue)
                    chunk = self.buffer.popleft()
                    if len(chunk) < frame_count:
                        padded = np.zeros(frame_count, dtype=np.float32)
                        padded[:len(chunk)] = chunk
                        return (padded.tobytes(), pyaudio.paContinue)
                    else:
                        return (chunk[:frame_count].tobytes(), pyaudio.paContinue)

            self.stream = self.pyaudio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                output=True,
                stream_callback=callback,
                frames_per_buffer=DEFAULT_CHUNK_SIZE
            )
            self.running = True
            self.stream.start_stream()
            Log.success("Audio player started")
            return True
            
        except Exception as e:
            Log.error(f"Failed to start audio player: {e}")
            if self.pyaudio:
                self.pyaudio.terminate()
                self.pyaudio = None
            return False

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        if self.pyaudio:
            try:
                self.pyaudio.terminate()
            except:
                pass
            self.pyaudio = None
        Log.info("Audio player stopped")

    def play(self, audio_data):
        if not self.running:
            return
        with self.buffer_lock:
            self.buffer.append(audio_data)

class LiveFMPlayer:
    def __init__(self, host='127.0.0.1', port=1234):
        self.rtl = RTLTCPClient(host, port)
        self.demodulator = FMDemodulator()
        self.audio_player = AudioPlayer(DEFAULT_AUDIO_RATE)
        self.running = False
        self.thread = None
        self.rms_level = 0.0

        self.config = {
            'frequency': 100.0e6,
            'sdr_sample_rate': DEFAULT_SAMPLE_RATE,
            'audio_rate': DEFAULT_AUDIO_RATE,
            'gain': 30.0,
            'use_hardware_agc': True,
            'freq_correction': 0
        }

    def connect(self):
        return self.rtl.connect()
    
    def set_host(self, host):
        self.config['host'] = host
        self.rtl.host = host
        Log.info(f"Host set to {host}")

    def set_port(self, port):
        self.config['port'] = port
        self.rtl.port = port
        Log.info(f"Port set to {port}")

    def set_frequency(self, freq_mhz):
       freq_hz = int(freq_mhz * 1e6)
       self.config['frequency'] = freq_hz
       if self.running:
           return self.rtl.set_frequency(freq_hz)
       return True

    def set_gain(self, gain_db):
        if self.config['use_hardware_agc']:
            Log.warning("Cannot set manual gain while AGC is enabled")
            return False
        gain_value = max(0, min(500, int(gain_db * 10)))
        success = self.rtl.send_command(RTL_TCP_SET_GAIN, gain_value)
        if success:
            self.current_gain = gain_db
            Log.info(f"Manual gain set to {gain_db} dB")
        return success


    def set_hardware_agc(self, enabled):
        self.config['use_hardware_agc'] = enabled
        if self.running:
            if enabled:
                return self.rtl.enable_hardware_agc()
            else:
                success = self.rtl.disable_hardware_agc()
                if success:
                    return self.rtl.set_gain(self.config['gain'])
                return success
        return True

    def set_freq_correction(self, ppm):
        self.config['freq_correction'] = ppm
        if self.running:
            return self.rtl.set_freq_correction(ppm)
        return True

    def initialize_sdr(self):
        success = True
        success &= self.rtl.set_sample_rate(self.config['sdr_sample_rate'])
        if self.config['use_hardware_agc']:
            success &= self.rtl.enable_hardware_agc()
        else:
            success &= self.rtl.disable_hardware_agc()
            success &= self.rtl.set_gain(self.config['gain'])
        success &= self.rtl.set_freq_correction(self.config['freq_correction'])
        success &= self.rtl.set_frequency(self.config['frequency'])
        return success

    def process_audio(self, audio_data):
        rms = np.sqrt(np.mean(audio_data**2)) + 1e-10
        self.rms_level = min(1.0, rms*10)
        audio_data = 0.5 * (audio_data / rms)
        try:
            b, a = signal.butter(4, 0.1)
            audio_data = signal.lfilter(b, a, audio_data)
        except:
            pass
        return np.clip(audio_data, -1.0, 1.0).astype(np.float32)

    def stream_loop(self):
        while self.running:
            samples = self.rtl.read_samples(65536)
            if samples is None:
                time.sleep(0.01)
                continue
            audio = self.demodulator.demodulate(samples)
            if len(audio) > 0:
                audio = resample_poly(audio, self.config['audio_rate'], int(self.config['sdr_sample_rate']))
                processed_audio = self.process_audio(audio)
                for i in range(0, len(processed_audio), DEFAULT_CHUNK_SIZE):
                    self.audio_player.play(processed_audio[i:i+DEFAULT_CHUNK_SIZE])

    def start(self):
        if self.running:
            return False
        if not self.initialize_sdr():
            Log.error("SDR initialization failed")
            return False
        if not self.audio_player.start():
            Log.error("Failed to start audio player")
            return False
        self.running = True
        self.thread = threading.Thread(target=self.stream_loop, daemon=True)
        self.thread.start()
        Log.success("Live FM streaming started")
        return True

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.audio_player.stop()
        Log.info("Live FM streaming stopped")

    def disconnect(self):
        self.rtl.disconnect()
        self.rms_level = 0

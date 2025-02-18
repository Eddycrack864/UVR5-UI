from pypresence import Presence
from pypresence.exceptions import DiscordNotFound, InvalidPipe
import datetime as dt
import threading
import functools

class RichPresenceManager:
    def __init__(self):
        self.client_id = "1339001292319621181"
        self.rpc = None
        self.running = False
        self.current_state = "Idling"
        self.lock = threading.Lock()
        self.discord_available = True
        
        self.presence_configs = {
            # Roformer
            "Performing BS/Mel Roformer Separation": {
                "small_image": "roformer",
                "small_text": "BS/Mel Roformer"
            },
            "Performing BS/Mel Roformer Batch Separation": {
                "small_image": "roformer",
                "small_text": "BS/Mel Roformer"
            },
            # MDXC
            "Performing MDXC Separationn": {
                "small_image": "mdxc",
                "small_text": "MDXC"
            },
            "Performing MDXC Batch Separation": {
                "small_image": "mdxc",
                "small_text": "MDXC"
            },
            # MDX-NET
            "Performing MDX-NET Separation": {
                "small_image": "mdxnet",
                "small_text": "MDX-NET"
            },
            "Performing MDX-NET Batch Separation": {
                "small_image": "mdxnet",
                "small_text": "MDX-NET"
            },
            # VR Arch
            "Performing VR Arch Separation": {
                "small_image": "vrarch",
                "small_text": "VR Arch"
            },
            "Performing VR Arch Batch Separation": {
                "small_image": "vrarch",
                "small_text": "VR Arch"
            },
            # Demucs
            "Performing Demucs Separation": {
                "small_image": "demucs",
                "small_text": "Demucs"
            },
            "Performing Demucs Batch Separation": {
                "small_image": "demucs",
                "small_text": "Demucs"
            },
            # Idling
            "Idling": {
                "small_image": "idling",
                "small_text": "Idling"
            }
        }

    def get_presence_config(self, state):
        return self.presence_configs.get(state, self.presence_configs["Idling"])

    def start_presence(self):
        try:
            if not self.running:
                self.rpc = Presence(self.client_id)
                try:
                    self.rpc.connect()
                    self.running = True
                    self.discord_available = True
                    self.update_presence()
                    print("Discord Rich Presence connected successfully")
                except (DiscordNotFound, InvalidPipe):
                    print("Discord is not running. Rich Presence will be disabled.")
                    self.discord_available = False
                    self.running = False
                    self.rpc = None
                except Exception as error:
                    print(f"An error occurred connecting to Discord: {error}")
                    self.discord_available = False
                    self.running = False
                    self.rpc = None
        except Exception as e:
            print(f"Unexpected error in start_presence: {e}")
            self.discord_available = False
            self.running = False
            self.rpc = None

    def update_presence(self):
        if self.rpc and self.running and self.discord_available:
            try:
                config = self.get_presence_config(self.current_state)
                self.rpc.update(
                    state=self.current_state,
                    details="Ultimate Vocal Remover 5 Gradio UI",
                    buttons=[{"label": "Download", "url": "https://github.com/Eddycrack864/UVR5-UI"}],
                    large_image="logo",
                    large_text="Separating tracks with UVR5 UI",
                    small_image=config["small_image"],
                    small_text=config["small_text"],
                    start=dt.datetime.now().timestamp(),
                )
            except Exception as e:
                print(f"Error updating Discord presence: {e}")
                self.discord_available = False
                self.cleanup()

    def set_state(self, state):
        if self.discord_available:
            with self.lock:
                self.current_state = state
                if self.running:
                    self.update_presence()

    def cleanup(self):
        self.running = False
        if self.rpc and self.discord_available:
            try:
                self.rpc.close()
            except:
                pass
        self.rpc = None
        self.discord_available = False

    def stop_presence(self):
        self.cleanup()

RPCManager = RichPresenceManager()

def track_presence(state_message):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if RPCManager.running and RPCManager.discord_available:
                RPCManager.set_state(state_message)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                if RPCManager.running and RPCManager.discord_available:
                    RPCManager.set_state("Idling")
        return wrapper
    return decorator
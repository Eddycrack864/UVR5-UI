"""Optional Discord Rich Presence. Never raises: if Discord isn't running it disables itself."""

import contextlib
import datetime as dt
import logging
import threading

logger = logging.getLogger(__name__)

CLIENT_ID = "1339001292319621181"
IDLE = "Idling"

# arch_id -> (small_image asset, label shown in Discord)
ACTIVITIES = {
    "roformer": ("roformer", "BS/Mel Roformer"),
    "mdx23c": ("mdxc", "MDXC"),
    "mdxnet": ("mdxnet", "MDX-NET"),
    "vrarch": ("vrarch", "VR Arch"),
    "demucs": ("demucs", "Demucs"),
    "ensemble": ("logo", "Ensemble"),
}


class RichPresenceManager:
    def __init__(self, client_id: str = CLIENT_ID):
        self.client_id = client_id
        self.rpc = None
        self.running = False
        self.lock = threading.Lock()

    def start(self) -> None:
        if self.running:
            return
        try:
            from pypresence import Presence
            from pypresence.exceptions import DiscordNotFound, InvalidPipe
        except ImportError:
            logger.info("pypresence is not installed. Rich Presence will be disabled.")
            return

        try:
            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.running = True
            logger.info("Discord Rich Presence connected successfully")
            self._update(IDLE, "idling", IDLE)
        except (DiscordNotFound, InvalidPipe):
            logger.info("Discord is not running. Rich Presence will be disabled.")
            self.rpc = None
        except Exception as e:
            logger.warning("An error occurred connecting to Discord: %s", e)
            self.rpc = None

    def _update(self, state: str, small_image: str, small_text: str) -> None:
        if not (self.rpc and self.running):
            return
        try:
            self.rpc.update(
                state=state,
                details="Ultimate Vocal Remover 5 Gradio UI",
                buttons=[{"label": "Download", "url": "https://github.com/Eddycrack864/UVR5-UI"}],
                large_image="logo",
                large_text="Separating tracks with UVR5 UI",
                small_image=small_image,
                small_text=small_text,
                start=dt.datetime.now().timestamp(),
            )
        except Exception as e:
            logger.warning("Error updating Discord presence: %s", e)
            self.stop()

    def set_activity(self, arch_id: str | None, batch: bool = False) -> None:
        with self.lock:
            if arch_id is None or arch_id not in ACTIVITIES:
                self._update(IDLE, "idling", IDLE)
                return
            image, label = ACTIVITIES[arch_id]
            kind = "Batch Separation" if batch else "Separation"
            self._update(f"Performing {label} {kind}", image, label)

    @contextlib.contextmanager
    def track(self, arch_id: str, batch: bool = False):
        """Show the activity while the block runs, then go back to idling."""
        self.set_activity(arch_id, batch)
        try:
            yield
        finally:
            self.set_activity(None)

    def stop(self) -> None:
        self.running = False
        if self.rpc:
            try:
                self.rpc.close()
            except Exception:
                pass
        self.rpc = None


presence = RichPresenceManager()

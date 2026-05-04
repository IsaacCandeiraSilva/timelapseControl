"""
Nikon D3300 capture via digiCamControl HTTP API (localhost:5513).
digiCamControl must be running with its web server enabled.
"""
import threading
import time

import cv2
import numpy as np
import requests
from PyQt6.QtCore import QThread, pyqtSignal

BASE_URL = "http://localhost:5513"
LIVEVIEW_FPS = 5        # D3300 USB live view is hardware-limited to ~5 fps
CONNECTION_POLL = 2.0   # seconds between connection checks


# Property name mapping: our key → digiCamControl property name
_PROP = {
    "iso":      "isonumber",
    "shutter":  "shutterspeed",
    "aperture": "fnumber",
}


class NikonClient:
    """Thin HTTP wrapper for digiCamControl's REST API."""

    def __init__(self, base_url: str = BASE_URL, timeout: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def ping(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/session/list", timeout=self.timeout)
            return r.status_code == 200
        except Exception:
            return False

    def camera_name(self) -> str:
        try:
            r = requests.get(f"{self.base_url}/session/list", timeout=self.timeout)
            sessions = r.json().get("Data") or []
            if sessions:
                return sessions[0].get("Name", "")
        except Exception:
            pass
        return ""

    def get_property(self, prop: str) -> dict:
        """Return {'value': str, 'allowed': [str, ...]} or {} on error."""
        api_name = _PROP.get(prop, prop)
        try:
            r = requests.get(f"{self.base_url}/camera/get/{api_name}", timeout=self.timeout)
            data = r.json()
            if data.get("Status") == "ok":
                return {
                    "value":   str(data.get("Data", "")),
                    "allowed": [str(v) for v in (data.get("AllowedValues") or [])],
                }
        except Exception:
            pass
        return {}

    def set_property(self, prop: str, value: str) -> bool:
        api_name = _PROP.get(prop, prop)
        try:
            r = requests.get(
                f"{self.base_url}/camera/set/{api_name}/{value}",
                timeout=self.timeout,
            )
            return r.json().get("Status") == "ok"
        except Exception:
            return False

    def capture(self) -> str | None:
        """Trigger capture (no AF). Returns the local file path saved by digiCamControl."""
        try:
            r = requests.get(f"{self.base_url}/camera/capturenoaf", timeout=30.0)
            data = r.json()
            if data.get("Status") == "ok":
                path = data.get("Data")
                return str(path) if path else None
        except Exception:
            pass
        return None

    def get_liveview_frame(self) -> np.ndarray | None:
        """Fetch one JPEG live-view frame and return as BGR numpy array."""
        try:
            r = requests.get(f"{self.base_url}/camera/liveview", timeout=self.timeout)
            if r.status_code == 200 and r.content:
                arr = np.frombuffer(r.content, dtype=np.uint8)
                return cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception:
            pass
        return None


class NikonThread(QThread):
    """
    Background thread: polls live view for preview + triggers interval captures.
    Public interface mirrors WebcamThread so MainWindow can swap sources transparently.
    """
    frame_ready        = pyqtSignal(object)       # numpy BGR frame
    timelapse_frame    = pyqtSignal(int)           # total frames captured so far
    camera_error       = pyqtSignal(str)
    connection_changed = pyqtSignal(bool, str)     # (connected, camera_name)

    def __init__(self, client: "NikonClient | None" = None, preview_fps: int = LIVEVIEW_FPS):
        super().__init__()
        self.client = client or NikonClient()
        self.preview_fps = preview_fps

        self._running = False
        self._recording = False
        self._capture_interval = 5.0

        self._frames_lock = threading.Lock()
        self._captured_frames: list[np.ndarray] = []
        self._last_capture_time = 0.0
        self._last_connected: bool | None = None   # None = unknown (first poll)

    # --- public API (same as WebcamThread) ---

    def start_recording(self, capture_interval: float) -> None:
        with self._frames_lock:
            self._captured_frames = []
        self._last_capture_time = 0.0
        self._capture_interval = capture_interval
        self._recording = True

    def stop_recording(self) -> list[np.ndarray]:
        self._recording = False
        with self._frames_lock:
            return list(self._captured_frames)

    def stop(self) -> None:
        self._running = False
        self.wait()

    # --- QThread ---

    def run(self) -> None:
        self._running = True
        frame_delay = 1.0 / self.preview_fps
        last_connection_check = 0.0

        while self._running:
            now = time.monotonic()

            # --- connection check (every CONNECTION_POLL seconds) ---
            if now - last_connection_check >= CONNECTION_POLL:
                connected = self.client.ping()
                last_connection_check = now
                if connected != self._last_connected:
                    name = self.client.camera_name() if connected else ""
                    self.connection_changed.emit(connected, name)
                    self._last_connected = connected

            if not self._last_connected:
                time.sleep(CONNECTION_POLL)
                continue

            # --- live view ---
            frame = self.client.get_liveview_frame()
            if frame is not None:
                self.frame_ready.emit(frame)

            # --- timelapse capture ---
            if self._recording:
                elapsed = now - self._last_capture_time
                if elapsed >= self._capture_interval:
                    self._do_capture()
                    self._last_capture_time = now

            time.sleep(frame_delay)

    def _do_capture(self) -> None:
        path = self.client.capture()
        if not path:
            self.camera_error.emit("Disparo falhou — verifique a câmera.")
            return
        img = cv2.imread(path)
        if img is None:
            self.camera_error.emit(f"Não foi possível ler o arquivo: {path}")
            return
        with self._frames_lock:
            self._captured_frames.append(img)
            count = len(self._captured_frames)
        self.timelapse_frame.emit(count)

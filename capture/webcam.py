import threading
import time

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal


class WebcamThread(QThread):
    frame_ready = pyqtSignal(object)   # numpy BGR frame — emitted at ~PREVIEW_FPS
    timelapse_frame = pyqtSignal(int)  # total timelapse frames captured so far
    camera_error = pyqtSignal(str)

    def __init__(self, camera_index: int = 0, preview_fps: int = 30):
        super().__init__()
        self.camera_index = camera_index
        self.preview_fps = preview_fps

        self._running = False
        self._recording = False
        self._capture_interval = 1.0

        self._frames_lock = threading.Lock()
        self._captured_frames: list[np.ndarray] = []
        self._last_capture_time = 0.0

    # --- public API (called from main thread) ---

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

    # --- QThread entry point ---

    def run(self) -> None:
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not cap.isOpened():
            self.camera_error.emit(f"Não foi possível abrir a câmera (índice {self.camera_index})")
            return

        self._running = True
        frame_delay = 1.0 / self.preview_fps

        while self._running:
            ret, frame = cap.read()
            if not ret:
                self.camera_error.emit("Erro ao ler frame da câmera.")
                break

            self.frame_ready.emit(frame)

            if self._recording:
                now = time.monotonic()
                if now - self._last_capture_time >= self._capture_interval:
                    with self._frames_lock:
                        self._captured_frames.append(frame.copy())
                        count = len(self._captured_frames)
                    self._last_capture_time = now
                    self.timelapse_frame.emit(count)

            time.sleep(frame_delay)

        cap.release()

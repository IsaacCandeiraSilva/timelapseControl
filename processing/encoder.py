import subprocess
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

import config

# libx264 requires even dimensions
_even = lambda n: n if n % 2 == 0 else n - 1


class EncoderThread(QThread):
    progress = pyqtSignal(int)        # 0–100
    finished = pyqtSignal(str, str)   # (original_path, social_path)
    error = pyqtSignal(str)

    def __init__(self, frames: list[np.ndarray], fps: int = config.TIMELAPSE_PLAYBACK_FPS):
        super().__init__()
        self.frames = frames
        self.fps = fps

    def run(self) -> None:
        if not self.frames:
            self.error.emit("Nenhum frame para codificar.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path(config.OUTPUT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        original_path = str(out_dir / f"original_{timestamp}.mp4")
        social_path   = str(out_dir / f"social_{timestamp}.mp4")

        h, w = self.frames[0].shape[:2]
        w, h = _even(w), _even(h)

        crop_w = _even(h * 9 // 16)
        crop_x = _even((w - crop_w) // 2)

        try:
            self._pipe(
                self.frames, w, h,
                vf=None,
                output=original_path,
                progress_start=0, progress_end=50,
            )
            self._pipe(
                self.frames, w, h,
                vf=f"crop={crop_w}:{h}:{crop_x}:0,scale=1080:1920",
                output=social_path,
                progress_start=50, progress_end=100,
            )
            self.finished.emit(original_path, social_path)
        except Exception as exc:
            self.error.emit(str(exc))

    # ------------------------------------------------------------------

    def _pipe(
        self,
        frames: list[np.ndarray],
        w: int,
        h: int,
        vf: str | None,
        output: str,
        progress_start: int,
        progress_end: int,
    ) -> None:
        cmd = [
            config.FFMPEG_BIN, "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
            "-r", str(self.fps),
            "-i", "pipe:0",
        ]
        if vf:
            cmd += ["-vf", vf]
        cmd += ["-vcodec", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", output]

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        # Drain stderr in a background thread to prevent deadlock:
        # FFmpeg writes verbose output to stderr; if the OS pipe buffer (~64 KB)
        # fills up, FFmpeg blocks on write → stops reading stdin → our write blocks.
        stderr_buf: list[bytes] = []
        drain = threading.Thread(target=lambda: stderr_buf.append(proc.stderr.read()), daemon=True)
        drain.start()

        total = len(frames)
        span = progress_end - progress_start
        try:
            for i, frame in enumerate(frames):
                proc.stdin.write(frame.tobytes())
                self.progress.emit(progress_start + int((i + 1) / total * span))
        finally:
            proc.stdin.close()

        proc.wait()
        drain.join()

        if proc.returncode != 0:
            err = b"".join(stderr_buf).decode(errors="replace")
            raise RuntimeError(f"FFmpeg falhou (código {proc.returncode}):\n{err}")

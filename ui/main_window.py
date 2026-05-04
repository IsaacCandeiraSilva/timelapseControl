import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

import config
from capture.webcam import WebcamThread
from processing.encoder import EncoderThread
from ui.live_view import LiveViewWidget

_STYLE = """
QMainWindow { background-color: #2b2b2b; }
QWidget      { background-color: #2b2b2b; color: #e0e0e0; font-size: 13px; }
QPushButton  {
    background-color: #3c3f41; color: #e0e0e0;
    border: 1px solid #555; border-radius: 4px;
    padding: 6px 18px;
}
QPushButton:hover   { background-color: #4c5052; }
QPushButton:pressed { background-color: #2d5a8e; }
QPushButton:disabled { color: #666; border-color: #444; }
QPushButton#btnStart { background-color: #2d6a2d; }
QPushButton#btnStart:hover { background-color: #3a8a3a; }
QPushButton#btnStop  { background-color: #7a2d2d; }
QPushButton#btnStop:hover  { background-color: #a03a3a; }
QDoubleSpinBox { background-color: #3c3f41; border: 1px solid #555; border-radius: 4px; padding: 4px; }
QLabel#recording { color: #ff5555; font-weight: bold; }
QProgressBar {
    background-color: #3c3f41; border: 1px solid #555; border-radius: 4px;
    text-align: center; color: #e0e0e0; height: 18px;
}
QProgressBar::chunk { background-color: #2d6a8e; border-radius: 3px; }
QStatusBar { background-color: #1e1e1e; color: #aaaaaa; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("timelapseControl")
        self.setMinimumSize(900, 680)
        self.setStyleSheet(_STYLE)

        self._webcam: WebcamThread | None = None
        self._encoder: EncoderThread | None = None
        self._is_recording = False
        self._elapsed_seconds = 0

        self._build_ui()
        self._start_preview()

    # ------------------------------------------------------------------ build

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._live_view = LiveViewWidget()
        root.addWidget(self._live_view)

        # controls row
        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)

        ctrl.addWidget(QLabel("Intervalo (s):"))
        self._interval_spin = QDoubleSpinBox()
        self._interval_spin.setRange(0.5, 60.0)
        self._interval_spin.setValue(config.DEFAULT_CAPTURE_INTERVAL)
        self._interval_spin.setSingleStep(0.5)
        self._interval_spin.setFixedWidth(90)
        ctrl.addWidget(self._interval_spin)

        ctrl.addStretch()

        self._recording_label = QLabel("")
        self._recording_label.setObjectName("recording")
        ctrl.addWidget(self._recording_label)

        self._frame_label = QLabel("Frames: 0")
        ctrl.addWidget(self._frame_label)

        self._elapsed_label = QLabel("00:00")
        ctrl.addWidget(self._elapsed_label)

        self._btn_folder = QPushButton("📁  Abrir pasta")
        self._btn_folder.clicked.connect(self._open_videos_folder)
        ctrl.addWidget(self._btn_folder)

        self._btn_start = QPushButton("▶  Iniciar Gravação")
        self._btn_start.setObjectName("btnStart")
        self._btn_start.clicked.connect(self._on_start)
        ctrl.addWidget(self._btn_start)

        self._btn_stop = QPushButton("■  Parar")
        self._btn_stop.setObjectName("btnStop")
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        ctrl.addWidget(self._btn_stop)

        root.addLayout(ctrl)

        # progress bar (hidden until encoding starts)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        root.addWidget(self._progress_bar)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Iniciando câmera...")

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)

    # ------------------------------------------------------------------ camera

    def _start_preview(self) -> None:
        self._webcam = WebcamThread(
            camera_index=config.WEBCAM_INDEX,
            preview_fps=config.PREVIEW_FPS,
        )
        self._webcam.frame_ready.connect(self._live_view.update_frame)
        self._webcam.timelapse_frame.connect(self._on_timelapse_frame)
        self._webcam.camera_error.connect(self._on_camera_error)
        self._webcam.start()
        self._status.showMessage("Câmera iniciada. Pronto para gravar.")

    # ------------------------------------------------------------------ recording slots

    def _on_start(self) -> None:
        if self._webcam is None:
            return
        interval = self._interval_spin.value()
        self._webcam.start_recording(interval)
        self._is_recording = True
        self._elapsed_seconds = 0
        self._elapsed_label.setText("00:00")
        self._frame_label.setText("Frames: 0")
        self._recording_label.setText("● REC")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._interval_spin.setEnabled(False)
        self._elapsed_timer.start()
        self._status.showMessage(f"Gravando — intervalo: {interval}s")

    def _on_stop(self) -> None:
        if self._webcam is None:
            return
        frames = self._webcam.stop_recording()
        self._elapsed_timer.stop()
        self._is_recording = False
        self._recording_label.setText("")
        self._btn_stop.setEnabled(False)
        self._btn_start.setEnabled(False)
        self._interval_spin.setEnabled(False)
        self._frame_label.setText(f"Frames: {len(frames)}")

        if not frames:
            self._status.showMessage("Nenhum frame capturado.")
            self._btn_start.setEnabled(True)
            self._interval_spin.setEnabled(True)
            return

        self._start_encoding(frames)

    def _on_timelapse_frame(self, count: int) -> None:
        self._frame_label.setText(f"Frames: {count}")

    def _on_camera_error(self, message: str) -> None:
        self._live_view.show_error(message)
        self._btn_start.setEnabled(False)
        self._status.showMessage(f"Erro de câmera: {message}")

    def _tick_elapsed(self) -> None:
        self._elapsed_seconds += 1
        minutes, seconds = divmod(self._elapsed_seconds, 60)
        self._elapsed_label.setText(f"{minutes:02d}:{seconds:02d}")

    # ------------------------------------------------------------------ encoding

    def _start_encoding(self, frames: list) -> None:
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._status.showMessage(f"Codificando {len(frames)} frames...")

        self._encoder = EncoderThread(frames, fps=config.TIMELAPSE_PLAYBACK_FPS)
        self._encoder.progress.connect(self._progress_bar.setValue)
        self._encoder.finished.connect(self._on_encoding_done)
        self._encoder.error.connect(self._on_encoding_error)
        self._encoder.start()

    def _on_encoding_done(self, original: str, social: str) -> None:
        self._progress_bar.setValue(100)
        self._progress_bar.setVisible(False)
        self._btn_start.setEnabled(True)
        self._interval_spin.setEnabled(True)
        orig_name = original.split("\\")[-1]
        soc_name  = social.split("\\")[-1]
        self._status.showMessage(
            f"Salvo: {orig_name}  |  {soc_name}  →  {config.OUTPUT_DIR}"
        )

    def _on_encoding_error(self, message: str) -> None:
        self._progress_bar.setVisible(False)
        self._btn_start.setEnabled(True)
        self._interval_spin.setEnabled(True)
        self._status.showMessage(f"Erro no encoding: {message}")

    # ------------------------------------------------------------------ folder

    def _open_videos_folder(self) -> None:
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        os.startfile(config.OUTPUT_DIR)

    # ------------------------------------------------------------------ close

    def closeEvent(self, event) -> None:
        if self._webcam is not None:
            self._webcam.stop()
        super().closeEvent(event)

import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy

_PLACEHOLDER_STYLE = (
    "background-color: #1a1a1a; color: #555555; font-size: 15px;"
)
_ACTIVE_STYLE = "background-color: #000000;"


class LiveViewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(640, 480)
        self.setStyleSheet(_PLACEHOLDER_STYLE)
        self.setText("Aguardando câmera...")

    def update_frame(self, frame: np.ndarray) -> None:
        if self.styleSheet() != _ACTIVE_STYLE:
            self.setStyleSheet(_ACTIVE_STYLE)
            self.setText("")

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(pixmap)

    def show_message(self, message: str) -> None:
        self.setStyleSheet(_PLACEHOLDER_STYLE)
        self.clear()
        self.setText(message)

    def show_error(self, message: str) -> None:
        self.show_message(message)

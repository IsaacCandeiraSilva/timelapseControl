from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from capture.nikon import NikonClient

_PROPS = {
    "iso":      "ISO",
    "shutter":  "Obturador",
    "aperture": "Abertura (f/)",
}

_DOT_ON  = "color: #55ff55; font-weight: bold;"
_DOT_OFF = "color: #ff5555; font-weight: bold;"


class NikonControlsWidget(QGroupBox):
    """Camera parameter panel for Nikon D3300 via digiCamControl."""

    def __init__(self, client: NikonClient, parent=None):
        super().__init__("Nikon D3300", parent)
        self._client = client
        self._combos: dict[str, QComboBox] = {}
        self._build_ui()

    # ------------------------------------------------------------------ build

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(8, 12, 8, 8)

        # status row
        status_row = QHBoxLayout()
        self._dot = QLabel("●")
        self._dot.setStyleSheet(_DOT_OFF)
        self._status_label = QLabel("Desconectado — inicie o digiCamControl")
        status_row.addWidget(self._dot)
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        self._btn_refresh = QPushButton("↺  Atualizar")
        self._btn_refresh.setFixedWidth(110)
        self._btn_refresh.clicked.connect(self._refresh)
        self._btn_refresh.setEnabled(False)
        status_row.addWidget(self._btn_refresh)
        root.addLayout(status_row)

        # property dropdowns
        props_row = QHBoxLayout()
        props_row.setSpacing(16)
        for prop, label in _PROPS.items():
            col = QVBoxLayout()
            col.setSpacing(3)
            col.addWidget(QLabel(label))
            combo = QComboBox()
            combo.setMinimumWidth(120)
            combo.setEnabled(False)
            combo.currentTextChanged.connect(
                lambda val, p=prop: self._on_changed(p, val)
            )
            self._combos[prop] = combo
            col.addWidget(combo)
            props_row.addLayout(col)
        props_row.addStretch()
        root.addLayout(props_row)

    # ------------------------------------------------------------------ public slots

    def on_connection_changed(self, connected: bool, name: str) -> None:
        if connected:
            self._dot.setStyleSheet(_DOT_ON)
            self._status_label.setText(f"Conectado — {name}" if name else "Conectado")
            self._btn_refresh.setEnabled(True)
            for combo in self._combos.values():
                combo.setEnabled(True)
            self._refresh()
        else:
            self._dot.setStyleSheet(_DOT_OFF)
            self._status_label.setText("Desconectado — inicie o digiCamControl")
            self._btn_refresh.setEnabled(False)
            for combo in self._combos.values():
                combo.setEnabled(False)
                combo.blockSignals(True)
                combo.clear()
                combo.blockSignals(False)

    # ------------------------------------------------------------------ private

    def _refresh(self) -> None:
        for prop, combo in self._combos.items():
            info = self._client.get_property(prop)
            combo.blockSignals(True)
            combo.clear()
            allowed = info.get("allowed", [])
            if allowed:
                combo.addItems(allowed)
                idx = combo.findText(info.get("value", ""))
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def _on_changed(self, prop: str, value: str) -> None:
        if value:
            self._client.set_property(prop, value)

import sys
from PyQt6.QtWidgets import QApplication

# Single QApplication for the entire test session (required by QThread signals)
_qapp = QApplication.instance() or QApplication(sys.argv)

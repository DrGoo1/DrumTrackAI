#!/usr/bin/env python3
"""Launch E-GMD Feature Extractor"""
import sys
from PySide6.QtWidgets import QApplication
from admin.ui.egmd_extraction_widget import EGMDExtractionWidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    widget = EGMDExtractionWidget()
    widget.setWindowTitle("E-GMD Feature Extraction")
    widget.resize(900, 750)
    widget.show()
    
    sys.exit(app.exec())

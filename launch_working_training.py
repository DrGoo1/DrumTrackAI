#!/usr/bin/env python3
"""
Launch the WORKING training widget
This actually runs training instead of just simulating it
"""
import sys
from PySide6.QtWidgets import QApplication
from admin.ui.working_training_widget import WorkingTrainingWidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    widget = WorkingTrainingWidget()
    widget.setWindowTitle("DrumTracKAI - Working Training Widget")
    widget.resize(800, 700)
    widget.show()
    
    sys.exit(app.exec())

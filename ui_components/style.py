from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

def apply_theme(app):
    app.setStyle("Fusion")
    
    palette = QPalette()
    bg_color = QColor(245, 245, 248) # Soft White
    text_color = QColor(40, 40, 40)
    accent_color = QColor(162, 210, 255) # Frosted Glass Blue #A2D2FF
    widget_bg = QColor(255, 255, 255, 220)
    
    palette.setColor(QPalette.Window, bg_color)
    palette.setColor(QPalette.WindowText, text_color)
    palette.setColor(QPalette.Base, widget_bg)
    palette.setColor(QPalette.AlternateBase, QColor(250, 250, 250))
    palette.setColor(QPalette.ToolTipBase, bg_color)
    palette.setColor(QPalette.ToolTipText, text_color)
    palette.setColor(QPalette.Text, text_color)
    palette.setColor(QPalette.Button, widget_bg)
    palette.setColor(QPalette.ButtonText, text_color)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, accent_color)
    palette.setColor(QPalette.Highlight, accent_color)
    palette.setColor(QPalette.HighlightedText, Qt.black)
    
    app.setPalette(palette)
    
    stylesheet = """
    QWidget {
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    }
    QMainWindow {
        background-color: #f5f5f8;
    }
    QPushButton {
        background-color: #B0C4DE; /* Steel Blue/Gray */
        color: #1a1a1a;
        border: none;
        padding: 8px 16px;
        border-radius: 12px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #A2D2FF; /* Frosted Glass Blue */
    }
    QPushButton:pressed {
        background-color: #87CEFA; /* Light Sky Blue */
    }
    QPushButton:disabled {
        background-color: #e0e0e0;
        color: #999;
    }
    QLineEdit, QTextEdit, QScrollArea {
        background-color: rgba(255, 255, 255, 0.85);
        border: 1px solid #dcdcdc;
        border-radius: 12px;
        padding: 5px;
        color: #333;
    }
    QListWidget {
        background-color: #F8FAFF; /* Glacier Blue */
        border: 1px solid #B0C4DE;
        border-radius: 12px;
        padding: 5px;
        color: #333;
        font-size: 14pt; /* Increased readability */
    }
    QLineEdit:focus, QTextEdit:focus {
        border: 1px solid #A2D2FF;
    }
    QScrollBar:vertical {
        border: none;
        background: rgba(200, 200, 200, 0.2);
        width: 8px;
        margin: 0px 0px 0px 0px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background: #ccc;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical:hover {
        background: #B0C4DE;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    #TitleLabel {
        font-size: 24px;
        font-weight: 800;
        color: #1a1a1a;
    }
    #SubtitleLabel {
        color: #666;
    }
    """
    app.setStyleSheet(stylesheet)

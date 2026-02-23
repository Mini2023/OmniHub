import sys
from PySide6.QtWidgets import QApplication
from ui_components.main_window import MainWindow
from ui_components.style import apply_theme

def main():
    app = QApplication(sys.argv)
    
    # Apply modern Dark Mode / Pink Accent theme
    apply_theme(app)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

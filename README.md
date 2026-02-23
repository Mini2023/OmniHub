# Project Omni-Hub: The Swiss Army Knife Desktop Application

Welcome to Project Omni-Hub! This is a modular, expandable Python desktop application built with PySide6, featuring a modern Dark Mode/Pink Accent theme.

## Features Included
1. **Universal Converter**: Convert images, video, and docs.
2. **Archive Master**: Unified interface for zip, rar, and 7z.
3. **AI Assistant**: Connects to a local Ollama instance for file searching and local summarization.
4. **Folder Watcher**: Background service that auto-sorts files in "Downloads".
5. **App Launcher**: One-click grid to launch frequently used applications.
6. **2026 Pro Add-ons**: Clipboard History, Encryption Vault, Disk Heatmap.

---

## Developer Guide: Adding a New Plugin Tab

To make Omni-Hub expandable, the UI and logic are fully modularized via a plugin-based architecture. To add a new tab to the main application window, follow these simple steps:

### 1. Create a Plugin Module
Create a new Python file in the `plugins/` directory (e.g., `tab_my_feature.py`).

### 2. Subclass QWidget
In your new file, create a class that inherits from `PySide6.QtWidgets.QWidget`.

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MyFeatureTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Add your brilliant UI components here
        label = QLabel("Welcome to my new feature!")
        layout.addWidget(label)
```

### 3. Register the Tab in Main Window
Open `ui_components/main_window.py` and import your new module:
```python
from plugins.tab_my_feature import MyFeatureTab
```

Inside the `__init__` method of `MainWindow`, add the tab to the central `QTabWidget`:
```python
self.my_feature_tab = MyFeatureTab()
self.tabs.addTab(self.my_feature_tab, "My New Feature")
```

Enjoy extending Project Omni-Hub!

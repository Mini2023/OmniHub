# OmniHub: The Overly Ambitious "Swiss Army Knife"

Welcome to **OmniHub**. Let's be honest—this started as a playground for testing ideas and seeing how many features one desktop app could handle before the UI started feeling like a cockpit. While it looks professional and runs on PySide6, this is primarily a **joke and test project** designed to push the boundaries of "feature bloat" in the most elegant way possible.

A significant portion of this project was co-authored by AI entities from the future—specifically **Claude Sonnet 4.6** and **Gemini 3.1 Flash**. If something works exceptionally well, credit the digital brains. If it crashes, blame Edward Kopp.

---

## Key Features

- **🧠 AI Assistant**: Deeply integrated module for local file searching, summarization, and chat. Powered by Ollama for maximum privacy.
- **🔄 Universal Converter**: A one-stop shop for converting images, videos, and documents without opening a browser.
- **📦 Archive Master**: A unified, modern interface for handling `.zip`, `.rar`, and `.7z` archives.
- **📁 Folder Watcher**: A silent background service that auto-sorts your clutter-filled "Downloads" folder into a temple of organization.
- **🚀 App Launcher**: A sleek grid-based dashboard for launching your favorite apps with a single click.
- **🛡️ Encryption Vault**: A secure local storage solution with a "2026 Pro" aesthetic for your sensitive data.
- **🌡️ System Monitoring**: Real-time System Health stats and a Disk Heatmap to visualize where your storage went.
- **📋 Productivity Plus**: Built-in Clipboard History, PDF document tools, and Image Pro processing.

---

## For Developers: The "Just Plug It In" Architecture

OmniHub was designed with a modular-first philosophy. We’ve ensured that adding new functionality doesn't require open-heart surgery on the core engine. If you're looking to expand this madness, follow the plugin pattern:

### 1. Isolated Plugin Modules
All UI components for new features live in the `plugins/` directory. Each tab is a self-contained Python file (e.g., `tab_your_feature.py`).

### 2. Standardized Logic
Decouple your business logic! Place heavy-duty computations or data handling in the `logic/` directory (e.g., `your_logic.py`). This keeps the UI responsive and the code testable.

### 3. Quick Registration
Integrating a new feature is as simple as subclassing `QWidget`, importing it into `ui_components/main_window.py`, and calling `self.tabs.addTab()`. 

#### Example Registration:
```python
from plugins.tab_your_feature import YourFeatureTab

# Inside MainWindow.__init__
self.new_tab = YourFeatureTab()
self.tabs.addTab(self.new_tab, "Your Feature")
```

Enjoy extending (or breaking) the OmniHub ecosystem!

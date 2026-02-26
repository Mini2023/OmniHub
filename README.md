# OmniHub: The  "Swiss Army Knife"

Welcome to **OmniHub**. This is just a test and joke project not intended for actual usage or public release. It is a collection of tools that i created to play around with stuff like AI, file management, system monitoring and encryption.

A significant portion of this project was created by AI agents because i am lazy, and that was something i wanted to play around with anyway. I used mainly **Claude Sonnet 4.6** for heavy tasks and **Gemini 3.1 Flash** for light tasks. If something works like shit well, blame the AI's. If it works credit me.

---

## Key Features

- **🧠 AI Assistant**: A module for file summarization, chat and local file searching. Powered by local Olamma or Gemini via API.
- **🔄 Universal Converter**: A module for easy conversion of multible formats and file types.
- **📦 Archive Master**: A module for unpacking and packing Archives (.zip .rar .7z)
- **📁 Folder Watcher**: A module for auto sorting selected folders into a temple of organization.
- **🚀 App Launcher**: A dashboard mosule for quick access to your favorite apps.
- **🛡️ Encryption Vault**: A module for encrypting and decrypting files into .enc Vaults. (AES-256, Twofish, Serpent)
- **🌡️ System Health**: Module for monitoring system health and fixing simple issues. (TEMP cleaner, Duplicate scanner, etc)
- **📋 Other Tools**: Clipboard history, PDF tools, Image tools, live widgets in dashboard etc.
- **Planned Tools**: expansion of image tools by integrating AI, Expansion of the quick actions in the dashboard and so on.
---

## New in v4.5

- **Image Pro Module**: A module for easy editing of images, including AI features using gemini. (background removal, smart focus crop, AI optimization etc)
- **Global Drop-Hub**: Fixes and improvements.
- **Quick Actions**: Huge expansion of library and structural changes.
- **Dashboard**: Major UI update of the dashboard, including more costumization options and new layout.

## Download / Webpage

 - omnihubwebpage.vercel.app
 -**Download via the Webpage or Github** (release or .zip)
 
## For Developers: Modular Architecture

OmniHub was designed with a modular-first philosophy. You can add new features by simply adding a new module to the `plugins/` directory.

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

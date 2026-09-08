import sys
import asyncio
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QStackedWidget
from config import GLOBAL_STYLE
from components.topbar import TopBarNav
from tabs.music_tab import MusicTab
from tabs.engine_tab import EngineTab
from tabs.maps_tab import MapsTab

class InfotainmentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("E46 Infotainment System")
        self.resize(800, 480) # Raspberry Pi display size

        # Main Layout Container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Navigation Bar
        self.topbar = TopBarNav()
        main_layout.addWidget(self.topbar)

        # Create Tab Instances
        self.music_tab = MusicTab()
        self.engine_tab = EngineTab()
        self.maps_tab = MapsTab()

        # Connect Music Signals directly to TopBarNav
        self.music_tab.track_changed.connect(self.topbar.update_music)
        self.music_tab.progress_changed.connect(self.topbar.update_music_progress)

        # Stacked Screens Area
        self.stack = QStackedWidget()
        self.stack.addWidget(self.music_tab)   # Index 0
        self.stack.addWidget(self.engine_tab)  # Index 1 (Middle / Default)
        self.stack.addWidget(self.maps_tab)    # Index 2

        main_layout.addWidget(self.stack)

        # Connect Navigation
        self.topbar.tab_changed.connect(self.stack.setCurrentIndex)
        
        # Show Engine Tab (Index 1) by default at startup
        self.stack.setCurrentIndex(1)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLE)

    # Initialize qasync event loop before creating Qt windows
    import qasync
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = InfotainmentWindow()
    window.show()

    with loop:
        loop.run_forever()
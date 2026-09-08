from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QButtonGroup,
    QLabel,
    QFrame,
    QVBoxLayout,
    QProgressBar,
)
from PyQt6.QtCore import pyqtSignal, Qt
from config import COLOR_TOPBAR


class TopBarNav(QWidget):
    tab_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.setFixedHeight(64)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLOR_TOPBAR};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(8)

        # -------------------------
        # E46 Logo
        # -------------------------
        title_logo = QLabel("E46")
        title_logo.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: 700;
                background: transparent;
            }
        """)

        layout.addWidget(title_logo)
        layout.addStretch()

        # -------------------------
        # Navigation (Engine in het midden = index 1)
        # -------------------------
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.tabs = [
            ("Music", 0),
            ("Engine", 1),  # Midden
            ("Maps", 2),
        ]

        for text, index in self.tabs:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumWidth(68)
            btn.setMinimumHeight(40)

            btn.setStyleSheet("""
                QPushButton {
                    color: #9da3ae;
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    margin: 0px;
                    font-size: 14px;
                    font-weight: 500;
                }

                QPushButton:hover {
                    color: white;
                    background-color: rgba(255, 255, 255, 0.06);
                }

                QPushButton:checked {
                    color: white;
                    background-color: rgba(255, 255, 255, 0.10);
                    font-weight: 600;
                }
            """)

            self.btn_group.addButton(btn, index)
            layout.addWidget(btn)

            # Engine Tab (Index 1) standaard als geselecteerd instellen
            if index == 1:
                btn.setChecked(True)

        layout.addStretch()

        # -------------------------
        # Music mini player
        # -------------------------
        self.music_box = QFrame()
        self.music_box.setFixedSize(230, 44)

        self.music_box.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
        """)

        music_layout = QVBoxLayout(self.music_box)
        music_layout.setContentsMargins(12, 5, 12, 5)
        music_layout.setSpacing(1)

        self.music_title = QLabel("No music playing")
        self.music_title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)

        self.music_artist = QLabel("—")
        self.music_artist.setStyleSheet("""
            QLabel {
                color: #8f96a3;
                font-size: 10px;
                background: transparent;
                border: none;
            }
        """)

        music_layout.addWidget(self.music_title)
        music_layout.addWidget(self.music_artist)

        self.music_progress = QProgressBar()
        self.music_progress.setRange(0, 100)
        self.music_progress.setValue(0)
        self.music_progress.setTextVisible(False)
        self.music_progress.setFixedHeight(3)

        self.music_progress.setStyleSheet("""
            QProgressBar {
                background-color: #303030;
                border: none;
                border-radius: 2px;
            }

            QProgressBar::chunk {
                background-color: #ffffff;
                border-radius: 2px;
            }
        """)

        music_layout.addWidget(self.music_progress)
        layout.addWidget(self.music_box)

        self.btn_group.idClicked.connect(self.tab_changed.emit)

    def update_music(self, title, artist):
        self.music_title.setText(title)
        self.music_artist.setText(artist)

    def update_music_progress(self, position, duration):
        if duration > 0:
            percent = int((position / duration) * 100)
            self.music_progress.setValue(min(percent, 100))
        else:
            self.music_progress.setValue(0)
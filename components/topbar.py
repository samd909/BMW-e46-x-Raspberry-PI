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

BG = "#000000"
BMW_RED = "#E7222E"


class TopBarNav(QWidget):
    tab_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.setFixedHeight(64)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {BG};
            }}
            QLabel {{
                background: transparent;
                background-color: transparent;
                color: {BMW_RED};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(8)

        layout.addStretch()

        # -------------------------
        # Navigation
        # -------------------------
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.tabs = [
            ("Music", 0),
            ("Engine", 1),
            ("Maps", 2),
        ]

        for text, index in self.tabs:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumWidth(68)
            btn.setMinimumHeight(40)

            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {BMW_RED};
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    margin: 0px;
                    font-size: 14px;
                    font-weight: 700;
                }}

                QPushButton:hover {{
                    color: {BMW_RED};
                    background-color: {BG};
                    border: 1px solid {BMW_RED};
                }}

                QPushButton:checked {{
                    color: {BG};
                    background-color: {BMW_RED};
                    font-weight: 800;
                }}
            """)

            self.btn_group.addButton(btn, index)
            layout.addWidget(btn)

            if index == 1:
                btn.setChecked(True)

        layout.addStretch()

        # -------------------------
        # Music mini player
        # -------------------------
        self.music_box = QFrame()
        self.music_box.setFixedSize(230, 44)

        self.music_box.setStyleSheet(f"""
            QFrame {{
                background-color: {BG};
                border: 1px solid {BMW_RED};
                border-radius: 8px;
            }}
        """)

        music_layout = QVBoxLayout(self.music_box)
        music_layout.setContentsMargins(12, 5, 12, 5)
        music_layout.setSpacing(1)

        self.music_title = QLabel("No music playing")
        self.music_title.setStyleSheet(f"""
            QLabel {{
                color: {BMW_RED};
                font-size: 12px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
        """)

        self.music_artist = QLabel("—")
        self.music_artist.setStyleSheet(f"""
            QLabel {{
                color: {BMW_RED};
                font-size: 10px;
                background: transparent;
                border: none;
            }}
        """)

        music_layout.addWidget(self.music_title)
        music_layout.addWidget(self.music_artist)

        self.music_progress = QProgressBar()
        self.music_progress.setRange(0, 100)
        self.music_progress.setValue(0)
        self.music_progress.setTextVisible(False)
        self.music_progress.setFixedHeight(3)

        self.music_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {BG};
                border: none;
                border-radius: 1px;
            }}

            QProgressBar::chunk {{
                background-color: {BMW_RED};
                border-radius: 1px;
            }}
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
import sys
import asyncio
import os
import aiohttp
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap
from dbus_next.aio import MessageBus
from dbus_next import DBusError

class ArtFetcher(QThread):
    art_loaded = pyqtSignal(bytes)

    def __init__(self, title, artist):
        super().__init__()
        self.title = title
        self.artist = artist

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.fetch_art())

    async def fetch_art(self):
        query = f"{self.artist} {self.title}"
        url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=1"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=3) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('resultCount', 0) > 0:
                            art_url = data['results'][0]['artworkUrl100'].replace('100x100bb', '300x300bb')
                            async with session.get(art_url, timeout=3) as img_resp:
                                if img_resp.status == 200:
                                    img_data = await img_resp.read()
                                    self.art_loaded.emit(img_data)
        except Exception as e:
            print(f"Artwork fetch error: {e}")


class MusicTab(QWidget):
    # Signals to stream data to TopBarNav
    track_changed = pyqtSignal(str, str)     # title, artist
    progress_changed = pyqtSignal(int, int)  # position_ms, duration_ms

    def __init__(self):
        super().__init__()
        self.track_duration = 0
        self.track_position = 0
        self.art_fetcher = None

        self.init_ui()

        # Defer task execution until the qasync loop is active
        QTimer.singleShot(0, lambda: asyncio.create_task(self.init_dbus()))

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left Column: Album Art
        self.art_label = QLabel()
        self.art_label.setFixedSize(220, 220)
        self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_label.setStyleSheet("border-radius: 12px; background-color: #1e1e1e; font-size: 48px;")
        self.set_placeholder_art("🎵")
        layout.addWidget(self.art_label)

        # Right Column: Track details & Progress
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("Waiting for Bluetooth...")
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        self.title_label.setWordWrap(True)

        self.artist_label = QLabel("No Device Connected")
        self.artist_label.setStyleSheet("font-size: 16px; color: #8e8e93;")
        self.artist_label.setWordWrap(True)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2c2c2e;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #ff9500;
                border-radius: 4px;
            }
        """)

        # Time labels
        time_layout = QHBoxLayout()
        self.time_elapsed = QLabel("0:00")
        self.time_elapsed.setStyleSheet("color: #8e8e93; font-size: 12px;")
        self.time_total = QLabel("0:00")
        self.time_total.setStyleSheet("color: #8e8e93; font-size: 12px;")
        
        time_layout.addWidget(self.time_elapsed)
        time_layout.addStretch()
        time_layout.addWidget(self.time_total)

        right_layout.addStretch()
        right_layout.addWidget(self.title_label)
        right_layout.addWidget(self.artist_label)
        right_layout.addSpacing(20)
        right_layout.addWidget(self.progress_bar)
        right_layout.addLayout(time_layout)
        right_layout.addStretch()

        layout.addLayout(right_layout)

    def set_placeholder_art(self, text):
        self.art_label.setPixmap(QPixmap())
        self.art_label.setText(text)

    def display_fetched_art(self, img_data):
        pixmap = QPixmap()
        pixmap.loadFromData(img_data)
        pixmap = pixmap.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        self.art_label.setPixmap(pixmap)

    def format_time(self, ms):
        seconds = int((ms / 1000) % 60)
        minutes = int((ms / (1000 * 60)) % 60)
        return f"{minutes}:{seconds:02d}"

    def update_metadata(self, track_data):
        title = track_data.get('Title', {}).value if 'Title' in track_data else "Unknown Track"
        artist = track_data.get('Artist', {}).value if 'Artist' in track_data else "Unknown Artist"
        duration = track_data.get('Duration', {}).value if 'Duration' in track_data else 0

        self.title_label.setText(title)
        self.artist_label.setText(artist)
        self.track_duration = duration
        self.time_total.setText(self.format_time(duration))

        # Emit track details to TopBarNav
        self.track_changed.emit(title, artist)

        # Reset artwork to placeholder while loading new art
        self.set_placeholder_art("🎵")

        if title != "Unknown Track":
            if self.art_fetcher and self.art_fetcher.isRunning():
                self.art_fetcher.terminate()

            self.art_fetcher = ArtFetcher(title, artist)
            self.art_fetcher.art_loaded.connect(self.display_fetched_art)
            self.art_fetcher.start()

    def sync_progress_ui(self):
        if self.track_duration > 0:
            percent = int((self.track_position / self.track_duration) * 100)
            self.progress_bar.setValue(min(percent, 100))
        else:
            self.progress_bar.setValue(0)

        self.time_elapsed.setText(self.format_time(self.track_position))

        # Emit progress update to TopBarNav
        self.progress_changed.emit(self.track_position, self.track_duration)

    async def init_dbus(self):
        try:
            bus = await MessageBus().connect()
            introspect = await bus.introspect('org.bluez', '/org/bluez/hci0')
            
            while True:
                await asyncio.sleep(1)
                if self.track_duration > 0 and self.track_position < self.track_duration:
                    self.track_position += 1000
                    self.sync_progress_ui()
        except Exception as e:
            print(f"D-Bus connection skipped or failed: {e}")
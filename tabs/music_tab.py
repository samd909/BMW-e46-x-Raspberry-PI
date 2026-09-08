import sys
import asyncio
import os
import urllib.parse
import urllib.request
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage, QFont
from dbus_next.aio import MessageBus
from dbus_next import BusType, DBusError


# Background thread to fetch album art without freezing the UI thread
class ArtFetcher(QThread):
    art_loaded = pyqtSignal(bytes)

    def __init__(self, title, artist):
        super().__init__()
        self.title = title
        self.artist = artist

    def run(self):
        try:
            query = f"{self.title} {self.artist}"
            url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                if data.get('resultCount', 0) > 0:
                    img_url = data['results'][0]['artworkUrl100'].replace('100x100bb', '600x600bb')
                    with urllib.request.urlopen(img_url, timeout=3) as img_resp:
                        self.art_loaded.emit(img_resp.read())
        except Exception as e:
            print(f"Artwork fetch error: {e}")


class MusicTab(QWidget):
    # Signals to stream data to TopBarNav
    track_changed = pyqtSignal(str, str)     # title, artist
    progress_changed = pyqtSignal(int, int)  # position_ms, duration_ms

    def __init__(self):
        super().__init__()
        self.media_player = None
        self.bus = None
        self.track_duration = 0  # ms
        self.track_position = 0  # ms
        self.art_fetcher = None

        self.init_ui()

        # Local timer for smooth progress increments between D-Bus sync updates
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self.tick_progress)

        # Defer D-Bus initialization to allow qasync event loop startup
        QTimer.singleShot(100, lambda: asyncio.create_task(self.connect_dbus()))

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel#TitleLabel {
                font-size: 22px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QLabel#ArtistLabel {
                font-size: 16px;
                color: #B3B3B3;
            }
            QLabel#TimeLabel {
                font-size: 12px;
                color: #888888;
                font-weight: 600;
            }
            QProgressBar {
                border: none;
                background-color: #282828;
                height: 8px;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #ff9500;
                border-radius: 4px;
            }
            QPushButton.control-btn {
                background-color: transparent;
                border: none;
                color: #B3B3B3;
                font-size: 22px;
            }
            QPushButton.control-btn:hover {
                color: #FFFFFF;
            }
            QPushButton.play-btn {
                background-color: #FFFFFF;
                border-radius: 25px;
                color: #000000;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton.play-btn:hover {
                background-color: #ff9500;
                color: #FFFFFF;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left Column: Album Art
        self.art_label = QLabel()
        self.art_label.setFixedSize(220, 220)
        self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_label.setStyleSheet("border-radius: 12px; background-color: #1e1e1e;")
        self.set_placeholder_art("🎵")
        layout.addWidget(self.art_label)

        # Right Column: Info, Progress & Controls
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("Connecting...")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setWordWrap(True)

        self.artist_label = QLabel("Searching for device")
        self.artist_label.setObjectName("ArtistLabel")
        self.artist_label.setWordWrap(True)

        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(4)
        meta_layout.addWidget(self.title_label)
        meta_layout.addWidget(self.artist_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        # Time labels
        time_layout = QHBoxLayout()
        self.time_elapsed = QLabel("0:00")
        self.time_elapsed.setObjectName("TimeLabel")
        self.time_total = QLabel("0:00")
        self.time_total.setObjectName("TimeLabel")
        
        time_layout.addWidget(self.time_elapsed)
        time_layout.addStretch()
        time_layout.addWidget(self.time_total)

        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(6)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addLayout(time_layout)

        # Playback Controls
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(44, 44)
        self.btn_prev.setProperty("class", "control-btn")
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(50, 50)
        self.btn_play.setProperty("class", "play-btn")
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(44, 44)
        self.btn_next.setProperty("class", "control-btn")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_prev.clicked.connect(lambda: asyncio.create_task(self.send_command("Previous")))
        self.btn_play.clicked.connect(lambda: asyncio.create_task(self.toggle_play_pause()))
        self.btn_next.clicked.connect(lambda: asyncio.create_task(self.send_command("Next")))

        ctrl_layout = QHBoxLayout()
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        ctrl_layout.setSpacing(16)
        ctrl_layout.addWidget(self.btn_prev)
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.btn_next)

        right_layout.addStretch()
        right_layout.addLayout(meta_layout)
        right_layout.addSpacing(15)
        right_layout.addLayout(progress_layout)
        right_layout.addSpacing(10)
        right_layout.addLayout(ctrl_layout)
        right_layout.addStretch()

        layout.addLayout(right_layout)

    def set_placeholder_art(self, symbol: str):
        self.art_label.setPixmap(QPixmap())
        self.art_label.setText(symbol)
        self.art_label.setFont(QFont("Arial", 48))

    def display_fetched_art(self, image_data):
        image = QImage()
        if image.loadFromData(image_data):
            pixmap = QPixmap.fromImage(image)
            pixmap = pixmap.scaled(
                220, 220,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self.art_label.setPixmap(pixmap)

    @staticmethod
    def format_time(ms):
        seconds = int((ms / 1000) % 60)
        minutes = int((ms / (1000 * 60)) % 60)
        return f"{minutes}:{seconds:02d}"

    # --- D-Bus Integration ---

    async def connect_dbus(self):
        try:
            self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
            introspection = await self.bus.introspect('org.bluez', '/')
            obj = self.bus.get_proxy_object('org.bluez', '/', introspection)
            om = obj.get_interface('org.freedesktop.DBus.ObjectManager')

            objects = await om.call_get_managed_objects()

            for path, interfaces in objects.items():
                if 'org.bluez.MediaPlayer1' in interfaces:
                    player_intro = await self.bus.introspect('org.bluez', path)
                    player_obj = self.bus.get_proxy_object('org.bluez', path, player_intro)
                    self.media_player = player_obj.get_interface('org.bluez.MediaPlayer1')

                    props = player_obj.get_interface('org.freedesktop.DBus.Properties')

                    track = await props.call_get('org.bluez.MediaPlayer1', 'Track')
                    status = await props.call_get('org.bluez.MediaPlayer1', 'Status')
                    position = await props.call_get('org.bluez.MediaPlayer1', 'Position')

                    self.update_playback_status(status.value)
                    self.update_position(position.value)
                    self.update_metadata(track.value)

                    props.on_properties_changed(self.on_properties_changed)
                    return

            self.title_label.setText("No Player Found")
            self.artist_label.setText("Connect phone in Bluetooth settings")
            # Retry connection after 3 seconds
            QTimer.singleShot(3000, lambda: asyncio.create_task(self.connect_dbus()))

        except Exception as e:
            self.title_label.setText("D-Bus Connection Error")
            self.artist_label.setText(str(e))
            QTimer.singleShot(3000, lambda: asyncio.create_task(self.connect_dbus()))

    def on_properties_changed(self, interface, changed_properties, invalidated):
        if interface == 'org.bluez.MediaPlayer1':
            if 'Track' in changed_properties:
                self.update_metadata(changed_properties['Track'].value)
            if 'Status' in changed_properties:
                self.update_playback_status(changed_properties['Status'].value)
            if 'Position' in changed_properties:
                self.update_position(changed_properties['Position'].value)

    def update_metadata(self, track_data):
        title = track_data.get('Title', {}).value if 'Title' in track_data else "Unknown Track"
        artist = track_data.get('Artist', {}).value if 'Artist' in track_data else "Unknown Artist"
        duration = track_data.get('Duration', {}).value if 'Duration' in track_data else 0

        self.title_label.setText(title)
        self.artist_label.setText(artist)
        self.track_duration = duration
        self.time_total.setText(self.format_time(duration))

        # Emit metadata update to TopBarNav
        self.track_changed.emit(title, artist)

        # Reset artwork to placeholder during fetch
        self.set_placeholder_art("🎵")

        if title != "Unknown Track":
            if self.art_fetcher and self.art_fetcher.isRunning():
                self.art_fetcher.terminate()

            self.art_fetcher = ArtFetcher(title, artist)
            self.art_fetcher.art_loaded.connect(self.display_fetched_art)
            self.art_fetcher.start()

    def update_playback_status(self, status):
        if status == "playing":
            self.btn_play.setText("⏸")
            self.progress_timer.start()
        else:
            self.btn_play.setText("▶")
            self.progress_timer.stop()

    def update_position(self, pos_ms):
        self.track_position = pos_ms
        self.sync_progress_ui()

    def tick_progress(self):
        if self.track_duration > 0 and self.track_position < self.track_duration:
            self.track_position += 1000
            self.sync_progress_ui()

    def sync_progress_ui(self):
        if self.track_duration > 0:
            percent = int((self.track_position / self.track_duration) * 100)
            self.progress_bar.setValue(min(percent, 100))
        else:
            self.progress_bar.setValue(0)

        self.time_elapsed.setText(self.format_time(self.track_position))

        # Emit position and duration updates to TopBarNav
        self.progress_changed.emit(self.track_position, self.track_duration)

    # --- Control Actions ---

    async def send_command(self, command):
        if self.media_player:
            func = getattr(self.media_player, f"call_{command.lower()}")
            await func()

    async def toggle_play_pause(self):
        if self.media_player:
            if self.btn_play.text() == "⏸":
                await self.media_player.call_pause()
            else:
                await self.media_player.call_play()
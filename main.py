#!/usr/bin/env python3
import sys
import argparse
import datetime
import shutil
import subprocess
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, 
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, 
    QLineEdit, QTextEdit, QSlider, QCheckBox, QMessageBox
)
from PyQt6.QtGui import QFont

from kbus_backend import KBusManager, GROUPS

# Strict Black & BMW Red QSS Styling voor 1024x600 Touchscreen
BLACK_RED_STYLE = """
QMainWindow, QWidget {
    background-color: #050505;
    color: #e6e6e6;
    font-family: 'DejaVu Sans', Arial, sans-serif;
}
QPushButton {
    background-color: #121212;
    color: #e6e6e6;
    border: 1px solid #2a0808;
    border-radius: 5px;
    padding: 6px;
    font-size: 11px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #240a0a;
    border-color: #cc0000;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #cc0000;
    color: white;
}
QPushButton.accent {
    background-color: #2c0000;
    color: #ff3333;
    border: 1px solid #cc0000;
}
QPushButton.accent:hover {
    background-color: #cc0000;
    color: white;
}
QWidget#panel {
    background-color: #0c0c0c;
    border: 1px solid #220505;
    border-radius: 6px;
}
QLineEdit {
    background-color: #0f0f0f;
    color: #e6e6e6;
    border: 1px solid #2a0808;
    border-radius: 4px;
    padding: 6px;
    font-size: 12px;
}
QTextEdit {
    background-color: #080808;
    color: #ff6666;
    border: 1px solid #2a0808;
    border-radius: 4px;
    font-family: monospace;
    font-size: 10px;
}
QSlider::groove:horizontal {
    height: 5px;
    background: #141414;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #cc0000;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #e6e6e6;
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QCheckBox {
    color: #e6e6e6;
    spacing: 6px;
    font-weight: bold;
    font-size: 11px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #2a0808;
    border-radius: 3px;
    background: #0f0f0f;
}
QCheckBox::indicator:checked {
    background: #cc0000;
    border-color: #cc0000;
}
"""

class Communicator(QObject):
    log_signal = pyqtSignal(str)

class E46Dashboard(QMainWindow):
    def __init__(self, port, baud):
        super().__init__()
        self.port = port
        self.baud = baud
        self.kbus = KBusManager()
        self.comm = Communicator()
        self.comm.log_signal.connect(self.append_log)

        self.playing = False
        self.volume_val = 55
        self.live_tx = False

        self.setWindowTitle("BMW E46 • 1024x600 Dashboard")
        
        # STRIKT GEFIXED OP 1024x600
        self.setFixedSize(1024, 600)
        self.setStyleSheet(BLACK_RED_STYLE)

        self.init_ui()
        
        # Achtergrond timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_queue)
        self.timer.start(100)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 6, 10, 6)
        main_layout.setSpacing(4)

        # --- TOPBAR (COMPACT VOOR 600H) ---
        header = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)
        lbl_title = QLabel("BMW E46")
        lbl_title.setFont(QFont("DejaVu Sans", 16, QFont.Weight.Bold))
        lbl_sub = QLabel("N46 • K-BUS INFOTAINMENT")
        lbl_sub.setStyleSheet("color: #883333; font-size: 9px;")
        title_layout.addWidget(lbl_title)
        title_layout.addWidget(lbl_sub)
        header.addLayout(title_layout)

        header.addStretch()

        right_header = QVBoxLayout()
        right_header.setSpacing(0)
        self.lbl_status = QLabel("○ K-BUS • DEMO")
        self.lbl_status.setStyleSheet("color: #883333; font-size: 10px;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.lbl_clock = QLabel("--:--")
        self.lbl_clock.setFont(QFont("DejaVu Sans", 16, QFont.Weight.Bold))
        self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        right_header.addWidget(self.lbl_status)
        right_header.addWidget(self.lbl_clock)
        header.addLayout(right_header)
        main_layout.addLayout(header)

        # --- PAGINA STACK ---
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, stretch=1)

        self.page_home = self.create_home_page()
        self.page_auto = self.create_auto_page()
        self.page_media = self.create_media_page()
        self.page_navi = self.create_navi_page()
        self.page_settings = self.create_settings_page()

        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_auto)
        self.stack.addWidget(self.page_media)
        self.stack.addWidget(self.page_navi)
        self.stack.addWidget(self.page_settings)

        # --- ONDERSTE NAVIGATIE BAR (TABS) ---
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(4)

        tabs = [
            ("HOME", lambda: self.stack.setCurrentWidget(self.page_home)),
            ("AUTO", lambda: self.stack.setCurrentWidget(self.page_auto)),
            ("MEDIA", lambda: self.stack.setCurrentWidget(self.page_media)),
            ("NAVI", lambda: self.stack.setCurrentWidget(self.page_navi)),
            ("SETTINGS", lambda: self.stack.setCurrentWidget(self.page_settings)),
        ]

        for name, callback in tabs:
            btn = QPushButton(name)
            btn.setFixedHeight(40)
            btn.clicked.connect(callback)
            nav_bar.addWidget(btn)

        btn_exit = QLabel("X") # Minimalistisch exit knopje of tekst
        btn_exit_btn = QPushButton("SLUIT")
        btn_exit_btn.setFixedHeight(40)
        btn_exit_btn.setProperty("class", "accent")
        btn_exit_btn.clicked.connect(self.close)
        nav_bar.addWidget(btn_exit_btn)

        main_layout.addLayout(nav_bar)

    # --- TAB 1: HOME ---
    def create_home_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Links: Snelle controls
        left_panel = QWidget()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("<b>SNELLE BEDIENING</b>"))
        
        grid = QGridLayout()
        grid.addWidget(QPushButton("RAAM L OPEN", clicked=lambda: self.send_cmd(*GROUPS['Ramen'][0])), 0, 0)
        grid.addWidget(QPushButton("RAAM L DICHT", clicked=lambda: self.send_cmd(*GROUPS['Ramen'][1])), 0, 1)
        grid.addWidget(QPushButton("RAAM R OPEN", clicked=lambda: self.send_cmd(*GROUPS['Ramen'][2])), 1, 0)
        grid.addWidget(QPushButton("RAAM R DICHT", clicked=lambda: self.send_cmd(*GROUPS['Ramen'][3])), 1, 1)
        grid.addWidget(QPushButton("VERGRENDEL", clicked=lambda: self.send_cmd(*GROUPS['Portieren'][0])), 2, 0)
        grid.addWidget(QPushButton("KOFFERBAK*", clicked=lambda: self.send_cmd(*GROUPS['Portieren'][2])), 2, 1)
        left_layout.addLayout(grid)
        layout.addWidget(left_panel, stretch=1)

        # Rechts: Media & Status Widget
        right_panel = QWidget()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("<b>MEDIA PREVIEW</b>"))
        
        self.lbl_play_status = QLabel("Gepauzeerd • Demo")
        self.lbl_play_status.setStyleSheet("color: #883333;")
        right_layout.addWidget(self.lbl_play_status)
        
        btn_box = QHBoxLayout()
        btn_box.addWidget(QPushButton("▶ / Ⅱ", clicked=self.toggle_play))
        right_layout.addLayout(btn_box)
        right_layout.addStretch()

        layout.addWidget(right_panel, stretch=1)
        return page

    # --- TAB 2: AUTO / K-BUS ---
    def create_auto_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        row, col = 0, 0
        for group_name, cmds in GROUPS.items():
            box = QWidget()
            box.setObjectName("panel")
            box_layout = QVBoxLayout(box)
            box_layout.addWidget(QLabel(f"<b>{group_name.upper()}</b>"))
            
            for name, payload, risk in cmds:
                btn = QPushButton(name)
                btn.clicked.connect(lambda checked, n=name, p=payload, r=risk: self.send_cmd(n, p, r))
                box_layout.addWidget(btn)
            
            layout.addWidget(box, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
        return page

    # --- TAB 3: MEDIA ---
    def create_media_page(self):
        page = QWidget()
        page.setObjectName("panel")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_icon = QLabel("♫")
        lbl_icon.setStyleSheet("color: #cc0000; font-size: 48px;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_icon)

        lbl_title = QLabel("BMW Audio Center")
        lbl_title.setFont(QFont("DejaVu Sans", 16, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel("Volume"))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(self.volume_val)
        slider.valueChanged.connect(lambda v: setattr(self, 'volume_val', v))
        vol_layout.addWidget(slider)
        layout.addLayout(vol_layout)

        return page

    # --- TAB 4: NAVIGATIE ---
    def create_navi_page(self):
        page = QWidget()
        page.setObjectName("panel")
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel("Google Maps / Chromium Kiosk")
        lbl.setFont(QFont("DejaVu Sans", 14, QFont.Weight.Bold))
        layout.addWidget(lbl)

        btn_map = QPushButton("OPEN GOOGLE MAPS FULLSCREEN")
        btn_map.setProperty("class", "accent")
        btn_map.setFixedHeight(50)
        btn_map.clicked.connect(self.start_maps)
        layout.addWidget(btn_map)

        return page

    # --- TAB 5: SETTINGS ---
    def create_settings_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Links: Verbindingen & Log
        left_box = QWidget()
        left_box.setObjectName("panel")
        left = QVBoxLayout(left_box)
        left.addWidget(QLabel("<b>K-BUS SERIEEL</b>"))
        
        self.port_input = QLineEdit(self.port)
        left.addWidget(self.port_input)

        self.btn_connect = QPushButton("VERBINDEN / VERBREKEN", clicked=self.toggle_serial)
        left.addWidget(self.btn_connect)

        self.chk_live = QCheckBox("LIVE K-BUS TX TOESTAAN")
        self.chk_live.stateChanged.connect(lambda state: setattr(self, 'live_tx', state == Qt.CheckState.Checked.State))
        left.addWidget(self.chk_live)

        left.addWidget(QLabel("LOG MONITOR:"))
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        left.addWidget(self.log_widget)
        
        layout.addWidget(left_box, stretch=1)

        # Rechts: Auto Info
        right_box = QWidget()
        right_box.setObjectName("panel")
        right = QVBoxLayout(right_box)
        right.addWidget(QLabel("<b>SYSTEEM INFO</b>"))
        right.addWidget(QLabel("Motortype: N46B20A"))
        right.addWidget(QLabel("ECU: Bosch MEV9"))
        right.addWidget(QLabel("Koelvloeistof: Wacht op K-Bus"))
        right.addStretch()

        layout.addWidget(right_box, stretch=1)
        return page

    # --- LOGICA ---
    def send_cmd(self, name, payload, risk='normal'):
        if risk in ('pinch', 'lock', 'motion'):
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Veiligheidswaarschuwing")
            dlg.setText(f"Alleen bedienen terwijl de auto stilstaat.\n\n{name} uitvoeren?")
            dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if dlg.exec() != QMessageBox.StandardButton.Yes:
                return

        success, msg = self.kbus.send(payload, live=self.live_tx)
        self.append_log(msg)

    def toggle_serial(self):
        if self.kbus.ser:
            self.kbus.close()
            self.lbl_status.setText("○ K-BUS • VERBROKEN")
            self.append_log("K-Bus verbroken.")
        else:
            try:
                port = self.port_input.text()
                self.kbus.connect(port, self.baud)
                self.lbl_status.setText(f"● K-BUS VERBONDEN")
                self.append_log(f"Verbonden: {port}")
            except Exception as e:
                QMessageBox.critical(self, "Fout", str(e))

    def poll_queue(self):
        while not self.kbus.rx_queue.empty():
            item = self.kbus.rx_queue.get_nowait()
            self.append_log(item)

    def append_log(self, text):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_widget.append(f"{timestamp} {text}")

    def update_clock(self):
        now = datetime.datetime.now()
        self.lbl_clock.setText(now.strftime("%H:%M"))

    def toggle_play(self):
        self.playing = not self.playing
        status = "▶ Spelend • Demo" if self.playing else "Gepauzeerd • Demo"
        self.lbl_play_status.setText(status)

    def start_maps(self):
        url = 'https://www.google.com/maps'
        browser = next((shutil.which(n) for n in ('chromium-browser', 'chromium', 'google-chrome') if shutil.which(n)), None)
        if browser:
            subprocess.Popen([browser, '--kiosk', '--new-window', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.append_log("Google Maps geopend in kiosk")
        else:
            import webbrowser
            webbrowser.open(url)
            self.append_log("Google Maps geopend in browser")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='/dev/ttyUSB0')
    ap.add_argument('--baud', type=int, default=9600)
    args = ap.parse_args()

    app = QApplication(sys.argv)
    dash = E46Dashboard(args.port, args.baud)
    dash.show()
    sys.exit(app.exec())
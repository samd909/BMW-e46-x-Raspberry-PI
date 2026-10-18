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
    QLineEdit, QTextEdit, QSlider, QCheckBox, QMessageBox, QFrame, QProgressBar, QSizePolicy
)
from PyQt6.QtGui import QFont

from kbus_backend import KBusManager, GROUPS
from mev9_reader import MEV9Reader

# Strakke Zwarte & BMW M-Rode styling gebaseerd op je voorbeeld
BLACK_RED_STYLE = """
QMainWindow, QWidget {
    background-color: #000000;
    color: #E7222E;
    font-family: 'DejaVu Sans', Arial, sans-serif;
}
QPushButton {
    background-color: #121212;
    color: #E7222E;
    border: 1px solid #E7222E;
    border-radius: 5px;
    padding: 6px 12px;
    min-height: 32px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #260c00;
    border-color: #E7222E;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #E7222E;
    color: white;
}
QPushButton.accent {
    background-color: #3d1200;
    color: #ff6622;
    border: 1px solid #E7222E;
}
QPushButton.accent:hover {
    background-color: #E7222E;
    color: white;
}
QWidget#panel {
    background-color: #000000;
    border: 1px solid #E7222E;
    border-radius: 8px;
}
QLineEdit {
    background-color: #0f0f0f;
    color: #E7222E;
    border: 1px solid #E7222E;
    border-radius: 6px;
    padding: 8px;
    font-size: 12px;
}
QTextEdit {
    background-color: #000000;
    color: #E7222E;
    border: 1px solid #E7222E;
    border-radius: 6px;
    font-family: monospace;
    font-size: 10px;
}
QSlider::groove:horizontal {
    height: 8px;
    background: #141414;
    border-radius: 4px;
}
QSlider::sub-page:horizontal {
    background: #E7222E;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #E7222E;
    width: 22px;
    margin: -7px 0;
    border-radius: 11px;
}
QCheckBox {
    color: #E7222E;
    spacing: 8px;
    font-weight: bold;
    font-size: 11px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #E7222E;
    border-radius: 4px;
    background: #0f0f0f;
}
QCheckBox::indicator:checked {
    background: #E7222E;
    border-color: #E7222E;
}
QProgressBar#LiveBar {
    background-color: #000000;
    border: 1px solid #E7222E;
    border-radius: 5px;
    min-height: 12px;
    max-height: 12px;
}
QProgressBar#LiveBar::chunk {
    background-color: #E7222E;
    border-radius: 4px;
}
QFrame#MetricCard, QFrame#LiveSlider {
    background-color: #000000;
    border: 1px solid #E7222E;
    border-radius: 8px;
}
"""

# --- HULP WIDGETS GEBASEERD OP JOUW VOORBEELD ---
class MetricCard(QFrame):
    def __init__(self, title, unit="", parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.title = QLabel(f'<span style="color:#E7222E;">&#9632;</span>&nbsp;&nbsp;{title}')
        self.title.setTextFormat(Qt.TextFormat.RichText)
        self.title.setStyleSheet("font-size: 10px; font-weight: 800; color: #E7222E;")

        self.value = QLabel("--")
        self.value.setStyleSheet("font-size: 24px; font-weight: 800; color: #E7222E;")

        self.unit = QLabel(unit)
        self.unit.setStyleSheet("font-size: 10px; font-weight: 700; color: #E7222E; padding-bottom: 3px;")

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(4)
        value_row.addWidget(self.value)
        value_row.addWidget(self.unit)
        value_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        layout.addWidget(self.title)
        layout.addStretch(1)
        layout.addLayout(value_row)

    def set_value(self, value, decimals=1):
        if value is None:
            self.value.setText("--")
            return
        if isinstance(value, float):
            self.value.setText(f"{value:.{decimals}f}")
        else:
            self.value.setText(str(value))


class LiveSlider(QFrame):
    def __init__(self, title, maximum, unit_type, unit_label, parent=None):
        super().__init__(parent)
        self.maximum = maximum
        self.unit_type = unit_type
        self.setObjectName("LiveSlider")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.title_label = QLabel(f'<span style="color:#E7222E;">&#9632;</span>&nbsp;&nbsp;{title}')
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        self.title_label.setStyleSheet("font-size: 11px; font-weight: 800; color: #E7222E;")

        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("font-size: 38px; font-weight: 800; color: #E7222E;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.unit_label = QLabel(unit_label)
        self.unit_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #E7222E;")
        self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.bar = QProgressBar()
        self.bar.setObjectName("LiveBar")
        self.bar.setRange(0, maximum)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.value_label)
        layout.addWidget(self.unit_label)
        layout.addStretch(1)
        layout.addWidget(self.bar)

    def set_value(self, value):
        if value is None:
            self.value_label.setText("--")
            self.bar.setValue(0)
            return
        value = max(0, min(self.maximum, value))
        if self.unit_type == "rpm":
            self.value_label.setText(f"{int(value):,}")
        else:
            self.value_label.setText(f"{value:.1f}")
        self.bar.setValue(int(value))


class Communicator(QObject):
    log_signal = pyqtSignal(str)


class E46Dashboard(QMainWindow):
    def __init__(self, port, obd_port, baud):
        super().__init__()
        self.port = port
        self.obd_port = obd_port
        self.baud = baud
        
        self.kbus = KBusManager()
        self.comm = Communicator()
        self.comm.log_signal.connect(self.append_log)

        self.playing = False
        self.volume_val = 55
        self.live_tx = False

        self.setWindowTitle("BMW E46 • 1024x600 Dashboard")
        self.setStyleSheet(BLACK_RED_STYLE)

        self.init_ui()
        self.showFullScreen()

        # Start de MEV9 reader voor de OBD2 motor data
        self.obd_reader = MEV9Reader(port=self.obd_port, parent=self)
        self.obd_reader.data_received.connect(self.update_obd_data)
        self.obd_reader.start()

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
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Bovenste 3% zwarte ruimte
        top_black = QWidget()
        top_black.setStyleSheet("background-color: #000000;")
        main_layout.addWidget(top_black, 3)

        # Topbar (25%)
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #000000;")

        header = QHBoxLayout(header_widget)
        header.setContentsMargins(18, 0, 18, 0)
        header.setSpacing(16)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        lbl_title = QLabel("BMW E46")
        lbl_title.setFont(QFont("DejaVu Sans", 23, QFont.Weight.Bold))
        lbl_sub = QLabel("N46 • K-BUS & OBD2")
        lbl_sub.setStyleSheet("color: #E7222E; font-size: 14px;")
        title_layout.addWidget(lbl_title)
        title_layout.addWidget(lbl_sub)
        
        title_container = QWidget()
        title_container.setLayout(title_layout)
        header.addWidget(title_container, alignment=Qt.AlignmentFlag.AlignVCenter)

        header.addStretch(1)

        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(10)

        tabs = [
            ("HOME", lambda: self.stack.setCurrentWidget(self.page_home)),
            ("AUTO", lambda: self.stack.setCurrentWidget(self.page_auto)),
            ("MEDIA", lambda: self.stack.setCurrentWidget(self.page_media)),
            ("NAVI", lambda: self.stack.setCurrentWidget(self.page_navi)),
            ("SETTINGS", lambda: self.stack.setCurrentWidget(self.page_settings)),
        ]

        for name, callback in tabs:
            btn = QPushButton(name)
            btn.setFixedSize(112, 58)
            btn.setFont(QFont("DejaVu Sans", 13, QFont.Weight.Bold))
            btn.clicked.connect(callback)
            nav_bar.addWidget(btn)

        nav_container = QWidget()
        nav_container.setLayout(nav_bar)
        header.addWidget(nav_container, alignment=Qt.AlignmentFlag.AlignVCenter)
        header.addStretch(1)

        right_header = QVBoxLayout()
        right_header.setSpacing(0)
        self.lbl_clock = QLabel("--:--")
        self.lbl_clock.setFont(QFont("DejaVu Sans", 28, QFont.Weight.Bold))
        self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right_header.addWidget(self.lbl_clock)
        
        right_container = QWidget()
        right_container.setLayout(right_header)
        header.addWidget(right_container, alignment=Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(header_widget, 25)

        # Main Page Stack (72%)
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 72)

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

    # --- HOMEPAGE MET MOTOR DATA & SNELLE K-BUS BEDIENING ---
    def create_home_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        # Linkskant: Live Motor Data (OBD2) in jouw gewenste strakke stijl
        left_panel = QWidget()
        left_panel.setObjectName("panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        
        lbl_motor_header = QLabel("<b>LIVE MOTORDATA (MEV9)</b>")
        left_layout.addWidget(lbl_motor_header)

        # Bovenste rij sliders (RPM, Throttle, Coolant)
        hero_row = QHBoxLayout()
        hero_row.setSpacing(8)
        self.rpm_slider = LiveSlider("RPM", 6800, "rpm", "RPM")
        self.throttle_slider = LiveSlider("THROTTLE", 100, "%", "%")
        self.coolant_slider = LiveSlider("COOLANT", 120, "c", "°C")
        hero_row.addWidget(self.rpm_slider, 1)
        hero_row.addWidget(self.throttle_slider, 1)
        hero_row.addWidget(self.coolant_slider, 1)
        left_layout.addLayout(hero_row, 3)

        # Onderste grid voor extra sensoren (Intake, MAF, Ignition, Load)
        mid_grid = QGridLayout()
        mid_grid.setHorizontalSpacing(6)
        mid_grid.setVerticalSpacing(6)

        self.card_intake = MetricCard("INTAKE", "°C")
        self.card_maf = MetricCard("MAF", "g/s")
        self.card_timing = MetricCard("IGNITION", "°")
        self.card_load = MetricCard("LOAD", "%")

        mid_grid.addWidget(self.card_intake, 0, 0)
        mid_grid.addWidget(self.card_maf, 0, 1)
        mid_grid.addWidget(self.card_timing, 0, 2)
        mid_grid.addWidget(self.card_load, 0, 3)
        left_layout.addLayout(mid_grid, 2)

        layout.addWidget(left_panel, stretch=6)

        # Rechtskant: Snelle K-Bus knoppen & Media Preview
        right_panel = QWidget()
        right_panel.setObjectName("panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)
        
        right_layout.addWidget(QLabel("<b>SNELLE K-BUS BEDIENING</b>"))
        
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.addWidget(QPushButton("RAAM L OPEN", clicked=lambda: self.send_cmd(*GROUPS['Ramen'][0])), 0, 0)
        grid.addWidget(QPushButton("RAAM L DICHT", clicked=lambda: self.send_cmd(*GROUPS['Ramen'][1])), 0, 1)
        grid.addWidget(QPushButton("RAAM R OPEN", clicked=lambda: self.send_cmd(*GROUPS['Ramen'][2])), 1, 0)
        grid.addWidget(QPushButton("RAAM R DICHT", clicked=lambda: self.send_cmd(*GROUPS['Ramen'][3])), 1, 1)
        grid.addWidget(QPushButton("VERGRENDEL", clicked=lambda: self.send_cmd(*GROUPS['Portieren'][0])), 2, 0)
        grid.addWidget(QPushButton("KOFFERBAK*", clicked=lambda: self.send_cmd(*GROUPS['Portieren'][2])), 2, 1)
        right_layout.addLayout(grid)

        right_layout.addSpacing(10)
        right_layout.addWidget(QLabel("<b>MEDIA PREVIEW</b>"))
        self.lbl_play_status = QLabel("Gepauzeerd • Demo")
        self.lbl_play_status.setStyleSheet("color: #E7222E;")
        right_layout.addWidget(self.lbl_play_status)
        
        btn_box = QHBoxLayout()
        btn_box.addWidget(QPushButton("▶ / Ⅱ", clicked=self.toggle_play))
        right_layout.addLayout(btn_box)
        right_layout.addStretch()

        layout.addWidget(right_panel, stretch=4)
        return page

    def update_obd_data(self, data):
        # Update alle velden live vanuit de MEV9 reader
        self.rpm_slider.set_value(data.get("rpm"))
        self.throttle_slider.set_value(data.get("throttle"))
        self.coolant_slider.set_value(data.get("coolant"))

        self.card_intake.set_value(data.get("intake"), 1)
        self.card_maf.set_value(data.get("maf"), 1)
        self.card_timing.set_value(data.get("timing"), 1)
        self.card_load.set_value(data.get("load"), 1)

    # --- TAB 2: AUTO / K-BUS ---
    def create_auto_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)
        
        row, col = 0, 0
        for group_name, cmds in GROUPS.items():
            box = QWidget()
            box.setObjectName("panel")
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(12, 12, 12, 12)
            box_layout.setSpacing(8)
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_icon = QLabel("♫")
        lbl_icon.setStyleSheet("color: #E7222E; font-size: 52px;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_icon)

        lbl_title = QLabel("BMW Audio Center")
        lbl_title.setFont(QFont("DejaVu Sans", 16, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        vol_layout = QHBoxLayout()
        vol_layout.setSpacing(15)
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel("Google Maps / Chromium Kiosk")
        lbl.setFont(QFont("DejaVu Sans", 14, QFont.Weight.Bold))
        layout.addWidget(lbl)

        btn_map = QPushButton("OPEN GOOGLE MAPS FULLSCREEN")
        btn_map.setProperty("class", "accent")
        btn_map.setFixedHeight(55)
        btn_map.clicked.connect(self.start_maps)
        layout.addWidget(btn_map)

        return page

    # --- TAB 5: SETTINGS ---
    def create_settings_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        left_box = QWidget()
        left_box.setObjectName("panel")
        left = QVBoxLayout(left_box)
        left.setContentsMargins(14, 14, 14, 14)
        left.setSpacing(10)
        left.addWidget(QLabel("<b>K-BUS & OBD2 CONFIGURATIE</b>"))
        
        left.addWidget(QLabel("K-Bus Port:"))
        self.port_input = QLineEdit(self.port)
        left.addWidget(self.port_input)

        left.addWidget(QLabel("OBD2 Port:"))
        self.obd_port_input = QLineEdit(self.obd_port)
        left.addWidget(self.obd_port_input)

        self.btn_connect = QPushButton("K-BUS VERBINDEN / VERBREKEN", clicked=self.toggle_serial)
        left.addWidget(self.btn_connect)

        self.chk_live = QCheckBox("LIVE K-BUS TX TOESTAAN")
        self.chk_live.stateChanged.connect(lambda state: setattr(self, 'live_tx', state == Qt.CheckState.Checked.State))
        left.addWidget(self.chk_live)

        left.addWidget(QLabel("LOG MONITOR:"))
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        left.addWidget(self.log_widget)
        
        layout.addWidget(left_box, stretch=1)

        right_box = QWidget()
        right_box.setObjectName("panel")
        right = QVBoxLayout(right_box)
        right.setContentsMargins(14, 14, 14, 14)
        right.setSpacing(10)
        right.addWidget(QLabel("<b>SYSTEEM INFO</b>"))
        right.addWidget(QLabel("Motortype: N46B20A"))
        right.addWidget(QLabel("ECU: Bosch MEV9"))
        right.addWidget(QLabel("Hardware: Gescheiden USB-poorten"))
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

        repeats = 2 if 'RAAM' in name.upper() else 1
        success, msg = self.kbus.send(payload, live=self.live_tx, repeat=repeats)
        self.append_log(msg)

    def toggle_serial(self):
        if self.kbus.ser:
            self.kbus.close()
            self.append_log("K-Bus verbroken.")
        else:
            try:
                port = self.port_input.text()
                self.kbus.connect(port, self.baud)
                self.append_log(f"K-Bus verbonden: {port}")
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
    ap.add_argument('--port', default='/dev/ttyUSB0', help='K-Bus serial port')
    ap.add_argument('--obd-port', default='/dev/ttyUSB1', help='OBD2 MEV9 serial port')
    ap.add_argument('--baud', type=int, default=9600)
    args = ap.parse_args()
    app = QApplication(sys.argv)
    dash = E46Dashboard(args.port, args.obd_port, args.baud)
    dash.show()
    sys.exit(app.exec())
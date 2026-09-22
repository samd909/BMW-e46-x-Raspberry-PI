from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QProgressBar,
    QSizePolicy,
)

from .mev9_reader import MEV9Reader


# ============================================================
# COLORS  —  PURE BLACK & BMW M-RED ONLY
# ============================================================

BG = "#000000"
BMW_RED = "#E7222E"


# ============================================================
# SMALL VALUE CARD  (mid / low tier metrics)
# ============================================================

class MetricCard(QFrame):

    def __init__(self, title, unit="", size="md", parent=None):
        super().__init__(parent)

        self.size = size
        self.setObjectName("MetricCard")

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        # TITLE (with small red BMW marker)
        self.title = QLabel()
        self.title.setTextFormat(Qt.TextFormat.RichText)
        self.title.setText(
            f'<span style="color:{BMW_RED};">&#9632;</span>&nbsp;&nbsp;{title}'
        )
        self.title.setObjectName(
            "MetricTitleMd" if size == "md" else "MetricTitleSm"
        )

        # VALUE
        self.value = QLabel("--")
        self.value.setObjectName(
            "MetricValueMd" if size == "md" else "MetricValueSm"
        )
        self.value.setAlignment(
            Qt.AlignmentFlag.AlignLeft |
            Qt.AlignmentFlag.AlignVCenter
        )

        # UNIT
        self.unit = QLabel(unit)
        self.unit.setObjectName(
            "MetricUnitMd" if size == "md" else "MetricUnitSm"
        )

        # VALUE ROW
        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(6)

        value_row.addWidget(self.value)
        value_row.addWidget(self.unit)
        value_row.addStretch()

        # MAIN LAYOUT
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

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


# ============================================================
# BIG HERO CARD  (RPM / THROTTLE / COOLANT — top tier)
# ============================================================

class LiveSlider(QFrame):

    def __init__(self, title, maximum, unit, unit_label, parent=None):
        super().__init__(parent)

        self.maximum = maximum
        self.unit = unit

        self.setObjectName("LiveSlider")

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        # TITLE
        self.title_label = QLabel()
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        self.title_label.setText(
            f'<span style="color:{BMW_RED};">&#9632;</span>&nbsp;&nbsp;{title}'
        )
        self.title_label.setObjectName("SliderTitle")

        # BIG CENTERED VALUE
        self.value_label = QLabel("--")
        self.value_label.setObjectName("SliderValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # UNIT
        self.unit_label = QLabel(unit_label)
        self.unit_label.setObjectName("SliderUnit")
        self.unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # PROGRESS BAR
        self.bar = QProgressBar()
        self.bar.setRange(0, maximum)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setObjectName("LiveBar")

        # SCALE LABELS
        self.min_label = QLabel("0")
        self.max_label = QLabel(str(maximum))

        self.min_label.setObjectName("SliderScale")
        self.max_label.setObjectName("SliderScale")
        self.max_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        scale = QHBoxLayout()
        scale.setContentsMargins(0, 0, 0, 0)
        scale.setSpacing(0)

        scale.addWidget(self.min_label)
        scale.addStretch()
        scale.addWidget(self.max_label)

        # MAIN LAYOUT
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(2)

        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.value_label)
        layout.addWidget(self.unit_label)
        layout.addStretch(1)
        layout.addWidget(self.bar)
        layout.addLayout(scale)

    def set_value(self, value):
        if value is None:
            self.value_label.setText("--")
            self.bar.setValue(0)
            return

        value = max(0, min(self.maximum, value))

        if self.unit == "rpm":
            self.value_label.setText(f"{int(value):,}")
        elif self.unit == "%":
            self.value_label.setText(f"{value:.1f}")
        else:
            self.value_label.setText(f"{value:.1f}")

        self.bar.setValue(int(value))


# ============================================================
# SECTION TITLE
# ============================================================

class SectionTitle(QLabel):

    def __init__(self, text):
        super().__init__(text)
        self.setObjectName("SectionTitle")


# ============================================================
# ENGINE TAB
# ============================================================

class EngineTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.reader = None
        self.setObjectName("EngineTab")

        self.build_ui()
        self.apply_style()
        self.start_reader()

    def build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(14, 12, 14, 10)
        main.setSpacing(9)

        # HEADER
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel("CROWD KILLER DASHBOARD")
        title.setObjectName("EngineTitle")

        subtitle = QLabel("MEV9 LIVE DATA")
        subtitle.setObjectName("EngineSubtitle")

        header.addWidget(title)
        header.addWidget(subtitle)
        header.addStretch()

        self.status_label = QLabel("CONNECTING...")
        self.status_label.setObjectName("Status")

        header.addWidget(self.status_label)

        main.addLayout(header)

        accent_line = QFrame()
        accent_line.setObjectName("AccentLine")
        accent_line.setFixedHeight(3)
        main.addWidget(accent_line)

        # HERO ROW
        hero_row = QHBoxLayout()
        hero_row.setContentsMargins(0, 4, 0, 0)
        hero_row.setSpacing(10)

        self.rpm_slider = LiveSlider("ENGINE SPEED", 6800, "rpm", "RPM")
        self.throttle_slider = LiveSlider("THROTTLE", 100, "%", "PERCENT")
        self.coolant_slider = LiveSlider("COOLANT", 120, "c", "DEG C")

        hero_row.addWidget(self.rpm_slider, 1)
        hero_row.addWidget(self.throttle_slider, 1)
        hero_row.addWidget(self.coolant_slider, 1)

        main.addLayout(hero_row, 5)

        # MID TIER
        main.addWidget(SectionTitle("AIRFLOW / IGNITION"))

        mid_grid = QGridLayout()
        mid_grid.setContentsMargins(0, 0, 0, 0)
        mid_grid.setHorizontalSpacing(8)
        mid_grid.setVerticalSpacing(6)

        self.card_intake = MetricCard("INTAKE", "°C", size="md")
        self.card_maf = MetricCard("MAF", "g/s", size="md")
        self.card_timing = MetricCard("IGNITION", "°", size="md")
        self.card_load = MetricCard("ENGINE LOAD", "%", size="md")

        mid_grid.addWidget(self.card_intake, 0, 0)
        mid_grid.addWidget(self.card_maf, 0, 1)
        mid_grid.addWidget(self.card_timing, 0, 2)
        mid_grid.addWidget(self.card_load, 0, 3)

        for col in range(4):
            mid_grid.setColumnStretch(col, 1)

        main.addLayout(mid_grid, 2)

        # LOW TIER
        main.addWidget(SectionTitle("FUEL / VEHICLE"))

        low_grid = QGridLayout()
        low_grid.setContentsMargins(0, 0, 0, 0)
        low_grid.setHorizontalSpacing(8)
        low_grid.setVerticalSpacing(6)

        self.card_stft = MetricCard("SHORT FUEL", "%", size="sm")
        self.card_ltft = MetricCard("LONG FUEL", "%", size="sm")
        self.card_speed = MetricCard("SPEED", "km/h", size="sm")

        low_grid.addWidget(self.card_stft, 0, 0)
        low_grid.addWidget(self.card_ltft, 0, 1)
        low_grid.addWidget(self.card_speed, 0, 2)

        for col in range(3):
            low_grid.setColumnStretch(col, 1)

        main.addLayout(low_grid, 1)

        # FOOTER
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 2, 0, 0)
        footer.setSpacing(6)

        self.connection_label = QLabel("DS2 / KWP2000 • 9600 8E1")
        self.connection_label.setObjectName("Footer")

        self.port_label = QLabel("/dev/ttyUSB0")
        self.port_label.setObjectName("Footer")
        self.port_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        footer.addWidget(self.connection_label)
        footer.addStretch()
        footer.addWidget(self.port_label)

        main.addLayout(footer)

    def apply_style(self):
        self.setStyleSheet(
            f"""
            /* =============================================
               GLOBAL DEFAULTS
               ============================================= */

            QWidget#EngineTab {{
                background-color: {BG};
                color: {BMW_RED};
            }}

            QLabel {{
                background: transparent;
                background-color: transparent;
                color: {BMW_RED};
            }}

            /* =============================================
               HEADER
               ============================================= */

            QLabel#EngineTitle {{
                font-size: 22px;
                font-weight: 800;
                letter-spacing: 2px;
                color: {BMW_RED};
            }}

            QLabel#EngineSubtitle {{
                color: {BMW_RED};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding-left: 4px;
            }}

            QLabel#Status {{
                color: {BMW_RED};
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 0.5px;
                padding: 4px 10px;
                border: 1px solid {BMW_RED};
                border-radius: 6px;
                background-color: {BG};
            }}

            QFrame#AccentLine {{
                background-color: {BMW_RED};
                border: none;
                border-radius: 1px;
            }}

            /* =============================================
               SECTION TITLES
               ============================================= */

            QLabel#SectionTitle {{
                color: {BMW_RED};
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1.5px;
                padding-top: 2px;
                padding-bottom: 0px;
                border-left: 3px solid {BMW_RED};
                padding-left: 7px;
            }}

            /* =============================================
               MID TIER CARDS
               ============================================= */

            QFrame#MetricCard {{
                background-color: {BG};
                border: 1px solid {BMW_RED};
                border-radius: 10px;
            }}

            QLabel#MetricTitleMd {{
                color: {BMW_RED};
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 0.6px;
            }}

            QLabel#MetricValueMd {{
                color: {BMW_RED};
                font-size: 34px;
                font-weight: 800;
            }}

            QLabel#MetricUnitMd {{
                color: {BMW_RED};
                font-size: 12px;
                font-weight: 700;
                padding-bottom: 5px;
            }}

            /* =============================================
               LOW TIER CARDS
               ============================================= */

            QLabel#MetricTitleSm {{
                color: {BMW_RED};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}

            QLabel#MetricValueSm {{
                color: {BMW_RED};
                font-size: 24px;
                font-weight: 800;
            }}

            QLabel#MetricUnitSm {{
                color: {BMW_RED};
                font-size: 10px;
                font-weight: 600;
                padding-bottom: 3px;
            }}

            /* =============================================
               HERO CARDS
               ============================================= */

            QFrame#LiveSlider {{
                background-color: {BG};
                border: 1px solid {BMW_RED};
                border-top: 3px solid {BMW_RED};
                border-radius: 12px;
            }}

            QLabel#SliderTitle {{
                color: {BMW_RED};
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 1.2px;
            }}

            QLabel#SliderValue {{
                color: {BMW_RED};
                font-size: 64px;
                font-weight: 800;
            }}

            QLabel#SliderUnit {{
                color: {BMW_RED};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 2px;
                padding-bottom: 4px;
            }}

            QLabel#SliderScale {{
                color: {BMW_RED};
                font-size: 9px;
            }}

            /* =============================================
               LIVE BAR
               ============================================= */

            QProgressBar#LiveBar {{
                background-color: {BG};
                border: 1px solid {BMW_RED};
                border-radius: 5px;
                min-height: 12px;
                max-height: 12px;
            }}

            QProgressBar#LiveBar::chunk {{
                background-color: {BMW_RED};
                border-radius: 4px;
            }}

            /* =============================================
               FOOTER
               ============================================= */

            QLabel#Footer {{
                color: {BMW_RED};
                font-size: 8px;
            }}
            """
        )

    def start_reader(self):
        self.reader = MEV9Reader(
            port="/dev/ttyUSB0",
            parent=self,
        )

        self.reader.data_received.connect(self.update_values)
        self.reader.error_received.connect(self.reader_error)
        self.reader.start()

    def update_values(self, data):
        self.status_label.setText("LIVE")
        self.status_label.setStyleSheet(
            f"""
            color: {BMW_RED};
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 0.5px;
            padding: 4px 10px;
            border: 1px solid {BMW_RED};
            border-radius: 6px;
            background-color: {BG};
            """
        )

        self.rpm_slider.set_value(data.get("rpm"))
        self.throttle_slider.set_value(data.get("throttle"))
        self.coolant_slider.set_value(data.get("coolant"))

        self.card_intake.set_value(data.get("intake"), 1)
        self.card_maf.set_value(data.get("maf"), 1)
        self.card_timing.set_value(data.get("timing"), 1)
        self.card_load.set_value(data.get("load"), 1)

        self.card_stft.set_value(data.get("stft"), 1)
        self.card_ltft.set_value(data.get("ltft"), 1)
        self.card_speed.set_value(data.get("speed"), 0)

    def reader_error(self, message):
        self.status_label.setText("OFFLINE")
        self.status_label.setStyleSheet(
            f"""
            color: {BMW_RED};
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 0.5px;
            padding: 4px 10px;
            border: 1px solid {BMW_RED};
            border-radius: 6px;
            background-color: {BG};
            """
        )

    def closeEvent(self, event):
        if self.reader is not None:
            self.reader.stop()
            self.reader = None
        event.accept()
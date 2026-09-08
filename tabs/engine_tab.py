import sys
import time
from PyQt6.QtWidgets import QWidget, QLabel, QGridLayout, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import serial


class OBD2ReaderThread(QThread):
    """
    Aparte thread die continu via de USB D-CAN kabel communiceert 
    zodat de GUI niet vastloopt tijdens het wachten op data.
    """
    data_received = pyqtSignal(dict)

    def __init__(self, port='/dev/ttyUSB0'):  # Op Pi is dit vaak /dev/ttyUSB0, op Windows 'COM3'
        super().__init__()
        self.port = port
        self.running = True

    def calculate_checksum(self, data: bytes) -> int:
        """DS2 Checksum is een XOR van alle bytes in het bericht"""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum

    def run(self):
        try:
            # E46 DS2 protocol draait op 9600 baud, 8 databits, geen parity, 1 stopbit
            ser = serial.Serial(self.port, baudrate=9600, timeout=0.5)
        except Exception as e:
            print(f"Kon OBD2 poort {self.port} niet openen: {e}")
            return

        # DS2 Request om de status analoge waardes op te vragen bij de Bosch/Siemens DME (0x12)
        # 0x12 = DME, 0x04 = Lengte, 0x0B = Read Status, 0x1D = Checksum
        cmd_status = bytes([0x12, 0x04, 0x0B, 0x1D])

        while self.running:
            try:
                # Buffer leegmaken en commando sturen
                ser.reset_input_buffer()
                ser.write(cmd_status)
                
                # DS2 stuurt echo van het request + de response terug
                response = ser.read(64)
                
                if len(response) >= 10:
                    # In de DS2 response stream van de DME (Byte mapping verschilt per ECU versie):
                    # KVS temp zit bij de meeste DME's rond byte index 4 of 5 (min 48 graden offset)
                    coolant_raw = response[4]
                    coolant_temp = coolant_raw - 48
                    
                    # Olie temp (Offset is vaak eveneens -48°C)
                    oil_raw = response[5]
                    oil_temp = oil_raw - 48
                    
                    # Accuspanning (meestal omgedraaid naar Volt door factor 0.1)
                    voltage_raw = response[8]
                    voltage = round(voltage_raw * 0.106, 1)

                    # Stuur verwerkte data naar de GUI
                    self.data_received.emit({
                        'coolant': coolant_temp,
                        'oil': oil_temp,
                        'voltage': voltage
                    })

            except Exception as e:
                print(f"Fout bij lezen OBD2 data: {e}")

            time.sleep(0.2)  # 5x per seconde pollen

        ser.close()

    def stop(self):
        self.running = False
        self.wait()


class MetricCard(QFrame):
    def __init__(self, title, unit=""):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            MetricCard {
                background-color: #1e1e1e;
                border-radius: 10px;
                border: 1px solid #333333;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #888888; font-size: 13px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("color: #00ffcc; font-size: 26px; font-weight: bold;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.unit = unit
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value, is_warning=False):
        color = "#ff4444" if is_warning else "#00ffcc"
        if isinstance(value, float):
            self.value_label.setText(f"{value:.1f} {self.unit}")
        else:
            self.value_label.setText(f"{value} {self.unit}")
        self.value_label.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: bold;")


class EngineTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #121212;")
        
        main_layout = QVBoxLayout(self)
        
        header = QLabel("E46 N46 OBD2 Telemetrie")
        header.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold; margin-bottom: 5px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        grid_layout = QGridLayout()
        grid_layout.setSpacing(12)
        
        # Kaarten
        self.card_coolant = MetricCard("Koelvloeistof (KVS)", "°C")
        self.card_oil_temp = MetricCard("Motorolie Temp", "°C")
        self.card_voltage = MetricCard("Accuspanning", "V")
        
        grid_layout.addWidget(self.card_coolant, 0, 0)
        grid_layout.addWidget(self.card_oil_temp, 0, 1)
        grid_layout.addWidget(self.card_voltage, 0, 2)
        
        main_layout.addLayout(grid_layout)

        # Start OBD2 Thread (/dev/ttyUSB0 voor Raspberry Pi, op Windows bijv. 'COM3')
        self.obd_thread = OBD2ReaderThread(port='/dev/ttyUSB0')
        self.obd_thread.data_received.connect(self.update_gui)
        self.obd_thread.start()

    def update_gui(self, data: dict):
        if 'coolant' in data:
            self.card_coolant.set_value(data['coolant'], is_warning=(data['coolant'] > 112))
        if 'oil' in data:
            self.card_oil_temp.set_value(data['oil'])
        if 'voltage' in data:
            self.card_voltage.set_value(data['voltage'], is_warning=(data['voltage'] < 11.8))

    def closeEvent(self, event):
        """Zorg ervoor dat de thread netjes stopt bij het afsluiten van de app"""
        self.obd_thread.stop()
        event.accept()
import time
import serial

from PyQt6.QtCore import QThread, pyqtSignal


class MEV9Reader(QThread):
    """
    BMW E46 N46B20A / MEV9 live-data reader.

    Communicatie:
        BMW KWP2000 / K-line
        9600 baud
        8E1

    Geeft live data terug via:
        data_received(dict)
    """

    data_received = pyqtSignal(dict)
    error_received = pyqtSignal(str)

    DME = 0x12
    TESTER = 0xF1

    UPDATE_INTERVAL = 0.20

    def __init__(
        self,
        port="/dev/ttyUSB0",
        parent=None
    ):
        super().__init__(parent)

        self.port = port
        self.running = True
        self.ser = None

    # ========================================================
    # CHECKSUM
    # ========================================================

    @staticmethod
    def xor_checksum(data):
        checksum = 0

        for byte in data:
            checksum ^= byte

        return checksum

    # ========================================================
    # KWP REQUEST
    # ========================================================

    def kwp_request(
        self,
        payload,
        timeout=0.35
    ):
        """
        Stuurt een BMW KWP2000 frame:

            B8 DEST SOURCE LENGTH PAYLOAD CHECKSUM
        """

        frame = bytearray([
            0xB8,
            self.DME,
            self.TESTER,
            len(payload),
        ])

        frame.extend(payload)

        frame.append(
            self.xor_checksum(frame)
        )

        self.ser.reset_input_buffer()

        # BMW K-line byte timing
        for byte in frame:

            self.ser.write(
                bytes([byte])
            )

            time.sleep(0.005)

        self.ser.flush()

        # USB/K-line adapter echo
        self.ser.read(
            len(frame)
        )

        old_timeout = self.ser.timeout

        self.ser.timeout = timeout

        # Response header
        header = self.ser.read(4)

        if len(header) != 4:

            self.ser.timeout = old_timeout

            return None

        if header[0] != 0xB8:

            self.ser.timeout = old_timeout

            return None

        length = header[3]

        # Payload + checksum
        rest = self.ser.read(
            length + 1
        )

        self.ser.timeout = old_timeout

        if len(rest) != length + 1:

            return None

        response = header + rest

        # Checksum controleren
        if self.xor_checksum(
            response[:-1]
        ) != response[-1]:

            return None

        return response

    # ========================================================
    # GENERIC OBD PID
    # ========================================================

    def read_pid(self, pid):

        response = self.kwp_request(
            bytes([
                0x01,
                pid
            ])
        )

        if not response:
            return None

        payload = response[4:-1]

        if len(payload) < 3:
            return None

        # Positive Mode 01 response
        if payload[0] != 0x41:
            return None

        if payload[1] != pid:
            return None

        return payload[2:]

    # ========================================================
    # RPM
    # ========================================================

    def read_rpm(self):

        data = self.read_pid(0x0C)

        if not data or len(data) < 2:
            return None

        raw = (
            (data[0] << 8)
            | data[1]
        )

        return raw / 4.0

    # ========================================================
    # COOLANT
    # ========================================================

    def read_coolant(self):

        data = self.read_pid(0x05)

        if not data:
            return None

        return data[0] - 40

    # ========================================================
    # INTAKE AIR
    # ========================================================

    def read_intake(self):

        data = self.read_pid(0x0F)

        if not data:
            return None

        return data[0] - 40

    # ========================================================
    # MAF
    # ========================================================

    def read_maf(self):

        data = self.read_pid(0x10)

        if not data or len(data) < 2:
            return None

        raw = (
            (data[0] << 8)
            | data[1]
        )

        return raw / 100.0

    # ========================================================
    # THROTTLE
    # ========================================================

    def read_throttle(self):

        data = self.read_pid(0x11)

        if not data:
            return None

        return (
            data[0]
            * 100.0
            / 255.0
        )

    # ========================================================
    # ENGINE LOAD
    # ========================================================

    def read_load(self):

        data = self.read_pid(0x04)

        if not data:
            return None

        return (
            data[0]
            * 100.0
            / 255.0
        )

    # ========================================================
    # IGNITION TIMING
    # ========================================================

    def read_timing(self):

        data = self.read_pid(0x0E)

        if not data:
            return None

        return (
            data[0] / 2.0
        ) - 64.0

    # ========================================================
    # SHORT TERM FUEL TRIM
    # ========================================================

    def read_stft(self):

        data = self.read_pid(0x06)

        if not data:
            return None

        return (
            (data[0] - 128)
            * 100.0
            / 128.0
        )

    # ========================================================
    # LONG TERM FUEL TRIM
    # ========================================================

    def read_ltft(self):

        data = self.read_pid(0x07)

        if not data:
            return None

        return (
            (data[0] - 128)
            * 100.0
            / 128.0
        )

    # ========================================================
    # SPEED
    # ========================================================

    def read_speed(self):

        data = self.read_pid(0x0D)

        if not data:
            return None

        return data[0]

    # ========================================================
    # VOLTAGE
    # ========================================================

    def read_voltage(self):

        data = self.read_pid(0x42)

        if not data or len(data) < 2:
            return None

        raw = (
            (data[0] << 8)
            | data[1]
        )

        return raw / 1000.0

    # ========================================================
    # READ ALL
    # ========================================================

    def read_all(self):

        return {
            "rpm": self.read_rpm(),
            "coolant": self.read_coolant(),

            "intake": self.read_intake(),
            "maf": self.read_maf(),

            "throttle": self.read_throttle(),
            "load": self.read_load(),

            "timing": self.read_timing(),

            "stft": self.read_stft(),
            "ltft": self.read_ltft(),

            "speed": self.read_speed(),

            "voltage": self.read_voltage(),
        }

    # ========================================================
    # THREAD
    # ========================================================

    def run(self):

        try:

            self.ser = serial.Serial(
                port=self.port,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.35,
                write_timeout=1.0,
            )

        except Exception as error:

            self.error_received.emit(
                f"Kan {self.port} niet openen: {error}"
            )

            return

        # K-line mode
        self.ser.dtr = False
        self.ser.rts = False

        time.sleep(0.5)

        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        while self.running:

            try:

                values = self.read_all()

                self.data_received.emit(
                    values
                )

            except Exception as error:

                self.error_received.emit(
                    str(error)
                )

            time.sleep(
                self.UPDATE_INTERVAL
            )

        if self.ser:

            self.ser.close()

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self.running = False

        self.wait()


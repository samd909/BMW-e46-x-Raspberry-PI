#!/usr/bin/env python3
import threading
import queue
import time
try:
    import serial
except ImportError:
    serial = None

GROUPS = {
    'Ramen': [
        ('Linksvoor OPEN', '3F 05 00 0C 52 01', 'normal'),
        ('Linksvoor DICHT', '3F 05 00 0C 53 01', 'pinch'),
        ('Rechtsvoor OPEN', '3F 05 00 0C 54 01', 'normal'),
        ('Rechtsvoor DICHT', '3F 05 00 0C 55 01', 'pinch'),
    ],
    'Portieren': [
        ('VERGRENDEL', '3F 05 00 0C 34 01', 'lock'),
        ('CV OMSCHAKELEN*', '3F 05 00 0C 03 01', 'lock'),
        ('KOFFERBAK', '3F 05 00 0C 02 01', 'lock'),
    ],
    'Verlichting': [
        ('INTERIEURLICHT*', '3F 05 00 0C 01 01', 'normal'),
        ('ALARMVERLICHTING*', '3F 05 00 0C 75 01', 'normal'),
        ('STADSLICHT*', '3F 0B BF 0C 00 00 00 00 7A 48 0A 06', 'normal'),
        ('MISTLAMPEN*', '3F 0B BF 0C 00 00 00 00 00 00 01 06', 'normal'),
        ('FOLLOW-ME-HOME*', '3F 0B BF 0C 00 00 80 00 00 00 00 06', 'normal'),
    ],
    'Overig': [
        ('WISSER*', '3F 05 00 0C 49 01', 'motion'),
        ('SPROEIER*', '3F 05 00 0C 62 01', 'motion'),
        ('VOL + (MFL)*', '50 04 68 32 11', 'normal'),
        ('VOL - (MFL)*', '50 04 68 32 10', 'normal'),
        ('R/T (MFL)*', '50 04 68 3B 02', 'normal'),
    ],
}

def frame_bytes(data):
    b = bytes.fromhex(data)
    if len(b) < 4 or b[1] != len(b)-1:
        raise ValueError('K-Bus lengte incorrect')
    x = 0
    for v in b: 
        x ^= v
    return b + bytes([x])

class KBusManager:
    def __init__(self):
        self.ser = None
        self.lock = threading.Lock()
        self.rx_queue = queue.Queue()
        self.running = True
        self.last_rx = 0.0

    def connect(self, port, baud=9600):
        if serial is None:
            raise RuntimeError("pyserial is niet geïnstalleerd.")
        with self.lock:
            if self.ser:
                self.close()
            self.ser = serial.Serial(port, baud, bytesize=8, parity='E', stopbits=1, timeout=0.1, write_timeout=0.4)
            threading.Thread(target=self._reader_loop, daemon=True).start()

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def _reader_loop(self):
        s = self.ser
        while self.running and s and s.is_open:
            try:
                b = s.read(1)
                if b:
                    if s.in_waiting:
                        b += s.read(s.in_waiting)
                    self.last_rx = time.monotonic()
                    self.rx_queue.put(f"RX {b.hex(' ').upper()}")
            except Exception as e:
                self.rx_queue.put(f"RX fout: {e}")
                break

    def send(self, payload, live=False, repeat=1, interval=0.05):
        """
        Verstuur een K-Bus commando. 
        repeat: aantal keer dat het commando achter elkaar wordt gestuurd (handig voor stroeve ramen).
        interval: pauze in seconden tussen de herhalingen.
        """
        try:
            data = frame_bytes(payload)
        except ValueError as e:
            return False, f"ONGELDIG frame: {e}"
        
        if not self.ser or not live:
            return True, f"DEMO {data.hex(' ').upper()}"
        
        results = []
        for i in range(repeat):
            if time.monotonic() - self.last_rx < 0.025:
                # Korte pauze voordat we de bus proberen te claimen
                time.sleep(0.025)
            
            try:
                with self.lock:
                    self.ser.write(data)
                    self.ser.flush()
                results.append(f"TX ({i+1}/{repeat}) {data.hex(' ').upper()}")
            except Exception as e:
                return False, f"TX fout: {e}"
            
            if i < repeat - 1:
                time.sleep(interval)
                
        return True, " | ".join(results)
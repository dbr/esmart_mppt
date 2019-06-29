# Library for communicating with eSmart 3 MPPT charger
# skagmo.com, 2018

from typing import List, Optional, Callable

import struct, time, serial, socket, requests
#from collections import namedtuple

# States
STATE_START = 0
STATE_DATA = 1

REQUEST_MSG0 = b"\xaa\x01\x01\x01\x00\x03\x00\x00\x1e\x32"
LOAD_OFF = b"\xaa\x01\x01\x02\x04\x04\x01\x00\xfe\x13\x38"
LOAD_ON = b"\xaa\x01\x01\x02\x04\x04\x01\x00\xfd\x13\x39"

DEVICE_MODE = ["IDLE", "CC", "", "FLOAT", "STARTING"]


class SolarData(object):
    def __init__(self, chg_mode: int, pv_volt: float, bat_volt: float,
                 chg_cur: float, load_volt: float, load_cur: float, chg_power: int,
                 load_power: int, bat_temp: int, int_temp: int, soc: int,
                 co2_gram: int):
        self.chg_mode = chg_mode
        self.pv_volt = pv_volt
        self.bat_volt = bat_volt
        self.chg_cur = chg_cur
        self.load_volt = load_volt
        self.load_cur = load_cur
        self.chg_power = chg_power
        self.load_power = load_power
        self.bat_temp = bat_temp
        self.int_temp = int_temp
        self.soc = soc
        self.co2_gram = co2_gram


class Esmart:
    def __init__(self) -> None:
        self.state = STATE_START
        self.data = [] # type: List[int]
        self.callback = None # type: Optional[Callable]
        self.port = ""
        self.timeout = 0
        self.ser = None # type: Optional[serial.Serial]

    def __del__(self) -> None:
        self.close()

    def set_callback(self, function: Callable) -> None:
        self.callback = function

    def open(self, port):
        self.ser = serial.Serial(port, 9600, timeout=0.1)
        self.port = port

    def close(self):
        if self.ser is not None:
            self.ser.close()
            self.ser = None

    def send(self, pl):
        self.ser.write(self.pack(pl))

    def parse(self, data) -> None:
        for c in data:
            if self.state == STATE_START:
                if c == 0xaa:
                    # Start character detected
                    self.state = STATE_DATA
                    self.data = []
                    self.target_len = 255

            elif self.state == STATE_DATA:
                self.data.append(c)
                # Received enough of the packet to determine length
                if len(self.data) == 5:
                    self.target_len = 6 + self.data[4]

                # Received whole packet
                if len(self.data) == self.target_len:
                    self.state = STATE_START

                    #print " ".join("{:02x}".format(ord(c)) for c in self.data)

                    # Source 3 is MPPT device
                    if self.data[2] == 3:
                        msg_type = self.data[3]

                        # Type 0 packet contains most data
                        if self.data[3] == 0:
                            data = SolarData(
                                chg_mode=int.from_bytes(self.data[7:9], byteorder='little'),
                                pv_volt=int.from_bytes(self.data[9:11], byteorder='little') / 10.0,
                                bat_volt=int.from_bytes(self.data[11:13], byteorder='little') / 10.0,
                                chg_cur=int.from_bytes(self.data[13:15], byteorder='little') / 10.0,
                                load_volt=int.from_bytes(self.data[17:19], byteorder='little') / 10.0,
                                load_cur=int.from_bytes(self.data[19:21], byteorder='little') / 10.0,
                                chg_power=int.from_bytes(self.data[21:23], byteorder='little'),
                                load_power=int.from_bytes(self.data[23:25], byteorder='little'),
                                bat_temp=self.data[25],
                                int_temp=self.data[27],
                                soc=self.data[29],
                                co2_gram=int.from_bytes(self.data[33:35], byteorder='little'),
                            )

                            if self.callback is not None:
                                self.callback(data)

    def tick(self):
        try:
            while self.ser.inWaiting():
                self.parse(self.ser.read(100))

            # Send poll packet to request data every 5 seconds
            if (time.time() - self.timeout) > 5:
                self.ser.write(REQUEST_MSG0)
                self.timeout = time.time()
                #time.sleep(0.5)
                #self.ser.write(LOAD_OFF)

        except IOError:
            print("Serial port error, fixing")
            self.ser.close()
            opened = 0
            while not opened:
                try:
                    self.ser = serial.Serial(self.port, 38400, timeout=0)
                    time.sleep(0.5)
                    if self.ser.read(100):
                        opened = 1
                    else:
                        self.ser.close()
                except serial.serialutil.SerialException:
                    time.sleep(0.5)
                    self.ser.close()
            print("Error fixed")

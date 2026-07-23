# test_serial.py
import serial
import time

# CHANGE THIS to your actual port:
# Windows: e.g. "COM3"
# Linux:   e.g. "/dev/ttyUSB0" or "/dev/ttyACM0"
# macOS:   e.g. "/dev/cu.usbmodem123451"
PORT = "/dev/cu.usbmodem101"
BAUD = 9600

ser = serial.Serial(PORT, BAUD, timeout=2)
time.sleep(2)  # give Arduino time to settle

for i in range(10):
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    print(i, repr(line))

ser.close()
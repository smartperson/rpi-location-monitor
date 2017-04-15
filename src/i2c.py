import Adafruit_GPIO.I2C as I2C
import RPi.GPIO as GPIO
import time

I2C.require_repeated_start()
GPIO.setmode(GPIO.BOARD)
GPIO.setup(7, GPIO.OUT)
GPIO.output(7, True)
time.sleep(2)
tempDevice = I2C.get_i2c_device(0x5C, 0)
try:
    tempDevice.write8(0x03, 0x00)
except:
    print 'sent wakeup command'
time.sleep(0.01)
tempDevice.writeList(0x03, [0x00, 0x04])
time.sleep(0.01)
dataList = tempDevice.readList(0x03, 8)
# Rpi might pick up an extra 0x80 because of previous ACK timing. Kludge to fix.
dataList[0] = dataList[0] & 0x7F 
print '[{}]'.format(', '.join(hex(x) for x in dataList))
GPIO.cleanup()
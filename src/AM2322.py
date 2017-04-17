#!/usr/bin/python
# origininal source: https://github.com/8devices/IoTPy/
from time import sleep
from struct import unpack
import pigpio
import RPi.GPIO as GPIO
import datetime as DateTime

I2C_ADDR_AM2322 = 0x5c # 0xB8 >> 1, for 7-bit address

PARAM_AM2322_READ = 0x03
REG_AM2322_HUMIDITY_MSB = 0x00
REG_AM2322_HUMIDITY_LSB = 0x01
REG_AM2322_TEMPERATURE_MSB = 0x02
REG_AM2322_TEMPERATURE_LSB = 0x03
REG_AM2322_DEVICE_ID_BIT_24_31 = 0x0B
class  CommunicationError(Exception):
    pass

class AM2322(object):
    """AM2322 temperature and humidity sensor class.
    """
    def __init__(self, interface=0, sensor_power=4, synchronous=True, sensor_address=I2C_ADDR_AM2322):
        self.interface = interface
        self.address = sensor_address
        self.temperature = -1000.0
        self.humidity = -1
        self._synchronous = synchronous
        self.thisPi = pigpio.pi()
        if sensor_power: #if you set the power pin to Nil or 0, we assume you're taking care of it
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(sensor_power, GPIO.OUT)
            GPIO.output(sensor_power, True)
            self._set_ready_at(seconds=2)
        else:
            self._set_ready_at(seconds=0)
        self.device = self.thisPi.i2c_open(interface, sensor_address)
    def _set_ready_at(self, seconds=3):
        self._ready_at = DateTime.datetime.now()+DateTime.timedelta(seconds=seconds)
        if self._synchronous:
            sleep(seconds)
    def _read_raw(self, command, regaddr, regcount):
        try:
            self.thisPi.i2c_write_quick(self.device, 0)
        except:
            pass # print 'sent wakeup command'
        self.thisPi.i2c_write_i2c_block_data(self.device, command, [regaddr, regcount])
        sleep(0.0015)
        (bufcount, buf) = self.thisPi.i2c_read_device(self.device, regcount+4)
        self._set_ready_at() # we need to wait 3 seconds before we can read again
        # RPi might pick up an extra 0x80 because of previous packet's ACK timing. Kludge to fix.
        buf[0] = buf[0] & 0x7F
        buf_str = "".join(chr(x) for x in buf)
        crc = unpack('<H', buf_str[-2:])[0]
        if crc != self._am_crc16(buf[:-2]):
            raise CommunicationError("AM2322 CRC error.")
        return buf_str[2:-2]
    def _am_crc16(self, buf):
        crc = 0xFFFF
        for c in buf:
            crc ^= c
            for i in range(8):
                if crc & 0x01:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc
    def read_uid(self):
        """Read and return unique 32bit sensor ID.
        :return: A unique 32bit sensor ID. rtype: int
        """
        resp = self._read_raw(PARAM_AM2322_READ, REG_AM2322_DEVICE_ID_BIT_24_31, 4)
        uid = unpack('>I', resp)[0]
        return uid
    def read(self):
        """Read and store temperature and humidity value.
        Read temperature and humidity registers from the sensor, then convert and store them.
        Use :func:`temperature` and :func:`humidity` to retrieve these values.
        """
        raw_data = self._read_raw(PARAM_AM2322_READ, REG_AM2322_HUMIDITY_MSB, 4)
        self.temperature = unpack('>H', raw_data[-2:])[0] / 10.0
        self.humidity = unpack('>H', raw_data[-4:2])[0] / 10.0
    def ready(self):
        if self._ready_at <= DateTime.datetime.now():
            return True
        else:
            return False
    def time_to_ready(self):
        delayRequired = (self._ready_at - DateTime.datetime.now()).total_seconds()
        if delayRequired < 0:
            delayRequired = 0
        return delayRequired

if __name__ == '__main__':
    am2322 = AM2322(0, synchronous=True)
    while True:
        am2322.read()
        print am2322.temperature, am2322.humidity
    GPIO.cleanup()

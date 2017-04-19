#!/usr/bin/python
# coding: utf-8
from flask import Flask
import threading
import time
import os
import sys

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
from Adafruit_IO import Client

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from AM2322 import AM2322

# temperatureReading = 0
# humidityReading = 0
ADAFRUIT_IO_KEY = os.environ.get('AIO_KEY')
DISP_RST = 24

app = Flask(__name__)

@app.route('/')
def hello_world():
    global temperatureReading
    global humidityReading
    return '{} currently: {}°F, {}% Humidity'.format(os.environ.get('ROOM_NAME','room'), temperatureReading, humidityReading)

def server():
    app.run(host='0.0.0.0', port=80)
        
def call_at_interval(period, callback, args):
    while True:
        time.sleep(period)
        callback(*args)

def setInterval(period, callback, *args):
    threading.Thread(target=call_at_interval, args=(period, callback, args)).start()

def broadcast_to_network():
    global temperatureReading
    global humidityReading
    global aio
    try:
        # sent_data = {'temperature': temperatureReading, 'humidity': humidityReading}
        # print("Sending {}, data {}".format(os.environ.get('AIO_BASENAME'), sent_data))
        # returned_data = aio.send_group(os.environ.get('AIO_BASENAME'), sent_data)
        returned_data = aio.send("{}-{}".format(os.environ.get('AIO_BASENAME'), "temperature"), temperatureReading)
        returned_data = aio.send("{}-{}".format(os.environ.get('AIO_BASENAME'), "humidity"), humidityReading)
        # print("Update returned {}".format(returned_data))
    except:
        print("Unexpected error:", sys.exc_info()[0])
        # print "Name error: {}".format(e.message)
        pass

def i2c_read_temperature():
    am2322.read()
    print am2322.temperature, am2322.humidity
    temperatureReading = (am2322.temperature*9/5)+32
    humidityReading = am2322.humidity

def i2c_display_setup(rst=DISP_RST):
    disp = Adafruit_SSD1306.SSD1306_128_64(rst)
    disp.begin()
    disp.clear()
    disp.display()
    width = disp.width
    height = disp.height
    image = Image.new('1', (width, height))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    padding = 2
    shape_width = 20
    top = padding
    bottom = height-padding
    x = 2
    x += 22
    x += 22
    x += 22
    x += 22
    font = ImageFont.load_default()
    # Some other nice fonts to try: http://www.dafont.com/bitmap.php
    #font = ImageFont.truetype('Minecraftia.ttf', 8)
    draw.text((x, top),    'Hello',  font=font, fill=255)
    draw.text((x, top+20), 'World!', font=font, fill=255)
    disp.image(image)
    disp.display()
    return disp

if __name__ == '__main__':
    global temperatureReading
    global humidityReading
    global aio
    temperatureReading = 0
    humidityReading = 0
    aio = Client(ADAFRUIT_IO_KEY)
    
    serverThread = threading.Thread(target=server)
    serverThread.start()
    
    am2322 = AM2322(0, synchronous=True)
    
    # display init
    disp = i2c_display_setup()
    setInterval(60, broadcast_to_network)
    
    while True:
        (temperatureReading, humidityReading) = i2c_read_temperature()
        draw.rectangle((0,0,disp.width,disp.height), outline=0, fill=0)
        draw.text((4, top),    u'Temp: {}°F'.format(temperatureReading), font=font, fill=255)
        draw.text((4, top+16), u'Humi: {}%'.format(humidityReading)    , font=font, fill=255)
        disp.image(image)
        disp.display()
        time.sleep(5)

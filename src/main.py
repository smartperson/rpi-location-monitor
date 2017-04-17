#!/usr/bin/python
# coding: utf-8
from flask import Flask
import threading
import time
import os

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from AM2322 import AM2322

# temperatureReading = 0
# humidityReading = 0

app = Flask(__name__)

@app.route('/')
def hello_world():
    global temperatureReading
    global humidityReading
    return '{} currently: {}°F, {}% Humidity'.format(os.environ.get('ROOM_NAME','room'), temperatureReading, humidityReading)

def server():
    app.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    global temperatureReading
    global humidityReading
    serverThread = threading.Thread(target=server)
    serverThread.start()
    
    am2322 = AM2322(0, synchronous=True)
    
    # display init
    RST = 24
    disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)
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
    while True:
        # time.sleep(am2322.time_to_ready())
        am2322.read()
        print am2322.temperature, am2322.humidity
        temperatureReading = (am2322.temperature*9/5)+32
        humidityReading = am2322.humidity
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        draw.text((4, top),    'Temp: {}°F'.format(temperatureReading), font=font, fill=255)
        draw.text((4, top+16), 'Humi: {}%'.format(humidityReading)    , font=font, fill=255)
        disp.image(image)
        disp.display()
        time.sleep(5)
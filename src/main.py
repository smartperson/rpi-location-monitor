#!/usr/bin/python
# coding: utf-8
from flask import Flask
import threading
import time
from datetime import datetime
import os
import sys
from socket import *
import json

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
from Adafruit_IO import Client
import RPi.GPIO as GPIO

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from cStringIO import StringIO

from AM2322 import AM2322

# temperatureReading = 0
# humidityReading = 0
ADAFRUIT_IO_KEY = os.environ.get('AIO_KEY')
ADAFRUIT_IO_BASENAME = os.environ.get('AIO_BASENAME')
ROOM_NAME = os.environ.get('ROOM_NAME', 'Room')
ROOM_PBM_64 = os.environ.get('ROOM_PBM_64')
UDP_PORT = 51231
DISP_RST = 24

app = Flask(__name__)

@app.route('/')
def web_index():
    global temperatureReading
    global humidityReading
    return '{} currently: {}°F, {}% Humidity'.format(ROOM_NAME, temperatureReading, humidityReading)

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
    global udpSocket
    try:
        # sent_data = {'temperature': temperatureReading, 'humidity': humidityReading}
        # print("Sending {}, data {}".format(os.environ.get('AIO_BASENAME'), sent_data))
        # returned_data = aio.send_group(os.environ.get('AIO_BASENAME'), sent_data)
        returned_data = aio.send("{}-{}".format(ADAFRUIT_IO_BASENAME, "temperature"), temperatureReading)
        returned_data = aio.send("{}-{}".format(ADAFRUIT_IO_BASENAME, "humidity"), humidityReading)
        # print("Update returned {}".format(returned_data))
    except:
        print("Unexpected error:", sys.exc_info()[0])
        # print "Name error: {}".format(e.message)
        pass
    data = {
        "time": datetime.utcnow().isoformat(),
        "name": ROOM_NAME,
        "identifier": ADAFRUIT_IO_BASENAME,
        "room_pbm64": ROOM_PBM_64,
        "temperature": temperatureReading,
        "humidity": humidityReading
    }#repr(time.time()) + '\n'
    dataJSON = json.dumps(data, separators=(',',':'))
    udpSocket.sendto(dataJSON, ('<broadcast>', UDP_PORT))

def i2c_read_temperature():
    am2322.read()
    print am2322.temperature, am2322.humidity
    temperatureReading = (am2322.temperature*9/5)+32
    humidityReading = am2322.humidity
    return (temperatureReading, humidityReading)

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
    return (disp, draw, image)

def network_listen():
    listenSocket = socket(socket.AF_INET,socket.SOCK_DGRAM)
    listenSocket.bind(("", UDP_PORT))
    while True:
        #1024 is sufficient buffer for our status packets, which are around 350B
        data,addr = UDPSock.recvfrom(1024) 
        print data.strip(),addr

if __name__ == '__main__':
    global temperatureReading
    global humidityReading
    global aio
    global udpSocket
    udpSocket = socket(AF_INET, SOCK_DGRAM)
    udpSocket.bind(('', 0))
    udpSocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    
    temperatureReading = 0
    humidityReading = 0
    aio = Client(ADAFRUIT_IO_KEY)
    
    serverThread = threading.Thread(target=server)
    serverThread.start()
    i2c_interface = 1
    if GPIO.RPI_INFO['P1_REVISION'] == 1: #old RPi have user i2c on bus 0
        i2c_interface = 0
    
    am2322 = AM2322(i2c_interface, synchronous=True)
    
    # display init
    (disp, draw, image) = i2c_display_setup()
    padding = 2
    top = padding
    font = ImageFont.load_default()
    localIcon = Image.open(StringIO(ROOM_PBM_64.decode("base64")))
    setInterval(60, broadcast_to_network)
        
    while True:
        (temperatureReading, humidityReading) = i2c_read_temperature()
        draw.rectangle((0,0,disp.width,disp.height), outline=0, fill=0)
        draw.text((32+padding, top),    u'{:.0f}°'.format(temperatureReading), font=font, fill=255)
        draw.text((32+padding, top+16), u'{:.0f}%'.format(humidityReading)    , font=font, fill=255)
        draw.rectangle((64,0,64+32,0+32), outline=255, fill=255) # test rectangle for spacing
        draw.text((96+padding, top),    u'{:.0f}°'.format(temperatureReading), font=font, fill=255)
        draw.text((96+padding, top+16), u'{:.0f}%'.format(humidityReading)    , font=font, fill=255)
        draw.rectangle((0,32,0+32,32+32), outline=255, fill=255) # test rectangle for spacing
        image.paste(localIcon, (0,0))
        disp.image(image)
        disp.display()
        time.sleep(5)

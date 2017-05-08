#!/usr/bin/python
# coding: utf-8
from flask import Flask
import threading
import time
from datetime import datetime, timedelta
import dateutil.parser
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
UDP_MULTICAST_GROUP = "224.0.0.111"
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
    }
    dataJSON = json.dumps(data, separators=(',',':'))
    udpSocket.sendto(dataJSON, (UDP_MULTICAST_GROUP, UDP_PORT))

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
    top = padding
    bottom = height-padding
    x = 2
    font = ImageFont.load_default()
    # Some other nice fonts to try: http://www.dafont.com/bitmap.php
    #font = ImageFont.truetype('Minecraftia.ttf', 8)
    disp.image(image)
    disp.display()
    return (disp, draw, image)

def i2c_display_update(display, draw, image, font):
    global monitorsTracked
    global temperatureReading
    global humidityReading
    # Clear and prepare
    index = 0
    draw.rectangle((0,0,disp.width,disp.height), outline=0, fill=0)
    padding = 2
    top = 1
    # Draw information for this device
    localIcon = Image.open(StringIO(ROOM_PBM_64.decode('base64')))
    baseX = (index % 1) * 64
    baseY = (index / 2) * 32
    image.paste(localIcon, (baseX,baseY))
    draw.text((baseX+32+padding, baseY+top),    u'{:.0f}°'.format(temperatureReading), font=font, fill=255)
    draw.text((baseX+32+padding, baseY+top+16), u'{:.0f}%'.format(humidityReading)    , font=font, fill=255)
    
    # Draw information for each known network device
    identifierToRemove = None
    for identifier, monitorData in monitorsTracked.iteritems():
        modifiedUTC = dateutil.parser.parse(monitorData["time"])
        if (modifiedUTC < (datetime.utcnow() - timedelta(hours=1))):
            identifierToRemove = identifier
            continue
        icon = Image.open(StringIO(monitorData["room_pbm64"].decode('base64')))
        index = index+1
        baseX = (index % 2) * 64
        baseY = (index / 2) * 32
        image.paste(icon, (baseX,baseY))
        draw.text((baseX+32+padding, baseY+top),    u'{:.0f}°'.format(monitorData["temperature"]), font=font, fill=255)
        draw.text((baseX+32+padding, baseY+16), u'{:.0f}%'.format(monitorData["humidity"])    , font=font, fill=255)
    if identifierToRemove:
        monitorsTracked.pop(identifierToRemove, None)
    disp.image(image)
    disp.display()
    

def network_listen():
    global monitorsTracked
    import fcntl
    import struct
    listenSocket = socket(AF_INET, SOCK_DGRAM)
    # listenSocket.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
    listenSocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    listenSocket.bind(("", UDP_PORT))
    multicast_group = UDP_MULTICAST_GROUP
    listenSocket.setsockopt(SOL_IP, IP_MULTICAST_LOOP, 0)
    interface_ip = inet_ntoa(fcntl.ioctl(listenSocket.fileno(), 0x8915, struct.pack('256s',"wlan0"[:15]))[20:24])
    listenSocket.setsockopt(SOL_IP, IP_MULTICAST_IF, inet_aton(interface_ip))
    mreq = inet_aton(multicast_group) + inet_aton(interface_ip)
    listenSocket.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, str(mreq)) # this might give us all multicasts…?
    
    while True:
        #1024 is sufficient buffer for our status packets, which are around 350B
        dataJSON,addr = listenSocket.recvfrom(1024)
        data = json.loads(dataJSON)
        monitorsTracked[data["identifier"]] = data

if __name__ == '__main__':
    global temperatureReading
    global humidityReading
    global aio
    global udpSocket
    global monitorsTracked
    udpSocket = socket(AF_INET, SOCK_DGRAM)
    udpSocket.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, 20)
    udpSocket.setsockopt(SOL_IP, IP_MULTICAST_LOOP, 0)
    
    monitorsTracked = {}
    listenThread = threading.Thread(target=network_listen)
    listenThread.start()

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
    # font = ImageFont.load_default()
    font = ImageFont.truetype("src/arial-bold.ttf", size=14)
    
    setInterval(60, broadcast_to_network)
    setInterval(42, i2c_display_update, disp, draw, image, font)
        
    while True:
        (temperatureReading, humidityReading) = i2c_read_temperature()
        time.sleep(5)

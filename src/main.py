from flask import Flask
import threading
import time

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import AM2320.py

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'

def server():
    app.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    serverThread = threading.Thread(target=server)
    serverThread.start()
    # display init
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
    x = padding
    draw.ellipse((x, top , x+shape_width, bottom), outline=255, fill=0)
    x += shape_width+padding
    draw.rectangle((x, top, x+shape_width, bottom), outline=255, fill=0)
    x += shape_width+padding
    # Draw a triangle.
    draw.polygon([(x, bottom), (x+shape_width/2, top), (x+shape_width, bottom)], outline=255, fill=0)
    x += shape_width+padding
    # Draw an X.
    draw.line((x, bottom, x+shape_width, top), fill=255)
    draw.line((x, top, x+shape_width, bottom), fill=255)
    x += shape_width+padding
    font = ImageFont.load_default()
    # Some other nice fonts to try: http://www.dafont.com/bitmap.php
    #font = ImageFont.truetype('Minecraftia.ttf', 8)
    draw.text((x, top),    'Hello',  font=font, fill=255)
    draw.text((x, top+20), 'World!', font=font, fill=255)
    disp.image(image)
    disp.display()
    
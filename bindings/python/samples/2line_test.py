#!/usr/bin/env python
# Display a runtext and a static text with double-buffering.

# sys.pathにsitepackagesがあるのにbs4を読み込んでくれない…強制的に読み込ませる
import sys
sys.path.append("/home/pi/.local/lib/python3.7/site-packages")

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from graphics import graphics
import time
import requests
from bs4 import BeautifulSoup
import re
import threading
import datetime
from PIL import Image

atcl_arr = []
temp = ""

def getNews():
    global atcl_arr
    atcl_arr_new = []
    
    # 接続
    print(str(datetime.datetime.now())+": getting NEWS...")
    #URL = "https://www.japantimes.co.jp/" # JT
    URL = "https://www.nikkei.com/news/category/" # 日経
    rest = requests.get(URL)
    soup = BeautifulSoup(rest.text, "html.parser")
    
    # HTMLパース
    #atcl_list = soup.find_all(attrs={"class" : "article-title"}) #JT
    atcl_list = soup.select('#CONTENTS_MAIN')[0].find_all(class_=re.compile("_titleL")) # 日経
    
    # 格納
    for atcl in atcl_list:
        print(atcl.string)
        atcl_arr_new.append(atcl.string)
    atcl_arr = atcl_arr_new
    
    return atcl_arr
        
def getTemperature():
    global temp
    
    print(str(datetime.datetime.now())+": getting current temperature...")
    URL = "https://tenki.jp/amedas/3/17/46091.html" # 海老名のアメダス
    rest = requests.get(URL)
    soup = BeautifulSoup(rest.text, "html.parser")
    temp_tag = soup.select('.amedas-current-list')[0].select('li')[0]
    temp_tag.select('span')[0].decompose()
    temp = temp_tag.text
    #print(temp.text)
    
    return temp

def displayLED():
    global atcl_arr
    global temp
    
    # LEDマトリクス設定
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.gpio_slowdown = 0
    matrix = RGBMatrix(options = options)
    
    offscreen_canvas = matrix.CreateFrameCanvas()
    pos = offscreen_canvas.width
    
    # 文字設定
    print("setting LED matrix options...")
    font1 = graphics.Font()
    font1.LoadFont("/home/pi/Downloads/font/sazanami-20040629/sazanami-gothic_16.bdf") # 上の行と分割しないとセグフォ
    font2 = graphics.Font()
    font2.LoadFont("/home/pi/Downloads/font/misaki_bdf_2021-05-05/misaki_gothic_2nd.bdf")
    textColor = graphics.Color(255, 255, 0)
    
    # 画像設定
    image = Image.open("/home/pi/ledmatrix/twitter_dot.png")
    image.thumbnail((8, 8), Image.ANTIALIAS)
    
    # Start loop
    i = 0
    print("Press CTRL-C to stop")
    while True:
        offscreen_canvas.Clear()
        graphics.DrawText(offscreen_canvas, font2, 0, 7, textColor, "外気温"+temp) # 静止文字
        length = graphics.DrawText(offscreen_canvas, font1, pos, 31, textColor, atcl_arr[i]) # 動く文字
        matrix.SetImage(image.convert('RGB'), 0, 8, False) # 画像
        
        # 動く文字の位置をずらす
        pos = pos - 1
        if (pos + length < 0): # 文字が左まで行って消えたら、posをリセット
            pos = offscreen_canvas.width
            # iをインクリメント、iがMAXなら0にする
            if (i == len(atcl_arr)-1):
                i = 0
            else:
                i += 1
        
        time.sleep(0.05)
        offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)

def worker():
    global atcl_arr
    global temp
    atcl_arr = getNews()
    temp = getTemperature()

def mainloop(time_interval, f, another):
    f() # 最初に情報取得してないと描画時にoutofindex
    
    now = time.time()
    t0 = threading.Thread(target=another)
    t0.setDaemon(True)
    t0.start()
    while True: # 5分後、以後5分ごとに実行
        wait_time = time_interval - ( (time.time() - now) % time_interval )
        time.sleep(wait_time)
        t = threading.Thread(target=f)
        t.setDaemon(True)
        t.start()
    
if __name__ == "__main__":
    mainloop(300, worker, displayLED)
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
import threading

atcl_arr = []
temp = ""

def getNews():
    print("getting NEWS...")
    URL = "https://www.japantimes.co.jp/"
    rest = requests.get(URL)
    soup = BeautifulSoup(rest.text, "html.parser")
    atcl_list = soup.find_all(attrs={"class" : "article-title"})
    for atcl in atcl_list:
        #print(atcl.string)
        atcl_arr.append(atcl.string)
    
    return atcl_arr
        
def getTemperature():
    print("getting current temperature...")
    URL = "https://tenki.jp/amedas/3/17/46091.html" # 海老名のアメダス
    rest = requests.get(URL)
    soup = BeautifulSoup(rest.text, "html.parser")
    temp = soup.select('.amedas-current-list')[0].select('li')[0]
    temp.select('span')[0].decompose()
    #print(temp.text)
    
    return temp.text

def displayLED():
    global atcl_arr
    global temp
    
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.gpio_slowdown = 0
    matrix = RGBMatrix(options = options)
    
    offscreen_canvas = matrix.CreateFrameCanvas()
    
    # LEDマトリクス設定
    print("setting LED matrix options...")
    font1 = graphics.Font()
    font1.LoadFont("/home/pi/Downloads/font/sazanami-20040629/sazanami-gothic_16.bdf") # 上の行と分割しないとセグフォ
    font2 = graphics.Font()
    font2.LoadFont("/home/pi/Downloads/font/misaki_bdf_2021-05-05/misaki_gothic_2nd.bdf")
    textColor = graphics.Color(255, 255, 0)
    pos = offscreen_canvas.width

    # Start loop
    i = 0
    print("Press CTRL-C to stop")
    while True:
        offscreen_canvas.Clear()
        graphics.DrawText(offscreen_canvas, font2, 0, 7, textColor, "外気温"+temp) # 静止文字
        length = graphics.DrawText(offscreen_canvas, font1, pos, 31, textColor, atcl_arr[i]) # 動く文字
        
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

def mainloop(time_interval, f, another):
    worker()
    
    now = time.time()
    t0 = threading.Thread(target=another)
    t0.setDaemon(True)
    t0.start()
    while True:
        t = threading.Thread(target=f)
        t.setDaemon(True)
        t.start()
        t.join()
        wait_time = time_interval - ( (time.time() - now) % time_interval )
        time.sleep(wait_time)

def worker():
    global atcl_arr
    global temp
    atcl_arr = getNews()
    temp = getTemperature()
    
if __name__ == "__main__":
    mainloop(3600, worker, displayLED)
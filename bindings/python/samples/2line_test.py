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

class createLED():
    # パネル設定用関数
    def __init__(self):
        self.font = []             # フォント
        self.textColor = []        # テキストカラー
        self.flagPreparedToDisplay = False # メイン関数を表示する準備ができたかどうかのフラグ
        
        # LEDマトリクス設定
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.gpio_slowdown = 0
        self.matrix = RGBMatrix(options = options)
        
        # キャンバス作成
        self.offscreen_canvas = self.matrix.CreateFrameCanvas()
        
        # 最低限のフォントだけ読み込み、WAITINGを表示させておく
        self.f = threading.Thread(target=self.displayLEDTemp)
        self.f.setDaemon(True)
        self.f.start()
        
        # 文字設定
        print("setting LED matrix options...")
        self.font.append(graphics.Font())
        self.font[0].LoadFont("/home/pi/Downloads/font/sazanami-20040629/sazanami-gothic_14.bdf") # 上の行と分割しないとセグフォ
        self.font.append(graphics.Font())
        self.font[1].LoadFont("/home/pi/Downloads/font/misaki_bdf_2021-05-05/misaki_gothic_2nd.bdf")
        self.textColor.append(graphics.Color(255, 255, 0))
        
        # 画像設定
        self.image = Image.open("/home/pi/ledmatrix/twitter_dot.png")

    # パネル点灯する関数（一時的）
    def displayLEDTemp(self):
        print('display "WAITING..."')
        font_simple = graphics.Font()
        font_simple.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/5x8.bdf")
        textColor_simple = graphics.Color(255, 255, 0)
        #while (self.flagPreparedToDisplay == False):
        timeout_start = time.time()
        while time.time() < timeout_start + 10: # 10秒経過後にWAITING表示を消すはずだが機能しない。ただ上のwhileより処理が早いのでこちらを使ってる…
            graphics.DrawText(self.offscreen_canvas, font_simple, 0, 31, textColor_simple, "WAITING...") # 静止文字
            self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)

    # パネル点灯する関数（メイン）
    def displayLEDMain(self):
        global atcl_arr
        global temp
        
        # Start loop
        i = 0
        pos = self.offscreen_canvas.width
        self.flagPreparedToDisplay = True
        print("display LED, Press CTRL-C to stop")
        while True:
            self.offscreen_canvas.Clear()
            graphics.DrawText(self.offscreen_canvas, self.font[1], 0, 7, self.textColor[0], "外気温"+temp) # 静止文字
            length = graphics.DrawText(self.offscreen_canvas, self.font[0], pos, 29, self.textColor[0], atcl_arr[i]) # 動く文字
            self.matrix.SetImage(self.image.convert('RGB'), 0, 8, False) # 画像
            
            # 動く文字の位置をずらす
            pos = pos - 1
            if (pos + length < 0): # 文字が左まで行って消えたら、posをリセット
                pos = self.offscreen_canvas.width
                # iをインクリメント、iがMAXなら0にする
                if (i == len(atcl_arr)-1):
                    i = 0
                else:
                    i += 1
            
            time.sleep(0.05)
            self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
    
def worker():
    global atcl_arr
    global temp
    atcl_arr = getNews()
    temp = getTemperature()

def mainloop(time_interval, f, another):
    f() # 最初に情報取得の完了まで待たないと描画時にoutofindex
    
    now = time.time()
    t0 = threading.Thread(target=another) # argsの,は必要。ないとエラー
    t0.setDaemon(True)
    t0.start() # 描画
    while True: # 5分後、以後5分ごとに実行
        wait_time = time_interval - ( (time.time() - now) % time_interval )
        time.sleep(wait_time)
        t = threading.Thread(target=f)
        t.setDaemon(True)
        t.start() # 情報取得を実行
    
if __name__ == "__main__":
    LED = createLED()
    mainloop(300, worker, LED.displayLEDMain)
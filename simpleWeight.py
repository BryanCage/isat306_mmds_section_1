import RPi.GPIO as gpio
import time
from HX711_TAT.hx711 import *  #Done

Offset = -2712.95              #Done
DT = 23
SCK= 24

scale = HX711(23,24,128)       #Done


gpio.setmode(gpio.BCM)
gpio.setup(SCK, gpio.OUT)
sample = 0


def readCount():
    i=0
    Count = 0
    gpio.setup(DT, gpio.OUT)
    gpio.output(DT,1)
    gpio.output(SCK, 0)
    gpio.setup(DT, gpio.IN)
    
    while gpio.input(DT) == 1:
        i=0
    for i in range(24):
        gpio.output(SCK, 1)
        Count = Count<<1
        
        gpio.output(SCK, 0)
        #time.sleep(0.001)
        if gpio.input(DT) == 0:
            Count = Count+1
            #print Count
    gpio.output(SCK,1)
    Count = Count^800000
    gpio.output(SCK,0)
    return Count
sample = readCount()
while 1:
    
    count = readCount()
    w=0
    w=(count-sample)/106
    print count,"g"
    
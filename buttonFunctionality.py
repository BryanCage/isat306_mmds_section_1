from RPi import GPIO
from time  import sleep
from Adafruit_CharLCD import Adafruit_CharLCD
from subprocess import check_output

import os
import serial
import sys
import threading
import time
import serial.tools.list_ports
import numpy as py

PIN_A = 17
PIN_B = 18
PIN_HX711_DAT = 2
PIN_HX711_CLK = 3
clickPin      = 27

firstClick=     False
click_Double=   False
click_Single=   False
count = 0
numClicks = {'numClicks': 0}
#===============================================
#===               GPIO SETUP                ===
#===============================================
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_HX711_DAT, GPIO.IN)
GPIO.setup(PIN_HX711_CLK, GPIO.IN)
GPIO.setup(clickPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# ============================================================
# ===   knobPressed(channel) -- ISR                              ===
# ============================================================
def knobPressed(channel):

    global click_Single
    global click_Double
    global firstClick
    global numButtonClicks
    global count
    
    os.system('clear')
    print('GPIO input: ' + str(GPIO.input(clickPin)))
    numClicks['numClicks'] += 1
    print(numClicks['numClicks'])


    #firstClick = True
    firstClick = not GPIO.input(clickPin)
    print(firstClick)
    if(not firstClick):
     
        for i in range(0, 1000):
            if(not GPIO.input(clickPin)):
                click_Double = True
                click_Single = False
                print('Button: Double Clicked')
        click_Single = True
        print('firstClick: ' + str(firstClick))
    if(click_Single):
        
        print('Button: Single Clicked')
    
def main():
    
    GPIO.add_event_detect(clickPin, GPIO.RISING, callback=knobPressed, bouncetime=30)
    raw_input("Program Running...")
    GPIO.cleanup()
    
if(__name__ == '__main__'):
    main()
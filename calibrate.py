import RPi.GPIO as gpio
import time
from HX711.hx711 import *  # Done
import serial
import os
import sys
import io

seed = -2322.95              # Done
DT = 23
SCK= 24

scale = HX711(23,24,128)       # Done

#Create Serial                 # Done
ser = ser = serial.Serial('/dev/tty', baudrate=9600,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                    )
sio = io.TextIOWrapper(io.BufferedRWPair(ser, ser))
                       
#os.system("echo 'print'")
scale.set_scale(seed)        # Done
scale.tare()                   # Done

gpio.setmode(gpio.BCM)
gpio.setup(SCK, gpio.OUT)
sample = 0


def calibrate():
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
        
        if gpio.input(DT) == 0:
            Count = Count+1
            
    gpio.output(SCK,1)
    Count = Count^800000
    gpio.output(SCK,0)
    return Count

sample = readCount()
print("\r")
while 1:
    
    scale.set_scale(seed)
    
    if(ser.inWaiting()):
        z = ser.read()
        if(z == '-'):
            seed -=5
        if(z == '+'):
            seed +=5
        if(z == 'x'):
             
            ser.write("Closing Serial Connection\r")
            
            ser.close()
            
            os.system('clear')
            
            GPIO.cleanup()
            sys.exit("Exiting Calibration...")
            

    units = scale.get_units(10)
   
    print("Seed Value: "+ str(seed) + "  Weight: " + str(units) + "\r")
    
        
##    count = readCount()
##    w=0
##    w=(count-sample)/106
    #print count,"g"
     
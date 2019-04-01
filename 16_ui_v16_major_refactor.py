# ===============================================================
#    !/usr/bin/env python
#    encoding: utf-8
#    -*- coding: utf-8 -*-#    MMDS v. 6.0
#    (c) 2014, Budd Churchward - WB7FHC
#    This is an Open Source Project
#    http://opensource.org/licenses/MIT

#    Search YouTube for 'WB7FHC' to see several videos of this project
#    as it was developed.

#    MIT license, all text above must be included in any redistribution
#    **********************************************************************

#    This project demonstrates several ways to use a rotary encoder as part of a user interface
#    with Arduino and LCD projects.

#    http://youtu.be/MzO__HCKP8I
# ===============================================================


# ===============================================================
# ===   IMPORTS ========                                      ===
# ===============================================================

import RPi.GPIO as GPIO
from time import sleep
from HX711.hx711 import *
from Adafruit_CharLCD import Adafruit_CharLCD
from datetime import datetime
from datetime import timedelta
from Functions.menuFunctions import *
from Functions.cameraFunctions import *
from mysql.connector import errorcode
from mysql.connector import (connection)
from subprocess import check_output
from monitor_v2_add_video import *
from menu import Menu

from Encoder.encoder import *
import os
import calendar
import csv
import json
import mimetypes
import mysql.connector
import re
import serial
import smtplib
import struct
import subprocess
import sys
import io
import threading
import time
import serial.tools.list_ports
import numpy as np
import Queue
from gpiozero import Button
from signal import pause
from absl import app
from absl import flags

# ===============================================
# ===            Instantiate LCD              ===
# ===============================================

lcd = Adafruit_CharLCD(rs=26, en=19, d4=13, d5=6, d6=5, d7=11, cols=16, lines=2)

lcd.clear()
lcd.message(" Mammal Monitor\n")
lcd.message("  Data Station")
##sleep(2)
##lcd.clear()
##lcd.message("Initializing.")
##sleep(0.75)
##lcd.clear()
##lcd.message("Initializing..")
##sleep(0.75)
##lcd.clear()
##lcd.message("Initializing...")
##sleep(1)
##lcd.clear()
##lcd.message("   Initialize\n")
##lcd.message("    Complete")
##sleep(1)
##lcd.clear()
##lcd.message("Main Menu")
##lcd.clear()
##lcd.message("Millis: " + str(millis()))
##sleep(2)
##lcd.clear()
##lcd.message("Millis: " +  str(millis()))
##sleep(2)
# lcd.clear()

# ===============================================
# ===            Instantiate SCALE            ===
# ===============================================

seed = {'seed': -2322.95}
DT = 23
SCK = 24

scale = HX711(23, 24, 128)
scale.set_scale(seed['seed'])
scale.tare()

# ===============================================
# === Set Default Units to grams in JSON file ===
# ===============================================

with open('config.json') as config_file:
    config = json.load(config_file)
    config['scale']['units']['g'] = True
    config['scale']['units']['lbs'] = False
    config['scale']['units']['oz'] = False
    config_file.close()
    config_file = open('config.json', 'w')
    config_file.write(json.dumps(config, indent=4, sort_keys=True))
    config_file.close()

# ===============================================
# ===             INTIALIZE THREADS           ===
# ===============================================
preview_on = False
event = threading.Event()
lock = threading.Lock()
event2 = threading.Event()
lock2 = threading.Lock()

previewCameraEvent = threading.Event()
previewCameraLock = threading.Lock()
t = threading.Thread(target=monitor_stream, args=(event, lock,))
t2 = threading.Thread(target=previewCamera, args=(previewCameraEvent, previewCameraLock,))
thread_test = threading.Thread(target=thread_test, args=(event2, lock2,))
t.daemon = True
t.start()
t2.start()
thread_test.start()

# ===============================================
# ===         SERAIL PORT FUNCTIONS           ===
# ===============================================

##def listPorts():
##    ports = list(serial.tools.list_ports.comports())
##
##    for p in ports:
##        p.description
##        p.device
##
##
##def getArduinoPort():
##    ports = list(serial.tools.list_ports.comports())
##
##    for p in ports:
##        if ("arduino" in p.description.lower()):
##            print("PORT: " + p.device)
##            return p.device
##
###=== USE TO GET SPECIFIC PORT ===================
##def getSpecifiedPort(portName):
##    ports = list(serial.tools.list_ports.comports())
##
##    for p in ports:
##        if portName in p.description.lower():
##            print("PORT: " + p.device)
##            return p.device
##
###===============================================
###===    INITIALIZE SERIAL PORT - CONFIGS     ===
###===============================================
##
##PORT = '{}'.format(getArduinoPort().strip())
##BAUD_RATE = 9600
##
### === Open Serial Port =========================
##ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
##
ser = serial.Serial('/dev/ttyAMA0', baudrate=9600,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                    )

# ===============================================
# ===            Assign Values             ===
# ===============================================
PIN_A = 17  # Clock
PIN_B = 18  # Data
PIN_21 = 21  # Red_LED
PIN_20 = 20  # Green_LED
PIN_16 = 16  # Blue_LED
PIN_HX711_DAT = 2
PIN_HX711_CLK = 3
clickPin = 27  # Switch Button

# ===============================================
# ===               GPIO SETUP                ===
# ===============================================
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_HX711_DAT, GPIO.IN)
GPIO.setup(PIN_HX711_CLK, GPIO.IN)
GPIO.setup(clickPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# ===============================================
# ===           LED DEBUG PINS                ===
# ===============================================
GPIO.setup(PIN_21, GPIO.OUT, initial=0)  # Set port/pin as an output (BLUE_LED)
GPIO.setup(PIN_20, GPIO.OUT, initial=0)  # Set port/pin as an output (GRENN_LED)
GPIO.setup(PIN_16, GPIO.OUT, initial=0)  # Set port/pin as an output (RED_LED)

GPIO.output(PIN_21, GPIO.LOW)
GPIO.output(PIN_20, GPIO.LOW)
GPIO.output(PIN_16, GPIO.LOW)

state = 0  # Used to read the encoder
encoder = 10  # to count the clicks up and down 0-9 command mode 10+ send mode
numButtonClicks = {'numClicks': 0}


# ===============================================
# ===       Instantiate Shutoff Button        ===
# ===============================================
def shutdown():
    config = open("config.json", "w")
    config["camera"]["record_mode"] = true
    config.close()
    subprocess.check_call(['sudo', 'poweroff'])


shutdown_btn = Button(20, hold_time=3)
shutdown_btn.when_held = shutdown

# ===============================================
# ===            Instantiate Encoder          ===
# ===============================================

rot_encode = Encoder(clickPin, PIN_A, PIN_B)

backButtonEncoderIndexPosition = 0  # Dynamically sets the back "Main Menu"
# list item index position according to
# length of dynamically populated menu_SSIDList

menu_MainList = [

    "Bluetooth",
    "Wifi",
    "Select SSID",
    "Scale Config",
    "Camera Config",
    "Display Info",
    "Start Monitor"

]
menu_BlueList = [

    "Blu T:  ON [OFF]"

]

menu_WifiList = [

    "Wifi:  ON [OFF]"

]

menu_ScaleList = [

    "Tare",
    "Calibrate Scale",
    "Units of Measure",
    "Main Menu"

]

menu_CameraList = [

    "Preview Camera  ",
    "Resolution",
    "Mode",
    "ISO",
    "Shutter Speed",
    "AWB",
    "Main Menu"

]

menu_cameraResolution = ["640 x 480", "1280 x 720", "1640 x 1232", "Back"]

menu_DisplayList = [

    "Box ID: 1111",
    "PI Name: \n Katrina Gobetz",
    "Hillendale\nTurtle Tracking",
    "Main Menu"

]

menu_ExposureList = [

    "off",
    "auto",
    "night",
    "nightpreview",
    "backlight",
    "spotlight",
    "sports",
    "snow",
    "beach",
    "verylong",
    "fixedfps",
    "antishake",
    "fireworks"

]

menu_ImagingList = ["[Image]   Video "]
menu_MonitorList = ["Run:  ON [OFF]  "]
menu_PreviewList = ["VuCam:  ON [OFF]"]

menu_SSIDList = []
menu_UnitsList = ["Units: [g] oz "]
menu_Calibrate = {'record': {'Val': 0, 'Wgt': 0}}
menu_Tare = {'weight': round(scale.get_units(10), 2)}
networks = ['MMDS_Hotspot', 'VIRUS_DETECTED', 'Cage']
units = ['g', 'lbs', 'oz']
units_registry = {'g': True, 'lbs': False, 'oz': False}


def getWifiStatus():
    global wifi_on

    ps = subprocess.Popen(['iwconfig'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        output = subprocess.check_output(('grep', 'ESSID'), stdin=ps.stdout)
        if ("off" in output):
            print("Wifi Off")
            wifi_on = False
            menu_WifiList[0] = "Wifi:  ON [OFF]"
            return False
        else:
            wifi_on = True
            print("Wifi On")
            menu_WifiList[0] = "Wifi: [ON] OFF "
            return True
    # print(output)
    # print(type(output))

    except subprocess.CalledProcessError:
        # grep did not match any lines
        wifi_on = False
        menu_WifiList[0] = "Wifi:  ON [OFF]"
        return False


firstClick = False
click_Double = False
click_Single = False
still_image = True


def resetCameraMode(bool):
    with open("config.json") as config_file:
        config = json.load(config_file)
        config["camera"]["record_mode"] = bool
        config_file.close()
        config_file = open("config.json", "w")
        config_file.write(json.dumps(config, indent=4, sort_keys=True))
        config_file.close()


resetCameraMode(True)

button_click_registry = {

    'firstClick': False,
    'click_Single': False,
    'click_Double': False

}

menu_registry = ({

    'main': True,
    'bluetooth': False,
    'wifi': False,
    'scale': False,
    'camera': False,
    'display': False,
    'monitor': False,
    'ssid': False,
    'calibrate': False

})

toggle_switches = {

    'wifi_on': True,
    'blue_on': True,
    'monitor_on': False,
    'ssid_select_state': False

}


def switch_toggle(tog_switch):
    if (toggle_switches[tog_switch] == True):
        toggle_switches[tog_switch] = False
    else:
        toggle_switches[tog_switch] = True
    print(toggle_switches)


def button_click_reset(click_type):
    if (click_type not in button_click_registry):
        print('Invalid reset selection')
        pass
    elif (click_type == 'all'):
        for key in button_click_registry:
            button_click_registry[key] = False
    # Toggle
    elif (button_click_registry[click_type] == True):
        button_click_registry[click_type] = False
    else:
        button_click_registry[click_type] = True


def menu_toggle(menu):
    if (menu_registry[menu] == True):
        menu_registry[menu] = False
    else:
        menu_registry[menu] = True
    print(menu_registry)


def menu(menu):
    for key in menu_registry:
        if (key == menu):
            menu_registry[key] = True
        else:
            menu_registry[key] = False
        print(menu_registry)


mode_Main = True
mode_Blue = False
mode_Wifi = False
mode_Scale = False
mode_Camera = False
mode_Display = False
mode_Monitor = False
mode_Preview = False
mode_SSID = False
blue_on = False  # Returns Bluetooth True/False
wifi_on = getWifiStatus()  # Returns Wifi True/False # Pipes iwconfig status of grep and ESSID from stdin to stdout to test wifi logic
print("Wifi Status: " + str(wifi_on))
ssid_selection_made = True
monitor_on = False
mode_toggle_Imaging = False
mode_Tare = False
mode_Calibrate = False
mode_Resolution = False
mode_AWB = False
mode_Shutter = False
mode_ISO = False
mode_Units = False

# ===============================================
# === ENCODINGS ===                           ===
# ===============================================
# MAIN MENU
encode_Blue = 10
encode_Wifi = 11
encode_SSID = 12
encode_Scale = 13
encode_Camera = 14
encode_Display = 15
encode_Monitor = 16

# SCALE MENU
encode_Tare = 20
encode_Calibrate = 21
encode_Units = 22
encode_ScaleExit = 23

# CAMERA CONFIG MENU
encode_Resolution = 37
encode_Mode = 38
encode_ISO = 39
encode_Shutter = 40
encode_AWB = 41

# NETWORK (SSID) Menu
encode_MMDS_Hotspot = 50
encode_VIRUS_DETECTED = 51

# MENU ENCODING RANGES

# Main Menu
numItems_menu_MainList = 7  # Number of items in the Main Menu
knobMax = numItems_menu_MainList + 10  # Use to cycle the menus around in a loop so that item first comes after item last
knobMin = 10;  # Use to cycle the opposite direction

# Bluetooth
numItems_menu_BlueList = 1
menu_BlueLowRange = 1
menu_BlueTopRange = 2

# Wifi
numItems_menu_WifiList = 1
menu_WifiLowRange = 4
menu_WifiTopRange = 5

# Camera Mode
numItems_menu_ImagingList = 1
menu_ImagingLowRange = 6
menu_ImagingTopRange = 7

# Scale Config
numItems_menu_ScaleList = 4  # Number of items in the Scale Menu -- List Format
menu_ScaleLowRange = 20
menu_ScaleTopRange = 24

# Camera Config
numItems_menu_CameraList = 7  # Number of items in the Camera Menu -- List Format
menu_CameraLowRange = 36
menu_CameraTopRange = 43

# Preview
numItems_menu_PreviewList = 1
numItems_menu_MonitorString = 1
menu_PreviewLowRange = 72
menu_PreviewTopRange = 73

# Display
numItems_menu_DisplayList = 4  # Number of items in the Display Menu -- List Format
menu_DisplayLowRange = 45
menu_DisplayTopRange = 49

# Monitor
numItems_menu_MonitorList = 1  # Number of items in the Monitor Menu -- List Format
numItems_menu_MonitorString = 1  # Number of items in the Monitor Menu -- String Format
menu_MonitorLowRange = 44
menu_MonitorTopRange = 45

# SSID
numItems_menu_SSIDList = len(menu_SSIDList)
menu_SSIDLowRange = 50
menu_SSIDTopRange = menu_SSIDLowRange + len(menu_SSIDList)

# Calibrate
numItems_menu_CalibrateList = 1  # Number of items in the Calibrate Menu
menu_CalibrateLowRange = 60
menu_CalibrateTopRange = 61

# Tare
numItems_menu_TareList = 1  # Number of items in the Tare Menu
menu_TareLowRange = 65
menu_TareTopRange = 66

# Units
numItems_menu_UnitsList = 1  # Number of items in the Units Menu
menu_UnitsLowRange = 70
menu_UnitsTopRange = 71

# Camera Resolution
numItems_menu_ResolutionList = 4
menu_ResolutionLowRange = 80
menu_ResolutionTopRange = 84

# Camera Framerate
numItems_menu_ShutterList = 4
menu_ShutterLowRange = 85
menu_ShutterTopRange = 89

# Camera AWB
numItems_menu_AWBList = 10
menu_AWBLowRange = 100
menu_AWBTopRange = 110

character = ' '  # stores the character we want to print or send
global monitor_proc
global previewCam_proc
# ===========================================
# ===           ARROW CHARACTERS          ===
# ===========================================
# Three of the edit features need a cursor which was hard to do on the LCD screen,
# so I went with a arrows instead. These defines the graphics

upArrow = [0b0, 0b100, 0b111, 0b10101, 0b100, 0b100, 0b100, 0b10]
lcd.create_char(0, upArrow)

downArrow = [0b0, 0b100, 0b100, 0b100, 0b100, 0b10101, 0b1110, 0b100]
lcd.create_char(1, downArrow);


# ================================================================
# ===      SEND FUNCTION DEFINITIONS                          ====
# ================================================================

# =================================================================
# ===  PYTHON LEARNING SECTION -- WORKING WITH ord(), chr()     ===
# =================================================================
# ===   chr(any int i.e. 97 or hex i.e. 0x61) will return       ===
# ===  ascii char representation.                              ===
# ===        ex: chr(97) == 'a' or chr(0x62) == 'b'             ===
# ===   conversly ord(any string character i.e. 'a')            ===
# ===  will return int representaion                           ===
# ===        ex. ord('a') returns the integer 97                ===
# =================================================================

# ===========================================
# ===         FUNCTION DEFINITIONS        ===
# ===========================================


# ============================================================
# === clearAllFlags()                               ===
# ============================================================        
def clearAllFlags():
    global click_Double
    global click_Single
    global mode_Main
    global mode_Blue
    global mode_Wifi
    global mode_Scale
    global mode_Camera
    global mode_Preview
    global mode_Display
    global mode_Monitor
    global mode_SSID
    global menu_SSIDList
    global mode_toggle_Imaging

    click_Double = False
    click_Single = False
    mode_Main = True
    mode_Blue = False
    mode_Wifi = False
    mode_Scale = False
    mode_Camera = False
    mode_Preview = False
    mode_Display = False
    mode_Monitor = False
    mode_SSID = False
    mode_toggle_Imaging = False
    menu_SSIDList = []


# ============================================================
# === knobTurned()  -- ISR                              ===
# ============================================================
def knobTurned(channel):
    global encoder
    global knobMin
    global knobMax

    global click_Double
    global click_Single

    global mode_Main
    global mode_Blue
    global mode_Scale
    global mode_Wifi
    global mode_Display
    global mode_Camera
    global mode_Preview
    global mode_Monitor
    global mode_SSID
    global mode_Calibrate
    global mode_Resolution
    global bump

    state = 0
    state = state + GPIO.input(PIN_A)
    state <<= 1
    state = state + GPIO.input(PIN_B)

    if (state == 0 or state == 1): return
    print('============================')
    print('=== knobTurned:          ===')
    print('============================')
    print(state)
    if (state == 2):
        bump = [0, 0, 1,
                1]  # simple array that tells me valid and invalid readings from the encoder and which way its turning
    else:
        bump = [0, 0, -1,
                -1]  # simple array that tells me valid and invalid readings from the encoder and which way its turning

    encoder += bump[state]  # added direction of turn to state
    if (encoder < knobMin):  # lower limit of any menu roll back to top
        encoder = knobMax - 1  # upper limit of any menu roll back to bottom
    if (encoder > knobMax - 1):
        encoder = knobMin
    print("Encoder: " + str(encoder))
    lcd.clear()
    lcd.set_cursor(0, 0)

    if (mode_Blue):
        showMenuList(menu_BlueList)
    # print("Bluetooth Menu")
    elif (mode_Wifi):
        showMenuList(menu_WifiList)
    # print("Wifi Menu")
    elif (mode_Scale):
        showMenuList(menu_ScaleList)
    # print("Scale Config")
    elif (mode_Camera):
        showMenuList(menu_CameraList)
    # print("Camera Config")
    elif (mode_Display):
        showMenuList(menu_DisplayList)
    # print("Display Unit Data")
    elif (mode_Monitor):
        showMenuList(menu_MonitorList)
    # print("Exec Monitor?")
    elif (mode_Preview):
        showMenuList(menu_PreviewList)
    elif (mode_SSID):
        showMenuList(menu_SSIDList)
    elif (mode_Calibrate):
        showCalibration(menu_Calibrate)
    elif (mode_Resolution):
        showMenuList(menu_cameraResolution)
    elif (mode_Tare):
        showTare()
    elif (mode_Units):
        showMenuList(menu_UnitsList)
    else:
        # print("Main Menu")
        showMainMenuList()


def showTare():
    global mode_Tare

    scale.tare()
    tare = 'Taring'
    period = '.'
    lcd.clear()
    for i in range(0, 10):
        tare += period
        lcd.set_cursor(0, 0)
        lcd.message(tare)
        sleep(0.2)
    sleep(1)
    if (not mode_Tare):
        lcd.clear()
        sleep(1)
        lcd.message('Back to Main')
        sleep(1)
        switchToMainMenuList(encode_Tare)
    else:
        while (not GPIO.input(clickPin)):
            wgt = round(scale.get_units(10), 2)
            lcd.clear()
            lcd.message(str(wgt) + ' ' + str(units[0]))


def convertUnits(wgt, unit):
    if (unit == 'g'):
        print(str(wgt) + ' g')
        return wgt
    elif (unit == 'oz'):
        convertedWeight = round(wgt * 0.035274, 2)
        print((str(convertedWeight) + ' oz'))
        return convertedWeight


def showCalibration(menu):
    scale.set_scale(seed['seed'])
    if (bump[2] == 1):
        seed['seed'] += 1
        print(seed['seed'])
        units = round(scale.get_units(10), 2)
        lcd.set_cursor(0, 0)
        lcd.message('    increase -->')
        lcd.set_cursor(0, 1)
        lcd.message(' Weight: ' + str(units))
        print('right')
    elif (bump[2] == -1):
        seed['seed'] -= 1
        print(seed['seed'])
        units = round(scale.get_units(10), 2)
        lcd.set_cursor(0, 0)
        lcd.message('<-- decrease')
        lcd.set_cursor(0, 1)
        lcd.message(' Weight: ' + str(units))
        print('left')
    else:
        return


def getSSIDMenu():
    global mode_SSID
    global mode_Wifi
    global mode_Main

    mode_SSID = True
    currentStatus()

    ssid = []
    try:
        scanoutput = check_output(["sudo", "iwlist", "wlan0", "scan"])

        for line in scanoutput.split():
            if line.startswith("ESSID"):
                line = line[7:-1]
                if (line == '' or line == 'xfinitywifi' or len(line) > 30 or (line not in networks)):
                    continue
                else:
                    ssid.append(line)
        for i in range(0, len(ssid)):
            menu_SSIDList.append(ssid[i])
        print(menu_SSIDList)
        menu_SSIDList.append("Main Menu")
        print(menu_SSIDList)
        lcd.clear()
        lcd.message(menu_SSIDList[0])
        switchToSSIDMenu(len(menu_SSIDList))

        button_click_registry['click_Single'] = False
        print("#7")
    except:
        mode_Wifi = False
        mode_Main = False
        mode_SSID = False

        print('Wifi not turned on')
        lcd.set_cursor(0, 0)
        lcd.message('  Turn Wifi on  ')
        lcd.set_cursor(0, 1)
        lcd.message(' and try again  ')
        sleep(1)
        lcd.clear()
        lcd.message('Redirect to Wifi')
        sleep(1)
        switchToWifiMenu()
        lcd.clear()
        lcd.message(menu_WifiList[0])
        currentStatus()
        pass


# ============================================================
# ===   knobPressed(channel) -- ISR                              ===
# ============================================================
def knobPressed(channel):
    global click_Single
    global click_Double
    global first_Click
    global encoder
    global mode_Main
    global mode_Blue
    global mode_Wifi
    global mode_Scale
    global mode_Camera
    global mode_Display
    global mode_Preview
    global mode_Monitor
    global mode_SSID
    global blue_on
    global wifi_on
    global monitor_on
    global preview_on
    global knobMax
    global menu_SSIDLowRange
    global ssid_selection_made
    global menu_SSIDList
    global numButtonClicks
    global mode_Calibrate
    global mode_Resolution
    global mode_Tare
    global mode_Units
    global event
    global monitor_proc
    global previewCam_proc
    global still_image
    global mode_toggle_Imaging

    click_Single = True
    button_click_registry['click_Single'] = True
    print('before call: ' + str(numButtonClicks))
    numButtonClicks['numClicks'] += 1
    print('after call: ' + str(numButtonClicks))
    if (encoder == encode_Blue and not mode_Blue):  # 1
        mode_Blue = True
        switchToBlueMenu()
        currentStatus()
        click_Single = False
        print("#1")
    elif (encoder == encode_Wifi and not mode_Wifi):  # 2
        mode_Wifi = True
        switchToWifiMenu()
        currentStatus()
        click_Single = False
        print("#2")
    elif (encoder == encode_Scale and not mode_Scale):
        if (monitor_on):
            lcd.set_cursor(0, 0)
            lcd.message("Monitor to off ")
            lcd.set_cursor(0, 1)
            lcd.message("b4 scale config")
            sleep(3)

            switchToMonitorMenu()
            lcd.clear()
            lcd.message(menu_MonitorList[0])
        else:
            mode_Scale = True
            lcd.set_cursor(0, 0)
            lcd.clear()
            lcd.message(menu_ScaleList[0])
            switchToScaleMenu()
            click_Single = False
            print("#3")
    elif (encoder == encode_Camera and not mode_Camera):
        mode_Camera = True
        lcd.set_cursor(0, 0)
        lcd.clear()
        lcd.message(menu_CameraList[0])
        switchToCameraMenu()
        click_Single = False
        print("#4")
    elif (encoder == encode_Display and not mode_Display):
        mode_Display = True
        lcd.set_cursor(0, 0)
        lcd.message(menu_DisplayList[0])
        switchToDisplayMenu()
        click_Single = False
        print("#5")
    elif (encoder == encode_Monitor and not mode_Monitor):
        lcd.set_cursor(0, 0)
        if (not monitor_on):
            lcd.message(menu_MonitorList[0])
        currentStatus()
        mode_Monitor = True
        switchToMonitorMenu()
        click_Single = False
        print("#6")
    elif (encoder == encode_SSID and not mode_SSID):

        getSSIDMenu()

    elif (encoder == knobMax - 1 and mode_SSID):
        clearAllFlags()
        lcd.set_cursor(0, 0)
        lcd.message(menu_MainList[2])
        mode_SSID = False
        switchToMainMenuList(encode_SSID)

    elif (encoder == encode_MMDS_Hotspot and mode_SSID):
        lcd.clear()
        lcd.message(menu_MainList[2])
        print(menu_SSIDList[encoder - menu_SSIDLowRange])
        print('knobMax: ' + str(knobMax) + ' Encoder: ' + str(encoder) + ' LowRange: ' + str(menu_SSIDLowRange))
        print('Sub: ' + str(encoder - menu_SSIDLowRange))
        selected_SSID = menu_SSIDList[encoder - menu_SSIDLowRange]
        print('selected SSID: ' + str(selected_SSID) + ' AdjEncoder: ' + str(knobMax - encoder))
        os.system('/sbin/wpa_cli select_network $(wpa_cli list_networks | grep ' + str(selected_SSID) + ' | cut -f 1)')

        mode_SSID = False
        switchToMainMenuList(encode_SSID)
    elif (encoder == encode_VIRUS_DETECTED and mode_SSID):
        lcd.clear()
        lcd.message(menu_MainList[2])
        print(menu_SSIDList[encoder - menu_SSIDLowRange])
        print('knobMax: ' + str(knobMax) + ' Encoder: ' + str(encoder) + ' LowRange: ' + str(menu_SSIDLowRange))
        print('Sub: ' + str(encoder - menu_SSIDLowRange))
        selected_SSID = menu_SSIDList[encoder - menu_SSIDLowRange]
        print('selected SSID: ' + str(selected_SSID) + ' AdjEncoder: ' + str(knobMax - encoder))
        os.system('/sbin/wpa_cli select_network $(wpa_cli list_networks | grep ' + str(selected_SSID) + ' | cut -f 1)')

        mode_SSID = False
        switchToMainMenuList(encode_SSID)

    elif (encoder == 1 and not blue_on and not mode_Main):
        clearAllFlags()

        os.system("sudo rfkill unblock bluetooth")
        menu_BlueList[0] = "Blu T: [ON] OFF "
        lcd.set_cursor(0, 0)
        lcd.message(menu_BlueList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Main")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_MainList[0]))
        blue_on = True
        switchToMainMenuList(encode_Blue)
        # knobTurned(17)
        print("#8")

    elif (encoder == 1 and blue_on and not mode_Main):
        clearAllFlags()
        os.system("sudo rfkill block bluetooth")
        menu_BlueList[0] = "Blu T:  ON [OFF]"
        lcd.set_cursor(0, 0)
        lcd.message(menu_BlueList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Main")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_MainList[0]))
        blue_on = False
        switchToMainMenuList(encode_Blue)
        # knobTurned(17)
        print("#9")

    elif (encoder == 4 and not wifi_on and not mode_Main):
        clearAllFlags()
        switchToMainMenuList(encode_Wifi)
        os.system("sudo rfkill unblock wifi")
        menu_WifiList[0] = "Wifi: [ON] OFF "
        lcd.set_cursor(0, 0)
        lcd.message(menu_WifiList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Main")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_MainList[1]))
        wifi_on = True
        # knobTurned(17)
        print("#9" + str(encoder))

    elif (encoder == 4 and wifi_on and not mode_Main):
        clearAllFlags()
        switchToMainMenuList(encode_Wifi)
        currentStatus()
        os.system("sudo rfkill block wifi")
        menu_WifiList[0] = "Wifi:  ON [OFF]"
        lcd.set_cursor(0, 0)
        lcd.message(menu_WifiList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Main")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_MainList[1]))
        # knobTurned(17)
        wifi_on = False
        print("#10")

    elif (encoder == 44 and not monitor_on and not mode_Main and not preview_on):

        monitor_on = True
        currentStatus()
        switchToMainMenuList(encode_Monitor)
        menu_MonitorList[0] = "Run: [ON] OFF "
        lcd.set_cursor(0, 0)
        lcd.message(menu_MonitorList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Main")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_MainList[6]))
        with open("config.json") as config_file:
            config = json.load(config_file)
            record_mode = config["camera"]["record_mode"]
            config_file.close()
        print("#11: " + str(record_mode))
        print("Still Image: " + str(record_mode))
        monitor_proc = subprocess.Popen(['python', '/home/pi/mammal_monitor/UI/monitor_v5.py'], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)


    elif (encoder == 44 and monitor_on and not mode_Main and not preview_on):
        clearAllFlags()
        monitor_on = False
        currentStatus()
        switchToMainMenuList(encode_Monitor)
        menu_MonitorList[0] = "Run:  ON [OFF]"
        lcd.set_cursor(0, 0)
        lcd.message(menu_MonitorList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Main")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_MainList[6]))
        monitor_proc.kill()
        with open("config.json") as config_file:
            config = json.load(config_file)
            record_mode = config["camera"]["record_mode"]
            config_file.close()
        print("#12: " + str(record_mode))


    elif (encoder == 44 and not mode_Main and preview_on):
        lcd.clear()
        lcd.set_cursor(0, 0)
        lcd.message("Preview must be\n off to monitor ")
        sleep(2)
        lcd.clear()
        lcd.set_cursor(0, 0)
        lcd.message("Back to Main    ")
        sleep(1)
        switchToMainMenuList(encode_Camera)
        lcd.clear()
        lcd.set_cursor(0, 0)
        lcd.message(str(menu_MainList[4]))

    elif (encoder == 20 and mode_Scale):

        mode_Scale = False
        mode_Main = False
        mode_Tare = True
        switchToTareMenu()
        showTare()

    elif (encoder == 21 and mode_Scale):
        mode_Scale = False
        mode_Main = False
        mode_Calibrate = True
        tare = 'Taring'
        period = '.'
        lcd.clear()
        for i in range(0, 10):
            tare += period
            lcd.set_cursor(0, 0)
            lcd.message(tare)
            sleep(0.2)
        sleep(1)
        units = round(scale.get_units(10), 2)
        lcd.clear()
        lcd.set_cursor(0, 0)
        lcd.message('Put Known Weight')
        lcd.set_cursor(0, 1)
        lcd.message('on scale')

        sleep(2)

        lcd.set_cursor(0, 0)
        lcd.message('Push Button for ')
        lcd.set_cursor(0, 1)
        lcd.message('    Main Menu   ')
        sleep(2)
        lcd.set_cursor(0, 0)
        lcd.message('<--  Rotate  -->')
        lcd.set_cursor(0, 1)
        lcd.message('  to Calibrate  ')
        sleep(2)

        switchToCalibrateMenu()
        click_Single = False
        print("#3")

    elif (encoder == 22 and mode_Scale):
        mode_Scale = False
        mode_Main = False
        mode_Units = True
        switchToUnitsMenu()
        print('Switched to Units Menu')

    elif (encoder == 60 and mode_Calibrate):
        clearAllFlags()
        currentStatus()
        lcd.clear()
        lcd.message('Back to Main')
        switchToMainMenuList(encode_Scale)
        sleep(1)
        lcd.clear()
        lcd.message(menu_MainList[3])
        mode_Scale = False
        mode_Calibrate = False

    elif (encoder == 65 and mode_Tare):
        clearAllFlags()
        currentStatus()
        lcd.clear()
        lcd.message('Back to Main')
        switchToMainMenuList(encode_Scale)
        sleep(1)
        lcd.clear()
        lcd.message(menu_MainList[3])
        mode_Tare = False

    elif (encoder == 70 and units_registry['g'] == False and not mode_Main):
        clearAllFlags()
        currentStatus()
        lcd.clear()
        menu_UnitsList[0] = "Units: [g] oz "
        lcd.set_cursor(0, 0)
        lcd.message(menu_UnitsList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Main")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_MainList[3]))
        mode_Units = False
        units_registry['g'] = True
        units_registry['oz'] = False
        units_registry['lbs'] = False
        with open('units.json') as f:
            unit_json = json.load(f)
            unit_json['scale']['units']['g'] = True
            unit_json['scale']['units']['lbs'] = False
            unit_json['scale']['units']['oz'] = False
            f.close()
            f = open('units.json', 'w')
            f.write(json.dumps(unit_json, indent=4, sort_keys=True))
            f.close()
        print(units_registry)
        switchToMainMenuList(encode_Scale)

        print("#70" + str(encoder))

    elif (encoder == 70 and units_registry['g'] == True and not mode_Main):
        clearAllFlags()

        currentStatus()
        menu_UnitsList[0] = "Units:  g [oz]"
        lcd.clear()
        lcd.set_cursor(0, 0)
        lcd.message(menu_UnitsList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Main")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_MainList[3]))
        mode_Units = False
        units_registry['g'] = False
        units_registry['oz'] = True
        units_registry['lbs'] = False
        with open('units.json') as f:
            unit_json = json.load(f)
            unit_json['scale']['units']['g'] = False
            unit_json['scale']['units']['lbs'] = False
            unit_json['scale']['units']['oz'] = True
            f.close()
            f = open('units.json', 'w')
            f.write(json.dumps(unit_json, indent=4, sort_keys=True))
            f.close()
        print(units_registry)
        switchToMainMenuList(encode_Scale)
        print("#70")

    elif (encoder == 23 and mode_Scale):
        clearAllFlags()
        switchToMainMenuList(encode_Scale)
        lcd.set_cursor(0, 0)
        lcd.message('Back to Main')
        sleep(1)
        lcd.clear()
        lcd.message(menu_MainList[3])
        mode_Scale = False

    elif (encoder == 36 and not mode_Preview):
        mode_Preview = True
        mode_Camera = False
        mode_Main = False
        switchToPreviewCamMenu()
        currentStatus()

    elif (encoder == 37 and not mode_Resolution):
        mode_Camera = False
        mode_Resolution = True
        lcd.clear()
        lcd.set_cursor(0, 0)
        lcd.message(menu_cameraResolution[0])
        switchToResolutionMenu()
        currentStatus()
        print("#37")

    elif (encoder == 38 and not mode_toggle_Imaging):
        mode_toggle_Imaging = True
        switchToImagingMenu()
        currentStatus()
        print("#38")

    elif (encoder == 6 and still_image and mode_toggle_Imaging):
        clearAllFlags()
        monitorStatus()
        mode_Camera = True
        still_image = False
        switchToCameraMenu()
        menu_ImagingList[0] = " Image   [Video]"
        lcd.set_cursor(0, 0)
        lcd.message(menu_ImagingList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Mode")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_CameraList[2]))
        with open("config.json") as config_file:
            config = json.load(config_file)
            config["camera"]["record_mode"] = False
            camera_mode = config["camera"]["record_mode"]
            config_file.close()
            config_file = open("config.json", "w")
            config_file.write(json.dumps(config, indent=4, sort_keys=True))
            config_file.close()
        encoder = 38
        print("Still Image: " + str(camera_mode))
        print("encoder: " + str(encoder))

    elif (encoder == 6 and not still_image and mode_toggle_Imaging):
        clearAllFlags()
        monitorStatus()
        mode_Camera = True
        still_image = True
        switchToCameraMenu()
        menu_ImagingList[0] = "[Image]   Video "
        lcd.set_cursor(0, 0)
        lcd.message(menu_ImagingList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Mode")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_CameraList[2]))
        with open("config.json") as config_file:
            config = json.load(config_file)
            config["camera"]["record_mode"] = True
            camera_mode = config["camera"]["record_mode"]
            config_file.close()
            config_file = open("config.json", "w")
            config_file.write(json.dumps(config, indent=4, sort_keys=True))
            config_file.close()
        encoder = 38
        print("Still Image: " + str(camera_mode))
        print("encoder: " + str(encoder))


    elif (encoder == 72 and mode_Preview and not preview_on and not monitor_on and not mode_Main):
        # clearAllFlags()
        preview_on = True
        print("Preview Before: " + str(mode_Preview))
        menu_PreviewList[0] = "VuCam: [ON] OFF "
        lcd.set_cursor(0, 0)
        lcd.message(menu_PreviewList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back To Main")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_MainList[4]))
        preview_on = True

        switchToMainMenuList(encode_Camera)
        previewCam_proc = subprocess.Popen(['python', '/home/pi/mammal_monitor/UI/previewCam.py'],
                                           stdout=subprocess.PIPE)
        currentStatus()
        print("Preview After: " + str(mode_Preview))
        print("Event Set: " + str(previewCameraEvent.isSet()))
        print("#11")

    elif (encoder == 72 and mode_Preview and preview_on and not monitor_on and not mode_Main):
        clearAllFlags()
        previewCam_proc.kill()
        menu_PreviewList[0] = "VuCam:  ON [OFF]"
        currentStatus()
        lcd.set_cursor(0, 0)
        lcd.message(menu_PreviewList[0])
        sleep(1)
        lcd.clear()
        lcd.message("Back to Config  ")
        sleep(1)
        lcd.clear()
        preview_on = False
        lcd.message(str(menu_MainList[4]))
        switchToMainMenuList(encode_Camera)
        print("Event Set: " + str(previewCameraEvent.isSet()))
        print("#12")

    elif (encoder == 72 and monitor_on):
        lcd.set_cursor(0, 0)
        lcd.message("Turn monitoring \n off to preview  ")
        sleep(2)
        lcd.clear()
        lcd.message("Back to Config ")
        sleep(1)
        lcd.clear()
        lcd.message(str(menu_MainList[6]))
        switchToMainMenuList(encode_Monitor)

    elif (encoder >= 80 and encoder <= menu_ResolutionTopRange - 1 and mode_Resolution and not monitor_on):

        try:
            if (encoder >= 80 and encoder <= menu_ResolutionTopRange - 2):
                with open('camera_config_test.json') as f:
                    camera_config = json.load(f)
                    encoderDiff = (encoder - menu_ResolutionLowRange)
                    newResolution = menu_cameraResolution[encoderDiff]
                    print("currentResolution: " + str(newResolution))
                    list_newResolution = newResolution.split("x")
                    print(list_newResolution)
                    newWidth = int(list_newResolution[0].strip())
                    print(type(newWidth))
                    newHeight = int(list_newResolution[1].strip())
                    print(newHeight)
                    camera_config['width'] = newWidth
                    camera_config['height'] = newHeight
                    if (newWidth == 640 or newWidth == 1280):
                        camera_config['framerate'] = 30
                    elif (newWidth == 1640):
                        camera_config['framerate'] = 40
                    else:
                        camera_config['framerate'] = 40
                    print(json.dumps(camera_config, indent=4, sort_keys=True))
                    print("Encoder: " + str(encoder))
                    f.close()
                    f = open('camera_config_test.json', 'w')
                    f.write(json.dumps(camera_config, indent=4, sort_keys=True))
                    f.close()

            lcd.clear()
            lcd.set_cursor(0, 0)
            lcd.message(menu_CameraList[1])
            mode_Resolution = False
            mode_Camera = True
            switchToCameraMenu()
            encoder = 37

        except ValueError:
            log = open("logfile_sys_argv.txt", "a+")
            log.write(dt.datetime.now().strftime("%m/%d/%Y %H:%M:%S: Log => "))
            log.write("currentResolution exception occurred")

    elif (encoder == 83 and mode_Resolution):

        try:
            lcd.clear()
            lcd.set_cursor(0, 0)
            lcd.message(menu_CameraList[1])
            mode_Resolution = False
            mode_Camera = True
            switchToCameraMenu()

        except ValueError:
            print(
                "Return to Previous Menu Error: Was not able to return to the resolution menu under camera configuration menu.")
            log = open("logfile_sys_argv.txt", "a+")
            log.write(dt.datetime.now().strftime("%m/%d/%Y %H:%M:%S: Log => "))
            log.write(
                "Return to Previous Menu Error: Was not able to return to the resolution menu under camera configuration menu.")
            log.close()

    elif (encoder == 42 and mode_Camera):
        clearAllFlags()
        lcd.set_cursor(0, 0)
        lcd.message(menu_MainList[4])
        mode_Camera = False
        switchToMainMenuList(encode_Camera)

    elif (mode_Display):

        if (encoder == 48 and mode_Display):
            clearAllFlags()
            lcd.set_cursor(0, 0)
            lcd.message(menu_MainList[5])
            mode_Display = False
            switchToMainMenuList(encode_Display)


# ============================================================
# === moveTextArrow() ===
# ============================================================
def moveTextArrow():
    global char_mode

    # print("Here I AM")
    lcd.set_cursor(arrowX, 2)
    lcd.write8(' ');
    arrowX = arrowX + bump[state]
    if (arrowX > 19):
        arrowX = 19
    if (arrowX < 0):
        arrowX = 0
    flipArrow = bin(0)
    flipArrow = flipArrow + arrow
    flipArrow <<= 1
    print(flipArrow, BIN)
    print(' ')
    arrow = (bump[state] > 0)
    flipArrow = flipArrow + arrow
    # flipArrow =+ 8;
    print(flipArrow, BIN)
    if (flipArrow == 1):
        arrowX -= 1
    if (flipArrow == 2):
        arrowX += 1
    lcd.set_cursor(arrowX, 2)
    lcd.write8(arrow, char_mode=True)


# ============================================================
# === showMenu()                                   ===
# ============================================================
def showMenuList(menu):
    global encoder
    global knobMax
    global knobMin

    lcd.message(menu[encoder - knobMin])
    print(encoder - knobMin)


#
##    if(type(menu) == dict):# and menu_registry['calibrate']):
##        scale.set_scale(seed['seed'])
##        units = round(scale.get_units(10),2)
##        print('Value: ' + str(seed) + ' Weight: ' + str(units) + '\r')
##        
##        lcd.set_cursor(0,0)
##        lcd.message(' <--Calibrate-->')
##        lcd.set_cursor(0,1)
##        lcd.message('  Weight: '+str(round(units,2)))
##    else:
##        print("Encoder: " + str(encoder))
##        print("from showMenuList: En: "+str(encoder)+" knobMin: "+str(knobMin)+" knobMax: "+str(knobMax))
##        print(mode_Main)
##        stopHere = len(menu[encoder-knobMin])
##        if (stopHere > 16):
##            stopHere = 16                             # truncate the text so it fits on one line
##        for i in range(1, stopHere):
##            lcd.set_cursor(0,0)
##            lcd.message(menu[encoder-knobMin])     # 10 represents the begin of encoder range "knobMin" ;put the text on the LCD

# ============================================================
# === showMainMenuList()                                   ===
# ============================================================
def showMainMenuList():
    global encoder
    global knobMax
    global knobMin
    global numItems_menu_MainList

    stopHere = len(str(menu_MainList[encoder - 10]))

    if (stopHere > 16):
        stopHere = 16  # truncate the text so it fits on one line
    for i in range(1, stopHere):
        lcd.set_cursor(0, 0)
        lcd.message(
            menu_MainList[encoder - 10])  # 10 represents the begin of encoder range "knobMin" ;put the text on the LCD


# ============================================================
# ===   switchToMainMenuList(encode_num)                             ===
# ============================================================
def switchToMainMenuList(encode_num):
    global mode_Main
    global knobMax
    global knobMin
    global encoder

    clearAllFlags()  # clear all flags before returning to Main Menu

    knobMax = numItems_menu_MainList + 10
    knobMin = 10
    print('encode_num: ' + str(encode_num))
    if (encode_num > 9 and encode_num < 17):
        encoder = encode_num
    else:
        encoder = 9
    mode_Main = True


# ============================================================
# ===  switchToBlueMenu()                                       ===
# ============================================================
def switchToBlueMenu():
    global knobMax
    global knobMin
    global encoder
    global mode_Blue
    global mode_Main

    mode_Main = False

    lcd.set_cursor(0, 0)
    lcd.message(menu_BlueList[0])
    mode_Blue = True
    knobMax = menu_BlueTopRange
    knobMin = menu_BlueLowRange
    encoder = menu_BlueLowRange


# ============================================================
# ===   switchToWifiMenu()                                 ===
# ============================================================
def switchToWifiMenu():
    global knobMax
    global knobMin
    global encoder
    global mode_Wifi
    global mode_Main

    mode_Main = False

    lcd.set_cursor(0, 0)
    lcd.message(menu_WifiList[0])
    mode_Wifi = True
    knobMax = menu_WifiTopRange
    knobMin = menu_WifiLowRange
    encoder = menu_WifiLowRange


# ============================================================
# ===   switchToImagingMenu()                              ===
# ============================================================
def switchToImagingMenu():
    global knobMax
    global knobMin
    global encoder
    global still_image
    global mode_toggle_Imaging
    global mode_Main

    mode_Main = False

    lcd.set_cursor(0, 0)
    lcd.message(menu_ImagingList[0])
    mode_toggle_Imaging = True
    knobMax = menu_ImagingTopRange
    knobMin = menu_ImagingLowRange
    encoder = menu_ImagingLowRange


# ============================================================
# ===   switchToScaleMenu()                                ===
# ============================================================
def switchToScaleMenu():
    global knobMax
    global knobMin
    global encoder
    global mode_Scale

    menu_ScaleTopRange = 24
    menu_ScaleLowRange = 20

    ##    lcd.clear()
    ##    lcd.message("Scale Config")
    ##    mode_Scale = True
    knobMax = menu_ScaleTopRange
    knobMin = menu_ScaleLowRange
    encoder = menu_ScaleLowRange
    return


# ============================================================
# ===   switchToResolutionMenu()                               ===
# ============================================================
def switchToResolutionMenu():
    global knobMax
    global knobMin
    global encoder

    knobMax = menu_ResolutionTopRange
    knobMin = menu_ResolutionLowRange
    encoder = menu_ResolutionLowRange
    return


# ============================================================
# ===   switchToFramerateMenu()                               ===
# ============================================================
def switchToFramerateMenu():
    global knobMax
    global knobMin
    global encoder

    knobMax = menu_FrameRateTopRange
    knobMin = menu_FrameRateLowRange
    encoder = menu_FrameRateLowRange
    return


# ============================================================
# ===   switchToCameraMenu()                               ===
# ============================================================
def switchToCameraMenu():
    global knobMax
    global knobMin
    global encoder
    global mode_Camera

    ##    lcd.clear()
    ##    lcd.message("Camera Config")
    ##    mode_Camera = True
    knobMax = menu_CameraTopRange
    knobMin = menu_CameraLowRange
    encoder = menu_CameraLowRange
    return


# ============================================================
# ===   switchToPreviewCamMenu()                               ===
# ============================================================
def switchToPreviewCamMenu():
    global mode_Main
    global mode_Preview
    global knobMax
    global knobMin
    global encoder

    mode_Main = False
    mode_Preview = True

    lcd.set_cursor(0, 0)
    lcd.message(menu_PreviewList[0])
    knobMax = menu_PreviewTopRange
    knobMin = menu_PreviewLowRange
    encoder = menu_PreviewLowRange
    return


# ============================================================
# ===   switchToDisplayMenu()                               ===
# ============================================================
def switchToDisplayMenu():
    global knobMax
    global knobMin
    global encoder
    global mode_Display

    ##    lcd.clear()
    ##    lcd.message("Display Info")
    ##    mode_Display = True
    knobMax = menu_DisplayTopRange
    knobMin = menu_DisplayLowRange
    encoder = menu_DisplayLowRange
    return


# ============================================================
# ===   switchToMonitorMenu()                               ===
# ============================================================
def switchToMonitorMenu():
    global knobMax
    global knobMin
    global encoder
    global mode_Monitor
    global mode_Main

    mode_Main = False

    lcd.set_cursor(0, 0)
    lcd.message(menu_MonitorList[0])
    mode_Monitor = True
    knobMax = menu_MonitorTopRange
    knobMin = menu_MonitorLowRange
    encoder = menu_MonitorLowRange


# ============================================================
# ===   switchToSSIDMenu()                               ===
# ============================================================   

def switchToSSIDMenu(length):
    global knobMax
    global knobMin
    global encoder
    global mode_SSID

    lcd.set_cursor(0, 0)
    lcd.message(menu_SSIDList[0])

    knobMax = menu_SSIDTopRange + length
    knobMin = menu_SSIDLowRange
    encoder = menu_SSIDLowRange
    print(knobMax)
    print(knobMin)
    print(encoder)
    return


# ============================================================
# ===   switchToCalibrateMenu()                               ===
# ============================================================   

def switchToCalibrateMenu():
    global knobMax
    global knobMin
    global encoder
    global mode_Calibrate

    knobMax = menu_CalibrateTopRange
    knobMin = menu_CalibrateLowRange
    encoder = menu_CalibrateLowRange
    print(knobMax)
    print(knobMin)
    print(encoder)
    return


# ============================================================
# ===   switchToTareMenu()                               ===
# ============================================================   

def switchToTareMenu():
    global knobMax
    global knobMin
    global encoder
    global mode_Tare

    knobMax = menu_TareTopRange
    knobMin = menu_TareLowRange
    encoder = menu_TareLowRange
    print(knobMax)
    print(knobMin)
    print(encoder)
    return


# ============================================================
# ===   switchToUnitsMenu()                               ===
# ============================================================ 
def switchToUnitsMenu():
    global knobMax
    global knobMin
    global encoder
    global mode_Units
    global mode_Main

    mode_Main = False
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.message(menu_UnitsList[0])
    mode_Units = True
    knobMax = menu_UnitsTopRange
    knobMin = menu_UnitsLowRange
    encoder = menu_UnitsLowRange


# ============================================================
# ===   executeMainMenuItems()                             ===
# ============================================================
def executeMainMenuItems():  # Works for either List or Serial methods
    return


# ============================================================
# ===   executeStoggleBlue()                                       ===
# ============================================================
def executetoggleBlue():
    return


# ============================================================
# ===   executetoggleWifi()                                       ===
# ============================================================
def executetoggleWifi():
    return


# ============================================================
# ===   executeScaleMenuItems()                                       ===
# ============================================================
def executeScaleMenuItems():
    return


# ============================================================
# ===   executeCameraMenuItems()                           ===
# ============================================================
def executeCameraMenuItems():
    return


# ============================================================
# ===   executeDisplayMenuItems()                          ===
# ============================================================
def executeDisplayMenuItems():
    return


# ============================================================
# ===   executeMonitoringMenuItems()                       ===
# ============================================================
def executeMonitoringMenuItems():
    return


# =============================================================
# === backToMain()                                     ===
# ============================================================
def backToMain():
    global menu_MainList
    global scaleConfig
    global encoder


# ============================================================
# === led_mode_debug()                                     ===
# ============================================================
def led_mode_debug():
    global mode_Blue
    global idleMode
    global cmdMode
    global led_Blue
    global led_Wifi

    while (mode_Blue and led_Blue):

        i = 0
        for i in range(0, 4):
            print(i)
            if (i <= 2):
                GPIO.output(PIN_16, GPIO.HIGH)
                sleep(0.1)
                GPIO.output(PIN_16, GPIO.LOW)
                sleep(0.1)
                i += 1
            else:
                led_Blue = False
                break

    while (wifiMode == True):  # idleMode Green
        GPIO.output(PIN_20, GPIO.HIGH)
        sleep(1)
        GPIO.output(PIN_20, GPIO.LOW)
        sleep(1)

    while (cmdMode == True):  # cmdMode Red
        GPIO.output(PIN_21, GPIO.HIGH)
        sleep(2)
        GPIO.output(PIN_21, GPIO.LOW)
        sleep(2)


# ============================================================
# === currentStatus()                                      ===
# ============================================================
def monitorStatus():
    global mode_Main
    global mode_Monitor
    global mode_Preview
    global monitor_on
    global preview_on

    print("Main Mode: " + str(mode_Main))
    print("Monitor Mode: " + str(mode_Monitor))
    print("Preview Mode: " + str(mode_Preview))
    print("Monitor On: " + str(monitor_on))
    print("Preview On: " + str(preview_on))


# ============================================================
# === currentStatus()                                      ===
# ============================================================
def currentStatus():
    global click_Single
    global mode_Main
    global mode_Blue
    global mode_Wifi
    global mode_Scale
    global mode_Camera
    global mode_Preview
    global mode_Display
    global mode_Monitor
    global monitor_on
    global preview_on
    global mode_SSID
    global wifi_on
    global blue_on
    global ssid_selection_made

    print("click_Single: " + str(click_Single))
    print("Main Mode: " + str(mode_Main))
    print("Bluetooth Mode: " + str(mode_Blue))
    print("Wifi Mode: " + str(mode_Wifi))
    print("SSID Mode: " + str(mode_SSID))
    print("ssid_selection_made: " + str(ssid_selection_made))
    print("Scale Mode: " + str(mode_Scale))
    print("Camera Mode: " + str(mode_Camera))
    print("Display Mode: " + str(mode_Display))
    print("Monitor Mode: " + str(mode_Monitor))
    print("Preview Mode: " + str(mode_Preview))
    print("Monitor On: " + str(monitor_on))
    print("Wifi On: " + str(wifi_on))
    print("Bluetooth On: " + str(blue_on))
    print("Preview On: " + str(preview_on))


# ============================================================
# === poll_buttonPress()                                      ===
# ============================================================
def poll_buttonPress():
    global click_Single
    global click_Double

    global clickPin
    print("polling button Press")

    first_Click = False
    first_Click = not GPIO.input(clickPin)
    if (first_Click):
        while (not GPIO.input(clickPin)):
            return
        sleep(0.2)
        for i in range(0, 1000):
            i += i
            if (not GPIO.input(clickPin)):
                click_Double = True
                click_Single = False
                print("Button Double Clicked")
        click_Single = True

    if (click_Single):

        if (encoder == encode_Blue and not mode_Blue):
            switchToBlueMenu()
            click_Single = False
            return

        elif (encoder == encode_Blue and mode_Blue):
            switchToBlueMenu()
            click_Single = False
            return

        elif (encoder == encode_Wifi and not mode_Wifi):
            toggle_Wifi()
            click_Single = False
            return

        elif (encoder == encode_Scale and not mode_Scale):
            switchToScaleMenu()
            click_Single = False
            return

        elif (encoder == encode_Camera and not mode_Camera):
            switchToCameraMenu()
            click_Single = False
            return

        elif (encoder == encode_Display and not mode_Display):
            switchToDisplayMenu()
            click_Single = False
            return

        elif (encoder == encode_Monitor and not mode_Monitor):
            switchToMonitorMenu()
            click_Single = False
            return
        else:
            switchToMainMenu()
            click_Single = False
            return

    if (mode_Blue):
        executetoggleBlue()
        return


# ============================================================
# ===  main()                                              ===
# ============================================================
def main():
    GPIO.add_event_detect(17, GPIO.RISING, callback=knobTurned, bouncetime=5)
    GPIO.add_event_detect(27, GPIO.FALLING, callback=knobPressed, bouncetime=200)

    raw_input("Program Running...")
    GPIO.cleanup()


if __name__ == '__main__':
    main()

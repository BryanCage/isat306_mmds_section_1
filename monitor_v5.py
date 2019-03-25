#!/usr/bin/env python
# encoding: utf-8
# -*- coding: utf-8 -*-
# title           :mammal_monitor.py
# description     :This program is firmware for a device used to passively monitor small mammals that enter the compartment (trap). A scale
#				  the scale is used to record weight and trigger a RPi Noir camera (IR) to record images during monitoring. This
#                 research is being conducted in part by students taking mammalogy under Dr. Katrina Gobetz at James Madison University.
# author          :Bryan A. Cage
# date            :09/28/2017
# version         :1.0
# usage           :python mammal_monitor.py
# notes           :
# python_version  :2.7.6
# =======================================================================

# IMPORTING MODULES
from datetime import timedelta
from dateutil import parser
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from mysql.connector import errorcode
from mysql.connector import (connection)
from picamera import PiCamera
from threading import Timer
from transitions import Machine
from HX711.hx711 import *

import calendar
import csv
import datetime
import RPi.GPIO as GPIO
import json
import os
import mimetypes
import mysql.connector
import numpy as np
import picamera
import Queue
import re
import serial
import smtplib
import struct
import subprocess
import sys
import threading
import time
import datetime as dt

# ====== Format data structure for datetime ==================================================

#  			%d is the day number
#			%m is the month number
#			%b is the month abbreviation
#			%y is the year last two digits
#			%Y is the all year
#			%x format = 09/30/13
#			%X format = 07:06:05

# =============================================================================================

##ser = serial.Serial('/dev/ttyAMA0', baudrate=9600,
##                    parity=serial.PARITY_NONE,
##                    stopbits=serial.STOPBITS_ONE,
##                    bytesize=serial.EIGHTBITS)

weight = 0
global imaging
global total_images
global record_data_enable
global streaming_weight_enable
global record1

running = True
recording = False

# Strings for csv file
filename = ""
csv_filename = ""
h264_filename = ""
locomotion = ""

# ~ # Initialize PiCamera
# ~ camera = PiCamera(resolution = (640, 480), framerate = 50)

monitor_bool_registry = {'monitor_on': False}
reg = {'compared_weight': 0, 'record_data_enable': True, 'streaming_weight_enable': True}

compared_weight = 0
record_data_enable = True
streaming_weight_enable = True
lightPin = 22
RCpin = 25
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.OUT)
GPIO.setup(lightPin, GPIO.OUT)

# ===============================================
# ===            Instantiate SCALE            ===
# ===============================================

seed = {'seed': -2322.95}
DT = 23
SCK = 24

scale = HX711(23, 24, 128)
scale.set_scale(seed['seed'])
scale.tare()


# =============================
#     CLASS DEFINITIONS
# =============================

class Record(object):
    # Define some states.
    states = ['streamingWeight', 'writing', 'imaging']

    def __init__(self, name):
        # Record Name.
        self.name = name

        # Number of images
        self.total_images = 0

        # Initialize the state machine
        self.machine = Machine(model=self, states=Record.states, initial='streamingWeight')

        # Add some transitions. We could also define these using a static list of
        # dictionaries, as we did with states above, and then pass the list to
        # the Machine initializer as the transitions= argument.

        # Threshold weight triggers recording data weight to file and imaging animal.
        self.machine.add_transition(trigger='scale_triggered', source='streamingWeight', dest='writing')

        # imaging back to stream the incoming weight from scale.
        self.machine.add_transition('imaging', 'writing', 'streamingWeight')

        self.machine.add_transition('writing', 'streamingWeight', 'imaging')

        self.machine.add_transition('streamingWeight', 'imaging', 'writing')

        self.machine.add_transition('to_imaging', 'writing', 'imaging',
                                    before='update_num_images')

        self.machine.add_transition('to_streamingWeight', '*', 'streamingWeight')

    def update_num_images(self):
        """ Number images taken for this record. """
        self.total_images += 1


# ===========================================
#     END CLASS DEFINITION
# ===========================================


# ==========================================
#     BEGINNING OF FUNCTION DEFINITIONS
# ==========================================

def parseWeight(input):
    first_split = input.split(',')
    # print(first_split[0])
    data = np.fromstring(first_split[0], dtype=float, sep=' ')
    data = float(data)
    return data


def days_hours_minutes(td):
    return td.days, td.seconds // 3600, (td.seconds // 60) % 60, td.seconds


def correctDigits(value):
    if (value < 10):
        value = "0" + str(value)
    return value


def writeData(value, units):  # Writes 'weight', 'Timestamp', 'Picture Name' to "weight_data.json" file

    dt = datetime.datetime.today()
    month = correctDigits(dt.month)
    day = correctDigits(dt.day)
    year = str(dt.year)
    hour = str(correctDigits(dt.hour))
    minute = str(correctDigits(dt.minute))
    second = str(correctDigits(dt.second))
    with open("config.json") as config_file:
        config = json.load(config_file)
        record_mode = config["camera"]["record_mode"]
        config_file.close()
    print("#11: " + str(record_mode))
    weight_data = open("weight_data.json", 'a+')
    weight_data.seek(0)
    weight_data.seek(0, 2)
    size = weight_data.tell()
    weight_data.truncate(size - 3)
    if config["camera"]["record_mode"]:
        weight_data.write(',\n')
        weight_data.write('   {\n')
        weight_data.write('      "Weight":"' + str(value) + '",\n')
        weight_data.write('      "Unit":"' + str(units) + '",\n')
        weight_data.write('      "Timestamp":"' + str(month) + '/' + str(day) + '/' + str(year) + ' ' + str(hour) + ':' + str(minute) + ':' + str(second) + '",\n')
        weight_data.write('      "Picture":"' + str(month) + str(day) + str(year) + str(hour) + str(minute) + str(second) + '.jpg' + '"\n')
        weight_data.write('   }\n]')
        weight_data.write('}')
        weight_data.close()
    elif not config["camera"]["record_mode"]:
        weight_data.write(',\n')
        weight_data.write('   {\n')
        weight_data.write('      "Weight":"' + str(value) + '",\n')
        weight_data.write('      "Unit":"' + str(units) + '",\n')
        weight_data.write('      "Timestamp":"' + str(month) + '/' + str(day) + '/' + str(year) + ' ' + str(hour) + ':' + str(minute) + ':' + str(second) + '",\n')
        weight_data.write('      "Video":"' + str(month) + str(day) + str(year) + str(hour) + str(minute) + str(second) + '.mp4' + '"\n')
        weight_data.write('   }\n]')
        weight_data.write('}')
        weight_data.close()


def takePicture():  # Captures an image and sets its name to the current date/time and saves in root directory

    dt = datetime.datetime.today()
    month = str(correctDigits(dt.month))
    day = str(correctDigits(dt.day))
    year = str(dt.year)
    hour = str(correctDigits(dt.hour))
    minute = str(correctDigits(dt.minute))
    second = str(correctDigits(dt.second))

    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.start_preview()
        time.sleep(2)
        picname = month + day + year + hour + minute + second
        camera.capture('%s.jpg' % picname)


def takeVideo(duration):  # Captures an video and sets its name to the current date/time and saves in root directory

    global h264_filename
    global recording

    recording = True
    scale.set_scale(seed['seed'])
    wgt = round(scale.get_units(10), 2)
    dt1 = datetime.datetime.today()
    month = str(correctDigits(dt1.month))
    day = str(correctDigits(dt1.day))
    year = str(dt1.year)
    hour = str(correctDigits(dt1.hour))
    minute = str(correctDigits(dt1.minute))
    second = str(correctDigits(dt1.second))
    picname = month + day + year + hour + minute + second
    camera = PiCamera(resolution=(640, 480), framerate=30)
    camera.start_preview(fullscreen=False, window=(20, 20, 640, 480))
    displayed_timeFormat = '%m/%d/%Y %H:%M:%S.%f'
    file_timeFormat = '%m%d%Y %H%M%S'

    filename = dt.datetime.now().strftime("%m%d%y%H%M%S")
    h264_filename = picname + ".h264"
    camera.start_recording(h264_filename)
    start = dt.datetime.now()
    while (dt.datetime.now() - start).seconds < duration:
        camera.annotate_text = dt.datetime.now().strftime('%m/%d/%Y %H:%M:%S.%f')
        camera.wait_recording(0.2)
    camera.stop_recording()
    camera.stop_preview()
    os.system("MP4Box -add " + h264_filename + " -fps 30 /home/pi/mammal_monitor/UI/" + picname + ".mp4")
    os.system("rm " + picname + ".h264")


video_thread = threading.Thread(target=takeVideo, name='Video', \
                                args=(5, 'Video'))


# ===========================================
# === New Functions ===
# ===========================================

def compareWeights():
    global weight
    global compared_weight
    weight = 0
    ser.flushInput()
    if (ser.inWaiting > 0):
        rawWeightStream = ser.readline()
        # rawWeightStream2 = ser.readline()
        weight = parseWeight(rawWeightStream)
        while (abs(weight - compared_weight) < 0.5):
            break

        # weight2 = parseWeight(rawWeightStream2)
        print("Weight from compareWeight: " + str(weight))
        return (weight, compared_weight)


def threshold_detection(threshold):
    global weight
    weight = 0
    weight = round(scale.get_units(10), 2)
    while (abs(round(scale.get_units(10), 2) - compared_weight < 0.5)):
        break
    weight_Diff = weight - compared_weight
    print("Weight Diff: " + str(weight_Diff))
    if (weight_Diff > threshold):
        return True
    else:
        return False


def threshold_detection_old((a, b), threshold):
    print("Weight from threshold_detection: " + str(weight))
    weightTuple = (a, b)

    weightDiff = weightTuple[0] - weightTuple[1]
    print("Weight Diff: " + str(weightDiff))
    if (weightDiff > threshold):
        return True
    else:
        return False


def currentUnit():
    array = []
    with open('config.json') as config_file:
        config = json.load(config_file)
        config_file.close()
        for key in config['scale']['units']:
            if (config['scale']['units'][key] == True):
                array.append(key)
        if (len(array) == 0 or len(array) >= 2):
            log = open("logfile.txt", "a+")
            log.write(dt.datetime.now().strftime("%m%d%Y %H:%M:%S: Log => "))
            log.write("Check units.json for error. Resetting units.json")
            log.close()
            config['scale']['units']['g'] = True
            config['scale']['units']['lbs'] = False
            config['scale']['units']['oz'] = False
            config_file.close()
            config_file = open('config.json', 'w')
            config_file.write(json.dumps(config, indent=4, sort_keys=True))
            config_file.close()
            default_unit = "g"
            return default_unit
        else:
            config_file.close()
            print("Array zero: " + str(array[0]))
            return array[0]


def convertUnits(wgt, unit):
    if (unit == "g"):
        print(str(wgt) + " g")
        return wgt
    elif (unit == "oz"):
        convertedWeight = round(wgt * 0.035274, 2)
        print((str(convertedWeight) + " oz"))
        return convertedWeight

# ==============================================
#     recordVideo (video)
# ==============================================
def recordVideo(duration):
    global recording
    global filename
    global csv_filename
    global h264_filename
    global record_data_enable
    global weight
    # Set timestamp format
    timeFormat = '%m/%d/%Y %H:%M:%S'

    with open('config.json') as config_file:
        config = json.load(config_file)
        config_file.close()
    unit = currentUnit()
    print(config["camera"]["width"])
    print(config["camera"]["height"])
    print(config["camera"]["framerate"])
    recording = True
    while recording:
        with picamera.PiCamera(resolution=(config["camera"]['width'], config["camera"]['height']),
                               framerate=config["camera"]['framerate']) as camera:  # 1296, 730
            camera.start_preview()
            filename = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            h264_filename = "VID/" + filename + ".h264"
            camera.start_recording(h264_filename)
            if(not currentUnit == "g"):
                for i in range(duration):
                    for j in range(1):
                        start = time.time()
                        weight = updateWeight()
                        converted_weight = convertUnits(weight, unit)
                        duration_updateWeight = time.time() - start
                        camera.annotate_text_size = config["camera"]['annotate_text_size']
                        camera.annotate_text = dt.datetime.now().strftime(timeFormat) + " wgt: " + str(converted_weight) + " " + unit
                        time.sleep(0.2)
                    time.sleep(1)
            else:
                for i in range(duration):
                    for j in range(1):
                        start = time.time()
                        weight = updateWeight()
                        duration_updateWeight = time.time() - start
                        camera.annotate_text_size = config["camera"]['annotate_text_size']
                        camera.annotate_text = dt.datetime.now().strftime(timeFormat) + " wgt: " + str(weight) + " " + unit
                        time.sleep(0.2)
                    time.sleep(1)
            camera.stop_recording()
            camera.stop_preview()
            camera.annotate_text = ""
            os.system("MP4Box -add " + h264_filename + " -fps 30 VID/" + filename + ".mp4")
            os.system("rm VID/*.h264")
        recording = False
    record_data_enable = False
    camera.close()

def recordData():
    count = 0
    num_pics = 1
    duration = 5
    global record_data_enable
    global record1
    record1 = Record("New Record")
    # ================================================================
    # Retrieve camera status from file
    # ================================================================
    with open("config.json") as config_file:
        config = json.load(config_file)
        config_file.close()
    if config["camera"]["record_mode"]:
        for x in range(0, num_pics):
            current_unit = currentUnit()
            weight = round(scale.get_units(10), 2)
            print("Current Unit: " + str(current_unit))
            print("Weight: " + str(weight))
            if (not current_unit == "g"):
                converted_weight = convertUnits(weight, current_unit)
                print(converted_weight)
                record1.scale_triggered()
                print(record1.state)
                writeData(converted_weight, current_unit)
                print("Weight was written to .json file: " + str(weight))
                record1.to_imaging()
                print(record1.state)
                takePicture()
                print("Image Acquired!")
                record1.to_streamingWeight()
                time.sleep(1)
                count += 1
                print("Count equals: " + str(count))
            else:
                record1.scale_triggered()
                print(record1.state)
                writeData(weight, current_unit)
                print("Weight was written to .json file: " + str(weight))
                record1.to_imaging()
                print(record1.state)
                takePicture()
                print("Image Acquired!")
                record1.to_streamingWeight()
                time.sleep(1)
                count += 1
                print("Count equals: " + str(count))
    # ================================================================
    elif not config["camera"]["record_mode"]:
        current_unit = currentUnit()
        weight = round(scale.get_units(10), 2)
        print("Current Unit: " + str(current_unit))
        print("Weight: " + str(weight))
        if (not current_unit == "g"):
            converted_weight = convertUnits(weight, current_unit)
            print(converted_weight)
            record1.scale_triggered()
            print(record1.state)
            writeData(converted_weight, current_unit)
            print("Weight was written to .json file: " + str(weight))
            record1.to_imaging()
            print(record1.state)
            recordVideo(5)
            print("Image Acquired!")
            record1.to_streamingWeight()
            time.sleep(1)
            count += 1
            print("Count equals: " + str(count))
        else:
            record1.scale_triggered()
            print(record1.state)
            writeData(weight, current_unit)
            print("Weight was written to .json file: " + str(weight))
            record1.to_imaging()
            print(record1.state)
            recordVideo(5)
            print("Image Acquired!")
            record1.to_streamingWeight()
            time.sleep(1)
            count += 1
            print("Count equals: " + str(count))
    record_data_enable = False


def recordDataVideo(duration):
    count = 0
    global record_data_enable
    global record1
    record1 = Record("New Record")
    weight = round(scale.get_units(10), 2)
    print(weight)
    record1.scale_triggered()
    print(record1.state)
    writeData(weight)
    print("Weight was written to .json file: " + str(weight))
    record1.to_imaging()
    print(record1.state)

    print("Video Captured!")
    record1.to_streamingWeight()
    time.sleep(1)
    count += 1
    print("Count equals: " + str(count))
    record_data_enable = False


def getWeight():
    scale.set_scale(seed['seed'])
    wgt = round(scale.get_units(10), 2)
    print('Wgt: ' + str(wgt))


##    if(ser.inWaiting > 0):
##        rawWeightStream = ser.readline()
##        weight = parseWeight(rawWeightStream)
##        return (weight)

def streamWeight():
    if (ser.inWaiting > 0):
        rawWeightStream = ser.readline()
        weight = parseWeight(rawWeightStream)
        print(weight)


def threshold_callback_response():  # if threshold(presence/no presence) - presence=recordData() or no presence=streamWeight()
    if GPIO.input(21):
        recordData()
        time.sleep(1)
    else:
        print(streamWeight())


def disable_data_recording_timer(delay):
    global record_data_enable

    for x in range(0, delay):
        print("Recording Disabled: " + str(x))
        time.sleep(1)
    GPIO.output(21, GPIO.LOW)
    record_data_enable = True


def RCtime(RCpin):
    reading = 0
    GPIO.setup(RCpin, GPIO.OUT)
    GPIO.output(RCpin, GPIO.LOW)
    time.sleep(0.1)

    GPIO.setup(RCpin, GPIO.IN)
    # This takes about 1 millisecond per loop cycle
    while (GPIO.input(RCpin) == GPIO.LOW):
        reading += 1
    return reading


def picPreview():  # Use to determine if IR lights are coming ON

    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.start_preview()
        time.sleep(2)
        camera.stop_preview()
        camera.close()


def turn_IR_ON():
    GPIO.output(lightPin, GPIO.HIGH)
    time.sleep(0.1)


def turn_IR_OFF():
    GPIO.output(lightPin, GPIO.LOW)
    time.sleep(0.1)


def streamLightSensorReading():
    light_read = RCtime(RCpin)
    print("Light Sensor: " + str(light_read))
    return light_read


def evaluateLighting():
    GPIO.output(lightPin, GPIO.LOW)
    light_read = RCtime(RCpin)
    print("Light Read: " + str(light_read))
    if (light_read > 2000):
        turn_IR_ON()
        print("Turning IR lights ON!")
    else:
        print("Turning IR lights OFF!")
        turn_IR_OFF()



# ==============================================
#     updateWeight
# ==============================================
def updateWeight():
    global weight

    while (1):
        weight = round(scale.get_units(10), 2)
        return weight

# ==============================================
#     start_record
# ==============================================
def start_record():
    global recording
    global filename
    global csv_filename
    global h264_filename

    recording = True
    filename = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_filename = "CSV/" + filename + ".csv"
    with open(csv_filename, "a+") as file:
        file.write("Locomotion,Start Time,End Time\n")
    h264_filename = "VID/*.h264"
    camera.start_recording(h264_filename)


# ==============================================
#     stop_record
# ==============================================
def stop_record():
    global recording
    global filename
    global h264_filename

    recording = False
    camera.stop_recording()
    camera.annotate_text = ""
    os.system("MP4Box -add " + h264_filename + " -fps 50 VID/" + filename + ".mp4")
    os.system("rm " + h264_filename)

# ====================================================
#     monitor_stream_w_subprocess_video (video)
# ====================================================
def monitor_stream_w_subprocess_video():
    record = Record("NewRecord")
    GPIO.output(21, GPIO.LOW)  # Initialize GPIO.output(21) to LOW
    global monitor_on
    monitor_on = True
    while (1):
        try:
            if (GPIO.input(21) and (record_data_enable)):  # Check whether pin 21 is high (threshold detected send pin 21 HIGH) and whether record_data_enable is True/False
                print('#1 video')
                evaluateLighting()
                recordVideo(5)  # parameter is the num_pics to take during recordData()						# records data; args = number of images/weights to be recorded at 1 Hz

            elif (GPIO.input(21) and (record_data_enable == False)):  # setting record_data_enable to False as the last step in recordData() allows a timer to be set which disables the scale from triggering a new recordData() cycle
                print('#2 video')
                disable_data_recording_timer(3)  # disables recordData() function; args = number of seconds to disable recordData()

            else:
                if (threshold_detection(2)):  # threshold_detection() compares the difference of two streaming weights taken 1 second apart; if the difference is greater than the threshold argument GPIO 21 is triggered HIGH
                    GPIO.output(21, GPIO.HIGH)
                else:
                    print('#3 video')
                    scale.set_scale(seed['seed'])
                    wgt = round(scale.get_units(10), 2)
                    print('Wgt: ' + str(wgt))
        except KeyboardInterrupt:
            GPIO.cleanup()  # ensure a clean exit when "Command C" is executed to leave program



# ==============================================
#     monitor_stream_w_subprocess (still images)
# ==============================================
def monitor_stream_w_subprocess():
    record1 = Record("NewRecord")  # Create new Finite State Machine for transitioning between data acquisiton states (i.e. 'writing', 'imaging', 'streamingWeights')
    GPIO.output(21, GPIO.LOW)  # Initialize GPIO.output(21) to LOW
    global monitor_on
    monitor_on = True
    while (1):
        try:
            if (GPIO.input(21) and (record_data_enable)):  # Check whether pin 21 is high (threshold detected send pin 21 HIGH) and whether record_data_enable is True/False
                print('#1 still')
                evaluateLighting()
                recordData(1)  # parameter is the num_pics to take during recordData()						# records data; args = number of images/weights to be recorded at 1 Hz

            elif (GPIO.input(21) and (record_data_enable == False)):  # setting record_data_enable to False as the last step in recordData() allows a timer to be set which disables the scale from triggering a new recordData() cycle
                print('#2 still')
                disable_data_recording_timer(3)  # disables recordData() function; args = number of seconds to disable recordData()

            else:
                if (threshold_detection(2)):  # threshold_detection() compares the difference of two streaming weights taken 1 second apart; if the difference is greater than the threshold argument GPIO 21 is triggered HIGH
                    GPIO.output(21, GPIO.HIGH)
                else:
                    print('#3 still')
                    scale.set_scale(seed['seed'])
                    wgt = round(scale.get_units(10), 2)
                    print('Wgt: ' + str(wgt))
        except KeyboardInterrupt:
            GPIO.cleanup()  # ensure a clean exit when "Command C" is executed to leave program


# ==============================================
#     monitor_stream
# ==============================================
def monitor_stream():
    record1 = Record("NewRecord")  # Create new Finite State Machine for transitioning between data acquisiton states (i.e. 'writing', 'imaging', 'streamingWeights')
    GPIO.output(21, GPIO.LOW)  # Initialize GPIO.output(21) to LOW
    global monitor_on
    monitor_on = True
    while (1):
        try:
            if (GPIO.input(21) and (record_data_enable)):  # Check whether pin 21 is high (threshold detected send pin 21 HIGH) and whether record_data_enable is True/False
                print('#1 still')
                evaluateLighting()
                recordData()
            elif (GPIO.input(21) and (record_data_enable == False)):  # setting record_data_enable to False as the last step in recordData() allows a timer to be set which disables the scale from triggering a new recordData() cycle
                print('#2 still')
                disable_data_recording_timer(3)  # disables recordData() function; args = number of seconds to disable recordData()

            else:
                if (threshold_detection(2)):  # threshold_detection() compares the difference of two streaming weights taken 1 second apart; if the difference is greater than the threshold argument GPIO 21 is triggered HIGH
                    GPIO.output(21, GPIO.HIGH)
                else:
                    print('#3 still')
                    scale.set_scale(seed['seed'])
                    wgt = round(scale.get_units(10), 2)
                    print('Wgt: ' + str(wgt))
        except KeyboardInterrupt:
            GPIO.cleanup()  # ensure a clean exit when "Command C" is executed to leave program

# ==========================================
#     END OF FUNCTION DEFINITIONS
# ==========================================


# ============================================================
# ===  main()                                              ===
# ============================================================
def main():
    # print("Len sys.argv: " + str(len(sys.argv)))
    # try:
    #     if (len(sys.argv) == 1):
    #         monitor_stream_w_subprocess()
    #     elif (len(sys.argv) == 2):
    #         still_image = sys.argv[1]
    #         if (still_image.lower() == 'true'):
    #             print("sys.argb true #2")
    #             still_image = True
    #         elif (still_image.lower() == 'false'):
    #             print("sys.argv false #3")
    #             still_image = False
    #         else:
    #             log = open("logfile_sys_argv.txt", "a+")
    #             log.write(dt.datetime.now().strftime("%m/%d/%Y %H:%M:%S: Log => "))
    #             log.write("System Argument: (" + str(sys.argv[1] + ") not boolean value. Exited Program\n"))
    #             log.close()
    #             sys.exit()
    #         print(type(still_image))
    #         print(still_image)
    #         if (still_image == True):
    #             print("Image: True #4")
    #             log = open("logfile_sys_argv.txt", "a+")
    #             log.write(dt.datetime.now().strftime("%m/%d/%Y %H:%M:%S: Log => "))
    #             log.write("System Argument: " + str(sys.argv[1] + " => Still Image Capture Enabled.\n"))
    #             log.close()
    #             monitor_stream_w_subprocess()
    #         elif (not still_image):
    #             print("Image: False #5")
    #             log = open("logfile_sys_argv.txt", "a+")
    #             log.write(dt.datetime.now().strftime("%m/%d/%Y %H:%M:%S: Log => "))
    #             log.write("System Argument: " + str(sys.argv[1]) + " => Video Capture Enabled.\n")
    #             log.close()
    #             monitor_stream_w_subprocess_video()
    #         else:
    #             log = open("logfile_sys_argv.txt", "a+")
    #             log.write(dt.datetime.now().strftime("%m/%d/%Y %H:%M:%S: Log => "))
    #             log.write("Else Condition Triggered: Sys Arg = " + str(sys.argv[1]) + "\n")
    #             log.close()
    #     else:
    #         log = open("logfile_sys_argv.txt", "a+")
    #         log.write(dt.datetime.now().strftime("%m/%d/%Y %H:%M:%S: Log => "))
    #         log.write("Too many argv arguments provided.\n")
    #         log.close()
    #         sys.exit(0)
    #
    # except ValueError:
    #     print("Error: #6")
    #     log = open("logfile_sys_argv.txt", "a+")
    #     log.write(dt.datetime.now().strftime("%m/%d/%Y %H:%M:%S: Log => "))
    #     log.write("Too few or too many argv arguments\n")
    #     log.close()
    #     monitor_stream_w_subprocess()
    try:
        monitor_stream()
    except ValueError:
        print("Could not start monitoring stream!")
        log = open("error_logfile", "a+")
        log.write(dt.datetime.now().strftime("%m/%d/%Y %H:%M:%S: Log => "))
        log.write("Could not start monitoring stream!")
        log.close()



if __name__ == '__main__':
    main()

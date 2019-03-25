# LemurCam, JMU IoT Fall 2019
# Bryan Cage, Victoria Guadin, Andrew Kirsch, Ryan Williams

import datetime as dt
import os
from tkinter import *
from tkinter import messagebox
from picamera import PiCamera

# Initialize simple button GUI
root = Tk()
root.title("LemurCam")
w = root.winfo_screenwidth() / 2
h = root.winfo_screenheight() / 2
root.geometry("+%d+%d" % (w, h))

# Initialize PiCamera
camera = PiCamera(resolution = (640, 480), framerate = 50)
camera.start_preview(fullscreen=False, window=(0, 0, 640, 480))

# Set timestamp format
timeFormat = '%Y-%m-%d %H:%M:%S.%f'

# Initialize boolean values
recording = False
running = True
hopping = False
leaping = False

# Strings for csv file
filename = ""
csv_filename = ""
h264_filename = ""
locomotion = ""

# Start recoding on PiCamera
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
    h264_filename = "VID/" + filename + ".h264"
    camera.start_recording(h264_filename)

# Stop recording on PiCamera
def stop_record():
    global recording
    global filename
    global h264_filename
    
    recording = False
    camera.stop_recording()
    camera.annotate_text = ""
    os.system("MP4Box -add " + h264_filename + " -fps 50 VID/" + filename + ".mp4")
    os.system("rm " + h264_filename)

# Create timestamps for lemur locomotion events (stored in CSV file)
def key_press(event):
    global hopping
    global leaping
    global recording
    global csv_filename
    global locomotion
    
    if recording:
        if event.char == '1':
            if hopping:
                locomotion += dt.datetime.now().strftime(timeFormat) + "\n"
                with open(csv_filename, "a") as file:
                    file.write(locomotion)
                locomotion = ""
                hopping = False
            elif leaping:
                locomotion += dt.datetime.now().strftime(timeFormat) + "\n"
                with open(csv_filename, "a") as file:
                    file.write(locomotion)
                locomotion = "HOPPING," + dt.datetime.now().strftime(timeFormat) + ","
                leaping = False
                hopping = True
            else:
                locomotion = "HOPPING," + dt.datetime.now().strftime(timeFormat) + ","
                hopping = True
        elif event.char == '2':
            if leaping:
                locomotion += dt.datetime.now().strftime(timeFormat) + "\n"
                with open(csv_filename, "a") as file:
                    file.write(locomotion)
                locomotion = ""
                leaping = False
            elif hopping:
                locomotion += dt.datetime.now().strftime(timeFormat) + "\n"
                with open(csv_filename, "a") as file:
                    file.write(locomotion)
                locomotion = "LEAPING," + dt.datetime.now().strftime(timeFormat) + ","
                hopping = False
                leaping = True
            else:
                locomotion = "LEAPING," + dt.datetime.now().strftime(timeFormat) + ","
                leaping = True

# Run on close
def close():
    global recording
    global running
    global hopping
    global leaping
    global locomotion
    
    # End locomotion on [x]
    if hopping or leaping:
        locomotion += dt.datetime.now().strftime(timeFormat) + "\n"
        with open(csv_filename, "a") as file:
            file.write(locomotion)
    # Stop recording on [x]
    if recording:
        stop_record() 
    # Prompt if user wants to close program
    if messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
        running = False
        camera.stop_preview()
        root.destroy()

app = Frame(root)
app.grid()

# Start recording button
start = Button(app, text = "Start Recording", width = 50, height = 2, bg = "white", command = start_record)
start.grid(row = 1, column = 1)

# Stop recording button
stop = Button(app, text = "Stop Recording", width = 50, height = 2, bg = "white", command = stop_record)
stop.grid(row = 2, column = 1)

# Bind keys for marking locomotion events
root.bind("<Key>", key_press)

# Prompt user to close
root.protocol("WM_DELETE_WINDOW", close)

# Running loop
while running:
    root.update()
    if recording:
        camera.annotate_text = dt.datetime.now().strftime(timeFormat)

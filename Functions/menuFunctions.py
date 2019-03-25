import os
from datetime import datetime
from datetime import timedelta
import time

start_time = datetime.now()
# =======================
#     MENUS FUNCTIONS
# =======================

# Main menu
def main_menu():
    os.system('clear')

    print("Tare"),
    print("Calibrate Scale"),
    print("Timestamp"),
    print("Set Report Rate"),
    print("Set Baud Rate"),
    print("Units of Measure"),
    print("Decimals[0]"),
    print("Average Amount"),
    print("Local Temp[Off]"),
    print("RemoteTemp[Off]"),
    print("Status LED [Off]"),
    print("SerialTrig [Off]"),
    print("Raw Read [Off]"),
    print("Main Menu")
    
    choice = raw_input(" >>  ")
    exec_menu(choice)

    return

# Execute menu
def exec_menu(choice):
    os.system('clear')
    ch = choice.lower()
    if ch == '':
        menu_actions['main_menu']()
    else:
        try:
            menu_actions[ch]()
        except KeyError:
            print ("Invalid selection, please try again.\n")
            menu_actions['main_menu']()
    return

# BLUETOOTH CONFIG
def bluetooth():
    try:
        os.system('clear')
        print("Bluetooth Functionality \r\n")
        return
    except:
        print "Cannot reach Bluetooth Functionality"
        menu_actions['main_menu']()


# Back to main menu
def back():
    menu_actions['main_menu']()

#Menu definition
menu_actions = {
    'main_menu': main_menu,
    '1': bluetooth,
    '9': back
}

##def millis():
##    dt = datetime.now() - start_time
##    ms = (dt.days * 24 * 60 * 60 + dt.seconds) * \
##        1000 + dt.microseconds / 1000.0
##    return ms

#===========================================
#===       CREATE MILLIS FUNCTION        ===
#===========================================
def millis():
    millis = int(round(time.time() * 1000))
    return millis

def setEncoderRange(encoder, knobMin, knobMax, PIN_A, PIN_B):
    
    
    bump = [0,0,-1,1]
    state = 0
    state = state + GPIO.input(PIN_A)
    state <<=1
    state = state + GPIO.input(PIN_B)
    print(state)
    

    encoder += bump[state]              # added direction of turn to state
    if(encoder < knobMin):              # lower limit of any menu roll back to top
        encoder = knobMax-1             # upper limit of any menu roll back to bottom
    if(encoder > knobMax -1):
        encoder = knobMin
    print(encoder)
    
if __name__ == '__main__':
    main_menu()
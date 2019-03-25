import subprocess
import serial

ser = serial.Serial('/dev/ttyUSB0', baudrate=9600,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                    )


    

        
#openScaleMenu(ser)

def getWifiStatus():
    
    ps = subprocess.Popen(['iwconfig'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        output = subprocess.check_output(('grep', 'ESSID'), stdin=ps.stdout)
        if("off" in output):
            return False
        else:
            return True
        #print(output)
        #print(type(output))
        
    except subprocess.CalledProcessError:
        # grep did not match any lines
        return False
    
    
def getWifiStatus():
    
    global wifi_on
    
    ps = subprocess.Popen(['iwconfig'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        output = subprocess.check_output(('grep', 'ESSID'), stdin=ps.stdout)
        if("off" in output):
            wifi_on = False
            menu_WifiList[0] = "Wifi:  ON [OFF]"
            return False
        else:
            wifi_on = True
            menu_WifiList[0] = "Wifi: [ON] OFF] "
            return True
        #print(output)
        #print(type(output))
        
    except subprocess.CalledProcessError:
        # grep did not match any lines
        wifi_on = False
        menu_WifiList[0] = "Wifi:  ON [OFF]"
        return False

def main():
    while ser.inWaiting() > 0:
        ser.open()
        scale_config = ser.readline()
        print(scale_config + "\n")

    #openScaleMenu(ser)
  
    
if __name__ == '__main__':
    main()
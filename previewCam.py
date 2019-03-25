from time import sleep
import picamera

global delay

def previewCamera(delay):
                
    with picamera.PiCamera() as camera:
        
        camera.resolution = (1024, 768)
        camera.start_preview()
        sleep(delay)
        camera.stop_preview()
      

def main():
    previewCamera(300)

if __name__ == '__main__':
    main()
from time import sleep
import picamera

def previewCamera(pc_event, pc_lock):
    pc_event.wait()
    if pc_event.is_set():
            
        with picamera.PiCamera() as camera:
            pc_lock.acquire()
            camera.resolution = (1024, 768)
            camera.start_preview()
            sleep(2)
            camera.stop_preview()
            pc_lock.release()

def thread_test(event2, lock2):
    if event2.wait():
        with lock2:
            print("Thread Test")

def main():
    
    
    preveiwCamera(10)


if __name__ == '__main__':
    main()
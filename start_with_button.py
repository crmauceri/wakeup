import RPi.GPIO as GPIO
import threading, time
from datetime import timedelta, datetime
import numpy as np

#GLOBAL VARIABLES#
lightInterupt = False
interuptChannels = []
lock = threading.Lock()

RED = 17
GREEN = 27
BLUE = 22
BUTTON_CHANNEL_BLUE = 6
BUTTON_CHANNEL_RED = 13

def initializeGPIO():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RED, GPIO.OUT)
    GPIO.setup(GREEN, GPIO.OUT)
    GPIO.setup(BLUE, GPIO.OUT)
    GPIO.setup(BUTTON_CHANNEL_BLUE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_CHANNEL_RED, GPIO.IN, pull_up_down=GPIO.PUD_UP)


class ThreadButton(threading.Thread):
    def __init__(self, channel, interuptChannels):
        super(ThreadButton, self).__init__()
        self.CHANNEL = channel
        self.interuptChannels = interuptChannels

    def run(self):
        global lightInterupt, interuptChannels
        while True:
            input = GPIO.input(self.CHANNEL)
            if input == False:
                print('Button Pressed')
                lock.acquire()
                lightInterupt = True
                interuptChannels = self.interuptChannels
                lock.release()
            time.sleep(0.5)


class ThreadLight(threading.Thread):
    def __init__(self, RED, GREEN, BLUE):
        super(ThreadLight, self).__init__()
        self.weekdays = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su']
        self.RED = RED
        self.GREEN = GREEN
        self.BLUE = BLUE
        self.lightON = False
        self.isTodaysAlarmActive = True
        self.waitingForAutoStop = False

        self.readAlarmFile()
        self.setTodaysAlarm()
        self.initializeGPIO()

    def run(self):
        global lightInterupt
        while (True):
            # If the time is midnight, re-read the alarm file and set todays alarm
            if datetime.time(datetime.now()).hour == 0:
                self.readAlarmFile()
                self.setTodaysAlarm()
                self.isTodaysAlarmActive = True

            # If the time is twenty minutes before the alarm, start light ramp up
            if self.isTodaysAlarmActive and datetime.now() >= self.rampWindow[0] and datetime.now() <= self.rampWindow[1]:
                self.rampLight(20 * 60)
                self.isTodaysAlarmActive = False
                self.waitingForAutoStop = True

            # If the time is half an hour after alarm, turn off light
            if self.waitingForAutoStop and datetime.now() >= self.stopWindow[0] and datetime.now() <= self.stopWindow[1]:
                self.turnOffLight()
                self.waitingForAutoStop = False

            # If the button is pressed and the light is currently on
            if lightInterupt and self.lightON:
                self.turnOffLight()
                lock.acquire()
                lightInterupt = False
                lock.release()
                self.waitingForAutoStop = False

            if lightInterupt and not self.lightON:
                self.turnOnLight()
                lock.acquire()
                lightInterupt = False
                lock.release()

            time.sleep(0.5)

    def readAlarmFile(self):
        self.alarms = {}
        with open('/home/pi/wakeupLamp/alarm.txt', 'r') as f:
            for line in f.read().split('\n'):
                symbols = line.split()
                time = symbols[0]
                for day in symbols[1:]:
                    self.alarms[day] = time

        print self.alarms

    def setTodaysAlarm(self):
        today = datetime.today()
        weekday = self.weekdays[today.weekday()]
        alarmTime = self.alarms[weekday]
        self.alarm = datetime(today.year, today.month, today.day, int(alarmTime[0:2]), int(alarmTime[2:]))
        self.rampWindow = [self.alarm-timedelta(seconds=21*60), self.alarm-timedelta(seconds=20*60)]
        self.stopWindow = [self.alarm+timedelta(seconds=30*60), self.alarm+timedelta(seconds=31*60)]
        print self.alarm

    def initializeGPIO(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.RED, GPIO.OUT)
        GPIO.setup(self.GREEN, GPIO.OUT)
        GPIO.setup(self.BLUE, GPIO.OUT)

    def rampLight(self, min):
        self.lightON = True
        timeStep = min / 3.0 / 100.0
        print(timeStep)
        time = np.linspace(0, 1, 100)
        #sigmoid = 1 / (1 + np.exp(-1*time))
        quadratic = np.multiply(time, time)

        self.rampChannel(self.RED, quadratic, timeStep)
        GPIO.output(self.RED, GPIO.HIGH)
        self.rampChannel(self.GREEN, quadratic, timeStep)
        GPIO.output(self.GREEN, GPIO.HIGH)
        self.rampChannel(self.BLUE, quadratic, timeStep)
        GPIO.output(self.BLUE, GPIO.HIGH)

    def rampChannel(self, channel, ramp, timeStep):
        global lightInterupt
        #Every timeStep we process one ramp value
        for intensity in ramp:
            if lightInterupt:
                self.isTodaysAlarmActive = False
                break
            self.blink(channel, intensity, timeStep)

    def blink(self, channel, intensity, duration):
        total_time = 0.0
        while(total_time<duration):
            if lightInterupt:
                self.isTodaysAlarmActive = False
                break
            GPIO.output(channel, GPIO.HIGH)
            time.sleep(1.0 / 60.0 * (intensity))
            GPIO.output(channel, GPIO.LOW)
            time.sleep(1.0 / 60.0 * (1-intensity))
            total_time += 1.0 / 60.0

    def turnOffLight(self):
        self.lightON = False
        GPIO.output(self.RED, GPIO.LOW)
        GPIO.output(self.GREEN, GPIO.LOW)
        GPIO.output(self.BLUE, GPIO.LOW)

    def turnOnLight(self):
        global interuptChannels
        self.lightON = True
        lock.acquire()
        for channel in interuptChannels:
            GPIO.output(channel, GPIO.HIGH)
        lock.release()
        #GPIO.output(self.GREEN, GPIO.HIGH)
        #GPIO.output(self.BLUE, GPIO.HIGH)

if __name__ == "__main__":
    try:
        print("Start the clock...")
        initializeGPIO()
        lightThread = ThreadLight(RED, GREEN, BLUE)
        buttonThreadBlue = ThreadButton(BUTTON_CHANNEL_BLUE, [RED, GREEN, BLUE])
        buttonThreadRed = ThreadButton(BUTTON_CHANNEL_RED, [RED])

        lightThread.start()
        buttonThreadBlue.start()
        buttonThreadRed.start()

        lightThread.join()
        buttonThreadBlue.join()
        buttonThreadRed.join()

    finally:
        GPIO.output(RED, GPIO.LOW)
        GPIO.output(GREEN, GPIO.LOW)
        GPIO.output(BLUE, GPIO.LOW)
        GPIO.cleanup()

import RPi.GPIO as GPIO
import time
from datetime import timedelta, datetime
import numpy as np

#GLOBAL VARIABLES#
lightON = False
alarms = {}
alarm = 1200
weekdays = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su']
RED = 17
GREEN = 27
BLUE = 22

def main():
    readAlarmFile()
    setTodaysAlarm()
    initializeGPIO()
    alarmLoop()

def readAlarmFile():
    global alarms
    with open('alarm.txt', 'r') as f:
        for line in f.read().split('\n'):
            symbols = line.split()
            time = symbols[0]
            for day in symbols[1:]:
                alarms[day] = time

    print alarms

def setTodaysAlarm():
    global alarm
    today = datetime.today()
    weekday = weekdays[today.weekday()]
    alarmTime = alarms[weekday]
    alarm = datetime(today.year, today.month, today.day, int(alarmTime[0:2]), int(alarmTime[2:]))
    print alarm

def initializeGPIO():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RED, GPIO.OUT)
    GPIO.setup(GREEN, GPIO.OUT)
    GPIO.setup(BLUE, GPIO.OUT)

def alarmLoop():
    while(True):
        curtime = datetime.time(datetime.now())
        #If the time is midnight, re-read the alarm file and set todays alarm
        if curtime.hour == 0:
            readAlarmFile()
            setTodaysAlarm()

        #If the time is twenty minutes before the alarm, start light ramp up
        if not lightON and datetime.now() >= alarm - timedelta(seconds=20*60) and datetime.now() < alarm + timedelta(seconds=30*60):
            rampLight(20)

        #If the time is half an hour after alarm, turn off light
        if lightON and datetime.now() >= alarm + timedelta(seconds=30*60):
            turnOffLight()

def rampLight(min):
    global lightON
    lightON = True
    timeStep = min / 3.0
    time = np.arange(-5, 5, 0.25)
    sigmoid = 1 / (1 + np.exp(-1*time))

    rampChannel(RED, sigmoid, timeStep)
    GPIO.output(RED, GPIO.HIGH)
    rampChannel(GREEN, sigmoid, timeStep)
    GPIO.output(GREEN, GPIO.HIGH)
    rampChannel(BLUE, sigmoid, timeStep)
    GPIO.output(BLUE, GPIO.HIGH)

def rampChannel(channel, ramp, timeStep):
    #Every timeStep we process one ramp value
    for intensity in ramp:
        blink(channel, intensity, timeStep)

def blink(channel, intensity, duration):
    total_time = 0.0
    while(total_time<duration):
        GPIO.output(channel, GPIO.HIGH)
        time.sleep(1.0 / 60.0 * (intensity))
        GPIO.output(channel, GPIO.LOW)
        time.sleep(1.0 / 60.0 * (1-intensity))
        total_time += 1.0 / 60.0

def turnOffLight():
    global lightON
    lightON = False
    GPIO.output(RED, GPIO.LOW)
    GPIO.output(GREEN, GPIO.LOW)
    GPIO.output(BLUE, GPIO.LOW)


if __name__ == "__main__":
    #print timePlusMinutes(8, 20, -30)
    #print timePlusMinutes(8, 40, 30)
    #print timePlusMinutes(8, 0, 30)

    try:
        initializeGPIO()
        main()
        #rampLight(60)
    finally:
        GPIO.output(RED, GPIO.LOW)
        GPIO.output(GREEN, GPIO.LOW)
        GPIO.output(BLUE, GPIO.LOW)
        GPIO.cleanup()

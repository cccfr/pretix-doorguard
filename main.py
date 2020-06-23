import time
import datetime
import json
import picamera
from pyzbar.pyzbar import decode
import png
from io import BytesIO
from PIL import Image
import requests

mateserver = "https://schwarzelunge.club.klaut.cloud"

headers = {}
with open("authHeader.json") as headerfile:
    headers = json.load(headerfile)
codes = {}
lastSync = datetime.datetime.now()

def getCodes():
    global lastSync
    print("getting codes")
    codes = {}
    res = requests.get("%s/api/v1/organizers/hustepeter/events/caferuss/checkinlists" %mateserver, headers=headers)
    if res.status_code != 200:
        print("error getting checkin lists")
        return
    lists = res.json()["results"]
    for checkinlist in lists:
        if checkinlist["name"] in ("daily, monthly, yearly"):
            res = requests.get("%s/api/v1/organizers/hustepeter/events/caferuss/checkinlists/%s/positions" %(mateserver, checkinlist["id"]), headers=headers)
            if res.status_code != 200:
                continue
            tickets = res.json()["results"]
            for ticket in tickets:
                codes[ticket["secret"]] = {"checkinlist": checkinlist["id"], "id": ticket["id"], "order": ticket["order"]}
    lastSync = datetime.datetime.now()
    print("current codes: %s" %codes)
    return codes

def checkinCode(code):
    res = requests.post("%s/api/v1/organizers/hustepeter/events/caferuss/checkinlists/%s/positions/%s/redeem/" %(mateserver, code["checkinlist"], code["id"]), headers=headers)
    if res.status_code != 201:
        print("cannot checkin ticket: %s" %code)

def openDoor():
    print("opening...")
    pass
    print("done opening")
    time.sleep(5)

def signalLED():
    print("flashing led")


codes = getCodes()

with picamera.PiCamera() as camera:
    stream = BytesIO()
    camera.start_preview()
    time.sleep(2)
    print("Scanner initialized")
    while True:
        timePassed = datetime.datetime.now() - lastSync
        if timePassed.seconds > 10:
            codes = getCodes()
            lastSync = datetime.datetime.now()
        stream.seek(0)
        camera.capture(stream, format='jpeg', use_video_port=True)
        stream.seek(0)
        frame = Image.open(stream)
        #frame.save("cam.png")
        barcodes=decode(frame)
        for barcode in barcodes:
            signalLED()
            data = barcode.data.decode("utf-8")
            print("code read: %s" %data )
            if data in codes.keys():
                print("found valid ticket: %s" %codes[data])
                checkinCode(codes[data])
                openDoor()



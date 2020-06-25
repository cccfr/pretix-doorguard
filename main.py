import time
import datetime
import json
import picamera
from pyzbar.pyzbar import decode
import png
from io import BytesIO
from PIL import Image
import requests

lastSync = datetime.datetime.now()
config = {}
#config = {
           "meteserver": "http://mete.cloud.cccfr", 
           "organizers": {"hustepeter": {"teercafe": ["daily", "monthly", "yearly"]}
           "headers": {"Authorization": "Token xxxxx"}
         }

def getCodes():
    global lastSync
    print("getting codes")
    codes = {}
    for organizer in config["organizers"].keys():
        for event in config["organizers"][organizer].keys():
            res = requests.get("%s/api/v1/organizers/%s/events/%s/checkinlists" %(config["meteserver"], organizer, event), headers=config["headers"])
            if res.status_code != 200:
                print("error getting checkin lists")
                return
            lists = res.json()["results"]
            for checkinlist in lists:
                if checkinlist["name"] in config["organizers"][organizer][event]:
                    res = requests.get("%s/api/v1/organizers/%s/events/%s/checkinlists/%s/positions" %(config["meteserver"], organizer, event, checkinlist["id"]), headers=config["headers"])
                    if res.status_code != 200:
                        continue
                    tickets = res.json()["results"]
                    for ticket in tickets:
                        codes[ticket["secret"]] = {"checkinlist": checkinlist["id"], "id": ticket["id"], "organizer": organizer, "event": event, "order": ticket["order"]}
    lastSync = datetime.datetime.now()
    print("current codes: %s" %codes)
    return codes

def checkinCode(code):
    res = requests.post("%s/api/v1/organizers/%s/events/%s/checkinlists/%s/positions/%s/redeem/" %(config["meteserver"], code["organizer"], code["event"], code["checkinlist"], code["id"]), headers=config["headers"])
    if res.status_code != 201:
        print("cannot checkin ticket: %s\n%s" %(code, res.text))

def openDoor():
    print("opening...")
    pass
    print("done opening")
    time.sleep(5)

def signalLED():
    print("flashing led")

def main():
    global config
    with open("config.json") as configfile:
        config = json.load(configfile)

    codes = {}
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
                    openDoor()
                    checkinCode(codes[data])

if __name__ == "__main__":
    main()

import time
import datetime
import json
import picamera
from pyzbar.pyzbar import decode
import png
from io import BytesIO
from PIL import Image
import requests
from systemd.journal import JournaldLogHandler
import logging
import sys, os
import subprocess

logger = logging.getLogger(__name__)
journald_handler = JournaldLogHandler()
journald_handler.setFormatter(logging.Formatter(
    '[%(levelname)s] %(message)s'
))
logger.addHandler(journald_handler)

stdouthandler = logging.StreamHandler(sys.stdout)
stdouthandler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(stdouthandler)
logger.setLevel(logging.INFO)


lastSync = datetime.datetime.now()
config = {}
#config = {
#           "pretix": "http://mete.cloud.cccfr", 
#           "organizers": {"hustepeter": {"teercafe": ["daily", "monthly", "yearly"]}
#           "headers": {"Authorization": "Token xxxxx"}
#         }

def getCodes():
    global lastSync
    logger.info("getting codes")
    codes = {}
    for organizer in config["organizers"].keys():
        for event in config["organizers"][organizer].keys():
            logger.debug("getting checkinlists for %s/%s" %(organizer, event))
            res = requests.get("%s/api/v1/organizers/%s/events/%s/checkinlists" %(config["pretix"], organizer, event), headers=config["headers"])
            if res.status_code != 200:
                logger.error("error getting checkin lists")
                return {}
            lists = res.json()["results"]
            logger.debug("found lists:\n%s" %lists)
            for checkinlist in lists:
                logger.debug("if %s in %s\n%s" %(checkinlist["name"], config["organizers"][organizer][event], checkinlist["name"] in config["organizers"][organizer][event]))
                if checkinlist["name"] in config["organizers"][organizer][event]:
                    res = requests.get("%s/api/v1/organizers/%s/events/%s/checkinlists/%s/positions" %(config["pretix"], organizer, event, checkinlist["id"]), headers=config["headers"])
                    if res.status_code != 200:
                        continue
                    tickets = res.json()["results"]
                    for ticket in tickets:
                        codes[ticket["secret"]] = {"checkinlist": checkinlist["id"], "id": ticket["id"], "organizer": organizer, "event": event, "order": ticket["order"]}
    lastSync = datetime.datetime.now()
    logger.info("current codes: %s" %codes)
    return codes

def checkinCode(code):
    res = requests.post("%s/api/v1/organizers/%s/events/%s/checkinlists/%s/positions/%s/redeem/" %(config["pretix"], code["organizer"], code["event"], code["checkinlist"], code["id"]), headers=config["headers"])
    if res.status_code != 201:
        logger.error("cannot checkin ticket: %s\n%s" %(code, res.text))

def openDoor():
    logger.info("opening")
    subprocess.run(["/bin/bash", "%s/openDoor.sh" %os.path.dirname(os.path.realpath(__file__))])
    time.sleep(5)

def signalLED():
    print("flashing led")

def main():
    global config
    global lastSync
    subprocess.run(["/bin/bash", "%s/initGPIO.sh" %os.path.dirname(os.path.realpath(__file__))])
    with open("%s/config.json" %os.path.dirname(os.path.realpath(__file__))) as configfile:
        config = json.load(configfile)

    codes = getCodes()
    if len(codes) == 0:
        codes = {}

    with picamera.PiCamera() as camera:
        stream = BytesIO()
        camera.start_preview()
        time.sleep(2)
        logger.info("Scanner initialized")
        logger.info("testing Opener")
        openDoor()
        while True:
            timePassed = datetime.datetime.now() - lastSync
            if timePassed.seconds > 10:
                newcodes = getCodes()
                if len(newcodes) > 0:
                    codes = newcodes
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
                logger.info("code read: %s" %data )
                if data in codes.keys():
                    logger.info("found valid ticket: %s" %codes[data])
                    openDoor()
                    checkinCode(codes[data])

if __name__ == "__main__":
    main()

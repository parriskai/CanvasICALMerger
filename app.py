from flask import Flask, send_file
from dotenv import load_dotenv
from threading import Thread
import icalendar
import requests
import time
import json
import os

app = Flask(__name__)
load_dotenv()
api_key = os.environ["CANVAS_TOKEN"]
canvas_url = "https://western.instructure.com"
ses = requests.session()
ses.headers["Authorization"] = "Bearer " + api_key

def exponental_backoff(f) -> requests.Response:
    t = 1
    while True:
        resp: requests.Response = f()
        if resp.status_code != 200:
            print(f"Responst Status Code: {resp.status_code} ({resp.reason})")
            print(f"Waiting {t} seconds before next attempt")
            time.sleep(t)
            t *= 2
        else:
            return resp

def update_ical():
    classes = exponental_backoff(lambda: ses.get(f"{canvas_url}/api/v1/courses")).json()
    combined_cal:icalendar.Calendar = icalendar.Calendar.new(name = "School Calender")
    for cls in classes:
        print(cls["name"])
        if "calendar" in cls and "ics" in cls["calendar"]:
            ical = cls["calendar"]["ics"]
            dl = exponental_backoff(lambda: ses.get(ical)).content
            cal  = icalendar.Calendar.from_ical(dl)
            for event in cal.walk(None):
                t = type(event)
                if t == icalendar.cal.calendar.Calendar:
                    pass
                elif t == icalendar.cal.event.Event:
                    combined_cal.add_component(event)
                else:
                    print("Unhandled type", t)
        else:
            print("\t- No ICS")
    with open("classes.ics", "wb") as f:
        f.write(combined_cal.to_ical())
        f.close()



def updater():
    while True:
        update_ical()
        time.sleep(60 * 60)


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/classes.ics")
def classes_ical():
    return send_file("classes.ics", mimetype="text/calendar")


if __name__ == "__main__":
    Thread(target=updater, daemon=True).start()
    app.run(host="0.0.0.0", port=8080, debug=False)
import logging, signal, argparse, sdnotify, calendar, sys
from logging.handlers import RotatingFileHandler
from datetime import datetime as dt
from models import Uploader
from outputs import *
from inputs import InputMicrophone, MotionDetector
#import metoffice


# MANUAL INPUTS
mic = InputMicrophone()

# CONFIG FILES
configfile = ".config/config.json"
configfile_video = ".config/config.json"
servicesfile = ".config/services_1.json"

def end_nicely():
    logging.info("quitting nicely")
    motdet.save_bg()
    logging.info("saved background")
    motdet.stop()
    motdet.file_handler.clean()
    logging.info("bye!")

def signal_term_handler(signal, frame):
    logging.warning('got SIGTERM')
    end_nicely()
    sys.exit(0)

def signal_abrt_handler(signal, frame):
    logging.warning('got SIGABRT')
    end_nicely()
    sys.exit(0)

def stills():
    logging.info("capturing a still image")
    # UPLOADER
    uploader = Uploader(configfile)
    # OUTPUTS
    camera = CameraOutput(0, uploader=(uploader, servicesfile))
    return camera


def video():
    logging.info("capturing a video")
    # UPLOADER
    uploader = Uploader(configfile_video)
    # OUTPUTS
    videocam = VideoCameraOutput(0, uploader=(uploader, servicesfile))
    return videocam


def motion():
    logging.info("starting motion detection")
#   weatherPerson = metoffice.Rain()
#   lastRainForecast = weatherPerson.getPrecipProb()
    notifier = sdnotify.SystemdNotifier()
    # UPLOADER
    uploader = Uploader(configfile_video)
    global motdet
#   motdet = MotionDetector(5, 100, 1000, 30, notifier, weatherPerson, uploader=(uploader, servicesfile))
    motdet = MotionDetector(min_frames=5,
                            max_frames=300,
                            min_area=1000,
                            max_silent_frames=30,
                            notifier=notifier,
                            uploader=(uploader, servicesfile))
    if motdet.file_handler.pending:
        motdet.file_handler.run()
    notifier.notify("READY=1")
    motdet.start()
#   sleepingWeatherPerson=0
    while True:
        try:
            time.sleep(60)
#           if not sleepingWeatherPerson:
#              lastRainForecast = weatherPerson.getPrecipProb()
#              sleepingWeatherPerson = 5
#           else:
#              sleepingWeatherPerson -= 1
        except KeyboardInterrupt:
            end_nicely()
            break

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-c", "--capture", required=True,
                            help="capture type: video, still, or motion")
    args = vars(arg_parser.parse_args())
    signal.signal(signal.SIGTERM, signal_term_handler)
    signal.signal(signal.SIGABRT, signal_abrt_handler)

    today = calendar.day_name[dt.now().weekday()]
    logfile = sys.path[0]+"/log/garden." + today + ".log"
    rotator = RotatingFileHandler(logfile, maxBytes=10485760, backupCount=2)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:(%(threadName)-10s):%(message)s",handlers=[rotator]
    )

    try:
        if args["capture"] == "video":
            video().fire(0)
        elif args["capture"] == "still":
            stills().fire(0)
        elif args["capture"] == "motion":
            motion()
    except IndexError:
        motion()

# End

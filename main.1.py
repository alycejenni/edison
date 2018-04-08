import logging, signal, argparse, sdnotify, calendar, sys
from datetime import datetime as dt
from models import Uploader
from outputs import *
from inputs import InputMicrophone, MotionDetector


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
    notifier = sdnotify.SystemdNotifier()
    # UPLOADER
    uploader = Uploader(configfile_video)
    global motdet
    motdet = MotionDetector(5, 100, 1000, 30, notifier, uploader=(uploader, servicesfile))
    if motdet.file_handler.pending:
        motdet.file_handler.run()
    notifier.notify("READY=1")
    motdet.start()
    while True:
        try:
            time.sleep(60)
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
    logging.basicConfig(
        filename=sys.path[0]+"/log/garden." + today + ".log",
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(message)s"
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

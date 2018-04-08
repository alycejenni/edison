import logging
from models import Uploader
from outputs import *
from inputs import InputMicrophone, MotionDetector
import argparse

logging.basicConfig(
    filename="/home/sissy/cam/log/garden.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s"
    )

# MANUAL INPUTS
mic = InputMicrophone()

# CONFIG FILES
configfile = ".config/config.json"
configfile_video = ".config/config.json"
servicesfile = ".config/services_1.json"

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
    # UPLOADER
    uploader = Uploader(configfile_video)
    global motdet
    motdet = MotionDetector(5, 100, 1000, 30, uploader=(uploader, servicesfile))
    if motdet.file_handler.pending:
        motdet.file_handler.run()
    motdet.start()
    while True:
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            logging.info("quitting nicely")
            motdet.save_bg()
            logging.info("saved background")
            motdet.stop()
            motdet.file_handler.clean()
            logging.info("bye!")
            break

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-c", "--capture", required=True,
                            help="capture type: video, still, or motion")
    args = vars(arg_parser.parse_args())
    try:
        if args["capture"] == "video":
            video().fire(0)
        elif args["capture"] == "still":
            stills().fire(0)
        elif args["capture"] == "motion":
            motion()
    except IndexError:
        motion()

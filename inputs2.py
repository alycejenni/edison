import cv2, math, os, pickle, sdnotify, logging, subprocess
import moviepy.editor as mpy
import numpy as np
from datetime import datetime as dt
from scipy.io import wavfile
from models import *

class InputMicrophone(Input):
    def __init__(self):
        self.thread = threading.Thread(target=self.record)

    def record(self):
        audioname = "audio1.wav"
        p = subprocess.Popen(
            ["arecord", "-D", "plughw:CARD=1", "-f", "S16_LE", "-q", "-d", "5",
             audioname])
        p.wait()
        freq, aud = wavfile.read(audioname)
        aud = abs(aud / (2. ** 15))
        os.remove(audioname)
        self.max_amp = max(aud)

    def get(self):
        self.thread.start()
        self.thread.join()
        self.thread = threading.Thread(target=self.record)

class MotionDetector(Input):
    def __init__(self, min_frames, max_frames, min_area, max_silent_frames, notifier, weatherPerson, uploader=None):
        self.cam = cv2.VideoCapture(0)
        self.background = None
        self.bgfile = None
        self.last_update = dt.now()
        self.min_moving_frames = min_frames
        self.max_moving_frames = max_frames
        self.min_area = min_area
        self.max_silent_frames = max_silent_frames
        self.moving_frames = 0
        self.silent_frames = 0
        self.cont = True
        self.fps = 30
        self.thread = threading.Thread(target=self.checktrigger)
        self.file_handler = FileHandler(filetype="mp4", uploader=uploader)
        self.notifier = notifier
        self.weatherPerson = weatherPerson
        self.watchdog_usec = os.environ["WATCHDOG_USEC"]

        self.setup()

    def setup(self):
        if not os.path.exists("backgrounds"):
            os.mkdir("backgrounds")
            self.bgfile = "backgrounds/bg1.pkl"
        else:
            bgfiles = os.listdir("backgrounds")
            bgfiles = sorted(bgfiles, key=lambda x: os.path.getmtime("backgrounds/" + x))

            # load the most recent bg file
            with open("backgrounds/" + bgfiles[-1], "rb") as file:
                self.background = pickle.load(file)
            logging.info("loaded background from " + bgfiles[-1])

            # now make a new file
            ix = int(bgfiles[-1].split(".")[0].replace("bg", "")) + 1
            fn = f"backgrounds/bg{ix}.pkl"
            while os.path.exists(fn):
                ix += 1
                fn = f"backgrounds/bg{ix}.pkl"
            self.bgfile = fn
            self.save_bg()

        self.res = (640, 480)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.res[0])
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.res[1])
        logging.info("Chance of rain is " + self.weatherPerson.lastRainForecast + "%")
        time.sleep(2)

    def save_bg(self):
        with open(self.bgfile, "wb") as file:
            pickle.dump(self.background, file)

    def start(self):
        self.cont = True
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self):
        self.cont = False
        self.thread.join()

    def checktrigger(self):
        crop_top = 0
        crop_bottom = 1
        crop_left = 0
        crop_right = 1
        l = int(self.res[0] * crop_left)
        r = int(self.res[0] * crop_right)
        t = int(self.res[1] * crop_top)
        b = int(self.res[1] * crop_bottom)
        raw_frame = self.cam.read()[1]
        vid_frames = []
        avg_centroids = []
        total_frames = 0
        total_time = 0
        usleep = lambda x: time.sleep(x/1000000.0)
        logging.info("WATCHDOG_USEC="+self.watchdog_usec)
        reading = True
        while reading:
            reading, f = self.cam.read()
            self.notifier.notify("WATCHDOG=1")
            start = dt.now()
            if not self.cont:
                break
            frame = f[t:b, l:r]
            imgrey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            imgrey = cv2.GaussianBlur(imgrey, (21, 21), 0)
            if self.background is None:
                self.background = imgrey.copy().astype("float")
                self.save_bg()
                raw_frame = None
                logging.info("initialised background")
                continue

            cv2.accumulateWeighted(imgrey, self.background, 0.5)
            frame_delta = cv2.absdiff(imgrey, cv2.convertScaleAbs(self.background))
            frame_threshold = cv2.threshold(frame_delta, 20, 255, cv2.THRESH_BINARY)[1]
            frame_dilated = cv2.dilate(frame_threshold, None, iterations=10)
            im2, contours, hier = cv2.findContours(frame_dilated, cv2.RETR_TREE,
                                                   cv2.CHAIN_APPROX_SIMPLE)

            motion = [c for c in contours if cv2.contourArea(c) >= self.min_area]
            frame_centroids = []

            for c in motion:
                x, y, w, h = cv2.boundingRect(c)
#                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                m = cv2.moments(c)
                cx = int(m['m10'] / m['m00'])
                frame_centroids.append(cx)

            if len(motion) == 0:
                if self.moving_frames != 0:
                    self.silent_frames += 1
                    if self.silent_frames == self.max_silent_frames:
                        if self.moving_frames >= self.min_moving_frames:
                            logging.info("movement ended")
                            self.make_vid(vid_frames, avg_centroids)
                        else:
                            logging.info("false alarm, sorry")
                        self.save_bg()
                        self.moving_frames = 0
                        vid_frames.clear()
                        avg_centroids.clear()
                    else:
                        vid_frames.append(f)
                        avg_centroids.append(avg_centroids[-1])
            else:
                self.moving_frames += 1
                self.silent_frames = 0
                vid_frames.append(f)
                avg_centroids.append(np.mean(frame_centroids))
                if self.moving_frames == 1: logging.info("what was that??")
                logging.info("Chance of rain in 3 hours beginning " + \
                              str(int(self.weatherPerson.slot/60)).ljust(4,'0') + \
                              " is " + self.weatherPerson.lastRainForecast + "%")
                if self.moving_frames == self.min_moving_frames:
                    logging.info("movement detected")
                if self.moving_frames == self.max_moving_frames:
                    logging.warning("this has been going on too long, stopping")
                    self.make_vid(vid_frames, avg_centroids)
                    self.save_bg()
                    self.moving_frames = 0
                    vid_frames.clear()
                    avg_centroids.clear()

            raw_frame = None
            total_time += (dt.now() - start).microseconds / 1000000
            total_frames += 1
            self.fps = total_frames / total_time
            frame_centroids.clear()

        self.cam.release()
        logging.info("camera closed, thread terminated")

    def make_vid(self, frames, centroids):
        direction = 1 if centroids[0] > centroids[-1] else 0
        if centroids[0] == centroids[-1]:
            direction = 2
        self.file_handler.set_direction(direction)
        logging.info("converting with ffmpeg...")
        frames = [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in frames]
        vid = mpy.ImageSequenceClip(frames, fps=self.fps)
        vid.write_videofile(self.file_handler.initial)
        logging.info("renaming...")
        self.file_handler.standard()
        self.file_handler.rename()
        self.file_handler.upload()
        self.file_handler.clean()

# End

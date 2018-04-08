import picamera
from models import *


class PinOutput(Output):
    def __init__(self, pin, trigger_value):
        super(PinOutput, self).__init__()
        self.pin = pin
        self.trigger_value = trigger_value
        self.setup()

    def setup(self):
        GPIO.setup(self.pin, GPIO.OUT)

    def on(self):
        GPIO.output(self.pin, GPIO.HIGH)

    def off(self):
        GPIO.output(self.pin, GPIO.LOW)

    def fire(self, value):
        if value == self.trigger_value:
            self.on()
        else:
            self.off()


class CameraOutput(Output):
    def __init__(self, trigger_value, uploader=None):
        super(CameraOutput, self).__init__()
        self.cam = picamera.PiCamera()
        self.trigger_value = trigger_value
        self.file_handler = FileHandler(uploader=uploader)
        self.dependents = []
        self.setup()

    def setup(self):
        self.cam.resolution = (640, 480)
        self.cam.iso = 400

    def add_dependent(self, dependent):
        if isinstance(dependent, InputWithFreeze):
            self.dependents.append(dependent)

    def shutter(self, seconds):
        self.cam.shutter_speed = int(seconds * 1000000)

    def set_shutter(self):
        ldr = self.manual_inputs["ldr"]
        s = min([ldr.get * 15, ldr.max_count * 15])
        if ldr.count_exceeded:
            print('night mode')
            self.cam.iso = 1600
            self.cam.shutter_speed = int(s)
            self.cam.framerate = 20
            self.cam.exposure_compensation = 25
        else:
            self.cam.shutter_speed = int(s)
            self.cam.framerate = 30
            self.cam.iso = 400
            self.cam.exposure_compensation = 0

    def fire(self, value):
        if value == self.trigger_value:
            self.set_shutter()
            time.sleep(1)
            print("taking picture...")
            self.cam.capture(self.file_handler.initial)
            print("done. " + str(self))
            for d in self.dependents:
                d.wait_for_ready()
            print("renaming/uploading...")
            self.file_handler.standard()
            self.file_handler.rename()
            self.file_handler.upload()
            self.file_handler.clean()

    def close(self):
        self.cam.close()

    def __repr__(self):
        return f"shutter speed: {str(self.cam.shutter_speed)}\niso: {str(self.cam.iso)}"


class VideoCameraOutput(CameraOutput):
    def __init__(self, trigger_value, uploader=None):
        super(VideoCameraOutput, self).__init__(trigger_value, uploader=None)
        self.file_handler = FileHandler(filetype="h264", uploader=uploader)

    def fire(self, value):
        if value == self.trigger_value:
            self.set_shutter()
            print("starting video...")
            self.manual_inputs["mic"].get()
            self.cam.start_recording(self.file_handler.initial)
            self.cam.wait_recording(5)
            self.cam.stop_recording()
            print("finished.")
            for d in self.dependents:
                d.wait_for_ready()
            print("renaming...")
            self.file_handler.standard()
            self.file_handler.rename()
            print("converting...")
            self.file_handler.convert("mp4")
            print(self.manual_inputs["mic"].max_amp)
            self.file_handler.upload()
            self.file_handler.clean()

    def __repr__(self):
        return "hello I'm a video camera?"


class TextOutput(Output):
    def __init__(self, trigger_value, notifier):
        super(TextOutput, self).__init__()
        self.trigger_value = trigger_value
        self.notifier = notifier

    def fire(self, value):
        if value == self.trigger_value:
            self.notifier.ifttt()

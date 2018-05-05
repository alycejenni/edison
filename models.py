import argparse, json, os, time, logging
import boto, ffmpy, httplib2, instapush,oauth2client,requests
from RPi import GPIO
from apiclient import discovery
from oauth2client import client, tools

GPIO.setmode(GPIO.BOARD)


class Observer(object):
    def __init__(self, output_method):
        self.output = output_method

    def notify(self, value):
        self.output(value)


class Notifier(object):
    def __init__(self, config_file):
        with open(config_file) as conffile:
            self.config = json.load(conffile)
        self.values = {
            "value1": time.time(),
            "value2": "",
            "value3": "DOG"
            }

    def ifttt(self):
        config = self.config["ifttt"]
        requests.post(config["url"], self.values)
        logging.info("notified via ifttt")

    def instapush(self):
        config = self.config["instapush"]
        app = instapush.App(config["id"], config["secret"])
        app.notify(config["event"], self.values)
        logging.info("notified via instapush")


class Uploader(object):
    def __init__(self, config_file, file=None, values=None):
        with open(config_file) as conffile:
            self.config = json.load(conffile)
        self.file = file
        self.values = values

    def drive(self):
        config = self.config["drive"]
        store = oauth2client.file.Storage(config["credential_path"])
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(config["client_secret"],
                                                  config["scopes"])
            flow.user_agent = config["app_name"]
            credentials = tools.run_flow(flow, store, argparse.ArgumentParser(
                parents=[tools.argparser]).parse_args())
            logging.info('Storing credentials to ' + config["credential_path"])
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('drive', 'v3', http=http)
        metadata = {
            "name": self.file
            }
        service.files().create(body=metadata, media_body=self.file).execute()
        logging.info("uploaded {0} to drive".format(self.file))

    def ifttt(self):
        config = self.config["ifttt"]
        requests.post(config["url"], self.values)
        logging.info("notified via ifttt")

    def instapush(self):
        config = self.config["instapush"]
        app = instapush.App(config["id"], config["secret"])
        app.notify(config["event"], self.values)
        logging.info("notified via instapush")

    def amazon(self):
        config = self.config["amazon"]
        s3 = boto.connect_s3(host=config["host"])
        bucket = s3.get_bucket(config["bucket"])
        logging.info("uploading {0} to amazon s3".format(self.file))
        key = bucket.new_key(self.file)
        key.set_contents_from_filename(self.file)
        key.set_acl(config["acl"])
        photo_url = key.generate_url(expires_in=0, query_auth=False)
        logging.info("done uploading")
        return photo_url

    def cleanup(self):
        os.remove(self.file)


class FileHandler(object):
#   def __init__(self, filetype="jpg", uploader=None):
    def __init__(self, filetype="mp4", uploader=None):
        self.filetype = filetype
        self.initial = "garden." + filetype
        self.path = "garden." + filetype
        self.direction = 0
        self.filename_set = False
        self.uploader = None
        if uploader:
            self.uploader = uploader[0]
            with open(uploader[1]) as conffile:
                self.services_config = json.load(conffile)

    @property
    def pending(self):
        return os.path.exists(self.initial)

    def run(self):
        self.standard()
        self.rename()
        self.upload()
        self.clean()

    def set_direction(self, value):
        if not self.filename_set:
            self.direction = value

    def standard(self):
        t = str(time.time()).replace(".", "_")
        self.path = "dog_{0}.".format(t) + self.filetype
        self.filename_set = True

    def rename(self):
        if os.path.exists(self.initial):
            os.rename(self.initial, self.path)

    def convert(self, newtype):
        ff = ffmpy.FFmpeg(inputs={
            self.path: None
            }, outputs={
            self.path.replace(self.filetype, newtype): None
            }, global_options=["-nostats -loglevel 0"])
        ff.run()
        self.clean()
        self.path = self.path.replace(self.filetype, newtype)

    def stats(self):
        return os.stat(self.path).st_size

    @property
    def direction_msg(self):
        if self.direction == 1:
            return "came in"
        elif self.direction == 2:
            return "is being a quantum boy"
        else:
            return "went out"

    def upload(self):
        if self.uploader and os.path.exists(self.path):
            self.uploader.file = self.path
            self.uploader.values = {
                "value1": time.time(),
                "value2": "",
                "value3": ""
                }
            if "amazon" in self.services_config:
                self.uploader.values["value2"] = self.uploader.amazon()
            if "drive" in self.services_config:
                self.uploader.drive()
            if "ifttt" in self.services_config:
                self.uploader.ifttt()
            if "instapush" in self.services_config:
                self.uploader.instapush()

    def clean(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        if os.path.exists(self.initial):
            os.remove(self.initial)
        self.filename_set = False


class Output(object):
    def __init__(self):
        self.manual_inputs = {}

    def add_manual_input(self, manual_input, name):
        if isinstance(manual_input, Input):
            self.manual_inputs[name] = manual_input

    def fire(self, value):
        logging.info("fired")


class Input(object):
    def setup(self):
        pass

    def get(self):
        return 0

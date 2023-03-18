# Setup for application including argument parser. 
import argparse
import importlib.util
import logging
import os
import numpy as np
import threading
import logging

from application import app
from application import TFLite_detection_stream
from application.services import security as vault
from application.services import telegram
from application.services.video_stream import VideoStream
from logging.handlers import TimedRotatingFileHandler

BACKUP_FILE_COUNT = 10

class FlaskThread(threading.Thread):
    def __init__(self, args):
        super(FlaskThread, self).__init__()
        self.args = args

    def run(self):
        logging.info("Starting flask server...")
        app.run(host=self.args.ip, port=self.args.port, threaded=True, use_reloader=False)

if __name__ == "__main__":
    # Define and parse input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--modeldir', help='Folder the .tflite file is located in',
                        default="Sample_TFLite_model")
    parser.add_argument('--streamurl', help='The full URL of the video stream e.g. http://ipaddress:port/stream/video.mjpeg',
                        default=vault.get_value("cameras", "DRIVEWAY", "url"))
    parser.add_argument('--graph', help='Name of the .tflite file, if different than detect.tflite',
                        default='detect.tflite')
    parser.add_argument('--labels', help='Name of the labelmap file, if different than labelmap.txt',
                        default='labelmap.txt')
    parser.add_argument('--threshold', help='Minimum confidence threshold for displaying detected objects',
                        default=0.5)
    parser.add_argument('--resolution', help='Desired webcam resolution in WxH. If the webcam does not support the resolution entered, errors may occur.',
                        default='704x480')
    parser.add_argument('--edgetpu', help='Use Coral Edge TPU Accelerator to speed up detection',
                        action='store_true')
    parser.add_argument("-i", "--ip", type=str, required=True,
        help="ip address of the device")
    parser.add_argument("-o", "--port", type=int, required=True,
        help="ephemeral port number of the server (1024 to 65535)")
    parser.add_argument('--channels', help='Number of camera channels in the network',
                    default=6)

    # Start rotating logger.
    logger = logging.getLogger("Rotating Log")
    logger.setLevel(logging.DEBUG)

    handler = TimedRotatingFileHandler(filename="logging/kernel_debug.log",
                                       when="d",
                                       interval=1,
                                       backupCount=BACKUP_FILE_COUNT)

    fmt = '%(asctime)s %(levelname)s %(message)s'
    formatter = logging.Formatter(fmt=fmt, datefmt='%m/%d/%Y %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    args = parser.parse_args()

    MODEL_NAME = args.modeldir
    STREAM_URL = args.streamurl
    GRAPH_NAME = args.graph
    LABELMAP_NAME = args.labels
    TFLite_detection_stream.min_conf_threshold = float(args.threshold)
    TFLite_detection_stream.resW, TFLite_detection_stream.resH = args.resolution.split('x')
    TFLite_detection_stream.imW, TFLite_detection_stream.imH = int(TFLite_detection_stream.resW), int(TFLite_detection_stream.resH)
    use_TPU = args.edgetpu
    TFLite_detection_stream.FEED_URL = str(args.ip) + ":" + str(args.port)
    CHANNELS = args.channels

    # Import TensorFlow libraries
    # If tflite_runtime is installed, import interpreter from tflite_runtime, else import from regular tensorflow
    # If using Coral Edge TPU, import the load_delegate library
    pkg = importlib.util.find_spec('tflite_runtime')
    if pkg:
        from tflite_runtime.interpreter import Interpreter
        if use_TPU:
            from tflite_runtime.interpreter import load_delegate
    else:
        from tensorflow.lite.python.interpreter import Interpreter
        if use_TPU:
            from tensorflow.lite.python.interpreter import load_delegate

    # If using Edge TPU, assign filename for Edge TPU model
    if use_TPU:
        # If user has specified the name of the .tflite file, use that name, otherwise use default 'edgetpu.tflite'
        if (GRAPH_NAME == 'detect.tflite'):
            GRAPH_NAME = 'edgetpu.tflite'       

    # Get path to current working directory
    TFLite_detection_stream.CWD_PATH = os.getcwd()

    # Path to .tflite file, which contains the model that is used for object detection
    PATH_TO_CKPT = os.path.join(TFLite_detection_stream.CWD_PATH,MODEL_NAME,GRAPH_NAME)

    # Path to label map file
    PATH_TO_LABELS = os.path.join(TFLite_detection_stream.CWD_PATH,MODEL_NAME,LABELMAP_NAME)

    # Load the label map
    with open(PATH_TO_LABELS, 'r') as f:
        TFLite_detection_stream.labels = [line.strip() for line in f.readlines()]

    # Have to do a weird fix for label map if using the COCO "starter model" from
    # https://www.tensorflow.org/lite/models/object_detection/overview
    # First label is '???', which has to be removed.
    if TFLite_detection_stream.labels[0] == '???':
        del(TFLite_detection_stream.labels[0])

    # Load the Tensorflow Lite model.
    # If using Edge TPU, use special load_delegate argument
    if use_TPU:
        TFLite_detection_stream.interpreter = Interpreter(model_path=PATH_TO_CKPT,
                                experimental_delegates=[load_delegate('libedgetpu.so.1.0')])
        print(PATH_TO_CKPT)
    else:
        TFLite_detection_stream.interpreter = Interpreter(model_path=PATH_TO_CKPT)

    TFLite_detection_stream.interpreter.allocate_tensors()

    # Get model details
    TFLite_detection_stream.input_details = TFLite_detection_stream.interpreter.get_input_details()
    TFLite_detection_stream.output_details = TFLite_detection_stream.interpreter.get_output_details()
    TFLite_detection_stream.height = TFLite_detection_stream.input_details[0]['shape'][1]
    TFLite_detection_stream.width = TFLite_detection_stream.input_details[0]['shape'][2]

    TFLite_detection_stream.floating_model = (TFLite_detection_stream.input_details[0]['dtype'] == np.float32)

    TFLite_detection_stream.input_mean = 127.5
    TFLite_detection_stream.input_std = 127.5

    # Check output layer name to determine if this model was created with TF2 or TF1,
    # because outputs are ordered differently for TF2 and TF1 models
    outname = TFLite_detection_stream.output_details[0]['name']

    if ('StatefulPartitionedCall' in outname): # This is a TF2 model
        TFLite_detection_stream.boxes_idx, TFLite_detection_stream.classes_idx, TFLite_detection_stream.scores_idx = 1, 3, 0
    else: # This is a TF1 model
        TFLite_detection_stream.boxes_idx, TFLite_detection_stream.classes_idx, TFLite_detection_stream.scores_idx = 0, 1, 2

    # Initialize cameras for detection
    for idx, cam_name in enumerate(TFLite_detection_stream.CAMERAS):
        # print(cam_name)
        channel_str= "channel=" + str(idx + 1)
        stream = VideoStream(resolution=(TFLite_detection_stream.imW,TFLite_detection_stream.imH), framerate=30, stream_url=STREAM_URL.replace("channel=1", channel_str))
        TFLite_detection_stream.CAMERAS.update({cam_name:[stream.start(), None, 0]})

    # start a thread that will perform motion detection
    t = threading.Thread(target=TFLite_detection_stream.detection)
    t.daemon = True
    t.start()

    # start the flask app
    flask_thread = FlaskThread(args)
    flask_thread.start()

    # start services
    telegram.start_bot()

    # Clean up
    for cam in TFLite_detection_stream.CAMERAS:
        TFLite_detection_stream.CAMERAS.get(cam)[0].stop()
        logging.info(f'stopped cam stream: {cam}')

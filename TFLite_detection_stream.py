######## Video Stream Object Detection Using Tensorflow-trained Classifier #########
#
# Author: Evan Juras (update by JanT)
# Date: 10/27/19 (updated 12/4/2019)
# Description: 
# This program uses a TensorFlow Lite model to perform object detection on a live video stream.
# It draws boxes and scores around the objects of interest in each frame from the
# stream. To improve FPS, the webcam object runs in a separate thread from the main program.
# This script will work with codecs supported by CV2 (e.g. MJPEG, RTSP, ...).
#
# This code is based off the TensorFlow Lite image classification example at:
# https://github.com/tensorflow/tensorflow/blob/master/tensorflow/lite/examples/python/label_image.py
#
# I added my own method of drawing boxes and labels using OpenCV.

# Import packages
import os
import argparse
import cv2
import numpy as np
import sys
import time
import threading
from threading import Thread
import importlib.util
import send_message
import datetime


from flask import Response
from flask import Flask
from flask import render_template

import psutil

# Define VideoStream class to handle streaming of video from webcam in separate processing thread
# Source - Adrian Rosebrock, PyImageSearch: https://www.pyimagesearch.com/2015/12/28/increasing-raspberry-pi-fps-with-python-and-opencv/
class VideoStream:
    """Camera object that controls video streaming"""
    def __init__(self,resolution=(640,480),framerate=30):
        # Initialize the PiCamera and the camera image stream
        self.stream = cv2.VideoCapture(STREAM_URL)
        ret = self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        ret = self.stream.set(3,resolution[0])
        ret = self.stream.set(4,resolution[1])
            
        # Read first frame from the stream
        (self.grabbed, self.frame) = self.stream.read()

	# Variable to control when the camera is stopped
        self.stopped = False

    def start(self):
	# Start the thread that reads frames from the video stream
        Thread(target=self.update,args=()).start()
        return self

    def update(self):
        # Keep looping indefinitely until the thread is stopped
        while True:
            # If the camera is stopped, stop the thread
            if self.stopped:
                # Close camera resources
                self.stream.release()
                return

            # Otherwise, grab the next frame from the stream
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
	# Return the most recent frame
        return self.frame

    def stop(self):
	# Indicate that the camera and thread should be stopped
        self.stopped = True

# Define and parse input arguments
parser = argparse.ArgumentParser()
parser.add_argument('--modeldir', help='Folder the .tflite file is located in',
                    required=True)
parser.add_argument('--streamurl', help='The full URL of the video stream e.g. http://ipaddress:port/stream/video.mjpeg',
                    required=True)
parser.add_argument('--graph', help='Name of the .tflite file, if different than detect.tflite',
                    default='detect.tflite')
parser.add_argument('--labels', help='Name of the labelmap file, if different than labelmap.txt',
                    default='labelmap.txt')
parser.add_argument('--threshold', help='Minimum confidence threshold for displaying detected objects',
                    default=0.5)
parser.add_argument('--resolution', help='Desired webcam resolution in WxH. If the webcam does not support the resolution entered, errors may occur.',
                    default='1280x720')
parser.add_argument('--edgetpu', help='Use Coral Edge TPU Accelerator to speed up detection',
                    action='store_true')
parser.add_argument("-i", "--ip", type=str, required=True,
    help="ip address of the device")
parser.add_argument("-o", "--port", type=int, required=True,
    help="ephemeral port number of the server (1024 to 65535)")

args = parser.parse_args()

start_time = datetime.datetime.now()

MODEL_NAME = args.modeldir
STREAM_URL = args.streamurl
GRAPH_NAME = args.graph
LABELMAP_NAME = args.labels
min_conf_threshold = float(args.threshold)
resW, resH = args.resolution.split('x')
imW, imH = int(resW), int(resH)
use_TPU = args.edgetpu

feed_url = str(args.ip) + ":" + str(args.port)

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
CWD_PATH = os.getcwd()

# Path to .tflite file, which contains the model that is used for object detection
PATH_TO_CKPT = os.path.join(CWD_PATH,MODEL_NAME,GRAPH_NAME)

# Path to label map file
PATH_TO_LABELS = os.path.join(CWD_PATH,MODEL_NAME,LABELMAP_NAME)

# Load the label map
with open(PATH_TO_LABELS, 'r') as f:
    labels = [line.strip() for line in f.readlines()]

# Have to do a weird fix for label map if using the COCO "starter model" from
# https://www.tensorflow.org/lite/models/object_detection/overview
# First label is '???', which has to be removed.
if labels[0] == '???':
    del(labels[0])

# Load the Tensorflow Lite model.
# If using Edge TPU, use special load_delegate argument
if use_TPU:
    interpreter = Interpreter(model_path=PATH_TO_CKPT,
                              experimental_delegates=[load_delegate('libedgetpu.so.1.0')])
    print(PATH_TO_CKPT)
else:
    interpreter = Interpreter(model_path=PATH_TO_CKPT)

interpreter.allocate_tensors()

# Get model details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
height = input_details[0]['shape'][1]
width = input_details[0]['shape'][2]

floating_model = (input_details[0]['dtype'] == np.float32)

input_mean = 127.5
input_std = 127.5

# Check output layer name to determine if this model was created with TF2 or TF1,
# because outputs are ordered differently for TF2 and TF1 models
outname = output_details[0]['name']

if ('StatefulPartitionedCall' in outname): # This is a TF2 model
    boxes_idx, classes_idx, scores_idx = 1, 3, 0
else: # This is a TF1 model
    boxes_idx, classes_idx, scores_idx = 0, 1, 2

# Initialize frame rate calculation
frame_rate_calc = 1
freq = cv2.getTickFrequency()

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
outputFrame = None
lock = threading.Lock()

# initialize a flask object
app = Flask(__name__)        

# Initialize video stream
videostream = VideoStream(resolution=(imW,imH),framerate=30).start()
time.sleep(1)

# IP camera RTSP URLs
CAMERAS = {
    "rtsp://admin:23578LockDown!40@192.168.100.12:554/cam/realmonitor?channel=1&subtype=1": "DRIVEWAY",
    "rtsp://admin:23578LockDown!40@192.168.100.12:554/cam/realmonitor?channel=2&subtype=0": "FRONT_PORCH",
    "rtsp://admin:23578LockDown!40@192.168.100.12:554/cam/realmonitor?channel=3&subtype=0": "SW_YARD",
    "rtsp://admin:23578LockDown!40@192.168.100.12:554/cam/realmonitor?channel=4&subtype=0": "W_PORCH",
    "rtsp://admin:23578LockDown!40@192.168.100.12:554/cam/realmonitor?channel=5&subtype=0": "N_YARD",
    "rtsp://admin:23578LockDown!40@192.168.100.12:554/cam/realmonitor?channel=6&subtype=0": "NE_YARD"
}

# Used for cooloff time between sending consecutive notification messages
message_time = datetime.datetime(1900, 1, 1)

@app.route("/")
def index():
	# return the rendered template
    return render_template("index.html")

def generate_frame():
	# grab global references to the output frame and lock variables
	global outputFrame, lock
	# loop over frames from the output stream
	while True:
		# wait until the lock is acquired
		with lock:
			# check if the output frame is available, otherwise skip
			# the iteration of the loop
			if outputFrame is None:
				continue
			# encode the frame in JPEG format
			(flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
			# ensure the frame was successfully encoded
			if not flag:
				continue
		# yield the output frame in the byte format
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
			bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
	# return the response generated along with the specific media
	# type (mime type)
	return Response(generate_frame(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")    

@app.route("/stats")
def stats():
	# return the response generated along with the specific media
	# type (mime type)
    def generate():

        while True:
            memory = psutil.virtual_memory()
            # Divide from Bytes -> KB -> MB
            available = round(memory.available/1024.0/1024.0,1)
            total = round(memory.total/1024.0/1024.0,1)

            disk = psutil.disk_usage('/')
            # Divide from Bytes -> KB -> MB -> GB
            free = round(disk.free/1024.0/1024.0/1024.0,1)
            total = round(disk.total/1024.0/1024.0/1024.0,1)

            uptime = datetime.datetime.now() - start_time
            # uptime = str(uptime.days) + " days " + str(uptime.seconds // 3600) + " hours " + str(uptime.seconds // 60) + " minutes "
 
            stats = """\
                Server uptime: %s\nCPU temperature: %s °C\nMemory: %s\nDisk: %s
            """%(str(uptime), 
                 str(psutil.cpu_percent()), 
                 str(available) + 'MB free / ' + str(total) + 'MB total ( ' + str(memory.percent) + '% )', 
                 str(free) + 'GB free / ' + str(total) + 'GB total ( ' + str(disk.percent) + '% )'
                )
            yield stats
            time.sleep(0.5)

    return Response(generate(), mimetype='text/plain')
    # while True:
    #     # with app.open_resource('./static/rpistats.txt') as f:
    #     #     stats = f.read()
    
    #     return Response(str(psutil.cpu_percent()) + '%', mimetype='text/plain')

# Main function for performing detection and notifying users of activity
def detection():
    global frame_rate_calc, outputFrame, message_time, CAMERAS, videostream, freq, feed_url, CWD_PATH

    #for frame1 in camera.capture_continuous(rawCapture, format="bgr",use_video_port=True):
    while True:

        # Start timer (for calculating frame rate)
        t1 = cv2.getTickCount()

        # Grab frame from video stream
        frame1 = videostream.read()

        # Acquire frame and resize to expected shape [1xHxWx3]
        frame = frame1.copy()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (width, height))
        input_data = np.expand_dims(frame_resized, axis=0)

        # Normalize pixel values if using a floating model (i.e. if model is non-quantized)
        if floating_model:
            input_data = (np.float32(input_data) - input_mean) / input_std

        # Perform the actual detection by running the model with the image as input
        interpreter.set_tensor(input_details[0]['index'],input_data)
        interpreter.invoke()

        # Retrieve detection results
        boxes = interpreter.get_tensor(output_details[boxes_idx]['index'])[0] # Bounding box coordinates of detected objects
        classes = interpreter.get_tensor(output_details[classes_idx]['index'])[0] # Class index of detected objects
        scores = interpreter.get_tensor(output_details[scores_idx]['index'])[0] # Confidence of detected objects

        # Loop over all detections and draw detection box if confidence is above minimum threshold
        for i in range(len(scores)):
            if ((scores[i] > min_conf_threshold) and (scores[i] <= 1.0)):

                # Get bounding box coordinates and draw box
                # Interpreter can return coordinates that are outside of image dimensions, need to force them to be within image using max() and min()
                ymin = int(max(1,(boxes[i][0] * imH)))
                xmin = int(max(1,(boxes[i][1] * imW)))
                ymax = int(min(imH,(boxes[i][2] * imH)))
                xmax = int(min(imW,(boxes[i][3] * imW)))
                
                cv2.rectangle(frame, (xmin,ymin), (xmax,ymax), (10, 255, 0), 2)

                # Draw label
                object_name = labels[int(classes[i])] # Look up object name from "labels" array using class index
                label = '%s: %d%%' % (object_name, int(scores[i]*100)) # Example: 'person: 72%'
                labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2) # Get font size
                label_ymin = max(ymin, labelSize[1] + 10) # Make sure not to draw label too close to top of window
                cv2.rectangle(frame, (xmin, label_ymin-labelSize[1]-10), (xmin+labelSize[0], label_ymin+baseLine-10), (255, 255, 255), cv2.FILLED) # Draw white box to put label text in
                cv2.putText(frame, label, (xmin, label_ymin-7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2) # Draw label text

                # Handle notifications based on detection results
                current_time = datetime.datetime.now()

                if object_name == 'person' and current_time >= (message_time + datetime.timedelta(minutes = 5)):
                    
                    # snapshot = frame.copy()

                    filepath = CWD_PATH + "/snapshot.jpeg"

                    cv2.imwrite(filepath, frame)

                    send_message.send_message(CAMERAS[STREAM_URL], current_time, feed_url, filepath)

                    message_time = current_time

        # Draw framerate in corner of frame
        cv2.putText(frame,'FPS: {0:.2f}'.format(frame_rate_calc),(30,50),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,0),2,cv2.LINE_AA)

        # All the results have been drawn on the frame, so it's time to display it.
        # cv2.imshow('SeamNet', frame) # uncomment for local video display

        with lock:
            outputFrame = frame.copy()

        # Calculate framerate
        t2 = cv2.getTickCount()
        time1 = (t2-t1)/freq
        frame_rate_calc= 1/time1

        # Press 'q' to quit
        if cv2.waitKey(1) == ord('q'):
            break

# start a thread that will perform motion detection
t = threading.Thread(target=detection)
t.daemon = True
t.start()

# start the flask app
app.run(host=args.ip, port=args.port, debug=True,
    threaded=True, use_reloader=False)          

# Clean up
cv2.destroyAllWindows()
videostream.stop()

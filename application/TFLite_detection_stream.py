# Video Stream Object Detection Using Tensorflow-trained Classifier
#
# This program uses a TensorFlow Lite model to perform object detection on a live video stream.
# To improve FPS, the webcam object runs in a separate thread from the main program.
# This script will work with codecs supported by CV2 (e.g. MJPEG, RTSP, ...).

# import security as vault
import numpy as np

# import os
# import argparse
# import driver
import cv2
import time
import threading
# import importlib.util
import datetime
# import psutil

from application.services import sms_service

# from flask import Flask, Response, request, make_response, render_template, jsonify
# from video_stream import VideoStream

# Global variables

min_conf_threshold = 0
resW, resH = 0, 0
imW, imH = 0, 0
FEED_URL = ""
CWD_PATH = ""
floating_model = None
interpreter = None
input_details = None 
output_details = None
labels = None
height = None
width = None
input_mean = 0 
input_std = 0 
boxes_idx = 0 
classes_idx = 0
scores_idx = 0

# START_TIME = time.time()

# MODEL_NAME = ""
# STREAM_URL = ""
# GRAPH_NAME = ""
# LABELMAP_NAME = ""
# min_conf_threshold = 0
# resW, resH = 0, 0
# imW, imH = 0, 0
# use_TPU = False
# IP = ""
# PORT = ""
# FEED_URL = ""

# CWD_PATH = ""
# PATH_TO_CKPT = ""
# PATH_TO_LABELS = ""

# interpreter = None
# input_details = None 
# height = None 
# width = None 
# input_mean = None 
# input_std = None 
# boxes_idx = None 
# classes_idx = None 
# scores_idx = None

# initialize a flask object
# MOVE TO APPLICATION MODULE
# app = Flask(__name__)    

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
# driveway_frame = None
# front_porch_frame = None
# sw_yard_frame = None
# w_porch_frame = None
# n_yard_frame = None
# ne_yard_frame = None

CAMERAS = {
    # cam_name : [stream, frame]
    "Driveway" : [None, None],
    "Front Porch" : [None, None],
    "SW Yard" : [None, None],
    "W Porch" : [None, None],
    "N Yard" : [None, None],
    "NE Yard" : [None, None]
}

lock = threading.Lock()

# IP camera names
# CAMERAS = ["Driveway", "Front Porch", "SW Yard", "W Porch", "N Yard", "NE Yard"]

# Used for cooloff time between sending consecutive notification messages
message_time = datetime.datetime(1900, 1, 1)

# Initialize frame rate calculation
frame_rate_calc = 1
freq = cv2.getTickFrequency()

def generate_frame(cam):
	# grab global references to the output frame and lock variables
    global lock

    cam = cam.replace("_", " ")

    # loop over frames from the output stream
    while True:
        # frame = None
    
        frame = CAMERAS.get(cam)[1]
        # if (cam == "driveway"):
        #     frame = driveway_frame
        # if (cam == "front_porch"):
        #     frame = front_porch_frame
        # if (cam == "sw_yard"):
        #     frame = sw_yard_frame
        # if (cam == "w_porch"):
        #     frame = w_porch_frame
        # if (cam == "n_yard"):
        #     frame = n_yard_frame
        # if (cam == "ne_yard"):
        #     frame = ne_yard_frame

        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if frame is None:
                continue

            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", frame)

            # ensure the frame was successfully encoded
            if not flag:
                continue

        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(encodedImage) + b'\r\n')

def draw_detection_box(i, frame, labels, boxes, classes, scores):
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

    return object_name

def prepare_notification(object_name, frame, idx):
    global message_time

    current_time = datetime.datetime.now()
    if object_name == 'person' and current_time >= (message_time + datetime.timedelta(minutes = 5)):
        filepath = CWD_PATH + "/snapshot.jpeg"
        cv2.imwrite(filepath, frame)
        sms_service.send_message(list(CAMERAS.keys())[idx], current_time, FEED_URL, filepath)
        message_time = current_time

# Main function for performing detection and notifying users of activity
def detection():
    global frame_rate_calc, message_time, freq, labels, CAMERAS, interpreter, width, height, input_mean, input_std, input_details, output_details, boxes_idx, scores_idx, classes_idx, min_conf_threshold

    while True:

        # Start timer (for calculating frame rate)
        t1 = cv2.getTickCount()

        frames = [] # frames (of any cam) to run detection on

        # Grab frame from video stream
        # frame1 = DRIVEWAY.read()
        for stream in CAMERAS.keys():
            pic = CAMERAS.get(stream)[0].read()
            CAMERAS[stream][1] = pic
            frames.append(pic)

        # frame2 = FRONT_PORCH.read()
        # frame3 = SW_YARD.read()
        # frame4 = W_PORCH.read()
        # frame5 = N_YARD.read()
        # frame6 = NE_YARD.read()

        for idx, f in enumerate(frames):
            # Force only use driveway. This can be removed if we
            # want to add detection on the other cameras.
            if idx != 0:
                break

            # Acquire frame and resize to expected shape [1xHxWx3]
            frame = f
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
                    object_name = draw_detection_box(i, frame, labels, boxes, classes, scores)

                    # Handle notifications based on detection results
                    prepare_notification(object_name, frame, idx)

            # Draw framerate in corner of frame
            # cv2.putText(frame,'FPS: {0:.2f}'.format(frame_rate_calc),(30,50),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,0),2,cv2.LINE_AA)

            frames[idx] = frame

        # All the results have been drawn on the frame, so it's time to display it.
        # cv2.imshow('SeamNet', frame) # uncomment for local video display

        with lock:
            for idx, cam in enumerate(CAMERAS.keys()):
                CAMERAS.get(cam)[1] = frames[idx].copy()
            # driveway_frame = frames[0].copy()
            # front_porch_frame = frame2.copy()
            # sw_yard_frame = frame3.copy()
            # w_porch_frame = frame4.copy()
            # n_yard_frame = frame5.copy()
            # ne_yard_frame = frame6.copy()

        # Calculate framerate
        t2 = cv2.getTickCount()
        time1 = (t2-t1)/freq
        frame_rate_calc= 1/time1

        # Press 'q' to quit
        if cv2.waitKey(1) == ord('q'):
            break

# def set_confidence():

if __name__ == '__main__':#'application.TFLite_detection_stream':
    # generate_frame()
    # detection()
    pass

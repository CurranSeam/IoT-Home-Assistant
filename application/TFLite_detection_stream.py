# Video Stream Object Detection Using Tensorflow-trained Classifier
#
# This program uses a TensorFlow Lite model to perform object detection on a live video stream.
# To improve FPS, the webcam object runs in a separate thread from the main program.
# This script will work with codecs supported by CV2 (e.g. MJPEG, RTSP, ...).

import numpy as np
import cv2
import threading
import datetime

from application.services import telegram
from application.services import sms_service

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

CAMERAS = {
    # cam_name : [stream, frame, active]
    "Driveway" : [None, None, 0],
    "Front Porch" : [None, None, 0],
    "SW Yard" : [None, None, 0],
    "W Porch" : [None, None, 0],
    "N Yard" : [None, None, 0],
    "NE Yard" : [None, None, 0]
}

lock = threading.Lock()

# Timestamp of a sent notification message
message_time = datetime.datetime(1900, 1, 1)

# Time-delta of the transmission of consecutive notification messages
message_cooloff = datetime.timedelta(seconds=15)

# Initialize frame rate calculation
frame_rate_calc = 1
freq = cv2.getTickFrequency()

def generate_frame(cam):
	# grab global reference the lock
    global lock

    cam = cam.replace("_", " ")

    # loop over frames from the output stream
    while True:
        frame = CAMERAS.get(cam)[1]

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
    global message_time, message_cooloff

    current_time = datetime.datetime.now()
    if object_name == 'person' and current_time >= (message_time + message_cooloff):
        filepath = CWD_PATH + "/snapshot.jpeg"
        cv2.imwrite(filepath, frame)
        telegram.send_detection_message(list(CAMERAS.keys())[idx], current_time, FEED_URL, filepath)
        message_time = current_time

# Main function for performing detection and notifying users of activity
def detection():
    global frame_rate_calc, message_time, freq, labels, CAMERAS, interpreter, width, height, input_mean, input_std, input_details, output_details, boxes_idx, scores_idx, classes_idx, min_conf_threshold

    while True:

        # Start timer (for calculating frame rate)
        t1 = cv2.getTickCount()

        frames = [] # frames (of any cam) to run detection on
        keys = list(CAMERAS.keys())

        # Grab frame from video stream
        for stream in CAMERAS.keys():
            pic = CAMERAS.get(stream)[0].read()
            frames.append(pic)

        for idx, f in enumerate(frames):
            # Force only use driveway. This can be removed if we
            # want to add detection on the other cameras.

            # Only do detection on selected cameras.
            if not CAMERAS.get(keys[idx])[2]:
                continue

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

        # All the results have been drawn on the frame, so it's time to display it.
        # cv2.imshow('SeamNet', frame) # uncomment for local video display

        with lock:
            for idx, cam in enumerate(CAMERAS.keys()):
                CAMERAS.get(cam)[1] = frames[idx]

        # Calculate framerate
        t2 = cv2.getTickCount()
        time1 = (t2-t1)/freq
        frame_rate_calc= 1/time1

        # Press 'q' to quit
        if cv2.waitKey(1) == ord('q'):
            break

if __name__ == '__main__':
    pass

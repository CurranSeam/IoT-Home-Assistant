# Video Stream Object Detection Using Tensorflow-trained Classifier
#
# This program uses a TensorFlow Lite model to perform object detection on a live video stream.
# To improve FPS, the webcam object runs in a separate thread from the main program.
# This script will work with codecs supported by CV2 (e.g. MJPEG, RTSP, ...).

# Import packages
import os
import argparse
import cv2
import numpy as np
import time
import threading
import importlib.util
import send_message
import datetime
import security as vault

from flask import Flask, Response, request, make_response, render_template
from video_stream import VideoStream

import psutil

# Global variables
START_TIME = time.time()

MODEL_NAME = ""
STREAM_URL = ""
GRAPH_NAME = ""
LABELMAP_NAME = ""
min_conf_threshold = 0
resW, resH = 0, 0
imW, imH = 0, 0
use_TPU = False
IP = ""
PORT = ""
FEED_URL = ""

CWD_PATH = ""
PATH_TO_CKPT = ""
PATH_TO_LABELS = ""

interpreter = None
input_details = None 
height = None 
width = None 
input_mean = None 
input_std = None 
boxes_idx = None 
classes_idx = None 
scores_idx = None

# initialize a flask object
app = Flask(__name__)    

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
driveway_frame = None
front_porch_frame = None
sw_yard_frame = None
w_porch_frame = None
n_yard_frame = None
ne_yard_frame = None

DRIVEWAY = None
FRONT_PORCH = None
SW_YARD = None
W_PORCH = None
N_YARD = None
NE_YARD = None

lock = threading.Lock()

# IP camera names
CAMERAS = ["Driveway", "Front Porch", "SW Yard", "W Porch", "N Yard", "NE Yard"]

# Used for cooloff time between sending consecutive notification messages
message_time = datetime.datetime(1900, 1, 1)

# Initialize frame rate calculation
frame_rate_calc = 1
freq = cv2.getTickFrequency()

@app.route("/")
def index():
	# return the rendered template
    try:
        # Authenticate username and password against the Vault.
        vault.authenticate(request.authorization.username, "login", 0)
        vault.authenticate(request.authorization.password, "login", 1)
    except:
        return make_response('Could not verify!', 401, {'WWW-Authenticate' : 'Basic realm="Login Required"'})
    print("DO WE MAKE IT?")
    return render_template("index.html")

def generate_frame(cam):
	# grab global references to the output frame and lock variables
    global driveway_frame, front_porch_frame, sw_yard_frame, w_porch_frame, n_yard_frame, ne_yard_frame, lock 

    # loop over frames from the output stream
    while True:
        frame = None
    
        if (cam == "driveway"):
            frame = driveway_frame
        if (cam == "front_porch"):
            frame = front_porch_frame
        if (cam == "sw_yard"):
            frame = sw_yard_frame
        if (cam == "w_porch"):
            frame = w_porch_frame
        if (cam == "n_yard"):
            frame = n_yard_frame
        if (cam == "ne_yard"):
            frame = ne_yard_frame

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

@app.route("/video_feed/<string:cam>/", methods=["GET"])
def video_feed(cam):
	# return the response generated along with the specific media
	# type (mime type)
    return Response(generate_frame(cam),
		mimetype = "multipart/x-mixed-replace; boundary=frame")    

@app.route("/active_cam", methods=['POST'])
def active_cam():
    global active_cam
    cam = request.form['active_cam']
    active_cam = cam.split("/")[-2]
    
    return cam

@app.route("/stats")
def stats():
    global frame_rate_calc
	# return the response generated along with the specific media
	# type (mime type)
    def generate():
        while True:
            memory = psutil.virtual_memory()

            # Divide from Bytes -> KB -> MB
            available = round(memory.available/1024.0/1024.0,1)
            mem_total = round(memory.total/1024.0/1024.0,1)

            disk = psutil.disk_usage('/')

            # Divide from Bytes -> KB -> MB -> GB
            free = round(disk.free/1024.0/1024.0/1024.0,1)
            disk_total = round(disk.total/1024.0/1024.0/1024.0,1)

            time_dif = time.time() - START_TIME
            d = divmod(time_dif, 86400) # days
            h = divmod(d[1],3600)  # hours
            m = divmod(h[1],60)  # minutes
            s = m[1] # seconds

            uptime = "%d days, %d hours, %d minutes, %d seconds" % (d[0],h[0],m[0], s)
 
            stats = """\
                FPS: %s\nServer uptime: %s\nCPU temperature: %s °C\nMemory: %s\nDisk: %s
            """%(str(int(frame_rate_calc)),
                 str(uptime), 
                 str(psutil.cpu_percent()), 
                 str(available) + 'MB free / ' + str(mem_total) + 'MB total ( ' + str(memory.percent) + '% )', 
                 str(free) + 'GB free / ' + str(disk_total) + 'GB total ( ' + str(disk.percent) + '% )'
                )
            yield stats
            time.sleep(0.1)

    return Response(generate(), mimetype='text/plain')

# Main function for performing detection and notifying users of activity
def detection():
    global frame_rate_calc, driveway_frame, front_porch_frame, sw_yard_frame, w_porch_frame, n_yard_frame, ne_yard_frame, message_time, CAMERAS, DRIVEWAY, freq, FEED_URL, CWD_PATH, active_cam

    while True:

        # Start timer (for calculating frame rate)
        t1 = cv2.getTickCount()

        # Grab frame from video stream
        frame1 = DRIVEWAY.read()
        frame2 = FRONT_PORCH.read()
        frame3 = SW_YARD.read()
        frame4 = W_PORCH.read()
        frame5 = N_YARD.read()
        frame6 = NE_YARD.read()


        frames = [frame1] # frames (of any cam) to run detection on

        for idx, f in enumerate(frames):
            # Acquire frame and resize to expected shape [1xHxWx3]
            frame = f.copy()
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

                        filepath = CWD_PATH + "/snapshot.jpeg"

                        cv2.imwrite(filepath, frame)

                        send_message.send_message(CAMERAS[idx], current_time, FEED_URL, filepath)

                        message_time = current_time

            # Draw framerate in corner of frame
            # cv2.putText(frame,'FPS: {0:.2f}'.format(frame_rate_calc),(30,50),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,0),2,cv2.LINE_AA)

            frames[idx] = frame

        # All the results have been drawn on the frame, so it's time to display it.
        # cv2.imshow('SeamNet', frame) # uncomment for local video display

        with lock:
            driveway_frame = frames[0].copy()
            front_porch_frame = frame2.copy()
            sw_yard_frame = frame3.copy()
            w_porch_frame = frame4.copy()
            n_yard_frame = frame5.copy()
            ne_yard_frame = frame6.copy()

        # Calculate framerate
        t2 = cv2.getTickCount()
        time1 = (t2-t1)/freq
        frame_rate_calc= 1/time1

        # Press 'q' to quit
        if cv2.waitKey(1) == ord('q'):
            break

if __name__ == "__main__":
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

    MODEL_NAME = args.modeldir
    STREAM_URL = args.streamurl
    GRAPH_NAME = args.graph
    LABELMAP_NAME = args.labels
    min_conf_threshold = float(args.threshold)
    resW, resH = args.resolution.split('x')
    imW, imH = int(resW), int(resH)
    use_TPU = args.edgetpu
    FEED_URL = str(args.ip) + ":" + str(args.port)

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

    # Initialize video stream
    DRIVEWAY = VideoStream(resolution=(imW,imH), framerate=30, stream_url=STREAM_URL).start()
    FRONT_PORCH = VideoStream(resolution=(imW,imH), framerate=30, stream_url=STREAM_URL.replace("channel=1", "channel=2")).start()
    SW_YARD = VideoStream(resolution=(imW,imH), framerate=30, stream_url=STREAM_URL.replace("channel=1", "channel=3")).start()
    W_PORCH = VideoStream(resolution=(imW,imH), framerate=30, stream_url=STREAM_URL.replace("channel=1", "channel=4")).start()
    N_YARD = VideoStream(resolution=(imW,imH), framerate=30, stream_url=STREAM_URL.replace("channel=1", "channel=5")).start()
    NE_YARD = VideoStream(resolution=(imW,imH), framerate=30, stream_url=STREAM_URL.replace("channel=1", "channel=6")).start()
    # time.sleep(1)

    # start a thread that will perform motion detection
    t = threading.Thread(target=detection)
    t.daemon = True
    t.start()

    # start the flask app
    app.run(host=args.ip, port=args.port, debug=True,
        threaded=True, use_reloader=False)          

    # Clean up
    cv2.destroyAllWindows()
    DRIVEWAY.stop()
    FRONT_PORCH.stop()
    SW_YARD.stop()
    W_PORCH.stop()
    N_YARD.stop()
    NE_YARD.stop()

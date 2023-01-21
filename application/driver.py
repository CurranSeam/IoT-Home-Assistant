# Setup for application including argument parser. 


from flask import Flask, Response, request, make_response, render_template, jsonify
from video_stream import VideoStream


# initialize a flask object
app = Flask(__name__)   









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



# def set_vault_state():
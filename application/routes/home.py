from application.services import security as vault
from application.services.video import object_detection

from flask import Response, request, jsonify, make_response, render_template, send_from_directory, Blueprint

bp = Blueprint('home', __name__)

@bp.route("/")
def index():
    try:
        # Authenticate username and password against the Vault.
        vault.authenticate(request.authorization.username, request.authorization.password)
    except:
        return make_response('Could not verify!', 401, {'WWW-Authenticate' : 'Basic realm="Login Required"'})

    return render_template("index.html")

@bp.route("/install")
def install():
    return render_template("install.html")

@bp.route('/sw.js', methods=['GET'])
def sw():
    return send_from_directory('static', 'sw.js')

# Detection
@bp.route("/video_feed/<string:cam>/", methods=["GET"])
def video_feed(cam):
	# return the response generated along with the specific media
	# type (mime type)
    return Response(object_detection.generate_frame(cam),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

@bp.route("/get_camera_data/<string:cam>")
def get_camera_data(cam):
    cameras, cameras_status = object_detection.get_camera_data()
    cameras = list(map(lambda x: x.replace(' ', '_'), cameras))

    idx = cameras.index(cam)
    detection = cameras_status[idx]

    if detection == 0:
        detection = "OFF"
    else:
        detection = "ON"
    return jsonify({'success': detection}), 200

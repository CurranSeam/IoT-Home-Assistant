import time
import datetime

from application import app
from application import TFLite_detection_stream
from application.services import security as vault
from application.services import svc_common
from application.services import telegram
from application.repository import user as User
from flask import Response, request, make_response, render_template, jsonify

# -------------------------------------------------------------------------------------------------
# HOME
@app.route("/")
def index():
	# return the rendered template
    try:
        # Authenticate username and password against the Vault.
        vault.authenticate(request.authorization.username, request.authorization.password)
    except:
        return make_response('Could not verify!', 401, {'WWW-Authenticate' : 'Basic realm="Login Required"'})
    return render_template("index.html")

# -------------------------------------------------------------------------------------------------
# SETTINGS
# Define the custom Jinja filter
@app.template_filter()
def zip_lists(a, b, c, d):
    return zip(a, b, c, d)

# Register the custom filter with Jinja
app.jinja_env.filters['zip'] = zip_lists

# Define the custom Jinja filter
@app.template_filter()
def zip_lists_detection(a, b):
    return zip(a, b)

# Register the custom filter with Jinja
app.jinja_env.filters['zip_detection'] = zip_lists_detection

@app.route("/settings")
def settings():
    cameras_status = []
    cameras = TFLite_detection_stream.CAMERAS.keys()

    names = User.get_first_names()
    tg_status = User.get_telegram_notify()
    sms_status = User.get_sms_notify()
    numbers = [f'XXX-XXX-{str(num)[-4:]}' for num in User.get_phone_numbers()]

    for key in cameras:
        cameras_status.append(TFLite_detection_stream.CAMERAS.get(key)[2])

    cooloff = TFLite_detection_stream.message_cooloff.total_seconds()
    return render_template("settings.html", users=names, telegram_statuses=tg_status,
                            sms_statuses = sms_status, phone_nums=numbers,
                            min_conf=TFLite_detection_stream.min_conf_threshold,
                            message_cooloff=cooloff, cams=cameras, cam_statuses=cameras_status)

@app.route('/users/<string:user>/<string:service>/notifications', methods=["PUT"])
def update_notification_status(user, service):
    data = request.get_json()
    notification_status = int(data['notification_status'])

    if service.lower() == "telegram":
        User.update_telegram_notify(user, notification_status)
    # sms
    else:
        User.update_sms_notify(user, notification_status)

    # Send notification of status change
    if notification_status:
        # we are opting in to notifications
        telegram.send_opt_message(user, True, service, TFLite_detection_stream.FEED_URL + "/settings")
    else:
        # opted out
        telegram.send_opt_message(user, False, service, TFLite_detection_stream.FEED_URL + "/settings")

    # Return a response to the frontend
    return jsonify({'success': True}), 200

@app.route("/settings/conf-threshold", methods=["PUT"])
def update_min_conf_threshold():
    data = request.get_json()
    new_threshold = float(data['new_conf_threshold'])
    TFLite_detection_stream.min_conf_threshold = new_threshold

    return jsonify({'success': True}), 200

@app.route("/settings/message-cooloff", methods=["PUT"])
def update_message_cooloff():
    data = request.get_json()
    cooloff_seconds = int(data['new_cooloff'])
    new_cooloff = datetime.timedelta(seconds=cooloff_seconds)
    TFLite_detection_stream.message_cooloff = new_cooloff

    return jsonify({'success': True}), 200

@app.route("/settings/<string:cam>/update-detection", methods=["PUT"])
def update_cam_detection_status(cam):
    data = request.get_json()
    new_state = int(data['detection_state'])
    TFLite_detection_stream.CAMERAS.get(cam)[2] = new_state

    return jsonify({'success': True}), 200

# -------------------------------------------------------------------------------------------------
# DETECTION
@app.route("/video_feed/<string:cam>/", methods=["GET"])
def video_feed(cam):
	# return the response generated along with the specific media
	# type (mime type)
    return Response(TFLite_detection_stream.generate_frame(cam),
		mimetype = "multipart/x-mixed-replace; boundary=frame")    

# DELETE IF UNUSED
# @app.route("/active_cam", methods=['POST'])
# def active_cam():
#     global active_cam
#     cam = request.form['active_cam']
#     active_cam = cam.split("/")[-2]
    
#     return cam

# -------------------------------------------------------------------------------------------------
# STATS
@app.route("/stats")
def stats():
    return render_template("stats.html")

@app.route("/get_stats")
def get_stats():
    global frame_rate_calc

    snap = request.args.get('snapshot', None)

	# return the response generated along with the specific media
	# type (mime type)
    def realtime():
        while True:
            yield svc_common.get_server_stats()
            time.sleep(0.1)

    def snapshot():
        return svc_common.get_server_stats(False)

    func = realtime if snap == None else snapshot
    return Response(func(), mimetype='text/plain')
# -------------------------------------------------------------------------------------------------

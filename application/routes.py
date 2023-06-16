import time
import datetime
import json

from application import app
from application import TFLite_detection_stream
from application.services import mqtt
from application.services import security as vault
from application.services import svc_common
from application.services import telegram
from application.repository import device as Device
from application.repository import reminder as Reminder
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
#DEVICES
@app.route("/devices")
def devices():
    users = User.get_users_by_id_asc()
    devices = {}

    for user in users:
        device_list = Device.get_devices_by_user(user.id)

        data = []
        if len(device_list) == 0:
            data.append({
                'name': "",
                'state': False,
                'tele_period': 0,
                'id': None
            })
        else:
            for d in device_list:
                data.append({
                    'name': d.name,
                    'state': d.is_on,
                    'tele_period': d.telemetry_period,
                    'id': d.id
                })

        devices[user.first_name] = data

    return render_template("devices.html", device_data=devices)

@app.route('/devices/<int:device_id>/toggle')
def toggle_device(device_id):
    device = Device.get_device(id=device_id)
    mqtt.power_toggle(device)

    return jsonify({'success': True}), 200

@app.route('/devices/<int:device_id>/telemetry-period', methods=["PUT"])
def update_telemetry_period(device_id):
    data = request.get_json()
    new_period = int(data['new_period'])

    device = Device.get_device(id=device_id)
    mqtt.update_telemetry_period(device, new_period)

    return jsonify({'success': True}), 200

# -------------------------------------------------------------------------------------------------
# REMINDERS

@app.route('/reminders')
def reminders():
    users = list(User.get_users_by_id_asc())
    reminders_list = []

    for user in users:
        reminders = Reminder.get_reminders_by_user(user)
        reminders_list.append(reminders)

    return render_template("reminders.html", users=users, reminders_list=reminders_list)

@app.route('/reminders/add-reminder', methods=['POST'])
def add_reminder():
    data = request.get_json()

    user_id = data['user_id']
    title = data['title']
    date = data['date']
    time = data['time']
    description = data['description']
    recurrence = data['recurrence']

    user = User.get_user(id=user_id)

    if date == '' or time == '' or title == '':
        return jsonify({'error': 'Title, Date, and Time fields are required'}), 400
    else:
        # Combine date and time inputs into a datetime object
        datetime_str = f"{date} {time}"
        reminder_datetime = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        Reminder.add_reminder(user, title, reminder_datetime, recurrence, description)

        return jsonify({'success': 'Reminder created successfully'})

@app.route('/reminders/delete-reminder', methods=["POST"])
def delete_reminder():
    data = request.get_json()
    reminder_id = data['reminder_id']
    user_firstname = data['user_firstname']
    reminder = Reminder.get_reminder(id=reminder_id)

    Reminder.delete_reminder(reminder_id)

    return jsonify({'success': f'{reminder.title} successfully deleted for {user_firstname} :O)'}), 200

# -------------------------------------------------------------------------------------------------
# SETTINGS

# Define the custom Jinja filters
@app.template_filter()
def zip_lists(a, b, c, d):
    return zip(a, b, c, d)

@app.template_filter()
def zip_lists_detection(a, b):
    return zip(a, b)

# Register the custom filters with Jinja
app.jinja_env.filters['zip'] = zip_lists
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

# -------------------------------------------------------------------------------------------------
# STATS
@app.route("/stats")
def stats():
    hostname = vault.get_value("APP", "config", "host")
    socket_port = vault.get_value("SOCKETS", "stats", "port")

    return render_template("stats.html", host=hostname, port=socket_port)

# Deprecated
# Can still hit endpoint in browser, but currently unused.
@app.route("/get_stats")
def get_stats():
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
    return json.dumps(func())

# -------------------------------------------------------------------------------------------------
#UTILITY
@app.route("/get_bot_username")
def get_bot_username():
    username = vault.get_value("APP", "config", "bot_username")
    return username

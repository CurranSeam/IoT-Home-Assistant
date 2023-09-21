import hashlib
import time
import datetime
import ipaddress
import json
import os
import requests
import urllib.parse

from application import app
from application.services import (mqtt,
                                  scheduler,
                                  security as vault,
                                  svc_common)
from application.repository import (device as Device,
                                    reminder as Reminder,
                                    temperature_sensor as TemperatureSensor,
                                    user as User)
from application.services.telegram import telegram
from application.services.video import object_detection
from application.utils.exception_handler import try_exec
from flask import Response, request, make_response, render_template, jsonify

@app.context_processor
def inject_shared_vars():
    server = f"{vault.get_value('APP', 'config', 'moniker')}Net"

    tg_identity = vault.get_value_encrypted("APP", "config", "telegram_identity")
    hash_object = hashlib.sha1(tg_identity)
    hashed_data = hash_object.hexdigest()

    return dict(hash=hashed_data, server=server)

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
        for d in device_list:
            data.append({
                'name': d.name,
                'state': d.is_on,
                'tele_period': d.telemetry_period,
                'id': d.id
            })

        devices[user.first_name] = data

    return render_template("devices.html", users=users, device_data=devices, scanned_devices=[])

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

@app.route('/devices/add-device', methods=["PUT"])
def add_device():
    data = request.get_json()
    ip_address = data['ip_address']
    device_name = data['device_name']

    if ip_address == '' or device_name == '':
        return jsonify({'error': "IP Address and Name fields are required"}), 400

    if ip_address in Device.get_ip_addresses():
        return jsonify({'error': "Device is already in use!"}), 400

    # Specifies the Subnet that the incoming IP address must reside in.
    # Matches on the first 16 bits of host IP address (i.e. xxx.xxx)
    network = f'{vault.get_value("APP", "config", "host")[:8]}0.0/16'

    try:
        ip = ipaddress.ip_address(ip_address)
        network = ipaddress.ip_network(network)

        if ip in network:
            url = f"http://{ip_address}"
            try:
                response = requests.get(url, timeout=3)

                # Check if device on the network is a tasmota device
                if response.status_code == 200 and "Tasmota" in response.text:
                    user_id = data['user_id']
                    user_firstname = data['user_firstname']

                    device = Device.add_device(user_id, device_name, ip_address)

                    device_full_topic = f'devices_{device.id}_%topic%/%prefix%/'
                    encoded_full_topic = urllib.parse.quote(device_full_topic, safe="")

                    request_params = {
                        "Topic" : device.name,
                        "FullTopic" : encoded_full_topic,
                        "MqttHost" : vault.get_value("APP", "config", "host")
                    }

                    for cmd in request_params:
                        payload = request_params[cmd]
                        url = f'http://{ip_address}/cm?cmnd={cmd}%20{payload}'
                        response = requests.get(url)
                    
                        if response.status_code != 200:
                            device = Device.delete_device(device.id)
                            return jsonify({'error': f'Failed to add {device_name} :O('}), response.status_code

                    mqtt.subscribe(device)
                    mqtt.write_power_state(device)

                    return jsonify({'success': f'{device_name} successfully added for {user_firstname} :O)'}), 200
            except requests.exceptions.RequestException:
                return jsonify({'error': f'{device_name} is unreachable :O('}), 400

            return jsonify({'error': f'{device_name} is not a Tasmota device :O('}), 400
        else:
            return jsonify({'error': f'{ip_address} is not on the LAN :O('}), 400

    except ValueError:
        return jsonify({'error': f'{ip_address} is an invalid IP address :O('}), 400

@app.route('/devices/delete-device', methods=["PUT"])
def delete_device():
    data = request.get_json()
    device_id = data['device_id']
    user_firstname = data['user_firstname']
    device = Device.get_device(id=device_id)

    mqtt.unsubscribe(device)
    Device.delete_device(device_id)

    return jsonify({'success': f'{device.name} successfully deleted for {user_firstname} :O)'}), 200

@app.route("/devices/scan")
def device_scan():
    new_scanned_devices = __scan_for_devices()

    if len(new_scanned_devices) == 0:
        return jsonify({'error': 'No devices found'})

    return jsonify(new_scanned_devices)

def __scan_for_devices():
    scan = []
    device_ip_addresses = Device.get_ip_addresses()

    for device in os.popen('arp -a'):
        ip_address = device.split(" ")[1].replace('(','').replace(')','')

        if ip_address not in device_ip_addresses:
            url = f"http://{ip_address}"

            try:
                response = requests.get(url, timeout=0.5)
                if response.status_code == 200 and "Tasmota" in response.text:
                    scan.append(ip_address)
            except requests.exceptions.RequestException:
                pass

    return scan

# -------------------------------------------------------------------------------------------------
#SENSORS

@app.route("/sensors")
def sensors():
    users = User.get_users_by_id_asc()
    temp_sensors = {}

    for user in users:
        temp_sensor_list = TemperatureSensor.get_sensors_by_user(user.id)

        data = []
        for t in temp_sensor_list:
            data.append({
                'location': t.location,
                'temperature': t.temperature,
                'temp_unit': t.temp_unit,
                'temp_delta_threshold': t.temp_delta_threshold,
                'id': t.id
            })

        temp_sensors[user.first_name] = data

    return render_template("sensors.html", users=users, sensor_data=temp_sensors, scanned_sensors=[])

@app.route('/sensors/add', methods=["PUT"])
def add_sensor():
    data = request.get_json()
    ip_address = data['ip_address']
    location = data['location']

    if ip_address == '' or location == '':
        return jsonify({'error': "IP Address and location fields are required"}), 400

    if ip_address in TemperatureSensor.get_ip_addresses():
        return jsonify({'error': "Sensor is already in use!"}), 400

    # Specifies the Subnet that the incoming IP address must reside in.
    # Matches on the first 16 bits of host IP address (i.e. xxx.xxx)
    network = f'{vault.get_value("APP", "config", "host")[:8]}0.0/16'

    try:
        ip = ipaddress.ip_address(ip_address)
        network = ipaddress.ip_network(network)

        if ip in network:
            url = f"http://{ip_address}/shelly"
            try:
                response = requests.get(url, timeout=3)

                if response.status_code == 200:
                    sensor_name = response.json()["id"]
                    user_id = data['user_id']
                    user_firstname = data['user_firstname']

                    sensor = TemperatureSensor.add_sensor(user_id, sensor_name, location, ip_address, "shelly")

                    url = f"http://{ip_address}/rpc"
                    mqtt_host = vault.get_value("APP", "config", "host")
                    mqtt_port = vault.get_value("APP", "config", "mqtt_port")


                    data = [
                        {
                            "id" : 1,
                            "method" : "HT_UI.SetConfig",
                            "params" : {
                                "config" : {
                                    "temperature_unit" : "F"
                                }
                            }
                        },
                        {
                            "id" : 1,
                            "method" :"Mqtt.SetConfig",
                            "params" : {
                                "config" : {
                                    "enable" : True,
                                    "server" : f"{mqtt_host}:{mqtt_port}",
                                    "topic_prefix" : f"sensors_{sensor.id}_{sensor.name}"
                                    }
                            }
                        },
                        {
                            "id" : 1,
                            "method" : "Shelly.Reboot"
                        }
                    ]

                    for idx, d in enumerate(data):
                        response = requests.post(url, data=json.dumps(d))

                        if response.status_code != 200:
                            TemperatureSensor.delete_sensor(sensor.id)
                            return jsonify({'error': f'Failed to add sensor :O('}), response.status_code

                        # Subscribe to topics and update data before sensor is rebooted.
                        if idx == len(data) - 1:
                            mqtt.subscribe(sensor)
                            mqtt.update_sensor_temp(sensor)

                    return jsonify({'success': f'Sensor successfully added for {user_firstname} :O)'}), 200
            except requests.exceptions.RequestException:
                return jsonify({'error': f'Sensor is unreachable :O('}), 400

            return jsonify({'error': f'Sensor is not a Shelly sensor :O('}), 400
        else:
            return jsonify({'error': f'{ip_address} is not on the LAN :O('}), 400

    except ValueError:
        return jsonify({'error': f'{ip_address} is an invalid IP address :O('}), 400

@app.route('/sensors/delete', methods=["PUT"])
def delete_sensor():
    data = request.get_json()
    sensor_id = data['sensor_id']
    user_firstname = data['user_firstname']
    temp_sensor = TemperatureSensor.get_sensor(id=sensor_id)

    mqtt.unsubscribe(temp_sensor)
    TemperatureSensor.delete_sensor(sensor_id)

    return jsonify({'success': f'Sensor successfully deleted for {user_firstname} :O)'}), 200

@app.route("/sensors/scan")
def sensor_scan():
    new_scanned_sensors = __scan_for_sensors()

    if len(new_scanned_sensors) == 0:
        return jsonify({'error': 'No sensor found'})

    return jsonify(new_scanned_sensors)

def __scan_for_sensors():
    scan = []
    sensor_ip_addresses = TemperatureSensor.get_ip_addresses()

    for sensor in os.popen('arp -a'):
        ip_address = sensor.split(" ")[1].replace('(','').replace(')','')

        if ip_address not in sensor_ip_addresses:
            url = f"http://{ip_address}/shelly"

            try:
                response = requests.get(url, timeout=0.5)

                if response.status_code == 200:
                    scan.append(ip_address)
            except requests.exceptions.RequestException:
                pass

    return scan

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

        reminder = Reminder.add_reminder(user, title, reminder_datetime, recurrence, description)
        ret, job = try_exec(scheduler.schedule_reminder, reminder)

        if not ret:
            Reminder.update_job_id(reminder, job.id)
            return jsonify({'success': 'Reminder created successfully'})

        Reminder.delete_reminder(reminder.id)
        return jsonify({'error': "Scheduling for the reminder was unsuccessful"}), 500

@app.route('/reminders/delete-reminder', methods=["POST"])
def delete_reminder():
    data = request.get_json()
    reminder_id = data['reminder_id']
    user_firstname = data['user_firstname']
    reminder = Reminder.get_reminder(id=reminder_id)

    scheduler.delete_job(reminder.job_id)
    Reminder.delete_reminder(reminder_id)

    return jsonify({'success': f'{reminder.title} successfully deleted for {user_firstname} :O)'}), 200

# -------------------------------------------------------------------------------------------------
# SETTINGS

# Define the custom Jinja filters
@app.template_filter()
def zip_lists(a, b, c, d, e, f):
    return zip(a, b, c, d, e, f)

@app.template_filter()
def zip_lists_detection(a, b):
    return zip(a, b)

# Register the custom filters with Jinja
app.jinja_env.filters['zip'] = zip_lists
app.jinja_env.filters['zip_detection'] = zip_lists_detection

@app.route("/settings")
def settings():
    cameras, cameras_status = object_detection.get_camera_data()

    names = User.get_first_names()
    ids = User.get_ids()

    tg_chat_ids = User.get_telegram_chat_ids()
    tg_status = User.get_telegram_notify()
    sms_status = User.get_sms_notify()
    numbers = [f'XXX-XXX-{str(num)[-4:]}' for num in User.get_phone_numbers()]

    cooloff = object_detection.message_cooloff.total_seconds()
    return render_template("settings.html", users=names, ids=ids, telegram_statuses=tg_status,
                            chat_ids=tg_chat_ids, sms_statuses=sms_status, phone_nums=numbers,
                            min_conf=object_detection.min_conf_threshold,
                            message_cooloff=cooloff, cams=cameras, cam_statuses=cameras_status)

@app.route('/users/<string:user_id>/<string:service>/notifications', methods=["PUT"])
def update_notification_status(user_id, service):
    data = request.get_json()
    notification_status = int(data['notification_status'])
    name = User.get_user(id=user_id).first_name
    settings_url = object_detection.FEED_URL + "/settings"

    if service.lower() == "telegram":
        User.update_telegram_notify(user_id, notification_status)
    # sms
    else:
        User.update_sms_notify(user_id, notification_status)

    # Send notification of status change
    if notification_status:
        # we are opting in to notifications
        telegram.send_opt_message(user_id, name, True, service, settings_url)
    else:
        # opted out
        telegram.send_opt_message(user_id, name, False, service, settings_url)

    # Return a response to the frontend
    return jsonify({'success': True}), 200

@app.route("/settings/conf-threshold", methods=["PUT"])
def update_min_conf_threshold():
    data = request.get_json()
    new_threshold = float(data['new_conf_threshold'])
    object_detection.min_conf_threshold = new_threshold

    return jsonify({'success': True}), 200

@app.route("/settings/message-cooloff", methods=["PUT"])
def update_message_cooloff():
    data = request.get_json()
    cooloff_seconds = int(data['new_cooloff'])
    new_cooloff = datetime.timedelta(seconds=cooloff_seconds)
    object_detection.message_cooloff = new_cooloff

    return jsonify({'success': True}), 200

@app.route("/settings/<string:cam>/update-detection", methods=["PUT"])
def update_cam_detection_status(cam):
    data = request.get_json()
    new_state = int(data['detection_state'])
    object_detection.CAMERAS.get(cam)[2] = new_state

    return jsonify({'success': True}), 200

# -------------------------------------------------------------------------------------------------
# DETECTION
@app.route("/video_feed/<string:cam>/", methods=["GET"])
def video_feed(cam):
	# return the response generated along with the specific media
	# type (mime type)
    return Response(object_detection.generate_frame(cam),
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

@app.route("/get_camera_data/<string:cam>")
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

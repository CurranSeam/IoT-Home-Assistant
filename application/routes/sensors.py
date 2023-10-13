import ipaddress
import os
import requests

from application.services import mqtt, security as vault
from application.repository import (temperature_sensor as TemperatureSensor,
                                    user as User)

from flask import request, render_template, json, jsonify, Blueprint

bp = Blueprint('sensors', __name__)

@bp.route("/sensors")
def sensors():
    users = User.get_users_by_id_asc()
    temp_sensors = {}

    for user in users:
        temp_sensor_list = TemperatureSensor.get_sensors_by_user(user.id)

        data = []
        for t in temp_sensor_list:
            data.append({
                'location': t.sensor.location,
                'temperature': t.temperature,
                'temp_unit': t.temp_unit,
                'temp_delta_threshold': t.temp_delta_threshold,
                'id': t.id
            })

        temp_sensors[user.first_name] = data

    return render_template("sensors.html", users=users, sensor_data=temp_sensors, scanned_sensors=[])

@bp.route('/sensors/add', methods=["PUT"])
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

                    t_sensor = TemperatureSensor.add_sensor(user_id, sensor_name, location, ip_address, "shelly")

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
                                    "topic_prefix" : f"sensors_{t_sensor.id}_{t_sensor.sensor.name}"
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
                            TemperatureSensor.delete_sensor(t_sensor.id)
                            return jsonify({'error': f'Failed to add sensor :O('}), response.status_code

                        # Subscribe to topics and update data before sensor is rebooted.
                        if idx == len(data) - 1:
                            mqtt.subscribe(t_sensor)
                            mqtt.update_sensor_temp(t_sensor)

                    return jsonify({'success': f'Sensor successfully added for {user_firstname} :O)'}), 200
            except requests.exceptions.RequestException:
                return jsonify({'error': f'Sensor is unreachable :O('}), 400

            return jsonify({'error': f'Sensor is not a Shelly sensor :O('}), 400
        else:
            return jsonify({'error': f'{ip_address} is not on the LAN :O('}), 400

    except ValueError:
        return jsonify({'error': f'{ip_address} is an invalid IP address :O('}), 400

@bp.route('/sensors/delete', methods=["PUT"])
def delete_sensor():
    data = request.get_json()
    sensor_id = data['sensor_id']
    user_firstname = data['user_firstname']
    temp_sensor = TemperatureSensor.get_sensor(id=sensor_id)

    mqtt.unsubscribe(temp_sensor)
    TemperatureSensor.delete_sensor(sensor_id)

    return jsonify({'success': f'Sensor successfully deleted for {user_firstname} :O)'}), 200

@bp.route("/sensors/scan")
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

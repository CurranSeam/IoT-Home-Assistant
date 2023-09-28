import ipaddress
import os
import requests
import urllib.parse

from application.services import mqtt, security as vault
from application.repository import (device as Device,
                                    user as User)

from flask import request, render_template, jsonify, Blueprint

bp = Blueprint('devices', __name__)

@bp.route("/devices")
def devices():
    users = User.get_users_by_id_asc()
    devices = {}

    for user in users:
        device_list = Device.get_devices_by_user(user.id)

        data = []
        for d in device_list:
            data.append({
                'name': d.name,
                'state': d.enabled,
                'tele_period': d.telemetry_period,
                'id': d.id
            })

        devices[user.first_name] = data

    return render_template("devices.html", users=users, device_data=devices, scanned_devices=[])

@bp.route('/devices/<int:device_id>/toggle')
def toggle_device(device_id):
    device = Device.get_device(id=device_id)
    mqtt.power_toggle(device)

    return jsonify({'success': True}), 200

@bp.route('/devices/<int:device_id>/telemetry-period', methods=["PUT"])
def update_telemetry_period(device_id):
    data = request.get_json()
    new_period = int(data['new_period'])

    device = Device.get_device(id=device_id)
    mqtt.update_telemetry_period(device, new_period)

    return jsonify({'success': True}), 200

@bp.route('/devices/add', methods=["PUT"])
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

@bp.route('/devices/delete', methods=["PUT"])
def delete_device():
    data = request.get_json()
    device_id = data['device_id']
    user_firstname = data['user_firstname']
    device = Device.get_device(id=device_id)

    mqtt.unsubscribe(device)
    Device.delete_device(device_id)

    return jsonify({'success': f'{device.name} successfully deleted for {user_firstname} :O)'}), 200

@bp.route("/devices/scan")
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

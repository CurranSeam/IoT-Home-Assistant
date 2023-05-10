import application.repository.device as Device
import application.repository.user as User
import json
import logging
import paho.mqtt.client as mqtt

from application.services import security as vault
from application.utils.exception_handler import try_exec

_client = mqtt.Client("RPI")

_sensor_data = {"voltage" : "V",
                "current" : "A",
                "power" : "W",
                "today" : "kWh",
                "yesterday" : "kWh",
                "total" : "kWh"}

# Callback functions
def on_connect(client, userdata, flags, rc):
    logging.info("MQTT client connected...")

    for device in Device.get_devices():
        # Subscribe to sensor telemetry for all devices
        client.subscribe(f'{device.user.id}/tele/{device.name}/SENSOR')

        # Subscribe to power state dump for all devices
        client.subscribe(f'{device.user.id}/stat/{device.name}/RESULT')

def on_message(client, userdata, msg):
    user_id, _, device_name, cmd = msg.topic.split("/")
    device = Device.get_device_by_user(id, device_name)

    if cmd == "RESULT":
        power = f'State: {json.loads(msg.payload)["POWER"]}'
        status = device.status.split("\n\n")
        status[0] = power
        status = "\n\n".join(status)

        Device.update_status(user_id, device_name, status)

    if cmd == "SENSOR":
        readings = json.loads(msg.payload)["ENERGY"]

        status = device.status.split("\n\n")[0] + "\n\n"
        for k, v in readings.items():
            if k.lower() in _sensor_data:
                electrical_unit = _sensor_data.get(k.lower())
                status += f"{k}: {v} {electrical_unit}\n\n"

        # Update device's status
        Device.update_status(user_id, device_name, status)

# Utility functions
def start():
    _client.on_connect = on_connect
    _client.on_message = on_message

    host = vault.get_value("APP", "config", "host")

    ret, _ = try_exec(_client.connect, host)

    if ret == 0:
        _client.loop_start()

def stop():
    _client.disconnect()
    logging.info("MQTT client disconnected")

# Device commands
def power_toggle(device):
    topic_name = device.name
    power_cmd = f'{device.user.id}/cmnd/{topic_name}/POWER'
    _client.publish(power_cmd, "TOGGLE")

import application.repository.device as Device
import application.repository.user as User
import json
import logging
import paho.mqtt.client as mqtt

from application.services import security as vault
from application.utils.exception_handler import try_exec

__client = mqtt.Client("RPI")

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
        subscribe(device)

def on_message(client, userdata, msg):
    user_id, _, device_name, cmd = msg.topic.split("/")
    device = Device.get_device_by_user(user_id, device_name)

    if cmd == "RESULT":
        payload = json.loads(msg.payload)

        if 'POWER' in payload:
            reading = payload['POWER']
            power = f'State: {reading}'

            status = device.status.split("\n\n")
            status[0] = power
            status = "\n\n".join(status)

            if reading.lower().strip() == "on":
                Device.update_is_on(user_id, device_name, True)
            else:
                Device.update_is_on(user_id, device_name, False)

            # Update device's status with the power state
            Device.update_status(user_id, device_name, status)

    elif cmd == "SENSOR":
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
    __client.on_connect = on_connect
    __client.on_message = on_message

    host = vault.get_value("APP", "config", "host")

    ret, _ = try_exec(__client.connect, host)

    if ret == 0:
        __client.loop_start()

def stop():
    __client.disconnect()
    logging.info("MQTT client disconnected")

# Device commands
def subscribe(device):
    __manage_subscriptions(device, "subscribe")

def unsubscribe(device):
    __manage_subscriptions(device, "unsubscribe")

def power_toggle(device):
    __publish(device, "POWER", "TOGGLE")

def write_power_state(device):
    __publish(device, "POWER", "")

def update_telemetry_period(device, new_period):
    __publish(device, "TelePeriod", new_period)

    Device.update_telemetry_period(device.user_id, device.id, new_period)

def __publish(device, cmd, payload):
    topic_name = device.name
    power_cmd = f'{device.user.id}/cmnd/{topic_name}/{cmd}'
    __client.publish(power_cmd, payload)

def __manage_subscriptions(device, action):
    # Sensor telemetry topic
    tele_topic = f'{device.user.id}/tele/{device.name}/SENSOR'

    # Topic that contains power state dump and other info
    result_topic = f'{device.user.id}/stat/{device.name}/RESULT'

    topics = [(tele_topic, 0), (result_topic, 0)]

    if action.lower() == "subscribe":
        __client.subscribe(topics)
    else:
        for topic, _ in topics:
            __client.unsubscribe(topic)

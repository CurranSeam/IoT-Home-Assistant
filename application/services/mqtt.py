import application.repository.device as DeviceRepo
import application.repository.temperature_sensor as TemperatureRepo
import json
import logging
import paho.mqtt.client as mqtt

from application.models.device import Device
from application.models.sensor import TemperatureSensor
from application.services import security as vault
from application.utils.exception_handler import try_exec, log_exception

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

    for device in DeviceRepo.get_devices():
        subscribe(device)

    for sensor in TemperatureRepo.get_sensors():
        subscribe(sensor)

def on_message(client, userdata, msg):
    component_data = msg.topic.split("/")[0]
    component = component_data.split("_")[0]

    if component == "devices":
        parse_device_message(msg)

    elif component == "sensors":
        parse_sensor_message(msg)

def parse_device_message(msg):
    component_data, _, cmd = msg.topic.split("/")
    _, component_id, _ = component_data.split("_")

    device = DeviceRepo.get_device(id=component_id)

    if cmd == "RESULT":
        payload = json.loads(msg.payload)

        if 'POWER' in payload:
            reading = payload['POWER']
            power = f'State: {reading}'

            status = device.status.split("\n\n")
            status[0] = power
            status = "\n\n".join(status)

            if reading.lower().strip() == "on":
                DeviceRepo.update_enabled(component_id, True)
            else:
                DeviceRepo.update_enabled(component_id, False)

            # Update device's status with the power state
            DeviceRepo.update_status(component_id, status)

    elif cmd == "SENSOR":
        readings = json.loads(msg.payload)["ENERGY"]

        status = device.status.split("\n\n")[0] + "\n\n"
        for k, v in readings.items():
            if k.lower() in _sensor_data:
                electrical_unit = _sensor_data.get(k.lower())
                status += f"{k}: {v} {electrical_unit}\n\n"

        # Update device's status
        DeviceRepo.update_status(component_id, status)

def parse_sensor_message(msg):
    component_data, _ = msg.topic.split("/")
    _, component_id, _ = component_data.split("_")

    sensor = TemperatureRepo.get_sensor(id=component_id)
    payload = json.loads(msg.payload)
    temperature_data = payload["temperature:0"]

    temperature = {
        "F" : temperature_data["tF"],
        "C" : temperature_data["tC"]
    }.get(sensor.temp_unit)

    TemperatureRepo.update_temperature(sensor, temperature)

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

# Component commands
def subscribe(component):
    __manage_subscriptions(component, "subscribe")

def unsubscribe(component):
    __manage_subscriptions(component, "unsubscribe")

def power_toggle(device):
    __publish(device, "POWER", "TOGGLE")

def write_power_state(device):
    __publish(device, "POWER")

def update_telemetry_period(device, new_period):
    __publish(device, "TelePeriod", new_period)

    DeviceRepo.update_telemetry_period(device.id, new_period)

def update_sensor_temp(sensor):
    __publish(sensor, payload="status_update")

def __publish(component, cmd="", payload=""):
    message = ""

    if isinstance(component, Device):
        message = f'devices_{component.id}_{component.name}/cmnd/{cmd}'

    elif isinstance(component, TemperatureSensor):
        message = f'sensors_{component.id}_{component.sensor.name}/command'

    __client.publish(message, payload)

def __manage_subscriptions(component, action):
    topics = []

    if isinstance(component, Device):
        # Sensor telemetry topic
        tele_topic = f'devices_{component.id}_{component.name}/tele/SENSOR'

        # Topic that contains power state dump and other info
        result_topic = f'devices_{component.id}_{component.name}/stat/RESULT'

        topics = [(tele_topic, 0), (result_topic, 0)]

    elif isinstance(component, TemperatureSensor):
        # Topic that contains device status as a response to
        # when status_update is published on <...>/command
        status_topic = f'sensors_{component.id}_{component.sensor.name}/status'
        topics = [(status_topic, 0)]

    else:
        log_exception("MQTT __manage_subscriptions: Unsupported component type")

    if action.lower() == "subscribe":
        __client.subscribe(topics)
    else:
        for topic, _ in topics:
            __client.unsubscribe(topic)

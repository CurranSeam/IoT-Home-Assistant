
from application.models.sensor import Sensor
from application.models.sensor import TemperatureSensor
from application.repository import user as User
from application.utils.exception_handler import log_exception

def get_sensor(id=None,
               ip_address=None,
               sensor=None,
               user=None):
    """
    Returns a temperature sensor based on a single given parameter.

    **IMPORTANT**: Can only pass in one
    parameter, otherwise None is returned.

    :param sensor: a Sensor record.
    :param user: a User record.
    """

    params = [id, ip_address, sensor, user]

    non_null_count = sum(param is not None for param in params)

    if non_null_count != 1:
        e = ValueError('application/repository/temperature_sensor.py: Exactly one parameter must be non-null')
        log_exception(e)
        return None

    temperature_sensor = {
        id: lambda: TemperatureSensor.get(TemperatureSensor.id == id),
        ip_address: lambda: TemperatureSensor.get(TemperatureSensor.ip_address == ip_address),
        sensor: lambda: TemperatureSensor.get(TemperatureSensor.sensor == sensor),
        user: lambda: TemperatureSensor.get(TemperatureSensor.user == user),
    }[next(filter(lambda param: param is not None, params))]

    return temperature_sensor()

def get_sensors():
    return TemperatureSensor.select()

def get_sensor_via_base(base_sensor):
    return TemperatureSensor.get(TemperatureSensor.sensor == base_sensor)

def get_sensors_by_user(user_id):
    query = TemperatureSensor.select().join(
                Sensor,
                on=(TemperatureSensor.sensor == Sensor.id),
            ).where(Sensor.user_id == user_id)
    return query

def add_sensor(user_id, name, location, ip_address, firmware):
    user = User.get_user(id=user_id)
    sensor = TemperatureSensor.create_with_sensor(user=user, name=name, location=location,
                                                  ip_address=ip_address, firmware=firmware)

    return sensor

def delete_sensor(id):
    temp_sensor = TemperatureSensor.get(TemperatureSensor.id == id)
    TemperatureSensor.delete_with_sensor(temp_sensor)

    return temp_sensor

def get_ip_addresses():
    return [t.sensor.ip_address for t in get_sensors()]

def update_temperature(sensor, temperature):
    sensor.temperature = temperature

    sensor.save()

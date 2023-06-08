from application.models.device import Device
from application.repository import user as User
from application.utils.exception_handler import log_exception

def get_device(id=None,
             name=None,
             user=None):
    """
    Returns a device based on a single given parameter.

    **IMPORTANT**: Can only pass in one
    parameter, otherwise None is returned.

    :param user: a User record.
    """

    params = [id, name, user]

    non_null_count = sum(param is not None for param in params)

    if non_null_count != 1:
        e = ValueError('application/repository/device.py: Exactly one parameter must be non-null')
        log_exception(e)
        return None

    device = {
        id: lambda: Device.get(Device.id == id),
        name: lambda: Device.get(Device.name == name),
        user: lambda: Device.get(Device.user == user),
    }[next(filter(lambda param: param is not None, params))]

    return device()

def get_devices():
    return Device.select()

def get_device_by_user(user_id, device_name=None):
    if user_id and device_name:
        return Device.get(Device.user.id == user_id and Device.name == device_name)
    else:
        return Device.get(Device.user.id == user_id)

def get_devices_by_user(user_id):
    return Device.select().where(Device.user_id == user_id)

def update_status(user_id, name, status):
    device = Device.get(Device.user_id == user_id and Device.name == name)
    device.status = status

    device.save()

def update_is_on(user_id, name, state):
    device = Device.get(Device.user_id == user_id and Device.name == name)
    device.is_on = state

    device.save()

def update_telemetry_period(user_id, device_id, new_period):
    device = Device.get(Device.user_id == user_id and Device.id == device_id)
    device.telemetry_period = new_period

    device.save()

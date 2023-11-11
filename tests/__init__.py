import os

os.environ['ENVIRONMENT'] = 'test'

from application import database
from application.models.user import User
from application.models.device import Device
from application.models.reminder import Reminder
from application.models.sensor import Sensor, TemperatureSensor
from application.models.scene import Scene
from application.models.scene import SceneAction

MODELS = [User, Device, Reminder, Sensor, TemperatureSensor, Scene, SceneAction]

with database:
    database.drop_tables(MODELS)
    database.create_tables(MODELS)

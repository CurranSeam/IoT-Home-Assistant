import os

os.environ['ENVIRONMENT'] = 'test'

from application import database
from application.models.user import User
from application.models.device import Device
from application.models.reminder import Reminder

MODELS = [User, Device, Reminder]

with database:
    database.drop_tables(MODELS)
    database.create_tables(MODELS)

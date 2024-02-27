# Utility to create the tables for the database. Run one of these functions
# before inserting any data into the database.

from application import database
from application.models.user import User
from application.models.device import Device
from application.models.reminder import Reminder
from application.models.sensor import Sensor, TemperatureSensor
from application.models.scene import Scene, SceneAction

# Create all initial tables
def create_tables():
    with database:
        database.create_tables([User, Device, Remider, Sensor, TemperatureSensor, Scene, SceneAction])

# Create or add a given table
def create_table(table):
    with database:
        database.create_tables([table])

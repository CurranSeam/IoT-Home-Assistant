import datetime

from peewee import *
from application import database
from application.models.user import User

class BaseModel(Model):
    class Meta:
        database = database

class Device(BaseModel):
    name = CharField()
    is_on = BooleanField(default=False)
    telemetry_period = IntegerField(default=300)
    status = TextField(default="No device data yet (system delay).")
    created_at = DateTimeField(default=datetime.datetime.now)
    user = ForeignKeyField(User, backref='devices')

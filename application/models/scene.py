import datetime
import json
from peewee import (Model, BlobField, BooleanField, CharField, DateTimeField,
                    ForeignKeyField, IntegerField, TextField)

from application import database
from application.models.user import User
from application.models.device import Device
from application.models.sensor import Sensor

class BaseModel(Model):
    class Meta:
        database = database

class Scene(BaseModel):
    name = CharField()
    description = TextField()
    enabled = BooleanField(default=True)
    status = CharField(default="Idle")
    created_at = DateTimeField(default=datetime.datetime.now)
    user = ForeignKeyField(User, backref='scenes', on_delete='CASCADE') 

class SceneAction(BaseModel):
    scene = ForeignKeyField(Scene, backref='actions', on_delete='CASCADE')
    enabled = BooleanField(default=True)

    sensor = ForeignKeyField(Sensor, backref='actions', null=True, on_delete='SET NULL')
    device = ForeignKeyField(Device, backref='actions', on_delete='CASCADE')

    start_time = DateTimeField(default=datetime.datetime.now)
    end_time = DateTimeField(null=True)

    action_type = CharField()
    action_param = BlobField(null=True)

    sequence_order = IntegerField(null=True)

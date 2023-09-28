import datetime
import json
from peewee import (Model, BooleanField, CharField, DateTimeField, ForeignKeyField,
                    ManyToManyField, PeeweeException, TextField)

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
    devices = ManyToManyField(Device, backref='actions')

    start_time = DateTimeField(null=True)
    end_time = DateTimeField(null=True)

    action_type = CharField()
    action_params = CharField()

    @classmethod
    def create_action(cls, scene, sensor, devices, action_type, action_params):
        with database.atomic() as transaction:
            try:
                return cls.create(scene=scene, sensor=sensor, devices=devices, action_type=action_type, action_params=json.dumps(action_params))
            except PeeweeException:
                transaction.rollback()

    def get_action_params(self):
        return json.loads(self.action_params)

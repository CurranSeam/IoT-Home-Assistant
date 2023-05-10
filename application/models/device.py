import datetime

from peewee import *
from application import database
from application.models.user import User

class BaseModel(Model):
    class Meta:
        database = database

class Device(BaseModel):
    name = CharField()
    status = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    user = ForeignKeyField(User, backref='devices')

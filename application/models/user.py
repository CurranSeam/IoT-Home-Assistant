import datetime

from peewee import *
from application import database

class BaseModel(Model):
    class Meta:
        database = database

class User(BaseModel):
    first_name = CharField()
    phone_number = IntegerField()
    username = CharField(unique=True)
    password = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)
    sms_notify = IntegerField(default=1)
    telegram_notify = IntegerField(default=0)
    telegram_chat_id = IntegerField(null=True)

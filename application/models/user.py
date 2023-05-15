import datetime

from peewee import *
from application import database

# model definitions -- the standard "pattern" is to define a base model class
# that specifies which database to use.  then, any subclasses will automatically
# use the correct storage.
class BaseModel(Model):
    class Meta:
        database = database

# the user model specifies its fields (or columns) declaratively, like django
class User(BaseModel):
    first_name = CharField()
    phone_number = IntegerField()
    username = CharField(unique=True)
    password = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)
    sms_notify = IntegerField(default=1)
    telegram_notify = IntegerField(default=1)
    telegram_chat_id = IntegerField(null=True)

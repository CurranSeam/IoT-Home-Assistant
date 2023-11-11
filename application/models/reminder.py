import datetime as date_time
from peewee import Model, CharField, TextField, DateTimeField, ForeignKeyField
from application import database
from application.models.user import User

class BaseModel(Model):
    class Meta:
        database = database

class Reminder(BaseModel):
    title = CharField()
    datetime = DateTimeField()
    recurrence = CharField()
    description = TextField(null=True)
    job_id = CharField(null=True)
    created_at = DateTimeField(default=date_time.datetime.now)
    user = ForeignKeyField(User, backref='reminders', on_delete='CASCADE')

import datetime

from peewee import (Model, CharField, DateTimeField, FloatField, 
                    ForeignKeyField, PeeweeException)
from application import database
from application.models.user import User

class BaseModel(Model):
    class Meta:
        database = database

class Sensor(BaseModel):
    name = CharField()
    type = CharField()
    location = CharField()
    ip_address = CharField()
    firmware = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)
    user = ForeignKeyField(User, backref='sensors', on_delete='CASCADE')

class TemperatureSensor(BaseModel):
    temperature = FloatField(default=0)
    temp_unit = CharField(default="F")
    temp_delta_threshold = FloatField(default=0.5)
    temp_offset = FloatField(default=0)
    humidity = FloatField(default=0)
    humidity_delta_threshold = FloatField(default=5)
    humidity_offset = FloatField(default=0)
    sensor = ForeignKeyField(Sensor, backref='temperature_sensor', unique=True, on_delete='CASCADE')

    @classmethod
    def create_with_sensor(cls, user, name, location, ip_address, firmware, **kwargs):
        with database.atomic() as transaction:
            try:
                sensor = Sensor.create(
                    name=name,
                    type="temperature_sensor",
                    location=location,
                    ip_address=ip_address,
                    firmware=firmware,
                    user=user
                )
                return cls.create(sensor=sensor, **kwargs)
            except PeeweeException:
                transaction.rollback()

    @classmethod
    def delete_with_sensor(cls, temperature_sensor):
        with database.atomic() as transaction:
            try:
                sensor = Sensor.get(id=temperature_sensor.sensor.id)
                sensor.delete_instance()
                temperature_sensor.delete_instance()

            except PeeweeException:
                transaction.rollback()

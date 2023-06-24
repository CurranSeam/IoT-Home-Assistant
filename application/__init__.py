import os

from flask import Flask
from peewee import SqliteDatabase

app = Flask(__name__)

# Determine the environment based on the ENVIRONMENT environment variable
if 'ENVIRONMENT' in os.environ:
    environment = os.environ['ENVIRONMENT']
else:
    environment = 'production'

# Set up the database based on the environment
if environment == 'test':
    database = SqliteDatabase('test.db', pragmas={'foreign_keys': 1})
else:
    database = SqliteDatabase('database.db', pragmas={'foreign_keys': 1})

@app.before_request
def before_request():
    database.connect()

@app.after_request
def after_request(response):
    database.close()
    return response

import application.routes

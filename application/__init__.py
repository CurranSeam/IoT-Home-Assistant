from flask import Flask
from peewee import SqliteDatabase

# Creates a peewee database instance.
# Models will use this database to persist information
database = SqliteDatabase('database.db', pragmas={'foreign_keys': 1})

app = Flask(__name__)

@app.before_request
def before_request():
    database.connect()

@app.after_request
def after_request(response):
    database.close()
    return response

import application.routes

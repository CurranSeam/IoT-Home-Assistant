import hashlib
import os

from application.services import security as vault
from flask import Flask, send_file
from peewee import SqliteDatabase

app = Flask(__name__)

#-----------------------------------------------------------------------
# Database setup

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

#-----------------------------------------------------------------------
# Routes setup

from application.routes import home
from application.routes import devices
from application.routes import sensors
from application.routes import reminders
from application.routes import settings
from application.routes import stats
from application.routes import scenes
from application.routes import scene_editor

app.register_blueprint(home.bp)
app.register_blueprint(devices.bp)
app.register_blueprint(sensors.bp)
app.register_blueprint(reminders.bp)
app.register_blueprint(settings.bp)
app.register_blueprint(stats.bp)
app.register_blueprint(scenes.bp)
app.register_blueprint(scene_editor.bp)

@app.route('/manifest.json')
def serve_manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')

@app.context_processor
def inject_shared_vars():
    server = f"{vault.get_value('APP', 'config', 'moniker')}Net"

    tg_identity = vault.get_value_encrypted("APP", "config", "telegram_identity")
    hash_object = hashlib.sha1(tg_identity)
    hashed_data = hash_object.hexdigest()

    return dict(hash=hashed_data, server=server)

# Put custom jinja filters into util file
@app.template_filter()
def zip_lists(a, b, c, d, e, f):
    return zip(a, b, c, d, e, f)

@app.template_filter()
def zip_lists_detection(a, b):
    return zip(a, b)

# Register the custom filters with Jinja
app.jinja_env.filters['zip'] = zip_lists
app.jinja_env.filters['zip_detection'] = zip_lists_detection

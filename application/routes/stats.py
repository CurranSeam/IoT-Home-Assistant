import hashlib
import time
import datetime
import ipaddress
import json
import os
from application.services import security as vault, svc_common
from flask import request, render_template, Blueprint

bp = Blueprint('stats', __name__)

@bp.route("/stats")
def stats():
    hostname = vault.get_value("APP", "config", "host")
    socket_port = vault.get_value("SOCKETS", "stats", "port")

    return render_template("stats.html", host=hostname, port=socket_port)

# Deprecated
# Can still hit endpoint in browser, but currently unused.
@bp.route("/get_stats")
def get_stats():
    snap = request.args.get('snapshot', None)

	# return the response generated along with the specific media
	# type (mime type)

    def realtime():
        while True:
            yield svc_common.get_server_stats()
            time.sleep(0.1)

    def snapshot():
        return svc_common.get_server_stats(False)

    func = realtime if snap == None else snapshot
    return json.dumps(func())

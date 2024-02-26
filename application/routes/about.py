import hashlib
import time
import datetime
import ipaddress
import json
import os
from application.services import security as vault, svc_common
from flask import request, render_template, Blueprint

bp = Blueprint('about', __name__)

@bp.route("/about")
def about():
    return render_template("about.html")

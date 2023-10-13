import datetime

from application import app
from application.repository import user as User
from application.services import security as vault
from application.services.telegram import telegram
from application.services.video import object_detection

from flask import request, render_template, jsonify, Blueprint, send_from_directory

bp = Blueprint('settings', __name__)

@bp.route("/settings")
def settings():
    cameras, cameras_status = object_detection.get_camera_data()

    names = User.get_first_names()
    ids = User.get_ids()

    tg_chat_ids = User.get_telegram_chat_ids()
    tg_status = User.get_telegram_notify()
    sms_status = User.get_sms_notify()
    numbers = [f'XXX-XXX-{str(num)[-4:]}' for num in User.get_phone_numbers()]

    cooloff = object_detection.message_cooloff.total_seconds()
    return render_template("settings.html", users=names, ids=ids, telegram_statuses=tg_status,
                            chat_ids=tg_chat_ids, sms_statuses=sms_status, phone_nums=numbers,
                            min_conf=object_detection.min_conf_threshold,
                            message_cooloff=cooloff, cams=cameras, cam_statuses=cameras_status)

@bp.route("/get_bot_username")
def get_bot_username():
    username = vault.get_value("APP", "config", "bot_username")
    return username

@bp.route('/get_bot_image', methods=["GET"])
def get_bot_image():
    return send_from_directory("static", "bot.png", mimetype='image/jpeg')

@bp.route('/users/<string:user_id>/<string:service>/notifications', methods=["PUT"])
def update_notification_status(user_id, service):
    data = request.get_json()
    notification_status = int(data['notification_status'])
    name = User.get_user(id=user_id).first_name
    settings_url = object_detection.FEED_URL + "/settings"

    if service.lower() == "telegram":
        User.update_telegram_notify(user_id, notification_status)
    # sms
    else:
        User.update_sms_notify(user_id, notification_status)

    # Send notification of status change
    if notification_status:
        # we are opting in to notifications
        telegram.send_opt_message(user_id, name, True, service, settings_url)
    else:
        # opted out
        telegram.send_opt_message(user_id, name, False, service, settings_url)

    # Return a response to the frontend
    return jsonify({'success': True}), 200

@bp.route("/settings/conf-threshold", methods=["PUT"])
def update_min_conf_threshold():
    data = request.get_json()
    new_threshold = float(data['new_conf_threshold'])
    object_detection.min_conf_threshold = new_threshold

    return jsonify({'success': True}), 200

@bp.route("/settings/message-cooloff", methods=["PUT"])
def update_message_cooloff():
    data = request.get_json()
    cooloff_seconds = int(data['new_cooloff'])
    new_cooloff = datetime.timedelta(seconds=cooloff_seconds)
    object_detection.message_cooloff = new_cooloff

    return jsonify({'success': True}), 200

@bp.route("/settings/<string:cam>/update-detection", methods=["PUT"])
def update_cam_detection_status(cam):
    data = request.get_json()
    new_state = int(data['detection_state'])
    object_detection.CAMERAS.get(cam)[2] = new_state

    return jsonify({'success': True}), 200

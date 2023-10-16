from application.repository import (device as Device,
                                    scene as Scene,
                                    scene_action as SceneAction,
                                    user as User)

from flask import request, render_template, jsonify, Blueprint

bp = Blueprint('scene_editor', __name__)

@bp.route('/scene-editor/<int:scene_id>/<int:user_id>')
def scene_editor(scene_id, user_id):
    user = User.get_user(id=user_id)

    scene_actions = SceneAction.get_scene_actions_by_user(user)
    devices = Device.get_devices_by_user(user_id)

    return render_template("scene_editor.html", scene_actions=scene_actions,
                           scene_id=scene_id, user_id=user_id, devices=devices)

@bp.route('/scene-editor/scene-action/add', methods=['PUT'])
def add_scene_action():
    data = request.get_json()

    scene_id = data['scene_id']
    action_type = data['action_type']
    action_param = data['action_param']
    device = data['device']
    start_time = data['start_time']
    end_time = data['end_time']
    sensor = data['sensor']

    scene = Scene.get_scene(id=scene_id)

    if device == '' or action_type == '':
        return jsonify({'error': 'device, and action type fields are required'}), 400

    if sensor == "" and action_param == "":
        SceneAction.add_scene_action(scene, device, action_type,
                                     start_time=start_time, end_time=end_time)
    else:
        SceneAction.add_scene_action(scene, device, action_type,
                                     action_param, sensor, start_time, end_time)

    return jsonify({'success': 'Scene action created successfully'}), 200

@bp.route('/scene-editor/scene-action/delete', methods=["POST"])
def delete_scene_action():
    data = request.get_json()
    action_id = data['scene_action_id']
    scene_action = SceneAction.get_scene_action(id=action_id)

    SceneAction.delete_scene_action(scene_action)

    return jsonify({'success': f'Scene action successfully deleted :O)'}), 200

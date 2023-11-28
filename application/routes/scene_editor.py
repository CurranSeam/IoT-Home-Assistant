import datetime

from application.repository import (device as Device,
                                    scene as Scene,
                                    scene_action as SceneAction,
                                    temperature_sensor as TemperatureSensor,
                                    user as User)

from application.services import scheduler
from application.utils.exception_handler import try_exec
from flask import request, render_template, jsonify, Blueprint

bp = Blueprint('scene_editor', __name__)

@bp.route('/scene-editor/<int:scene_id>/<int:user_id>')
def scene_editor(scene_id, user_id):
    scene = Scene.get_scene(id=scene_id)

    action_sequence = SceneAction.get_sequence(scene)
    devices = Device.get_devices_by_user(user_id)

    temperature_sensors = []
    for t in TemperatureSensor.get_sensors_by_user(user_id=user_id):
        temperature_sensors.append({
            "name": t.sensor.name,
            "id": t.sensor.id
        })

    return render_template("scene_editor.html", scene_actions=scene.actions, sequence=action_sequence,
                           scene_name=scene.name, scene_id=scene_id, user_id=user_id, devices=devices,
                           t_sensors=temperature_sensors)

@bp.route('/scene-editor/scene-action/add', methods=['PUT'])
def add_scene_action():
    data = request.get_json()

    scene_id = data['scene_id']
    action_type = data['action_type']
    action_param = data['action_param']
    device = data['device']
    start = data['start_time']
    end = data['end_time']
    sensor = data['sensor']

    if device == '' or action_type == '':
        return jsonify({'error': 'device and action type fields are required'}), 400

    if action_type == "temperature-control" and end == '':
        return jsonify({'error': 'End time is required'}), 400

    scene = Scene.get_scene(id=scene_id)

    start_str = f"{start.split('T')[0]} {start.split('T')[1]}"
    start_datetime = datetime.datetime.strptime(start_str, '%Y-%m-%d %H:%M')

    # Simple on or off action (not sensor controlled)
    if sensor == "" and action_param == "":
        SceneAction.add_scene_action(scene, device, action_type,
                                     start_time=start_datetime)
    else:
        end_str = f"{end.split('T')[0]} {end.split('T')[1]}"
        end_datetime = datetime.datetime.strptime(end_str, '%Y-%m-%d %H:%M')

        SceneAction.add_scene_action(scene, device, action_type,
                                     float(action_param), sensor, start_datetime, end_datetime)

    return jsonify({'success': 'Scene action created successfully'}), 200

@bp.route('/scene-editor/scene-action/sequence/add', methods=['PUT'])
def schedule_action_sequence():
    data = request.get_json()
    scene_id = data["scene_id"]
    action_ids = data['scene_actions']
    scene = Scene.get_scene(id=scene_id)

    if len(action_ids) == 0:
         return jsonify({'error': "Scene must contain at least one action"}), 400

    for action_id in action_ids:
        scene_action = SceneAction.get_scene_action(id=int(action_id))
        SceneAction.update_enabled(scene_action, True)

        if scene.enabled:
            error, job = try_exec(scheduler.schedule_scene_action, scene_action)

            if error:
                return jsonify({'error': "Scheduling for scene actions was unsuccessful"}), 500
            
            SceneAction.update_job_id(scene_action, job.id)

    for action in scene.actions:
        if str(action.id) not in action_ids:
            SceneAction.update_enabled(action, False)

    return jsonify({'success': 'Scene actions successfully scheduled'}), 200

@bp.route('/scene-editor/scene-action/delete', methods=["POST"])
def delete_scene_action():
    data = request.get_json()
    action_id = data['scene_action_id']
    scene_action = SceneAction.get_scene_action(id=action_id)

    scheduler.delete_job(scene_action.job_id)
    SceneAction.delete_scene_action(scene_action)

    return jsonify({'success': f'Scene action successfully deleted :O)'}), 200

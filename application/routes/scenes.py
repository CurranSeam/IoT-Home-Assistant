from application.services import scheduler
from application.repository import (scene as Scene,
                                    scene_action as SceneAction,
                                    user as User)
from application.utils.exception_handler import try_exec

from flask import request, render_template, jsonify, Blueprint

bp = Blueprint('scenes', __name__)

@bp.route('/scenes')
def scenes():
    users = list(User.get_users_by_id_asc())
    scenes = []

    for user in users:
        user_scenes = Scene.get_scenes_by_user(user)
        scenes.append(user_scenes)

    return render_template("scenes.html", users=users, scenes=scenes)

@bp.route('/scenes/add', methods=['PUT'])
def add_scene():
    data = request.get_json()

    user_id = data['user_id']
    scene_name = data['scene_name']
    description = data['description']

    user = User.get_user(id=user_id)

    if scene_name == '' or description == '':
        return jsonify({'error': 'Name, and description fields are required'}), 400

    Scene.add_scene(user, scene_name, description)
    return jsonify({'success': f'{scene_name} scene created successfully'})

@bp.route('/scenes/<int:scene_id>/toggle', methods=["PUT"])
def toggle_scene(scene_id):
    data = request.get_json()
    enabled = int(data['enabled'])
    scene = Scene.get_scene(id=scene_id)

    if not enabled:
        Scene.update_enabled(scene, False)
    else:
        Scene.update_enabled(scene, True)

    for scene_action in scene.actions:
        if not enabled:
            scheduler.delete_job(scene_action.job_id)
        else:
            job = scheduler.schedule_scene_action(scene_action)
            SceneAction.update_job_id(scene_action, job.id)

    return jsonify({'success': f'{scene.name} scene toggled successfully :O)'}), 200

@bp.route('/scenes/delete', methods=["POST"])
def delete_scene():
    data = request.get_json()
    scene_id = data['scene_id']
    scene_name = data['scene_name']
    user_firstname = data['user_firstname']
    scene = Scene.get_scene(id=scene_id)

    for scene_action in scene.actions:
        scheduler.delete_job(scene_action.job_id)

    Scene.delete_scene(scene)

    return jsonify({'success': f'{scene_name} scene successfully deleted for {user_firstname} :O)'}), 200

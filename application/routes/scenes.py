from application.services import scheduler
from application.repository import (scene as Scene,
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
    else:
        Scene.add_scene(user, scene_name, description)
        return jsonify({'success': f'{scene_name} scene created successfully'})

@bp.route('/scenes/delete', methods=["POST"])
def delete_reminder():
    data = request.get_json()
    scene_id = data['scene_id']
    scene_name = data['scene_name']
    user_firstname = data['user_firstname']
    scene = Scene.get_scene(id=scene_id)

    Scene.delete_scene(scene)

    return jsonify({'success': f'{scene_name} scene successfully deleted for {user_firstname} :O)'}), 200

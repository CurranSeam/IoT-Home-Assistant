import datetime

from application.models.scene import Scene, SceneAction
from application.utils.exception_handler import log_exception

def get_scene_action(id=None, scene=None, user=None):
    """
    Returns a scene action based on a single given parameter.

    **IMPORTANT**: Can only pass in one
    parameter, otherwise None is returned.

    :param scene: a Scene record.
    :param user: a User record.
    """

    params = [id, scene, user]

    non_null_count = sum(param is not None for param in params)

    if non_null_count != 1:
        e = ValueError('application/repository/scene_action.py: Exactly one parameter must be non-null')
        log_exception(e)
        return None

    scene_action = {
        id: lambda: SceneAction.get(SceneAction.id == id),
        scene: lambda: SceneAction.get(SceneAction.scene == scene),
        user: lambda: SceneAction.get(SceneAction.user == user),
    }[next(filter(lambda param: param is not None, params))]

    return scene_action()

def get_scene_actions():
    return SceneAction.select()

def get_sequence(scene):
    sequence = []

    for action in scene.actions:
       if action.enabled:
           sequence.append(action)

    return sequence

def add_scene_action(scene, device, action_type, action_param=None,
                     sensor=None, start_time=None, end_time=None):
    scene_action = SceneAction.create(scene=scene, device=device,
                                      action_type=action_type, action_param=action_param,
                                      sensor=sensor, start_time=start_time, end_time=end_time)

    return scene_action

def delete_scene_action(scene_action):
    scene_action.delete_instance()

    return scene_action

def update_sequence_order(scene_action, order):
    scene_action.sequence_order = order
    scene_action.save()

    return scene_action

def update_enabled(scene_action, enabled):
    scene_action.enabled = enabled
    scene_action.save()

    return scene_action

def update_job_id(scene_action, job_id):
    scene_action.job_id = job_id
    scene_action.save()

    return scene_action

def update_start_time(scene_action, start_time):
    scene_action.start_time = start_time
    scene_action.save()

    return scene_action

def update_end_time(scene_action, end_time):
    scene_action.end_time = end_time
    scene_action.save()

    return scene_action

def adjust_start_end_time(scene_action):
    start_delta = (datetime.datetime.now() - scene_action.start_time).days
    end_delta = (datetime.datetime.now() - scene_action.end_time).days

    if start_delta > 0 and end_delta > 0:
        start_time = scene_action.start_time + datetime.timedelta(days=start_delta)

        end_offset_hours = (scene_action.end_time - scene_action.start_time).total_seconds() / 3600
        update_start_time(scene_action, start_time)
        end_time = scene_action.start_time + datetime.timedelta(hours=end_offset_hours)

        update_end_time(scene_action, end_time)

    return scene_action

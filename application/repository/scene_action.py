from application.models.scene import Scene, SceneAction
from application.repository import user as User
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

    reminder = {
        id: lambda: SceneAction.get(SceneAction.id == id),
        scene: lambda: SceneAction.get(SceneAction.scene == scene),
        user: lambda: SceneAction.get(SceneAction.user == user),
    }[next(filter(lambda param: param is not None, params))]

    return reminder()

def get_scene_actions():
    return SceneAction.select().order_by(SceneAction.Scene.user.id)

def get_scene_actions_by_user(user):
    query = SceneAction.select().join(
        Scene,
        on=(SceneAction.scene == Scene.id),
    ).where(Scene.user== user)

    return query

def add_scene_action(scene, device, action_type, action_param=None,
                     sensor=None, start_time=None, end_time=None):
    scene_action = SceneAction.create(scene=scene, device=device,
                                      action_type=action_type, action_param=action_param,
                                      sensor=sensor, start_time=start_time, end_time=end_time)

    return scene_action

def delete_scene_action(scene_action):
    scene_action.delete_instance()

    return scene_action

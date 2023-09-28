from application.models.scene import Scene
from application.repository import user as User
from application.utils.exception_handler import log_exception

def get_scene(id=None, user=None):
    """
    Returns a scene based on a single given parameter.

    **IMPORTANT**: Can only pass in one
    parameter, otherwise None is returned.

    :param user: a User record.
    """

    params = [id, user]

    non_null_count = sum(param is not None for param in params)

    if non_null_count != 1:
        e = ValueError('application/repository/scene.py: Exactly one parameter must be non-null')
        log_exception(e)
        return None

    reminder = {
        id: lambda: Scene.get(Scene.id == id),
        user: lambda: Scene.get(Scene.user == user),
    }[next(filter(lambda param: param is not None, params))]

    return reminder()

def get_scenes():
    return Scene.select().order_by(Scene.datetime)

def get_scenes_by_user(user):
    return Scene.select().where(Scene.user == user)

def add_scene(user, name, description=None):
    scene = Scene.create(user=user, name=name, description=description)

    return scene

def delete_scene(scene):
    scene.delete_instance()

    return scene

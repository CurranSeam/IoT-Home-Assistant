from application.models.user import User
from application.utils.exception_handler import log_exception

def get_user(id=None,
             first_name=None,
             phone_number=None,
             username=None,
             telegram_chat_id=None):
    """
    Returns a user based on given parameter.

    **IMPORTANT**: Can only pass in one
    parameter, otherwise None is returned.
    """

    params = [id, first_name, phone_number, username, telegram_chat_id]

    non_null_count = sum(param is not None for param in params)

    if non_null_count != 1:
        e = ValueError('application/repository/user.py: Exactly one parameter must be non-null')
        log_exception(e)
        return None

    user = {
        id: lambda: User.get(User.id == id),
        first_name: lambda: User.get(User.first_name == first_name),
        phone_number: lambda: User.get(User.phone_number == phone_number),
        username: lambda: User.get(User.username == username),
        telegram_chat_id: lambda: User.get(User.telegram_chat_id == telegram_chat_id)
    }[next(filter(lambda param: param is not None, params))]

    return user()

# Add param to indicate if ordering or not.
def get_first_names():
    users = __get_users_order_by(User.id)

    return [user.first_name for user in users]

# Add param to indicate if ordering or not.
def get_telegram_chat_ids(active=0):
    users = __get_users_order_by(User.id)

    if active:
        users = users.where(User.telegram_notify == 1)

    return [user.telegram_chat_id for user in users]

def get_telegram_chat_id(first_name):
    return User.get(User.first_name == first_name).telegram_chat_id

# Add param to indicate if ordering or not.
def get_telegram_notify():
    users = __get_users_order_by(User.id)

    return [user.telegram_notify for user in users]

# Add param to indicate if ordering or not.
def get_sms_notify():
    users = __get_users_order_by(User.id)

    return [user.sms_notify for user in users]

def get_phone_number(chat_id=None, active=0, first_name=None):
    if first_name and not chat_id and not active:
        return User.get(User.first_name == first_name).phone_number
    elif chat_id:
        return User.get(User.telegram_chat_id == chat_id and
                        User.sms_notify == active).phone_number

# Add param to indicate if ordering or not.
def get_phone_numbers(active=0):
    users = __get_users_order_by(User.id)

    if active:
        users = users.where(User.sms_notify == 1)

    return [user.phone_number for user in users]

def update_telegram_notify(first_name, status):
    user = User.get(User.first_name == first_name)
    user.telegram_notify = status

    user.save()

def update_sms_notify(first_name, status):
    user = User.get(User.first_name == first_name)
    user.sms_notify = status

    user.save()

# Might be slightly faster to use this since it is not ordered.
def __get_users():
    return User.select()

def __get_users_order_by(selector, desc=False):
    users = __get_users()

    if not desc:
        return users.order_by(selector)

    return users.order_by(selector).desc()

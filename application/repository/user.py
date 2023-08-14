from application.models.user import User
from application.utils.exception_handler import log_exception

def add_user(first_name,
             phone_number,
             username,
             password,
             sms_notify=1,
             telegram_notify=0,
             telegram_chat_id=None):
    user = User.create(
        first_name=first_name,
        phone_number=phone_number,
        username=username,
        password=password,
        sms_notify=sms_notify,
        telegram_notify=telegram_notify,
        telegram_chat_id=telegram_chat_id
    )

    return user

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

def get_users_by_id_asc():
    """
    Returns list of users in ascending order by first name.
    """
    return __get_users_order_by(User.id)

def get_ids():
    users = __get_users_order_by(User.id)

    return [user.id for user in users]

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

def get_telegram_chat_id(user_id):
    return User.get(User.id == user_id).telegram_chat_id

# Add param to indicate if ordering or not.
def get_telegram_notify():
    users = __get_users_order_by(User.id)

    return [user.telegram_notify for user in users]

# Add param to indicate if ordering or not.
def get_sms_notify():
    users = __get_users_order_by(User.id)

    return [user.sms_notify for user in users]

def get_phone_number(chat_id=None, active=0, user_id=None):
    if user_id and not chat_id and not active:
        return User.get(User.id == user_id).phone_number
    elif chat_id:
        return User.get(User.telegram_chat_id == chat_id and
                        User.sms_notify == active).phone_number

# Add param to indicate if ordering or not.
def get_phone_numbers(active=0):
    users = __get_users_order_by(User.id)

    if active:
        users = users.where(User.sms_notify == 1)

    return [user.phone_number for user in users]

def update_telegram_notify(user_id, status):
    user = User.get(User.id == user_id)
    user.telegram_notify = status

    user.save()

def update_sms_notify(user_id, status):
    user = User.get(User.id == user_id)
    user.sms_notify = status

    user.save()

def update_telegram_chat_id(user_id, chat_id):
    user = User.get(User.id == user_id)
    user.telegram_chat_id = chat_id

    user.save()

# Might be slightly faster to use this since it is not ordered.
def __get_users():
    return User.select()

def __get_users_order_by(selector, desc=False):
    users = __get_users()

    if not desc:
        return users.order_by(selector)

    return users.order_by(selector).desc()

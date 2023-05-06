from application.models.user import User

def get_user(username):
    return User.get(User.username == username)

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

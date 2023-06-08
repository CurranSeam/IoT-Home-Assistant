from application.models.reminder import Reminder
from application.repository import user as User
from application.utils.exception_handler import log_exception

def get_reminder(id=None, user=None):
    """
    Returns a reminder based on a single given parameter.

    **IMPORTANT**: Can only pass in one
    parameter, otherwise None is returned.

    :param user: a User record.
    """

    params = [id, user]

    non_null_count = sum(param is not None for param in params)

    if non_null_count != 1:
        e = ValueError('application/repository/reminder.py: Exactly one parameter must be non-null')
        log_exception(e)
        return None

    reminder = {
        id: lambda: Reminder.get(Reminder.id == id),
        user: lambda: Reminder.get(Reminder.user == user),
    }[next(filter(lambda param: param is not None, params))]

    return reminder()

def get_reminders_by_user(user):
    return Reminder.select().where(Reminder.user == user)

def add_reminder(user_id, title, reminder_datetime, recurrence, description=None):
    user = User.get_user(id=user_id)
    reminder = Reminder.create(
                        user=user,
                        title=title,
                        datetime=reminder_datetime,
                        description=description,
                        recurrence=recurrence
                    )
    return reminder

def delete_reminder(reminder_id):
    reminder = Reminder.get(Reminder.id == reminder_id)
    reminder.delete_instance()

    return reminder

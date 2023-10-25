from application.models.reminder import Reminder
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

def get_reminders():
    return Reminder.select().order_by(Reminder.datetime)

def get_reminders_by_user(user):
    return Reminder.select().where(Reminder.user == user)

def add_reminder(user, title, reminder_datetime, recurrence, description=None):
    reminder = Reminder.create(
                        user=user,
                        title=title,
                        datetime=reminder_datetime,
                        description=description,
                        recurrence=recurrence
                    )
    return reminder

def delete_reminder(reminder):
    reminder.delete_instance()

    return reminder

def update_datetime(reminder, datetime):
    reminder.datetime = datetime
    reminder.save()

    return reminder

def update_recurrence(reminder, recurrence):
    reminder.recurrence = recurrence
    reminder.save()

    return reminder

def update_description(reminder, description):
    reminder.description = description
    reminder.save()

    return reminder

def update_job_id(reminder, job_id):
    reminder.job_id = job_id
    reminder.save()

    return reminder

import application.repository.reminder as Reminder
import application.repository.user as User

from application.services import svc_common
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from dateutil.relativedelta import relativedelta
from functools import partial

from application.services.telegram import telegram

# Scheduler for executing background tasks asynchronously
scheduler = BackgroundScheduler()

def start():
    for reminder in Reminder.get_reminders():
        schedule_reminder(reminder)

    schedule_morning_message()

    scheduler.start()

def schedule_reminder(reminder):
    message = svc_common.get_reminder_message(reminder)
    recurrence = reminder.recurrence.lower()
    time = reminder.datetime

    trigger_mapping = {
        'none': partial(scheduler.add_job, telegram.send_reminder, 'date',
                        args=[reminder.user_id, message],
                        run_date=time),
        'every-minute' : partial(scheduler.add_job, telegram.send_reminder,
                         IntervalTrigger(minutes=1),
                         args=[reminder.user_id, message],
                         next_run_time=time),
        'daily': partial(scheduler.add_job, telegram.send_reminder,
                         IntervalTrigger(days=1),
                         args=[reminder.user_id, message],
                         next_run_time=time),
        'bi-weekly': partial(scheduler.add_job, telegram.send_reminder,
                             IntervalTrigger(weeks=2),
                             args=[reminder.user_id, message],
                             next_run_time=time),
        'weekly': partial(scheduler.add_job, telegram.send_reminder,
                          IntervalTrigger(weeks=1),
                          args=[reminder.user_id, message],
                          next_run_time=time),
        'monthly': partial(scheduler.add_job, telegram.send_reminder,
                           __set_cron(day=time.day, hour=time.hour, minute=time.minute),
                           args=[reminder.user_id, message],
                           next_run_time=time),
        'annually': partial(scheduler.add_job, telegram.send_reminder,
                            __set_cron(month=time.month, day=time.day, hour=time.hour, minute=time.minute),
                            args=[reminder.user_id, message],
                            next_run_time=time)
    }

    schedule_job = trigger_mapping.get(recurrence)
    if schedule_job is None:
        raise Exception(f"Invalid reminder recurrence: {recurrence}")

    job = schedule_job()

    return job

def schedule_morning_message():
    return scheduler.add_job(telegram.send_morning_message, __set_cron(hour=9, minute=0))

def delete_job(job_id):
    scheduler.remove_job(job_id)

def __set_cron(year="*", month="*", day="*",
               hour="*", minute="*", second="0"):
    return CronTrigger(year=year, month=month, day=day,
                       hour=hour, minute=minute, second=second)
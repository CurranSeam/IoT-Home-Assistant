import application.repository.reminder as Reminder
import application.repository.user as User

from application.services import svc_common, telegram
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from dateutil.relativedelta import relativedelta
from functools import partial

# Scheduler for executing background tasks asynchronously
scheduler = BackgroundScheduler()

def start():
    for reminder in Reminder.get_reminders():
        schedule_reminder(reminder)

    scheduler.start()

def schedule_reminder(reminder):
    message = svc_common.get_reminder_message(reminder)
    recurrence = reminder.recurrence.lower()

    trigger = lambda interval: set_cron(reminder.datetime + relativedelta(**interval))
    set_cron = lambda next_run_date: CronTrigger(year=next_run_date.year, month=next_run_date.month,
                                                day=next_run_date.day, hour=next_run_date.hour,
                                                minute=next_run_date.minute)

    trigger_mapping = {
        'none': partial(scheduler.add_job, telegram.send_reminder, 'date',
                        args=[reminder.user_id, message], run_date=reminder.datetime),
        'daily': partial(scheduler.add_job, telegram.send_reminder,
                         IntervalTrigger(days=1), args=[reminder.user_id, message]),
        'bi-weekly': partial(scheduler.add_job, telegram.send_reminder,
                             IntervalTrigger(weeks=2), args=[reminder.user_id, message]),
        'weekly': partial(scheduler.add_job, telegram.send_reminder,
                          IntervalTrigger(weeks=1), args=[reminder.user_id, message]),
        'monthly': partial(scheduler.add_job, telegram.send_reminder,
                           trigger({'months': 1}), args=[reminder.user_id, message]),
        'annually': partial(scheduler.add_job, telegram.send_reminder,
                            trigger({'years': 1}), args=[reminder.user_id, message])
    }

    schedule_job = trigger_mapping.get(recurrence)
    if schedule_job is None:
        raise Exception(f"Invalid reminder recurrence: {recurrence}")

    job = schedule_job()

    return job

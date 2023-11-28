import datetime

from application.repository import (reminder as Reminder,
                                    scene_action as SceneAction,
                                    temperature_sensor as TemperatureSensor)
from application.services import mqtt, svc_common
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from functools import partial

from application.services.telegram import telegram

# Scheduler for executing background tasks asynchronously
scheduler = BackgroundScheduler()

def start():
    for reminder in Reminder.get_reminders():
        schedule_reminder(reminder)

    for action in SceneAction.get_scene_actions():
        if action.enabled and action.scene.enabled:
            SceneAction.adjust_start_end_time(action)
            schedule_scene_action(action, now=True)

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

def schedule_scene_action(scene_action, now=None):
    func = {
        "on" : mqtt.power_on,
        "off" : mqtt.power_off,
        "temperature-control" : __regulate_temperature
    }.get(scene_action.action_type)

    if func == None:
        raise Exception("Invalid action_type")

    if func == __regulate_temperature:
        run_time = scene_action.start_time

        if now and (scene_action.start_time < datetime.datetime.now() < scene_action.end_time):
            run_time = datetime.datetime.now() + datetime.timedelta(seconds=5)

        job = scheduler.add_job(func, IntervalTrigger(minutes=1),
                                args=[scene_action],
                                next_run_time=run_time)

        SceneAction.update_job_id(scene_action, job.id)
        return job

    return scheduler.add_job(func, IntervalTrigger(days=1),
                             args=[scene_action.device],
                             next_run_time=scene_action.start_time,
                             misfire_grace_time=86400)

def delete_job(job_id):
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        pass

def __set_cron(year="*", month="*", day="*",
               hour="*", minute="*", second="0"):
    return CronTrigger(year=year, month=month, day=day,
                       hour=hour, minute=minute, second=second)

def __regulate_temperature(scene_action):
    if datetime.datetime.now() >= scene_action.end_time:
        mqtt.power_off(scene_action.device)
        delete_job(scene_action.job_id)

        tomorrow_start = scene_action.start_time + datetime.timedelta(days=1)
        tomorrow_end = scene_action.end_time + datetime.timedelta(days=1)

        SceneAction.update_start_time(scene_action, tomorrow_start)
        SceneAction.update_end_time(scene_action, tomorrow_end)

        job = scheduler.add_job(__regulate_temperature, IntervalTrigger(minutes=1),
                                args=[scene_action],
                                next_run_time=tomorrow_start)

        SceneAction.update_job_id(scene_action, job.id)
        return job

    temperature_sensor = TemperatureSensor.get_sensor_via_base(scene_action.sensor)

    if temperature_sensor.temperature < scene_action.action_param: 
        mqtt.power_on(scene_action.device)
    else:
        mqtt.power_off(scene_action.device)

    return scheduler.get_job(scene_action.job_id)

import os
import sys

# Get the absolute path to the root directory
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

sys.path.append(root_path)

import time
import datetime
import pytest

# This must be imported in all test files for setup.
import tests

from application.services.telegram import telegram
from application.repository import (reminder as Reminder,
                                    device as Device,
                                    user as User,
                                    scene as Scene,
                                    scene_action as SceneAction,
                                    temperature_sensor as TemperatureSensor)
from application.services import scheduler
from apscheduler.triggers.cron import CronTrigger
from dateutil.relativedelta import relativedelta

SENT_REMINDER = "placeholder"

# Mock function for sending reminders
def mock_send_reminder(_, message):
    global SENT_REMINDER
    SENT_REMINDER = message

def mock_schedule_morning_msg():
    hour = datetime.datetime.now().hour
    job = scheduler.scheduler.add_job(telegram.send_morning_message,
                                      CronTrigger(year="*", month="*", day="*",
                                                  hour=hour, minute="0", second="0"))
    return job

@pytest.fixture(scope="session")
def setup_scheduler():
    scheduler.start()

    # Replace the real functions with mocks
    telegram.send_reminder = mock_send_reminder
    scheduler.schedule_morning_message = mock_schedule_morning_msg
    
    user = User.add_user(
        'Baburao',
        '8881212',
        'starGarage',
        'riks'
    )

    reminder = Reminder.add_reminder(
        user,
        'Evict Raju',
        datetime.datetime.now(),
        'none',
    )

    yield user, reminder

    scheduler.scheduler.remove_all_jobs()
    scheduler.scheduler.shutdown()

def test_reminder_sending(setup_scheduler):
    global SENT_REMINDER
    _, reminder = setup_scheduler
    now = datetime.datetime.now() + datetime.timedelta(seconds=0.1)

    Reminder.update_description(reminder, "Uthale")
    Reminder.update_datetime(reminder, now)

    scheduler.schedule_reminder(reminder)
    time.sleep(0.1)

    assert SENT_REMINDER == f"Evict Raju today at {now.time()}.\n\nUthale"

def test_reminder_preloading(setup_scheduler):
    _, reminder = setup_scheduler
    now = datetime.datetime.now()

    Reminder.update_datetime(reminder, now)
    Reminder.update_recurrence(reminder, "daily")

    job = scheduler.schedule_reminder(reminder)
    assert job.name == "mock_send_reminder"

    scheduler.scheduler.shutdown()
    scheduler.start()

    jobs = scheduler.scheduler.get_jobs()
    assert jobs[1].name == "mock_send_reminder"

    scheduler.scheduler.remove_all_jobs()

def test_reminder_recurrence_invalid(setup_scheduler):
    global SENT_REMINDER
    _, reminder = setup_scheduler
    now = datetime.datetime.now() + datetime.timedelta(seconds=2)

    Reminder.update_datetime(reminder, now)
    Reminder.update_recurrence(reminder, "every-nanosecond")

    with pytest.raises(Exception):
        scheduler.schedule_reminder(reminder)

@pytest.mark.parametrize("recurrence, timedelta", [("every-minute", datetime.timedelta(minutes=1)),
                                                   ("daily", datetime.timedelta(days=1)),
                                                   ("bi-weekly", datetime.timedelta(weeks=2)),
                                                   ("weekly", datetime.timedelta(weeks=1)),
                                                   ("monthly", relativedelta(months=1)),
                                                   ("annually", relativedelta(years=1))])
def test_reminder_recurrence(setup_scheduler, recurrence, timedelta):
    _, reminder = setup_scheduler
    now = datetime.datetime.now()

    Reminder.update_datetime(reminder, now)
    Reminder.update_recurrence(reminder, recurrence)

    job = scheduler.schedule_reminder(reminder)

    next_run_time = job.next_run_time.replace(tzinfo=None).replace(microsecond=0, second=0)
    expected_next_run_time = now.replace(microsecond=0, second=0)

    assert next_run_time == expected_next_run_time

    time.sleep(0.3)

    next_run_time = job.next_run_time.replace(tzinfo=None).replace(microsecond=0, second=0)
    expected_next_run_time = (reminder.datetime + timedelta).replace(microsecond=0, second=0)

    assert next_run_time == expected_next_run_time

def test_morning_message_sending():
    morning = datetime.datetime.now()

    job = scheduler.schedule_morning_message()

    next_run_time = job.next_run_time.replace(tzinfo=None).replace(minute=0)
    expected_next_run_time = (morning + datetime.timedelta(days=1)).replace(minute=0, second=0, microsecond=0)

    assert next_run_time == expected_next_run_time

def test_scene_action_temperature_control(setup_scheduler):
    user, _ = setup_scheduler
    scene = Scene.add_scene(user, "test scene", "testing temperature control")
    device = Device.add_device(user.id, "booster battery", "108.108.108.108")
    t_sensor = TemperatureSensor.add_sensor(user.id, "asdasd", "car", "253.253.253.253", "shelly")
    now = datetime.datetime.now()
    scene_action = SceneAction.add_scene_action(scene, device, "temperature-control", 75,
                                                t_sensor.id, now, now + datetime.timedelta(hours=2))

    job = scheduler.schedule_scene_action(scene_action)

    next_run_time = job.next_run_time.replace(tzinfo=None).replace(second=0, microsecond=0)
    expected_next_run_time = (now + datetime.timedelta(minutes=1)).replace(second=0, microsecond=0)

    assert next_run_time == expected_next_run_time

    scheduler.scheduler.remove_all_jobs()
    scene_action_ended = SceneAction.add_scene_action(scene, device, "temperature-control", 75, t_sensor.id,
                                                      datetime.datetime.now() - datetime.timedelta(days=1) + datetime.timedelta(hours=2),
                                                      datetime.datetime.now())

    old_start_time = scene_action_ended.start_time
    old_end_time = scene_action_ended.end_time

    job2 = scheduler.__regulate_temperature(scene_action_ended)

    new_start_time = scene_action_ended.start_time
    new_end_time = scene_action_ended.end_time

    assert new_start_time == old_start_time + datetime.timedelta(days=1)
    assert new_end_time == old_end_time + datetime.timedelta(days=1)

    next_run_time = job2.next_run_time.replace(tzinfo=None).replace(second=0, microsecond=0)
    expected_next_run_time = new_start_time.replace(second=0, microsecond=0)

    assert next_run_time == expected_next_run_time

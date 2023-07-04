import os
import sys

# Get the absolute path to the root directory
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

sys.path.append(root_path)

import time
import datetime
import pytest
import tests

from application.repository import (reminder as Reminder, user as User)
from application.services import telegram, scheduler
from dateutil.relativedelta import relativedelta

SENT_REMINDER = "placeholder"

# Mock function for sending reminders
def mock_send_reminder(user, message):
    global SENT_REMINDER
    SENT_REMINDER = f"Reminder for {user}: {message}"

@pytest.fixture(scope="session")
def setup_scheduler():
    scheduler.start()

    # Replace the send_reminder function with the mock
    telegram.send_reminder = mock_send_reminder

    user = User.add_user(
        'Baburao',
        '8881212',
        'starGarage',
        'riks'
    )

    reminder = Reminder.add_reminder(
        user,
        'Test Reminder',
        datetime.datetime.now(),
        'none',
    )

    yield reminder

    scheduler.scheduler.remove_all_jobs()
    scheduler.scheduler.shutdown()

def test_reminder_sending(setup_scheduler):
    global SENT_REMINDER
    reminder = setup_scheduler
    now = datetime.datetime.now() + datetime.timedelta(seconds=2)

    Reminder.update_description(reminder, "Uthale")
    Reminder.update_datetime(reminder, now)

    scheduler.schedule_reminder(reminder)
    time.sleep(2)

    assert SENT_REMINDER == f"Reminder for Baburao: Test Reminder today at {now.time()}.\n\nUthale"

def test_reminder_preloading(setup_scheduler):
    reminder = setup_scheduler
    now = datetime.datetime.now()

    Reminder.update_datetime(reminder, now)
    Reminder.update_recurrence(reminder, "daily")

    job = scheduler.schedule_reminder(reminder)
    assert job.name == "mock_send_reminder"

    scheduler.scheduler.shutdown()
    scheduler.start()

    jobs = scheduler.scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].name == "mock_send_reminder"

    scheduler.scheduler.remove_all_jobs()

def test_reminder_recurrence_invalid(setup_scheduler):
    global SENT_REMINDER
    reminder = setup_scheduler
    now = datetime.datetime.now() + datetime.timedelta(seconds=2)

    Reminder.update_datetime(reminder, now)
    Reminder.update_recurrence(reminder, "every-nanosecond")

    with pytest.raises(Exception):
        scheduler.schedule_reminder(reminder)

@pytest.mark.parametrize("recurrence, timedelta", [("daily", datetime.timedelta(days=1)),
                                                   ("bi-weekly", datetime.timedelta(weeks=2)),
                                                   ("weekly", datetime.timedelta(weeks=1)),
                                                   ("monthly", relativedelta(months=1)),
                                                   ("annually", relativedelta(years=1))])
def test_reminder_recurrence(setup_scheduler, recurrence, timedelta):
    reminder = setup_scheduler
    now = datetime.datetime.now()

    Reminder.update_datetime(reminder, now)
    Reminder.update_recurrence(reminder, recurrence)

    job = scheduler.schedule_reminder(reminder)

    next_run_time = job.next_run_time.replace(tzinfo=None).replace(microsecond=0, second=0)
    expected_next_run_time = (reminder.datetime + timedelta).replace(microsecond=0, second=0)

    assert next_run_time == expected_next_run_time

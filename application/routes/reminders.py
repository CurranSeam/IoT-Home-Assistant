import datetime

from application.services import scheduler
from application.repository import (reminder as Reminder,
                                    user as User)
from application.utils.exception_handler import try_exec

from flask import request, render_template, jsonify, Blueprint

bp = Blueprint('reminders', __name__)

@bp.route('/reminders')
def reminders():
    users = list(User.get_users_by_id_asc())
    reminders_list = []

    for user in users:
        reminders = Reminder.get_reminders_by_user(user)
        reminders_list.append(reminders)

    return render_template("reminders.html", users=users, reminders_list=reminders_list)

@bp.route('/reminders/add-reminder', methods=['POST'])
def add_reminder():
    data = request.get_json()

    user_id = data['user_id']
    title = data['title']
    date = data['date']
    time = data['time']
    description = data['description']
    recurrence = data['recurrence']

    user = User.get_user(id=user_id)

    if date == '' or time == '' or title == '':
        return jsonify({'error': 'Title, Date, and Time fields are required'}), 400
    else:
        # Combine date and time inputs into a datetime object
        datetime_str = f"{date} {time}"
        reminder_datetime = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')

        reminder = Reminder.add_reminder(user, title, reminder_datetime, recurrence, description)
        ret, job = try_exec(scheduler.schedule_reminder, reminder)

        if not ret:
            Reminder.update_job_id(reminder, job.id)
            return jsonify({'success': 'Reminder created successfully'})

        Reminder.delete_reminder(reminder.id)
        return jsonify({'error': "Scheduling for the reminder was unsuccessful"}), 500

@bp.route('/reminders/delete-reminder', methods=["POST"])
def delete_reminder():
    data = request.get_json()
    reminder_id = data['reminder_id']
    user_firstname = data['user_firstname']
    reminder = Reminder.get_reminder(id=reminder_id)

    scheduler.delete_job(reminder.job_id)
    Reminder.delete_reminder(reminder_id)

    return jsonify({'success': f'{reminder.title} successfully deleted for {user_firstname} :O)'}), 200

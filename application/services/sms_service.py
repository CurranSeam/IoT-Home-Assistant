from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

from application.services import security as vault
from application.services import svc_common

from application.utils.exception_handler import try_exec
from application.repository import user as User

import smtplib
import os

def send_detection_message(camera, timestamp, telegram_chat_id=None):
    """
    Sends an SMS message via a carrier through SMTP for detection.
    """
    text = svc_common.get_detection_message(camera, timestamp)
    recipient = None

    if telegram_chat_id:
        recipient = User.get_phone_number(telegram_chat_id, 1)

    send_message(text, recipients=recipient)

def send_message(text, recipients=None, img_filename=None):
    msg = MIMEMultipart()
    msg['Subject'] = "/"
    msg.attach(MIMEText(text))

    if img_filename:
        img_data = open(img_filename, 'rb').read()
        image = MIMEImage(img_data, name=os.path.basename(img_filename))
        msg.attach(image)

    server, email = __setup_smtp_server()

    if not recipients:
        recipients = __get_active_numbers()

    recipients = __prepare_for_carriers(recipients)

    # Edge case causes crash if no active recipients.
    if len(recipients) > 0:
        try_exec(server.sendmail, email, recipients, msg.as_string())
        server.close()

def send_opt_message(user_id, user_first_name, opt_in, service):
    """
    Sends an SMS message via a carrier through SMTP for opt-in/opt-out.
    """
    text = svc_common.get_opt_message(user_first_name, opt_in, service)
    recipient = User.get_phone_number(user_id=user_id)

    send_message(text, recipients=recipient)

def __setup_smtp_server():
    auth = (vault.get_value("credentials", "sms_auth", "username"), 
            vault.get_value("credentials", "sms_auth", "password"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(auth[0], auth[1])
    return server, auth[0]

def __get_active_numbers():
    numbers = User.get_phone_numbers(active=1)

    return numbers

def __prepare_for_carriers(numbers):
    """
    Accepts phone number(s) and prepares them for transport
    by appending carrier domains to them
    """
    if not isinstance(numbers, list):
        numbers = [numbers]

    address = vault.get_value("carriers", "tmobile", "address")
    return [str(phone_no) + address for phone_no in numbers]

from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from application.services import security as vault
from application.services import svc_common

import smtplib
import os

def send_detection_message(camera, timestamp):
    """
    Sends an SMS message via a carrier through SMTP for detection.
    """
    text = svc_common.get_detection_message(camera, timestamp);
    send_message(text)

def send_message(text, img_filename=None, recipients=None):
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

    # Edge case causes crash if no active recipients.
    if len(recipients) > 0:
        server.sendmail(email, recipients, msg.as_string())

def send_opt_message(user, opt_in):
    """
    Sends an SMS message via a carrier through SMTP for opt-in/opt-out.
    """
    text = svc_common.get_opt_message(user, opt_in)

    # This needs to be changed with https://trello.com/c/MhK6UZ1M
    recipient = vault.get_value("recipients", user, "phone_number") + vault.get_value("carriers", "tmobile", "address")

    send_message(text, recipients=recipient)

def __setup_smtp_server():
    auth = (vault.get_value("credentials", "sms_auth", "username"), 
            vault.get_value("credentials", "sms_auth", "password"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(auth[0], auth[1])
    return server, auth[0]

def __get_active_numbers():
    people = svc_common.get_active_users_value("phone_number")

    # This needs to be changed with https://trello.com/c/MhK6UZ1M
    # Returns list of SMS recipients ["phone_no" + "carrier_addr" ... n]
    address = vault.get_value("carriers", "tmobile", "address")
    return [phone_no + address for phone_no in people]

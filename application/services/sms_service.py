from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from application.services import security as vault
from application.services import svc_common

import smtplib
import os

def send_message(camera, timestamp, feed_url, img_filename):
    """
    Sends an SMS message via a carrier through SMTP. 
    """
    text = svc_common.get_detection_message(camera, timestamp, feed_url);

    msg = MIMEMultipart()
    msg.attach(MIMEText(text))

    img_data = open(img_filename, 'rb').read()
    image = MIMEImage(img_data, name=os.path.basename(img_filename))

    msg.attach(image)
    server, email = setup_smtp_server()
    recipients = get_active_numbers()

    # Edge case causes crash if no active recipients.
    if len(recipients) > 0:
        server.sendmail(email, recipients, msg.as_string())

def send_opt_message(user, opt_in, settings_url):
    """
    Sends an SMS message via a carrier through SMTP for opt-in/opt-out.
    """
    title = str("SeamNet Info").center(32)
    text = None

    if opt_in:
        text = """\
        %s\n\n%s,\nYou have opted in for SeamNet SMS notifications.\n\nTo opt out, click the link below:\n%s
        """%(title, user, str(settings_url))
    else:
        text = """\
        %s\n\n%s,\nYou have opted out of SeamNet SMS notifications.\n\nTo opt back in, click the link below:\n%s
        """%(title, user, str(settings_url))

    server, email = setup_smtp_server()

    # This needs to be changed with https://trello.com/c/MhK6UZ1M
    recipient = vault.get_value("recipients", user, "phone_number") + vault.get_value("carriers", "tmobile", "address")

    msg = MIMEMultipart()
    msg.attach(MIMEText(text))

    server.sendmail(email, recipient, text)

def setup_smtp_server():
    auth = (vault.get_value("credentials", "sms_auth", "username"), 
            vault.get_value("credentials", "sms_auth", "password"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(auth[0], auth[1])
    return server, auth[0]

def get_active_numbers():
    people = svc_common.get_active_users_value("phone_number")

    # This needs to be changed with https://trello.com/c/MhK6UZ1M
    # Returns list of SMS recipients ["phone_no" + "carrier_addr" ... n]
    address = vault.get_value("carriers", "tmobile", "address")
    return [phone_no + address for phone_no in people]

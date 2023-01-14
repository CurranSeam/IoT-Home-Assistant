from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from application.services import security as vault

import smtplib
import os

def send_message(camera, timestamp, feed_url, img_filename):
    """
    Sends an SMS message via a carrier through SMTP. 
    """
    timestamp = timestamp.replace(microsecond=0) # Remove milliseconds for readability
    title = str("SeamNet Alert").center(32)
    text = """\
    %s\n\nPerson detected on %s\n\nat %s\n\nView live feed below:\n%s\n\n(v  '  -- ' )>︻╦╤─ - - - 
    """%(title, camera, str(timestamp), str(feed_url))

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
    people = []

    # Add active phone numbers
    for name in vault.get_keys("recipients"):
        active = int(vault.get_value("recipients", name, "active"))
        if active: 
            people.append(vault.get_value("recipients", name, "phone_number")) 

    # This needs to be changed with https://trello.com/c/MhK6UZ1M
    # Returns list of SMS recipients ["phone_no" + "carrier_addr" ... n]
    address = vault.get_value("carriers", "tmobile", "address")
    return [phone_no + address for phone_no in people]

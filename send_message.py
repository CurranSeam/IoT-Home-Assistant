from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import smtplib
import sys
import os
import security as vault

import sys
sys.path.append('/')
import env
 
def send_message(camera, timestamp, feed_url, img_filename, carrier = "tmobile"):
    """
    Sends an SMS message via a carrier through SMTP. 
    """

    timestamp = timestamp.replace(microsecond=0) # Remove milliseconds for readabillity
    title = str("SeamNet Alert").center(32)
    text = """\
    %s\n\nPerson detected on %s\n\nat %s\n\nView live feed below:\n%s\n\n(v  '  -- ' )>︻╦╤─ - - - 
    """%(title, camera, str(timestamp), str(feed_url))

    msg = MIMEMultipart()
    msg.attach(MIMEText(text))

    img_data = open(img_filename, 'rb').read()
    image = MIMEImage(img_data, name=os.path.basename(img_filename))

    msg.attach(image)

    email = vault.get_value("sms", 0)
    password = vault.get_value("sms", 1)
    recipients = [vault.get_value(person) + env.CARRIERS[carrier] for person in env.RECIPIENTS.keys()] 

    auth = (email, password)
 
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(auth[0], auth[1])
 
    server.sendmail(auth[0], recipients, msg.as_string())

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(f"Usage: python3 {sys.argv[0]} <PHONE_NUMBER> <CARRIER> <MESSAGE>")
        sys.exit(0)
 
    phone_number = sys.argv[1]
    carrier = sys.argv[2]
    message = sys.argv[3]
 
    send_message(phone_number, carrier, message)
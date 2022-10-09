from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import smtplib
import sys
import os
 
CARRIERS = {
    "att": "@mms.att.net",
    "tmobile": "@tmomail.net",
    "verizon": "@vtex.com",
    "sprint": "@page.nextel.com"
}
 
EMAIL = "seamutility@gmail.com"
PASSWORD = "jbnpdnldvqdhqlqt"

RECIPIENTS = ["2064036916@tmomail.net", "2064229458@tmomail.net"]
 
def send_message(camera, timestamp, feed_url, img_filename):
    timestamp = timestamp.replace(microsecond=0) # Remove milliseconds for readabillity

    text = """\
    ^^^ SeamNet Alert! ^^^\n\nPerson detected in %s\n\nat %s\n\nView live feed below:\n%s\n\n(v  '  -- ' )>︻╦╤─ - - - 
    """%(camera, str(timestamp), str(feed_url))

    msg = MIMEMultipart()
    # msg['Subject'] = "SeamNet Alert (v ' - ')>"
    msg.attach(MIMEText(text))

    img_data = open(img_filename, 'rb').read()
    image = MIMEImage(img_data, name=os.path.basename(img_filename))

    msg.attach(image)

    # recipient = phone_number + CARRIERS[carrier]
    auth = (EMAIL, PASSWORD)
 
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(auth[0], auth[1])
 
    server.sendmail(auth[0], RECIPIENTS, msg.as_string())

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(f"Usage: python3 {sys.argv[0]} <PHONE_NUMBER> <CARRIER> <MESSAGE>")
        sys.exit(0)
 
    phone_number = sys.argv[1]
    carrier = sys.argv[2]
    message = sys.argv[3]
 
    send_message(phone_number, carrier, message)
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import smtplib
import sys
 
CARRIERS = {
    "att": "@mms.att.net",
    "tmobile": "@tmomail.net",
    "verizon": "@vtex.com",
    "sprint": "@page.nextel.com"
}
 
EMAIL = "seamutility@gmail.com"
PASSWORD = "jbnpdnldvqdhqlqt"
 
def send_message(phone_number, carrier, camera, timestamp, feed_url):
    timestamp = timestamp.replace(microsecond=0) # Remove milliseconds for readabillity
    text = """\
    \n\nPerson detected in %s\n\nat %s\n\nLive feed:\n%s
    """%(camera, str(timestamp), str(feed_url))

    msg = MIMEMultipart()
    msg['Subject'] = "SeamNet Alert (v ' - ')>"
    msg.attach(MIMEText(text))

    recipient = phone_number + CARRIERS[carrier]
    auth = (EMAIL, PASSWORD)
 
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(auth[0], auth[1])
 
    server.sendmail(auth[0], recipient, msg.as_string())

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(f"Usage: python3 {sys.argv[0]} <PHONE_NUMBER> <CARRIER> <MESSAGE>")
        sys.exit(0)
 
    phone_number = sys.argv[1]
    carrier = sys.argv[2]
    message = sys.argv[3]
 
    send_message(phone_number, carrier, message)
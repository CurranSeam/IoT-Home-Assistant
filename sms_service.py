from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import smtplib
import os
import security as vault

def send_message(camera, timestamp, feed_url, img_filename):
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

    auth = (vault.get_value("credentials", "sms_auth", "username"), 
            vault.get_value("credentials", "sms_auth", "password"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(auth[0], auth[1])

    recipients = get_active_numbers()

    server.sendmail(auth[0], recipients, msg.as_string())

def get_active_numbers():
    people = []

    # Add active phone numbers
    for name in vault.get_keys("recipients"):
        active = int(vault.get_value("recipients", name, "active"))
        if active: 
            people.append(vault.get_value("recipients", name, "phone_number")) 

    # Returns list of SMS recipients ["phone_no" + "carrier_addr" ... n]
    address = vault.get_value("carriers", "tmobile", "address")
    return [phone_no + address for phone_no in people]

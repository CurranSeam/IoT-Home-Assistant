from application.services import security as vault

ALERT_TITLE = "SeamBot Alert"

def get_detection_message(camera, timestamp, feed_url):
    # Remove milliseconds for readability
    timestamp = timestamp.replace(microsecond=0)

    return "{}\n\nPerson detected on {}\n\nat {}\n\nView live feed below:\n{}\n\n(v  '  -- ' )>︻╦╤─ - - - ".format(ALERT_TITLE, camera, str(timestamp), str(feed_url))

def bot_greet_message():
    return "Hi!\n\nI'm SeamBot, your home assistant.\n\nSee /help for a list of commands that I can respond to."

def bot_forbidden_message(user_id):
    return "Unauthorized. Bot access denied for user:{}.".format(user_id)

def get_active_users_value(field):
    values = []

    # Add active phone numbers
    for name in vault.get_keys("recipients"):
        active = int(vault.get_value("recipients", name, "active"))
        if active:
            values.append(vault.get_value("recipients", name, field))

    return values

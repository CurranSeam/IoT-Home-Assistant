import psutil
import time

from application.services import security as vault
from application import TFLite_detection_stream

START_TIME = time.time()
ALERT_TITLE = "SeamBot Alert"

def get_detection_message(camera, timestamp, feed_url):
    # Remove milliseconds for readability
    timestamp = timestamp.replace(microsecond=0)

    return "{}\n\nPerson detected on {}\n\nat {}\n\nView live feed below:\n{}\n\n(v  '  -- ' )>︻╦╤─ - - - ".format(ALERT_TITLE, camera, str(timestamp), str(feed_url))

def get_bot_greet_msg():
    return "Hi!\n\nI'm SeamBot, your home assistant.\n\nSee /help for a list of commands that I can respond to."

def get_bot_confirm_msg():
    # Sends a thumbs up emoji
    return "Will do! \U0001F44D"

def get_bot_forbidden_msg(user_id):
    return "Unauthorized. Bot access denied for user:{}.".format(user_id)

def get_bot_stats_msg():
    return "Here are the stats for SeamNet:"

def get_active_users_value(field):
    values = []

    # Add active phone numbers
    for name in vault.get_keys("recipients"):
        active = int(vault.get_value("recipients", name, "active"))
        if active:
            values.append(vault.get_value("recipients", name, field))

    return values

def get_server_stats(show_fps=True):
    memory = psutil.virtual_memory()

    # Divide from Bytes -> KB -> MB
    available = round(memory.available/1024.0/1024.0,1)
    mem_total = round(memory.total/1024.0/1024.0,1)

    disk = psutil.disk_usage('/')

    # Divide from Bytes -> KB -> MB -> GB
    free = round(disk.free/1024.0/1024.0/1024.0,1)
    disk_total = round(disk.total/1024.0/1024.0/1024.0,1)

    time_dif = time.time() - START_TIME
    d = divmod(time_dif, 86400) # days
    h = divmod(d[1],3600)  # hours
    m = divmod(h[1],60)  # minutes
    s = m[1] # seconds

    uptime = "%d days, %d hours, %d minutes, %d seconds" % (d[0],h[0],m[0], s)

    fps = f"FPS: {str(int(TFLite_detection_stream.frame_rate_calc))}\n\n" if show_fps else ""
    stats = """%sServer uptime: %s\n\nCPU temperature: %s °C\n\nMemory: %s\n\nDisk: %s
    """%(fps,
        str(uptime),
        str(psutil.cpu_percent()),
        str(available) + 'MB free / ' + str(mem_total) + 'MB total ( ' + str(memory.percent) + '% )',
        str(free) + 'GB free / ' + str(disk_total) + 'GB total ( ' + str(disk.percent) + '% )'
        )

    return stats

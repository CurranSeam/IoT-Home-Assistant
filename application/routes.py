# -------------------------------------------------------------------------------------------------
# HOME
@app.route("/")
def index():
	# return the rendered template
    try:
        # Authenticate username and password against the Vault.
        vault.authenticate(request.authorization.username, request.authorization.password)
    except:
        return make_response('Could not verify!', 401, {'WWW-Authenticate' : 'Basic realm="Login Required"'})
    return render_template("index.html")
# -------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------
# SETTINGS
# Define the custom Jinja filter
@app.template_filter()
def zip_lists(a, b, c):
    return zip(a, b, c)

# Register the custom filter with Jinja
app.jinja_env.filters['zip'] = zip_lists

@app.route("/settings")
def settings():
    status = []
    recipients = vault.get_keys("recipients")
    numbers = []
    for key in recipients:
        status.append(int(vault.get_value("recipients", key, "active")))
        numbers.append("XXX-XXX-" + vault.get_value("recipients", key, "phone_number")[-4:])
    return render_template("settings.html", users=recipients, statuses=status, phone_nums=numbers, min_conf=min_conf_threshold)

@app.route('/users/<string:user>/sms-notifications', methods=["PUT"])
def update_sms_status(user):
    data = request.get_json()
    sms_status = int(data['sms_notifications'])

    # Update the user's record in the database
    vault.put_value("recipients", user, "active", str(sms_status))

    # Send sms notification of status change
    if sms_status:
        # we are opting in to sms notifications
        sms_service.send_opt_message(user, True, FEED_URL + "/settings")
    else:
        # opted out
        sms_service.send_opt_message(user, False, FEED_URL + "/settings")

    # Return a response to the frontend
    return jsonify({'success': True}), 200

@app.route("/settings/conf-threshold", methods=["PUT"])
def update_min_conf_threshold():
    global min_conf_threshold

    data = request.get_json()
    new_threshold = float(data['new_conf_threshold'])
    min_conf_threshold = new_threshold

    return jsonify({'success': True}), 200
# -------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------
# DETECTION
@app.route("/video_feed/<string:cam>/", methods=["GET"])
def video_feed(cam):
	# return the response generated along with the specific media
	# type (mime type)
    return Response(generate_frame(cam),
		mimetype = "multipart/x-mixed-replace; boundary=frame")    

# DELETE IF UNUSED
# @app.route("/active_cam", methods=['POST'])
# def active_cam():
#     global active_cam
#     cam = request.form['active_cam']
#     active_cam = cam.split("/")[-2]
    
#     return cam
# -------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------
# STATS
@app.route("/stats")
def stats():
    return render_template("stats.html")

@app.route("/get_stats")
def get_stats():
    global frame_rate_calc
	# return the response generated along with the specific media
	# type (mime type)
    def generate():
        while True:
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
 
            stats = """\
                FPS: %s\nServer uptime: %s\nCPU temperature: %s °C\nMemory: %s\nDisk: %s
            """%(str(int(frame_rate_calc)),
                 str(uptime), 
                 str(psutil.cpu_percent()), 
                 str(available) + 'MB free / ' + str(mem_total) + 'MB total ( ' + str(memory.percent) + '% )', 
                 str(free) + 'GB free / ' + str(disk_total) + 'GB total ( ' + str(disk.percent) + '% )'
                )
            yield stats
            time.sleep(0.1)

    return Response(generate(), mimetype='text/plain')
# -------------------------------------------------------------------------------------------------

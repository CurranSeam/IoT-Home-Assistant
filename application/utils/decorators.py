from application.repository import user as User
import application.routes
from functools import wraps
from flask import request, jsonify, make_response, redirect
import jwt

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None

        # ensure the jwt-token is passed with the headers
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        
        # throw error if no token provided
        if not token:
            # return make_response(jsonify({"message": "A valid token is missing!"}), 401)
            return redirect("/login")
        try:
           # decode the token to obtain user public_id
            data = jwt.decode(token)
            current_user = User.get_user(username=data['public_id'])
        except:
            return redirect("/login")

         # Return the user information attached to the token
        return f(current_user, *args, **kwargs)
    return decorator
from functools import wraps
from flask import session, redirect, url_for, flash, jsonify

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # If it's an API request, return 401
            # We can check if the endpoint returns JSON by its path or accept headers, 
            # but simplest here is just checking if it is /api/
            # Assuming we might use this for views too.
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            if session.get('role') != role:
                return jsonify({"error": "Unauthorized Access"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

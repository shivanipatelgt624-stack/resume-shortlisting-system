from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from config.database import db_config
from config.firebase_config import firebase_config
import traceback

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('register.html')

@auth_bp.route('/api/auth/sessionLogin', methods=['POST'])
def session_login():
    """Verify Firebase ID token and establish a server-side session"""
    data = request.json
    id_token = data.get('idToken')
    
    if not id_token:
        return jsonify({"error": "No ID token provided"}), 400
        
    decoded_token = firebase_config.verify_token(id_token)
    if not decoded_token:
        return jsonify({"error": "Invalid or expired ID token"}), 401
        
    uid = decoded_token['uid']
    email = decoded_token.get('email', '')
    
    # Check if user exists in database
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, fullname, role FROM users WHERE id = %s", (uid,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User record not found in database. Please register first."}), 404
            
        # Set session variables
        session['user_id'] = user[0]
        session['fullname'] = user[1]
        session['role'] = user[2]
        session['email'] = email
        
        # Decide redirect URL based on role
        redirect_url = url_for('success') # Used to be home, now going to dummy redirect
        
        return jsonify({"status": "success", "redirect": redirect_url})
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()

@auth_bp.route('/api/auth/register', methods=['POST'])
def api_register():
    """Store complete user metadata after Firebase registration"""
    data = request.json
    uid = data.get('uid')
    email = data.get('email')
    fullname = data.get('fullname')
    role = data.get('role')
    
    if not all([uid, email, fullname, role]):
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        # insert into db
        query = """
            INSERT INTO users (id, fullname, email, role) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (uid, fullname, email, role))
        conn.commit()
        
        # Also auto-login the user into server session
        session['user_id'] = uid
        session['fullname'] = fullname
        session['role'] = role
        session['email'] = email
        
        return jsonify({"status": "success", "redirect": url_for('success')})
    except Exception as e:
        print(f"Registration DB error: {traceback.format_exc()}")
        # Check if it's a unique constraint violation
        if 'unique constraint' in str(e).lower() or 'duplicate' in str(e).lower():
            return jsonify({"error": "Email or ID already exists"}), 409
        return jsonify({"error": "Internal server error"}), 500
    finally:
        conn.close()

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))

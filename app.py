import os
from flask import Flask, jsonify, render_template, redirect, url_for, session, send_from_directory
from config.database import db_config
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.api_routes import api_bp
from routes.chat_routes import chat_bp, init_chat_socketio
from flask_socketio import SocketIO
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_dev_key_change_in_prod')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(api_bp)
app.register_blueprint(chat_bp)

# Initialize SocketIO events
init_chat_socketio(socketio)

# Initialize database tables on app startup
def init_db():
    """Initialize database tables"""
    try:
        conn = db_config.get_connection()
        db_config.create_tables(conn)
        conn.close()
        print("[SUCCESS] Database tables initialized successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {str(e)}")

# Call it immediately when the module is imported (required for `flask run`)
init_db()

@app.route("/")
def home():
    if 'user_id' in session:
        if session.get('role') == 'recruiter':
            return redirect(url_for('dashboard.recruiter_dashboard'))
        else:
            return redirect(url_for('dashboard.seeker_dashboard'))
    return render_template("index.html")

@app.route("/success")
def success():
    """Dummy redirection page after login or signup"""
    return render_template("success.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    """Serve uploaded resume files securely"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    return send_from_directory(uploads_dir, filename)

@app.route("/api/health")
def health():
    """Health check endpoint that tests database connection"""
    try:
        if db_config.test_connection():
            return jsonify({"status": "healthy", "database": "connected"}), 200
        else:
            return jsonify({"status": "unhealthy", "database": "disconnected"}), 503
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # Initialize database before running the app
    init_db()
    print("[SUCCESS] Server is starting on http://127.0.0.1:5000")
    # use_reloader=False is critical to avoid the double-start crash with eventlet on Windows
    socketio.run(app, debug=True, host='127.0.0.1', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)

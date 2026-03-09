import os
import firebase_admin
from firebase_admin import credentials, auth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FirebaseConfig:
    def __init__(self):
        self.app = None
        self.initialize_app()
    
    def initialize_app(self):
        """Initialize the Firebase Admin SDK"""
        try:
            # Check if already initialized
            if not firebase_admin._apps:
                # Resolve path to the credentials file
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                cred_path = os.path.join(base_dir, 'config', 'firebase_credentials.json')
                
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    self.app = firebase_admin.initialize_app(cred)
                    print("[SUCCESS] Firebase Admin SDK initialized successfully")
                else:
                    print(f"[ERROR] Firebase credentials not found at {cred_path}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Firebase: {str(e)}")
            
    def verify_token(self, id_token):
        """Verify a Firebase ID token and return its decoded payload"""
        try:
            # Allow a 60-second clock skew since the local PC clock can be slightly off
            decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=60)
            return decoded_token
        except Exception as e:
            print(f"Token verification failed: {e}")
            return None

firebase_config = FirebaseConfig()

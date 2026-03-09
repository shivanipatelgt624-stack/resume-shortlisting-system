import os
import pg8000
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DatabaseConfig:
    """Database configuration and connection management"""
    
    def __init__(self):
        """Initialize database configuration from environment variables"""
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        self.database = os.getenv('DB_NAME', 'resume_db')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', '')
        
    def get_connection(self):
        """
        Establish and return a PostgreSQL database connection
        
        Returns:
            psycopg2 connection object
            
        Raises:
            psycopg2.Error: If connection fails
        """
        try:
            conn = pg8000.connect(
                host=self.host,
                port=int(self.port) if self.port else None,
                database=self.database,
                user=self.user,
                password=self.password
            )
            print(f"[SUCCESS] Successfully connected to PostgreSQL database: {self.database}")
            return conn
        except Exception as e:
            print(f"[ERROR] Failed to connect to PostgreSQL database")
            print(f"  Error: {str(e)}")
            raise
            
    def test_connection(self):
        """
        Test the database connection
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            # version may be returned as a single string or tuple depending on driver
            ver_text = version[0] if isinstance(version, (list, tuple)) else version
            print(f"  PostgreSQL Version: {ver_text}")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] Connection test failed: {str(e)}")
            return False
            
    def create_tables(self, conn):
        """
        Create necessary database tables if they don't exist
        
        Args:
            conn: Database connection object
        """
        try:
            cursor = conn.cursor()

            # Create users table
            create_users_table = """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(255) PRIMARY KEY,
                fullname VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                role VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_users_table)
            print("[SUCCESS] Users table created/verified")

            # Create resumes table
            create_resumes_table = """
            CREATE TABLE IF NOT EXISTS resumes (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL UNIQUE,
                applicant_name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(20),
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content TEXT
            );
            """

            cursor.execute(create_resumes_table)
            print("[SUCCESS] Resumes table created/verified")
            
            # Create jobs table
            create_jobs_table = """
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                recruiter_id VARCHAR(255) REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                skills TEXT NOT NULL,
                min_experience INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_jobs_table)
            print("[SUCCESS] Jobs table created/verified")
            
            # Create applications table
            create_applications_table = """
            CREATE TABLE IF NOT EXISTS applications (
                id SERIAL PRIMARY KEY,
                job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
                job_seeker_id VARCHAR(255) REFERENCES users(id) ON DELETE CASCADE,
                resume_path VARCHAR(500) NOT NULL,
                extracted_text TEXT,
                detected_skills TEXT,
                status VARCHAR(50) DEFAULT 'Applied',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(job_id, job_seeker_id)
            );
            """
            cursor.execute(create_applications_table)
            
            # We removed the ALTER TABLE statements here because they were causing 
            # a transaction rollback when the columns already existed.
                
            print("[SUCCESS] Applications table created/verified/updated")

            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            print(f"[ERROR] Error creating tables: {str(e)}")
            return False

# Create a global database config instance
db_config = DatabaseConfig()

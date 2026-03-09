# Resume Shortlisting System - Database Setup Guide

## Project Structure

```
resume_shortlisting_system/
├── config/
│   ├── __init__.py
│   └── database.py          # Database configuration and connection management
├── scripts/
│   └── test_db.py           # Database operations test suite (insert/select/update/delete)
├── venv/                     # Python virtual environment
├── .env                      # Environment variables (database credentials)
├── requirements.txt          # Python package dependencies
└── app.py                    # Main Flask application
```

## Installation & Setup

**STATUS:** ✓ COMPLETED

### 1. Prerequisites
- ✓ Python 3.14.3 (already installed)
- ✓ PostgreSQL 18.1 (already installed and running)

### 2. Install Python Dependencies

The following packages have been installed in your virtual environment:
- **psycopg2-binary** (2.9.9) - PostgreSQL adapter for Python
- **python-dotenv** (1.0.0) - Load environment variables from .env file
- **Flask** (3.1.2) - Web framework

View all installed packages:
```bash
pip list
```

### 3. PostgreSQL Database Setup

#### On Windows:

**Option 1: Download and Install PostgreSQL**
1. Download from https://www.postgresql.org/download/windows/
2. During installation, set:
   - Username: `postgres`
   - Password: Your secure password
   - Port: `5432` (default)

**Option 2: Use Windows Subsystem for Linux (WSL 2)**
```bash
# Install PostgreSQL in WSL
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL service
sudo service postgresql start

# Login as postgres user
sudo -u postgres psql
```

#### Create Database and User

Once PostgreSQL is running:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE resume_db;

# Create user (optional, or use 'postgres')
CREATE USER resume_user WITH PASSWORD 'secure_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE resume_db TO resume_user;

# Exit
\q
```

### 4. Configure Environment Variables

Edit `.env` file in the project root:

```env
# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=resume_db
DB_USER=postgres
DB_PASSWORD=your_password_here
```

**Replace** `your_password_here` with your actual PostgreSQL password.

### 5. Test the Database Connection

**Status:** ✓ COMPLETED

Database connection has been verified and is working:
```
✓ Successfully connected to PostgreSQL database: resume_db
  PostgreSQL Version: PostgreSQL 18.1 on x86_64-windows, compiled by msvc-19.44.35221, 64-bit
✓ Resumes table created/verified
✓ Database tables initialized successfully
```

To manually test the connection:
```bash
python -c "from config.database import db_config; db_config.test_connection()"
```

## Database Configuration (`config/database.py`)

### Features:
- ✓ Loads credentials from `.env` file (no hardcoding!)
- ✓ Graceful error handling with descriptive messages
- ✓ Connection pooling support (can be extended)
- ✓ Automatic table creation on first run
- ✓ SQL injection prevention using parameterized queries

### Usage in Your Application:

```python
from config.database import db_config

# Test connection
db_config.test_connection()

# Get connection
conn = db_config.get_connection()
cursor = conn.cursor()

# Execute query with parameterized statements (SAFE!)
cursor.execute("SELECT * FROM resumes WHERE email = %s", (user_email,))
results = cursor.fetchall()

# Always close connections
cursor.close()
conn.close()
```

## Flask Integration

**STATUS:** ✓ COMPLETED

The Flask application has been integrated with the database:

### Features Added:
- ✓ Database initialization on app startup
- ✓ Automatic table creation
- ✓ Health check endpoint `/api/health`
- ✓ JSON response formatting

### Running the Flask App:
```bash
python app.py
```

### Available Endpoints:
- `GET /` - Home endpoint (returns JSON status)
- `GET /api/health` - Database health check

### Health Check Example:
```bash
curl http://localhost:5000/api/health
```

Returns:
```json
{"status": "healthy", "database": "connected"}
```

### Tests Included:
1. **Connection Test** - Verifies database connectivity
2. **Table Creation** - Creates resumes table if not exists
3. **INSERT Test** - Inserts sample resume records
4. **SELECT Test** - Retrieves and displays all resumes
5. **UPDATE Test** - Modifies existing resume records
6. **DELETE Test** - Removes resume records

### Run Tests:
```bash
python scripts/test_db.py
```

## Expected Table Schema

```sql
CREATE TABLE resumes (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    applicant_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(20),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content TEXT
);
```

## Error Handling

### Common Issues:

**1. "Connection refused" Error**
```
Error: connection to server at "localhost" (127.0.0.1), port 5432 failed
```
**Solution:** PostgreSQL is not running
- Start PostgreSQL service
- Check if credentials in `.env` are correct

**2. "Database does not exist" Error**
```
Error: database "resume_db" does not exist
```
**Solution:** Create the database using psql (see step 4 above)

**3. "Access denied" Error**
```
Error: FATAL: password authentication failed
```
**Solution:** Check username and password in `.env` file

**4. "No such file or directory" Error**
```
Error: connection to server at "localhost" (::1)
```
**Solution:** PostgreSQL service not running, or wrong host in `.env`

## Completion Status

### ✓ COMPLETED TASKS
1. ✓ Database configuration complete
2. ✓ Environment variables configured (.env)
3. ✓ PostgreSQL connection verified (PostgreSQL 18.1)
4. ✓ Resume table created
5. ✓ Database integrated with Flask app
6. ✓ Health check endpoint added (/api/health)
7. ✓ Database initialization function created

### UPCOMING TASKS
1. Create API endpoints for resume upload/retrieval
2. Implement resume parsing logic
3. Add shortlisting algorithm
4. Implement database connection pooling
5. Add audit logging for database operations

## Security Best Practices

✓ **Implemented:**
- Environment variables for credentials (no hardcoding)
- Parameterized queries (SQL injection prevention)
- Graceful error handling
- Connection validation

**To Add:**
- Database connection pooling
- Query result caching
- Audit logging for database operations
- SSL/TLS encryption for connections

## Technologies Used

- **Python** 3.14.3
- **PostgreSQL** 12+ (recommended)
- **psycopg2** - Python-PostgreSQL adapter
- **python-dotenv** - Environment variable management
- **Flask** - Web framework (when integrated)

## Support & Troubleshooting

Run diagnostic checks:
```bash
# Check Python setup
python --version

# Check package installation
pip list

# Test database connectivity
python scripts/test_db.py

# View environment configuration
type .env
```

---
**Created:** February 7, 2026
**Task:** S1-T3 Database Connection

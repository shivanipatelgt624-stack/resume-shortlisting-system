import os
from flask import Blueprint, render_template, request, session, jsonify
from utils.auth import login_required, role_required
from config.database import db_config

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/recruiter/dashboard')
@role_required('recruiter')
def recruiter_dashboard():
    """Render the recruiter dashboard showing their posted jobs"""
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT j.id, j.title, j.description, j.skills, j.min_experience, j.created_at,
                   COUNT(a.id) as applicant_count
            FROM jobs j
            LEFT JOIN applications a ON j.id = a.job_id
            WHERE j.recruiter_id = %s 
            GROUP BY j.id
            ORDER BY j.created_at DESC
        """
        cursor.execute(query, (session['user_id'],))
        # Fetch dictionary-like format for easier template rendering
        columns = [col[0] for col in cursor.description]
        jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return render_template('dashboard/recruiter.html', jobs=jobs)
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return render_template('dashboard/recruiter.html', jobs=[], error="Failed to load jobs.")
    finally:
        conn.close()

@dashboard_bp.route('/job/<int:job_id>/applications')
@role_required('recruiter')
def job_applications(job_id):
    """Render all applications for a specific job"""
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        
        # Verify the recruiter owns this job, and get job title
        cursor.execute("SELECT title FROM jobs WHERE id = %s AND recruiter_id = %s", (job_id, session['user_id']))
        job = cursor.fetchone()
        if not job:
            return render_template('dashboard/applications.html', job=None, applications=[], error="Job not found or unauthorized.")
            
        job_title = job[0]
        
        # Fetch applications with seeker info
        query = """
            SELECT a.id, a.resume_path, a.status, a.applied_at, a.detected_skills, a.extracted_text, 
                   u.fullname, u.email
            FROM applications a
            JOIN users u ON a.job_seeker_id = u.id
            WHERE a.job_id = %s
            ORDER BY a.applied_at DESC
        """
        cursor.execute(query, (job_id,))
        columns = [col[0] for col in cursor.description]
        applications = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Extract just the filename for routing
        for app in applications:
            if app['resume_path']:
                app['resume_filename'] = os.path.basename(app['resume_path'])
            else:
                app['resume_filename'] = None
        
        return render_template('dashboard/applications.html', job={"id": job_id, "title": job_title}, applications=applications)
        
    except Exception as e:
        print(f"Error fetching applications: {e}")
        return render_template('dashboard/applications.html', job=None, applications=[], error="Failed to load applications.")
    finally:
        conn.close()

@dashboard_bp.route('/seeker/dashboard')
@role_required('job_seeker')
def seeker_dashboard():
    """Render the job seeker dashboard showing available jobs"""
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        # Fetch all open jobs. In a real app we might want pagination.
        cursor.execute("""
            SELECT j.id, j.title, j.description, j.skills, j.min_experience, j.created_at, u.fullname as recruiter_name
            FROM jobs j
            JOIN users u ON j.recruiter_id = u.id
            ORDER BY j.created_at DESC
        """)
        columns = [col[0] for col in cursor.description]
        jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Also fetch jobs this user has already applied to
        cursor.execute("SELECT job_id, status, applied_at FROM applications WHERE job_seeker_id = %s", (session['user_id'],))
        applied_jobs = {row[0]: {'status': row[1], 'applied_at': row[2]} for row in cursor.fetchall()}
        
        return render_template('dashboard/seeker.html', jobs=jobs, applied_jobs=applied_jobs)
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return render_template('dashboard/seeker.html', jobs=[], applied_jobs={}, error="Failed to load jobs.")
    finally:
        conn.close()

@dashboard_bp.route('/api/jobs', methods=['POST'])
@role_required('recruiter')
def create_job():
    """API endpoint to create a new job posting"""
    data = request.json
    title = data.get('title')
    description = data.get('description')
    skills = data.get('skills')
    min_experience = data.get('min_experience', 0)
    
    if not all([title, description, skills]):
         return jsonify({"error": "Title, description, and skills are required"}), 400
         
    conn = db_config.get_connection()
    try:
         cursor = conn.cursor()
         query = """
             INSERT INTO jobs (recruiter_id, title, description, skills, min_experience)
             VALUES (%s, %s, %s, %s, %s)
         """
         cursor.execute(query, (session['user_id'], title, description, skills, min_experience))
         conn.commit()
         return jsonify({"status": "success", "message": "Job created successfully!"})
    except Exception as e:
         print(f"Job creation error: {e}")
         return jsonify({"error": "Failed to create job"}), 500
    finally:
         conn.close()

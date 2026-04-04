import os
from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
from utils.auth import login_required, role_required
from config.database import db_config

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/recruiter/dashboard')
@role_required('recruiter')
def recruiter_dashboard():
    """Render the recruiter dashboard showing their posted jobs"""
    user_id = session.get('user_id')
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        
        # --- NEW: Mandatory Onboarding Check ---
        cursor.execute("SELECT company_name, company_logo, company_website, industry, company_description FROM recruiter_profiles WHERE user_id = %s", (user_id,))
        profile_row = cursor.fetchone()
        if not profile_row:
            return redirect(url_for('dashboard.recruiter_onboarding'))
            
        company_profile = {
            'company_name': profile_row[0],
            'company_logo': profile_row[1],
            'company_website': profile_row[2],
            'industry': profile_row[3],
            'company_description': profile_row[4]
        }
            
        query = """
            SELECT j.id, j.title, j.description, j.skills, j.min_experience, j.created_at, j.status,
                   COUNT(a.id) as applicant_count
            FROM jobs j
            LEFT JOIN applications a ON j.id = a.job_id
            WHERE j.recruiter_id = %s 
            GROUP BY j.id
            ORDER BY j.created_at DESC
        """
        cursor.execute(query, (user_id,))
        # Fetch dictionary-like format for easier template rendering
        columns = [col[0] for col in cursor.description]
        jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return render_template('dashboard/recruiter.html', jobs=jobs, company_profile=company_profile)
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return render_template('dashboard/recruiter.html', jobs=[], error="Failed to load jobs.")
    finally:
        conn.close()

@dashboard_bp.route('/job/<int:job_id>/skills-overview')
@role_required('recruiter')
def skills_overview(job_id):
    """Full-page skills comparison across all applicants for a job."""
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        # Verify job ownership
        cursor.execute(
            "SELECT id, title, skills FROM jobs WHERE id = %s AND recruiter_id = %s",
            (job_id, session['user_id'])
        )
        job_row = cursor.fetchone()
        if not job_row:
            return render_template('dashboard/skills_overview.html', job=None, applicants=[], error="Job not found.")
        job = {'id': job_row[0], 'title': job_row[1], 'skills': job_row[2]}

        # Fetch all applicants with scores and skills
        cursor.execute("""
            SELECT a.id, u.fullname, u.email,
                   a.skill_score, a.experience_score, a.final_score,
                   a.detected_skills, a.ai_feedback, a.status
            FROM applications a
            JOIN users u ON a.job_seeker_id = u.id
            WHERE a.job_id = %s
            ORDER BY COALESCE(a.final_score, 0) DESC
        """, (job_id,))
        columns = [col[0] for col in cursor.description]
        applicants = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Required skill list from job
        required_skills = [s.strip().lower() for s in job['skills'].split(',') if s.strip()]

        return render_template('dashboard/skills_overview.html',
                               job=job, applicants=applicants,
                               required_skills=required_skills)
    except Exception as e:
        print(f"Skills overview error: {e}")
        return render_template('dashboard/skills_overview.html', job=None, applicants=[], error=str(e))
    finally:
        conn.close()

@dashboard_bp.route('/job/<int:job_id>')
@role_required('recruiter')
def job_detail(job_id):
    """Render the full job details page with skill summary."""
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        # Get job info and verify ownership
        cursor.execute("""
            SELECT j.id, j.title, j.description, j.skills, j.min_experience, j.created_at,
                   COUNT(a.id) as applicant_count
            FROM jobs j
            LEFT JOIN applications a ON j.id = a.job_id
            WHERE j.id = %s AND j.recruiter_id = %s
            GROUP BY j.id
        """, (job_id, session['user_id']))
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        if not row:
            return render_template('dashboard/recruiter.html', jobs=[], error="Job not found.")
        job = dict(zip(columns, row))

        # Aggregate skill frequency across all applicants
        cursor.execute("""
            SELECT detected_skills FROM applications WHERE job_id = %s AND detected_skills IS NOT NULL
        """, (job_id,))
        skill_counts = {}
        for (skills_str,) in cursor.fetchall():
            for skill in skills_str.split(','):
                skill = skill.strip().lower()
                if skill:
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1
        # Sort by frequency
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)

        return render_template('dashboard/job_detail.html', job=job, skill_stats=sorted_skills)
    except Exception as e:
        print(f"Error fetching job detail: {e}")
        return render_template('dashboard/job_detail.html', job=None, skill_stats=[], error="Failed to load job.")
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
        
        # Fetch applications with seeker info and AI evaluation scores
        query = """
            SELECT a.id, a.job_seeker_id, a.resume_path, a.status, a.applied_at, a.detected_skills, a.extracted_text, 
                   a.skill_score, a.experience_score, a.final_score, a.ai_feedback,
                   u.fullname, u.email, u.profile_pic
            FROM applications a
            JOIN users u ON a.job_seeker_id = u.id
            WHERE a.job_id = %s
            ORDER BY a.final_score DESC NULLS LAST, a.applied_at DESC
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

@dashboard_bp.route('/job/<int:job_id>/applications/<int:app_id>')
@role_required('recruiter')
def applicant_detail(job_id, app_id):
    """Render the dedicated AI evaluation page for a single applicant."""
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()

        # Verify recruiter owns this job
        cursor.execute("SELECT title FROM jobs WHERE id = %s AND recruiter_id = %s", (job_id, session['user_id']))
        job = cursor.fetchone()
        if not job:
            return render_template('dashboard/applicant_detail.html', job=None, applicant=None, error="Job not found or unauthorized.")

        job_title = job[0]

        # Fetch the specific application
        query = """
            SELECT a.id, a.resume_path, a.status, a.applied_at, a.detected_skills,
                   a.skill_score, a.experience_score, a.final_score, a.ai_feedback,
                   a.interest_reason, a.availability, a.introduction,
                   u.fullname, u.email
            FROM applications a
            WHERE a.id = %s AND a.job_id = %s
        """
        # (Note: Since we use u.fullname and u.email we must JOIN users)
        query = """
            SELECT a.id, a.job_seeker_id, a.resume_path, a.status, a.applied_at, a.detected_skills,
                   a.skill_score, a.experience_score, a.final_score, a.ai_feedback,
                   a.interest_reason, a.availability, a.introduction,
                   u.fullname, u.email, u.phone, u.profile_pic,
                   sp.experience_type, sp.experience_details, sp.education_details, sp.skills
            FROM applications a
            JOIN users u ON a.job_seeker_id = u.id
            LEFT JOIN seeker_profiles sp ON u.id = sp.user_id
            WHERE a.id = %s AND a.job_id = %s
        """
        cursor.execute(query, (app_id, job_id))
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        if not row:
            return render_template('dashboard/applicant_detail.html', job={"id": job_id, "title": job_title}, applicant=None, error="Applicant not found.")

        applicant = dict(zip(columns, row))
        
        # Parse JSON fields from seeker_profiles
        import json
        for key in ['experience_details', 'education_details', 'skills']:
            if applicant.get(key):
                try:
                    applicant[key] = json.loads(applicant[key])
                except Exception as ex:
                    print(f"Error parsing {key}: {ex}")
                    applicant[key] = []
            else:
                applicant[key] = []
        
        # --- NEW: Automated status trigger ---
        # If the recruiter opens the applicant and it's still 'Applied', move to 'Viewed'
        if applicant['status'] == 'Applied':
            try:
                cursor.execute("UPDATE applications SET status = 'Viewed' WHERE id = %s", (app_id,))
                conn.commit()
                applicant['status'] = 'Viewed'  # Update local dict for current page render
            except Exception as update_err:
                print(f"Error auto-updating status to Viewed: {update_err}")

        if applicant['resume_path']:
            applicant['resume_filename'] = os.path.basename(applicant['resume_path'])
        else:
            applicant['resume_filename'] = None

        return render_template('dashboard/applicant_detail.html',
                               job={"id": job_id, "title": job_title},
                               applicant=applicant)
    except Exception as e:
        print(f"Error fetching applicant detail: {e}")
        return render_template('dashboard/applicant_detail.html', job=None, applicant=None, error="Failed to load applicant.")
    finally:
        conn.close()

@dashboard_bp.route('/seeker/apply/<int:job_id>')
@role_required('job_seeker')
def seeker_apply(job_id):
    """Render the dedicated application and questionnaire page for a specific job."""
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        
        # Verify job exists
        cursor.execute("SELECT id, title FROM jobs WHERE id = %s", (job_id,))
        job_row = cursor.fetchone()
        if not job_row:
            return redirect(url_for('dashboard.seeker_dashboard'))
            
        # Check if already applied
        cursor.execute("SELECT id FROM applications WHERE job_id = %s AND job_seeker_id = %s", 
                      (job_id, session['user_id']))
        if cursor.fetchone():
            return redirect(url_for('dashboard.seeker_dashboard'))
            
        job = {'id': job_row[0], 'title': job_row[1]}
        return render_template('dashboard/apply_job.html', job=job)
    except Exception as e:
        print(f"Error loading apply page: {e}")
        return redirect(url_for('dashboard.seeker_dashboard'))
    finally:
        conn.close()

@dashboard_bp.route('/seeker/dashboard')
@role_required('job_seeker')
def seeker_dashboard():
    """Render the job seeker dashboard showing available jobs"""
    user_id = session.get('user_id')
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        
        # --- NEW: Mandatory Onboarding Check ---
        cursor.execute("SELECT user_id FROM seeker_profiles WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            return redirect(url_for('dashboard.seeker_onboarding'))
            
        cursor.execute("""
            SELECT j.id, j.title, j.description, j.skills, j.min_experience, j.created_at, 
                   j.roles_responsibilities, j.eligibility_criteria, j.status,
                   COALESCE(j.company_name, u.fullname) as recruiter_name, 
                   COALESCE(j.company_logo, u.profile_pic) as company_logo
            FROM jobs j
            JOIN users u ON j.recruiter_id = u.id
            WHERE j.status = 'Open'
            ORDER BY j.created_at DESC
        """)
        columns = [col[0] for col in cursor.description]
        jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        import datetime
        for job in jobs:
            if isinstance(job.get('created_at'), str):
                try:
                    job['created_at'] = datetime.datetime.fromisoformat(job['created_at'].split('.')[0])
                except:
                    pass

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
    """API endpoint to create a new job posting with optional company branding"""
    user_id = session.get('user_id')
    title = request.form.get('title')
    description = request.form.get('description')
    skills = request.form.get('skills')
    min_experience = request.form.get('min_experience', 0)
    company_name = request.form.get('company_name') # Optional
    roles_responsibilities = request.form.get('roles_responsibilities')
    eligibility_criteria = request.form.get('eligibility_criteria')
    
    if not all([title, description, skills]):
         return jsonify({"error": "Title, description, and skills are required"}), 400
         
    # Fetch profile for fallback if needed
    conn = db_config.get_connection()
    company_profile = None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT company_name, company_logo FROM recruiter_profiles WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        if row:
            company_profile = {'name': row[0], 'logo': row[1]}
    except Exception as e:
        print(f"Error fetching profile fallback: {e}")
    finally:
        if 'conn' in locals() and conn: conn.close()

    if not company_name and company_profile:
        company_name = company_profile['name']

    # Handle Company Logo Upload
    company_logo_url = None
    is_new_logo = False
    if 'company_logo' in request.files:
        file = request.files['company_logo']
        if file and file.filename:
            is_new_logo = True
            from werkzeug.utils import secure_filename
            import os
            from datetime import datetime
            
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if ext in ['png', 'jpg', 'jpeg', 'webp', 'gif']:
                unique_filename = f"job_logo_{user_id}_{int(datetime.now().timestamp())}.{ext}"
                upload_dir = os.path.join('static', 'uploads', 'company_logos')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                company_logo_url = f"/static/uploads/company_logos/{unique_filename}"

    if not is_new_logo and company_profile:
        company_logo_url = company_profile['logo']

    conn = db_config.get_connection()
    try:
         cursor = conn.cursor()
         query = """
             INSERT INTO jobs (
                recruiter_id, title, description, skills, min_experience, 
                company_name, company_logo, roles_responsibilities, eligibility_criteria
             )
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
         """
         cursor.execute(query, (
             session['user_id'], title, description, skills, min_experience, 
             company_name if company_name else None,
             company_logo_url,
             roles_responsibilities if roles_responsibilities else None,
             eligibility_criteria if eligibility_criteria else None
         ))
         conn.commit()
         return jsonify({"status": "success", "message": "Job created successfully!"})
    except Exception as e:
         print(f"Job creation error: {e}")
         return jsonify({"error": "Failed to create job"}), 500
    finally:
         conn.close()

@dashboard_bp.route('/seeker/profile')
@role_required('job_seeker')
def seeker_profile():
    '''Renders the Job Seeker Profile dashboard'''
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM seeker_profiles WHERE user_id = %s", (session['user_id'],))
        row = cursor.fetchone()
        columns = [col[0] for col in cursor.description]
        
        profile = None
        if row:
            profile_dict = dict(zip(columns, row))
            import json
            
            def parse_json_safely(data):
                if not data: return []
                if isinstance(data, (list, dict)): return data
                try:
                    return json.loads(data)
                except:
                    return []

            profile = {
                'user_id': profile_dict.get('user_id'),
                'experience_type': profile_dict.get('experience_type'),
                'experience_details': parse_json_safely(profile_dict.get('experience_details')),
                'education_details': parse_json_safely(profile_dict.get('education_details')),
                'skills': parse_json_safely(profile_dict.get('skills'))
            }
        
        return render_template('dashboard/seeker_profile.html', profile=profile)
    except Exception as e:
        print(f"Error fetching seeker profile: {e}")
        return render_template('dashboard/seeker_profile.html', profile=None, error="Failed to load profile data.")
    finally:
        conn.close()

@dashboard_bp.route('/seeker/job/<int:job_id>')
@role_required('job_seeker')
def job_detail_seeker(job_id):
    '''Render the comprehensive job detail page for a Job Seeker'''
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Fetch full job details alongside recruiter information acting as company
        query = '''
            SELECT j.id, j.title, j.description, j.skills, j.min_experience, j.created_at,
                   j.roles_responsibilities, j.eligibility_criteria,
                   COALESCE(j.company_name, u.fullname) as company_name, 
                   COALESCE(j.company_logo, u.profile_pic) as company_logo
            FROM jobs j
            JOIN users u ON j.recruiter_id = u.id
            WHERE j.id = %s
        '''
        cursor.execute(query, (job_id,))
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        
        if not row:
            return redirect(url_for('dashboard.seeker_dashboard'))
            
        import datetime
        job = dict(zip(columns, row))
        if isinstance(job.get('created_at'), str):
            try:
                job['created_at'] = datetime.datetime.fromisoformat(job['created_at'].split('.')[0])
            except:
                pass
        
        # 2. Check if the user has already applied
        cursor.execute("SELECT status, applied_at FROM applications WHERE job_id = %s AND job_seeker_id = %s", (job_id, session['user_id']))
        application = cursor.fetchone()
        
        return render_template('dashboard/job_detail_seeker.html', job=job, application=application)
        
    except Exception as e:
        print(f"Error loading seeker job detail: {e}")
        return redirect(url_for('dashboard.seeker_dashboard'))
    finally:
        conn.close()
@dashboard_bp.route('/seeker/job/<int:job_id>/progress')
@role_required('job_seeker')
def job_progress_seeker(job_id):
    '''Render the comprehensive job application progress page for a seeker'''
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        
        # Fetch job and recruiter name for context
        query = '''
            SELECT j.id, j.title, 
                   COALESCE(j.company_name, u.fullname) as company_name, 
                   COALESCE(j.company_logo, u.profile_pic) as company_logo
            FROM jobs j
            JOIN users u ON j.recruiter_id = u.id
            WHERE j.id = %s
        '''
        cursor.execute(query, (job_id,))
        job_row = cursor.fetchone()
        
        if not job_row:
             return redirect(url_for('dashboard.seeker_dashboard'))
        
        job = {
            'id': job_row[0],
            'title': job_row[1],
            'company_name': job_row[2],
            'company_logo': job_row[3]
        }
        
        # Fetch application details for this seeker and this job
        cursor.execute("""
            SELECT status, applied_at, ai_feedback, final_score
            FROM applications 
            WHERE job_id = %s AND job_seeker_id = %s
        """, (job_id, session['user_id']))
        app_row = cursor.fetchone()
        
        if not app_row:
            return redirect(url_for('dashboard.seeker_dashboard'))
            
        application = {
            'status': app_row[0],
            'applied_at': app_row[1],
            'ai_feedback': app_row[2],
            'final_score': app_row[3]
        }
        
        return render_template('dashboard/job_progress.html', job=job, application=application)
        
    except Exception as e:
        print(f"Error fetching job progress: {e}")
        return redirect(url_for('dashboard.seeker_dashboard'))
    finally:
        conn.close()

# --- ONBOARDING VIEWS ---

@dashboard_bp.route('/recruiter/onboarding')
@role_required('recruiter')
def recruiter_onboarding():
    """Render the recruiter onboarding/profile setup page."""
    return render_template('dashboard/onboarding_recruiter.html')

@dashboard_bp.route('/seeker/onboarding')
@role_required('job_seeker')
def seeker_onboarding():
    """Render the job seeker onboarding/profile setup page."""
    return render_template('dashboard/onboarding_seeker.html')

# --- ONBOARDING API HANDLERS ---

@dashboard_bp.route('/api/recruiter/onboarding', methods=['POST'])
@role_required('recruiter')
def submit_recruiter_onboarding():
    """Save recruiter company profile during onboarding."""
    user_id = session.get('user_id')
    company_name = request.form.get('company_name')
    industry = request.form.get('industry')
    website = request.form.get('website')
    description = request.form.get('description')
    
    if not company_name:
        return jsonify({"error": "Company name is required"}), 400
        
    # Handle Logo (Optional)
    logo_url = None
    if 'logo' in request.files:
        file = request.files['logo']
        if file and file.filename:
            from werkzeug.utils import secure_filename
            import os
            from datetime import datetime
            
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            unique_filename = f"recruiter_logo_{user_id}_{int(datetime.now().timestamp())}.{ext}"
            upload_dir = os.path.join('static', 'uploads', 'company_logos')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            logo_url = f"/static/uploads/company_logos/{unique_filename}"

    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO recruiter_profiles (user_id, company_name, company_website, industry, company_description, company_logo)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                company_website = EXCLUDED.company_website,
                industry = EXCLUDED.industry,
                company_description = EXCLUDED.company_description,
                company_logo = COALESCE(EXCLUDED.company_logo, recruiter_profiles.company_logo)
        """
        cursor.execute(query, (user_id, company_name, website, industry, description, logo_url))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Recruiter onboarding error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@dashboard_bp.route('/api/seeker/onboarding', methods=['POST'])
@role_required('job_seeker')
def submit_seeker_onboarding():
    """Save seeker profile during onboarding."""
    user_id = session.get('user_id')
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    phone = data.get('phone')
    exp_type = data.get('experience_type')
    skills_text = data.get('skills_text')
    bio = data.get('bio_summary')
    
    if not all([phone, exp_type, skills_text]):
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Update user phone
        cursor.execute("UPDATE users SET phone = %s WHERE id = %s", (phone, user_id))
        
        # 2. Insert into seeker_profiles
        query = """
            INSERT INTO seeker_profiles (user_id, full_name, email, phone, experience_type, skills, introduction)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                experience_type = EXCLUDED.experience_type,
                skills = EXCLUDED.skills,
                introduction = EXCLUDED.introduction,
                phone = EXCLUDED.phone
        """
        cursor.execute(query, (
            user_id, 
            session.get('fullname'), 
            session.get('email'), 
            phone, 
            exp_type, 
            skills_text, 
            bio
        ))
        
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Seeker onboarding error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

import os
import uuid
from flask import Blueprint, request, session, jsonify
from werkzeug.utils import secure_filename
from utils.auth import role_required
from config.database import db_config
from routes.chat_routes import socketio

api_bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api_bp.route('/api/apply/<int:job_id>', methods=['POST'])
@role_required('job_seeker')
def apply_to_job(job_id):
    """API endpoint for a job seeker to apply by uploading a resume"""
    if 'resume' not in request.files:
         return jsonify({"error": "No resume file part"}), 400
         
    file = request.files['resume']
    if file.filename == '':
         return jsonify({"error": "No selected file"}), 400
         
    if file and allowed_file(file.filename):
         try:
             # Ensure upload directory exists
             os.makedirs(UPLOAD_FOLDER, exist_ok=True)
             
             # Create a secure and unique filename
             ext = file.filename.rsplit('.', 1)[1].lower()
             unique_filename = f"{session['user_id']}_{str(uuid.uuid4())[:8]}.{ext}"
             file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
             
             # Save file
             file.save(file_path)

             # Convert to PDF if doc or docx
             if ext in ['doc', 'docx']:
                 try:
                     from services.pdf_converter import pdf_converter
                     pdf_filename = f"{session['user_id']}_{str(uuid.uuid4())[:8]}_converted.pdf"
                     pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
                     if pdf_converter.convert_to_pdf(file_path, pdf_path):
                         # Remove original docx and point to new pdf
                         try:
                             os.remove(file_path)
                         except:
                             pass
                         file_path = pdf_path
                 except Exception as conv_err:
                     print(f"Warning: PDF conversion failed, proceeding with original docx: {conv_err}")
             
             # Save application to database
             conn = db_config.get_connection()
             cursor = conn.cursor()
             
             # Check if already applied
             cursor.execute("SELECT id FROM applications WHERE job_id = %s AND job_seeker_id = %s", (job_id, session['user_id']))
             if cursor.fetchone():
                 # Should theoretically not happen due to UI, but secure it anyway
                 conn.close()
                 # Cleanup the saved file since it's a duplicate application
                 if os.path.exists(file_path):
                     os.remove(file_path)
                 return jsonify({"error": "You have already applied to this job."}), 409
                 
             # Fetch required skills for the job to pass to the extractor
             cursor.execute("SELECT skills FROM jobs WHERE id = %s", (job_id,))
             job_record = cursor.fetchone()
             required_skills = job_record[0] if job_record else ""
             
             # --- SPRINT 4 SCRIPT ADDITIONS --- #
             try:
                 from services.parser_service import parser_service
                 from services.skill_extractor import skill_extractor
                 
                 raw_text = parser_service.extract_text(file_path)
                 cleaned_text = parser_service.clean_text(raw_text)
                 
                 detected_skills = skill_extractor.extract_skills(cleaned_text, required_skills)
                 detected_skills_str = ", ".join(detected_skills)
                 
             except Exception as parse_error:
                 print(f"Error during parsing: {parse_error}")
                 raw_text = None
                 detected_skills_str = None
             
             query = """
                 INSERT INTO applications (job_id, job_seeker_id, resume_path, status, extracted_text, detected_skills)
                 VALUES (%s, %s, %s, %s, %s, %s)
             """
             cursor.execute(query, (job_id, session['user_id'], file_path, 'Applied', raw_text, detected_skills_str))
             conn.commit()
             conn.close()
             
             return jsonify({"status": "success", "message": "Application submitted successfully!"})
             
         except Exception as e:
             print(f"File upload/DB error: {e}")
             return jsonify({"error": "An internal error occurred."}), 500
    else:
        return jsonify({"error": "Invalid file type. Only PDF and Word docs are allowed."}), 400

@api_bp.route('/api/evaluate/<int:application_id>', methods=['POST'])
@role_required('recruiter')
def evaluate_application(application_id):
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        # Enhanced query to fetch application details AND seeker profile for holistic AI evaluation
        cursor.execute('''
            SELECT a.extracted_text, j.title, j.description, j.skills,
                   a.interest_reason, a.availability, a.introduction,
                   sp.experience_type, sp.experience_details, sp.education_details, sp.skills as profile_skills
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            LEFT JOIN seeker_profiles sp ON a.job_seeker_id = sp.user_id
            WHERE a.id = %s AND j.recruiter_id = %s
        ''', (application_id, session['user_id']))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Unauthorized or applicant not found"}), 403
            
        (resume_text, job_title, job_desc, job_skills, 
         interest_reason, availability, introduction,
         exp_type, exp_details, edu_details, profile_skills) = row

        # Package extra context for the AI
        candidate_context = {
            "interest_reason": interest_reason,
            "availability": availability,
            "introduction": introduction,
            "experience_type": exp_type,
            "experience_details": exp_details,
            "education_details": edu_details,
            "profile_skills": profile_skills
        }
            
        from services.scoring_service import scoring_service
        score_data = scoring_service.evaluate_resume(resume_text, job_title, job_desc, job_skills, candidate_context)
        
        cursor.execute('''
            UPDATE applications
            SET skill_score=%s, experience_score=%s, final_score=%s, ai_feedback=%s, status='Evaluating'
            WHERE id=%s
        ''', (score_data['skill_score'], score_data['experience_score'], score_data['final_score'], score_data.get('ai_feedback', ''), application_id))
        conn.commit()
        return jsonify(score_data)
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@api_bp.route('/api/jobs/<int:job_id>', methods=['DELETE'])
@role_required('recruiter')
def delete_job(job_id):
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        # Close the job by updating status instead of deleting
        cursor.execute("UPDATE jobs SET status = 'Closed' WHERE id = %s AND recruiter_id = %s", (job_id, session['user_id']))
        conn.commit()
        return jsonify({"status": "success", "message": "Job position closed successfully!"})
    finally:
        conn.close()

@api_bp.route('/api/applications/bulk-shortlist', methods=['POST'])
@role_required('recruiter')
def bulk_shortlist():
    data = request.json
    app_ids = data.get('application_ids', [])
    if not app_ids:
        return jsonify({"error": "No applications selected."}), 400
        
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        shortlisted_count = 0
        for app_id in app_ids:
            # 1. Get Seeker ID and Job Title
            cursor.execute("""
                SELECT a.job_seeker_id, j.title
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.id = %s AND j.recruiter_id = %s
            """, (app_id, session['user_id']))
            row = cursor.fetchone()
            if not row: continue
            
            seeker_id, job_title = row
            
            # 2. Update status
            cursor.execute("UPDATE applications SET status = 'Shortlisted' WHERE id = %s", (app_id,))
            shortlisted_count += 1
            
            # 3. Find or Create 1:1 Conversation
            cursor.execute("""
                SELECT c.id FROM conversations c
                JOIN participants p1 ON c.id = p1.conversation_id
                JOIN participants p2 ON c.id = p2.conversation_id
                WHERE c.type = 'individual' AND p1.user_id = %s AND p2.user_id = %s
            """, (session['user_id'], seeker_id))
            conv_row = cursor.fetchone()
            
            if conv_row:
                conv_id = conv_row[0]
            else:
                cursor.execute("INSERT INTO conversations (type) VALUES ('individual') RETURNING id")
                conv_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO participants (conversation_id, user_id) VALUES (%s, %s)", (conv_id, session['user_id']))
                cursor.execute("INSERT INTO participants (conversation_id, user_id) VALUES (%s, %s)", (conv_id, seeker_id))
            
            # 4. Send Automated Message
            auto_msg = f"Congratulations! You have been shortlisted for the position of {job_title}. We will get back to you soon regarding the next steps."
            cursor.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (%s, %s, %s) RETURNING id, timestamp",
                (conv_id, session['user_id'], auto_msg)
            )
            msg_id, msg_ts = cursor.fetchone()
            
            # 5. Emit Socket Event (Real-time)
            if socketio:
                socketio.emit('new_message', {
                    'id': msg_id,
                    'conversation_id': conv_id,
                    'sender_id': session['user_id'],
                    'sender_name': session.get('fullname', 'Recruiter'),
                    'content': auto_msg,
                    'timestamp': msg_ts.isoformat() if hasattr(msg_ts, 'isoformat') else str(msg_ts)
                }, room=f"conv_{conv_id}")

        conn.commit()
        return jsonify({"success": True, "message": f"Successfully shortlisted {shortlisted_count} candidates and sent congratulatory messages."})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@api_bp.route('/api/applications/bulk-reject', methods=['POST'])
@role_required('recruiter')
def bulk_reject():
    data = request.json
    app_ids = data.get('application_ids', [])
    if not app_ids:
        return jsonify({"error": "No applications selected."}), 400
        
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        rejected_count = 0
        for app_id in app_ids:
            # 1. Get Seeker ID, Job Title, and AI Feedback
            cursor.execute("""
                SELECT a.job_seeker_id, j.title, a.ai_feedback
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.id = %s AND j.recruiter_id = %s
            """, (app_id, session['user_id']))
            row = cursor.fetchone()
            if not row: continue
            
            seeker_id, job_title, feedback = row
            
            # 2. Update status
            cursor.execute("UPDATE applications SET status = 'Rejected' WHERE id = %s", (app_id,))
            rejected_count += 1
            
            # 3. Find or Create 1:1 Conversation
            cursor.execute("""
                SELECT c.id FROM conversations c
                JOIN participants p1 ON c.id = p1.conversation_id
                JOIN participants p2 ON c.id = p2.conversation_id
                WHERE c.type = 'individual' AND p1.user_id = %s AND p2.user_id = %s
            """, (session['user_id'], seeker_id))
            conv_row = cursor.fetchone()
            
            if conv_row:
                conv_id = conv_row[0]
            else:
                cursor.execute("INSERT INTO conversations (type) VALUES ('individual') RETURNING id")
                conv_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO participants (conversation_id, user_id) VALUES (%s, %s)", (conv_id, session['user_id']))
                cursor.execute("INSERT INTO participants (conversation_id, user_id) VALUES (%s, %s)", (conv_id, seeker_id))
            
            # 4. Construct Rejection Message with AI Feedback
            if not feedback or feedback.strip() == "":
                feedback = "our team has reviewed your application and decided not to move forward at this time."
            else:
                feedback = f"our AI analysis suggests focusing on: {feedback}"
                
            auto_msg = f"Thank you for applying for the position of {job_title}. While we aren't moving forward, {feedback}"
            
            cursor.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (%s, %s, %s) RETURNING id, timestamp",
                (conv_id, session['user_id'], auto_msg)
            )
            msg_id, msg_ts = cursor.fetchone()
            
            # 5. Emit Socket Event (Real-time)
            if socketio:
                socketio.emit('new_message', {
                    'id': msg_id,
                    'conversation_id': conv_id,
                    'sender_id': session['user_id'],
                    'sender_name': session.get('fullname', 'Recruiter'),
                    'content': auto_msg,
                    'timestamp': msg_ts.isoformat() if hasattr(msg_ts, 'isoformat') else str(msg_ts)
                }, room=f"conv_{conv_id}")

        conn.commit()
        return jsonify({"success": True, "message": f"Successfully rejected {rejected_count} candidates and sent feedback messages."})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@api_bp.route('/api/jobs/analytics', methods=['GET'])
@role_required('recruiter')
def get_analytics():
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE recruiter_id = %s", (session['user_id'],))
        jobs_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE j.recruiter_id = %s
        ''', (session['user_id'],))
        apps_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE j.recruiter_id = %s AND a.status = 'Shortlisted'
        ''', (session['user_id'],))
        short_count = cursor.fetchone()[0]
        
        return jsonify({
            "total_jobs": jobs_count,
            "total_applications": apps_count,
            "shortlisted": short_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@api_bp.route('/api/seeker/profile/update', methods=['POST'])
@role_required('job_seeker')
def update_seeker_profile():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    user_id = session['user_id']
    import json
    phone = data.get('phone', '')
    experience_type = data.get('experience_type', '')
    experience_details = json.dumps(data.get('experience_details', []))
    education_details = json.dumps(data.get('education_details', []))
    skills = json.dumps(data.get('skills', []))
    
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET phone = %s WHERE id = %s", (phone, user_id))
        session['phone'] = phone
        
        upsert_query = '''
            INSERT INTO seeker_profiles 
                (user_id, highest_education, education_years, experience_type, experience_details, skills, education_details)
            VALUES 
                (%s, '', NULL, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                experience_type = EXCLUDED.experience_type,
                experience_details = EXCLUDED.experience_details,
                skills = EXCLUDED.skills,
                education_details = EXCLUDED.education_details
        '''
        cursor.execute(upsert_query, (
            user_id, experience_type, experience_details, skills, education_details
        ))
        conn.commit()
        return jsonify({"success": True, "message": "Profile updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@api_bp.route('/api/profile/upload-photo', methods=['POST'])
def upload_profile_photo():
    if 'photo' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['photo']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and file.filename.lower().endswith(('png', 'jpg', 'jpeg')):
        import uuid
        filename = f"{session['user_id']}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join('static', 'uploads', 'profiles')
        os.makedirs(filepath, exist_ok=True)
        file.save(os.path.join(filepath, filename))
        url = f"/static/uploads/profiles/{filename}"
        conn = db_config.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET profile_pic = %s WHERE id = %s", (url, session['user_id']))
            conn.commit()
            session['profile_pic'] = url
            return jsonify({"photo_url": url})
        finally:
            conn.close()
    return jsonify({"error": "Invalid format"}), 400

@api_bp.route('/api/applications/<int:app_id>/status', methods=['POST'])
@role_required('recruiter')
def update_application_status(app_id):
    data = request.json
    status = data.get('status')
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE applications SET status = %s WHERE id = %s", (status, app_id))
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()

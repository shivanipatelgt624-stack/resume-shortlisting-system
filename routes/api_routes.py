import os
import uuid
from flask import Blueprint, request, session, jsonify
from werkzeug.utils import secure_filename
from utils.auth import role_required
from config.database import db_config

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

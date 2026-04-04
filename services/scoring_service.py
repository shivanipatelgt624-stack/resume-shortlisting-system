import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class ScoringService:
    def __init__(self):
        # We initialized lazily to ensure .env is loaded before grabbing the key
        self.client = None

    def get_client(self):
        if not self.client:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                print("WARNING: GROQ_API_KEY not found in environment")
            self.client = Groq(api_key=api_key)
        return self.client

    def evaluate_resume(self, resume_text, job_title, job_description, job_skills, candidate_context=None):
        if not resume_text:
            return {
                "skill_score": 0, "experience_score": 0, "final_score": 0,
                "ai_feedback": "No resume text found or extracted."
            }
            
        context_str = ""
        if candidate_context:
            context_str = f"""
Additional Candidate Context:
- Introduction: {candidate_context.get('introduction', 'N/A')}
- Interest Reason: {candidate_context.get('interest_reason', 'N/A')}
- Availability: {candidate_context.get('availability', 'N/A')}
- Experience Type: {candidate_context.get('experience_type', 'N/A')}
- Profile Experience: {candidate_context.get('experience_details', 'N/A')}
- Profile Education: {candidate_context.get('education_details', 'N/A')}
- Profile Skills: {candidate_context.get('profile_skills', 'N/A')}
"""

        prompt = f"""You are an expert technical recruiter and AI scoring engine.
Evaluate this candidate based on their resume, their professional profile, and their specific job application responses.
Provide a holistic assessment of their fit for the role.

Job Title: {job_title}
Job Description: {job_description}
Required Skills: {job_skills}

{context_str}

Resume Text:
{resume_text[:6000]}

You MUST output ONLY a valid JSON object matching this exact format:
{{
  "skill_score": <integer 0-100 based on skill matches across resume and profile>,
  "experience_score": <integer 0-100 based on relevant depth and career progression>,
  "final_score": <integer 0-100 overall fit, considering skills, motivation (interest reason), and availability>,
  "ai_feedback": "<A comprehensive 3-5 sentence personalized evaluation for the recruiter. Mention specific strengths from their resume/profile and touch upon their stated motivation and availability.>"
}}
"""
        try:
            client = self.get_client()
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise JSON outputting machine. You only output valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            response_text = chat_completion.choices[0].message.content
            response_json = json.loads(response_text)
            
            return {
                "skill_score": int(response_json.get("skill_score", 0)),
                "experience_score": int(response_json.get("experience_score", 0)),
                "final_score": int(response_json.get("final_score", 0)),
                "ai_feedback": str(response_json.get("ai_feedback", "AI failed to provide feedback."))
            }
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return {
                "skill_score": 0,
                "experience_score": 0,
                "final_score": 0,
                "ai_feedback": f"Scoring failed due to an AI service error: {str(e)}"
            }

scoring_service = ScoringService()

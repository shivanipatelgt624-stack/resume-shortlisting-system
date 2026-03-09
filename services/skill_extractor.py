import re

class SkillExtractor:
    @staticmethod
    def extract_skills(resume_text, required_skills_string):
        """
        Matches cleaned resume text against a comma-separated list of required skills.
        Returns a list of matching skills.
        """
        if not resume_text or not required_skills_string:
            return []
            
        # Clean both text sources to ensure matching works
        resume_text = resume_text.lower()
        
        # Parse the required skills into a list, lowercased, and cleaned
        raw_skills = [s.strip().lower() for s in required_skills_string.split(',')]
        required_skills = [s for s in raw_skills if s]
        
        detected_skills = []
        
        for skill in required_skills:
            # Create a word boundary regex to avoid partial matches
            # e.g., 'C' matching inside 'react', or 'Java' inside 'Javascript'
            # We must escape the skill string because of skills like C++
            escaped_skill = re.escape(skill)
            
            # Using simple regex to find the skill as an exact word block
            # \b doesn't always work perfectly with symbols like ++, so we use a custom boundary check
            # Look for the skill surrounded by non-word characters or string boundaries
            pattern = r'(?:^|[^a-z0-9_])' + escaped_skill + r'(?:[^a-z0-9_]|$)'
            
            if re.search(pattern, resume_text):
                detected_skills.append(skill)
                
        return detected_skills

skill_extractor = SkillExtractor()

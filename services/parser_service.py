import os
import re
import fitz  # PyMuPDF
from docx import Document

class ParserService:
    @staticmethod
    def extract_text(file_path):
        """Extract text from PDF, DOCX, or Image file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        ext = file_path.rsplit('.', 1)[1].lower()
        if ext == 'pdf':
            return ParserService._extract_from_pdf(file_path)
        elif ext in ['docx', 'doc']:
            return ParserService._extract_from_docx(file_path)
        elif ext in ['png', 'jpg', 'jpeg']:
            return ParserService._extract_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _extract_from_image(file_path):
        """Extract text from an image using Groq's Vision API."""
        try:
            import base64
            from groq import Groq
            
            # Read image to base64
            with open(file_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            
            chat_completion = client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all the text tightly and exactly from this image. Do not include any conversational filler, just the extracted text."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                temperature=0.1
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error reading Image via Groq: {e}")
            raise

    @staticmethod
    def _extract_from_pdf(file_path):
        """Extract text from a PDF file using PyMuPDF."""
        text = ""
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            print(f"Error reading PDF: {e}")
            raise
        return text

    @staticmethod
    def _extract_from_docx(file_path):
        """Extract text from a DOCX file."""
        try:
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        except Exception as e:
            print(f"Error reading DOCX: {e}")
            raise
            
    @staticmethod
    def clean_text(text):
        """
        Clean the extracted text by lowercasing, 
        removing special symbols, and normalizing spacing.
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Replace newlines and tabs with spaces
        text = text.replace('\n', ' ').replace('\t', ' ')
        
        # Remove special characters (keep alphanumeric, standard punctuation, and spaces)
        # We might want to keep C++, C#, .NET so we don't completely strip all symbols.
        # Let's keep + and # for now.
        text = re.sub(r'[^a-z0-9\s\.\+#,-]', ' ', text)
        
        # Normalize multiple spaces into a single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

# Create singleton instance
parser_service = ParserService()

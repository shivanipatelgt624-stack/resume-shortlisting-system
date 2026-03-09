import os
import re
import fitz  # PyMuPDF
from docx import Document

class ParserService:
    @staticmethod
    def extract_text(file_path):
        """Extract text from PDF or DOCX file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        ext = file_path.rsplit('.', 1)[1].lower()
        if ext == 'pdf':
            return ParserService._extract_from_pdf(file_path)
        elif ext in ['docx', 'doc']:
            return ParserService._extract_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

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

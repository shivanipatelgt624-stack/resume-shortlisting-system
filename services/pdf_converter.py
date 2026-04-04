import os

class PDFConverter:
    @staticmethod
    def convert_to_pdf(input_path, output_path):
        """
        Converts a Word document (.doc or .docx) to a PDF file using Microsoft Word via COM.
        Returns True if successful, False otherwise.
        """
        try:
            import pythoncom
            import win32com.client
            
            # Initialize COM for the current thread
            pythoncom.CoInitialize()
            
            # Dispatch Word Application
            word = win32com.client.DispatchEx('Word.Application')
            word.Visible = False
            
            # Ensure absolute paths are used for COM
            abs_input = os.path.abspath(input_path)
            abs_output = os.path.abspath(output_path)
            
            # Open document
            doc_obj = word.Documents.Open(abs_input)
            
            # Save as PDF (FileFormat=17)
            doc_obj.SaveAs(abs_output, FileFormat=17)
            
            # Close and quit
            doc_obj.Close()
            word.Quit()
            
            return True
        except Exception as e:
            print(f"Failed to convert to PDF: {e}")
            try:
                # Attempt to quit word if an error happened while it was open
                word.Quit()
            except:
                pass
            return False

    @staticmethod
    def convert_image_to_pdf(input_path, output_path):
        """Converts an image file (PNG, JPG) to a PDF using Pillow."""
        try:
            from PIL import Image
            image = Image.open(input_path)
            # Convert to RGB if necessary (e.g. for PNG with alpha channel)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(output_path, "PDF", resolution=100.0)
            return True
        except Exception as e:
            print(f"Failed to convert image to PDF: {e}")
            return False

pdf_converter = PDFConverter()

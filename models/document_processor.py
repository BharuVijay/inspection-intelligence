"""
Document ingestion and preprocessing module
Handles file upload, parsing, and text extraction
"""
try:
    import fitz as pymupdf  # PyMuPDF
except ImportError:
    pymupdf = None
import PyPDF2
from pathlib import Path
from typing import List, Tuple
import tempfile


class DocumentProcessor:
    """Processes various document formats"""
    
    def __init__(self):
        self.supported_formats = {'.pdf', '.txt', '.png', '.jpg', '.jpeg'}
    
    def extract_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF documents
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text content
        """
        text_content = []
        try:
            pdf_lib = pymupdf
            if pdf_lib is not None and hasattr(pdf_lib, "open"):
                with pdf_lib.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf):
                        text = page.get_text()
                        if text.strip():
                            text_content.append(f"--- Page {page_num + 1} ---\n{text}")
            else:
                with open(file_path, "rb") as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    for page_num, page in enumerate(reader.pages):
                        text = page.extract_text() or ""
                        if text.strip():
                            text_content.append(f"--- Page {page_num + 1} ---\n{text}")

            return "\n".join(text_content)
        except Exception as e:
            raise ValueError(f"Error extracting PDF: {str(e)}")
    
    def extract_from_text(self, file_path: str) -> str:
        """
        Extract content from text files
        
        Args:
            file_path: Path to text file
            
        Returns:
            File content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Error reading text file: {str(e)}")
    
    def extract_from_file(self, file_path: str) -> Tuple[str, str]:
        """
        Extract content from any supported file format
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (extracted_text, file_type)
        """
        path = Path(file_path)
        file_ext = path.suffix.lower()
        
        if file_ext not in self.supported_formats:
            raise ValueError(
                f"Unsupported format: {file_ext}. "
                f"Supported: {', '.join(self.supported_formats)}"
            )
        
        content = ""
        file_type = "unknown"

        if file_ext == '.pdf':
            content = self.extract_from_pdf(file_path)
            file_type = 'pdf'
        elif file_ext == '.txt':
            content = self.extract_from_text(file_path)
            file_type = 'text'
        elif file_ext in {'.png', '.jpg', '.jpeg'}:
            # For images, create a placeholder (would need OCR for real implementation)
            content = self._extract_from_image(file_path)
            file_type = 'image'
        
        return content, file_type
    
    def _extract_from_image(self, file_path: str) -> str:
        """
        Placeholder for image extraction (OCR)
        In production, use Tesseract or cloud vision APIs
        
        Args:
            file_path: Path to image file
            
        Returns:
            Extracted text (placeholder)
        """
        return f"[Image content from {Path(file_path).name} - OCR extraction placeholder]"
    
    def preprocess_text(self, text: str) -> str:
        """
        Clean and preprocess extracted text
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        # Remove duplicate empty lines
        cleaned = '\n'.join(lines)
        return cleaned
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Split text into overlapping chunks for processing
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks


def process_uploaded_file(file_content: bytes, file_name: str) -> Tuple[str, str]:
    """
    Process uploaded file and extract content
    
    Args:
        file_content: Binary content of file
        file_name: Name of file
        
    Returns:
        Tuple of (extracted_text, file_type)
    """
    processor = DocumentProcessor()
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=Path(file_name).suffix, delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name
    
    try:
        content, file_type = processor.extract_from_file(tmp_path)
        content = processor.preprocess_text(content)
        return content, file_type
    finally:
        Path(tmp_path).unlink()  # Clean up temp file


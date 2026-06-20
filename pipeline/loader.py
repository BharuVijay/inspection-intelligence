import json
import os
from pathlib import Path
import PyPDF2

def load_sample_reports():
    """Load inspection reports from sample_reports.json"""
    data_dir = Path(__file__).parent.parent / "data"
    json_file = data_dir / "sample_reports.json"
    
    if json_file.exists():
        with open(json_file, 'r') as f:
            return json.load(f)
    return []

def extract_pdf_text():
    """Extract text from PDF"""
    data_dir = Path(__file__).parent.parent / "data"
    pdf_file = data_dir / "The_Merged_Approved_Documents_Oct24.pdf"
    
    texts = []
    if pdf_file.exists():
        try:
            with open(pdf_file, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(reader.pages[:5]):  # First 5 pages
                    text = page.extract_text()
                    if text.strip():
                        texts.append({
                            "source": f"PDF Page {page_num + 1}",
                            "text": text
                        })
        except Exception as e:
            print(f"Error reading PDF: {e}")
    
    return texts

def get_image_counts():
    """Get counts of positive and negative crack images"""
    data_dir = Path(__file__).parent.parent / "data"
    images_dir = data_dir / "Concrete Crack Images for Classification"
    
    counts = {
        "positive": 0,
        "negative": 0
    }
    
    if images_dir.exists():
        positive_dir = images_dir / "Positive"
        negative_dir = images_dir / "Negative"
        
        if positive_dir.exists():
            counts["positive"] = len([f for f in positive_dir.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
        
        if negative_dir.exists():
            counts["negative"] = len([f for f in negative_dir.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
    
    return counts

def get_image_samples(category='negative', limit=5):
    """Get sample image paths for preview"""
    data_dir = Path(__file__).parent.parent / "data"
    images_dir = data_dir / "Concrete Crack Images for Classification"
    
    category_dir = images_dir / category.capitalize()
    images = []
    
    if category_dir.exists():
        for img_file in sorted(category_dir.iterdir())[:limit]:
            if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                images.append(str(img_file))
    
    return images


import os
from pathlib import Path
import pymupdf
from typing import Dict, Any, List

class PDFProcessingError(Exception):
    pass

def validate_pdf_file(file_path: Path, max_size_bytes: int = 100 * 1024 * 1024) -> None:
    if not file_path.exists():
        raise PDFProcessingError("File not found on server")
    
    file_size = file_path.stat().st_size
    if file_size > max_size_bytes:
        raise PDFProcessingError(f"File size ({file_size / (1024 * 1024):.1f} MB) exceeds maximum allowed limit of 100 MB")
    
    # Validate magic bytes
    with open(file_path, "rb") as f:
        header = f.read(5)
        if not header.startswith(b"%PDF-"):
            raise PDFProcessingError("Invalid file signature: File is not a valid PDF")
            
    # Validate PyMuPDF can open and read pages
    try:
        doc = pymupdf.open(file_path)
        if len(doc) == 0:
            raise PDFProcessingError("PDF contains no pages")
        doc.close()
    except Exception as e:
        raise PDFProcessingError(f"PDF structure is corrupted or unreadable: {str(e)}")

def extract_pdf_content(file_path: Path, low_text_threshold: int = 50, max_size_bytes: int = 100 * 1024 * 1024) -> Dict[str, Any]:
    """
    Extracts text page-by-page from PDF.
    Calculates character count and detects scanned / low text pages.
    """
    validate_pdf_file(file_path, max_size_bytes)
    
    doc = pymupdf.open(file_path)
    total_pages = len(doc)
    
    pages_data: List[Dict[str, Any]] = []
    extracted_pages = 0
    scanned_pages = 0
    low_text_pages = 0
    
    for idx, page in enumerate(doc):
        page_num = idx + 1
        text = page.get_text("text").strip()
        char_count = len(text)
        
        # Check images on page to distinguish pure blank vs scanned image
        images = page.get_images()
        has_images = len(images) > 0
        
        is_low_text = False
        is_scanned = False
        
        if char_count < low_text_threshold:
            is_low_text = True
            low_text_pages += 1
            if has_images or char_count == 0:
                is_scanned = True
                scanned_pages += 1
        else:
            extracted_pages += 1
            
        pages_data.append({
            "page_number": page_num,
            "character_count": char_count,
            "is_scanned": is_scanned,
            "is_low_text": is_low_text,
            "text_content": text
        })
        
    doc.close()
    
    # Trigger OCR warning if more than 15% or at least 2 pages have low text / scanned
    ocr_warning = (scanned_pages > 0 or low_text_pages > 1)
    
    return {
        "total_pages": total_pages,
        "extracted_pages": extracted_pages,
        "scanned_pages": scanned_pages,
        "low_text_pages": low_text_pages,
        "ocr_warning": ocr_warning,
        "pages": pages_data
    }

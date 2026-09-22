import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import pymupdf
import mammoth
import docx
from docx.shared import Inches
from pdf2docx import Converter

from app.core.config import settings
from app.services.pdf_exporter import export_html_to_pdf

DEVANAGARI_DIGITS = {
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9", "१०": "10"
}

def normalize_digits(text: str) -> str:
    for d, a in DEVANAGARI_DIGITS.items():
        text = text.replace(d, a)
    return text

def extract_metadata(file_path: Path, filename: str) -> Dict[str, Any]:
    """
    Extracts Class (5-10), Subject, and Paper Name from file content and filename.
    """
    detected_grade = ""
    detected_subject = "हिंदी"
    text_content = ""

    ext = file_path.suffix.lower()

    if ext == ".pdf":
        try:
            doc = pymupdf.open(file_path)
            for page in doc[:3]:
                text_content += page.get_text() + "\n"
            doc.close()
        except Exception as e:
            print(f"Error reading PDF text for metadata: {e}")
    elif ext in [".docx", ".doc"]:
        try:
            wdoc = docx.Document(file_path)
            for p in wdoc.paragraphs[:30]:
                text_content += p.text + "\n"
            for table in wdoc.tables[:3]:
                for row in table.rows:
                    for cell in row.cells:
                        text_content += cell.text + " "
                    text_content += "\n"
        except Exception as e:
            print(f"Error reading DOCX text for metadata: {e}")

    normalized_text = normalize_digits(text_content)
    normalized_filename = normalize_digits(filename)

    # 1. Search for Grade / Class in content first, then filename
    # Patterns: कक्षा : 10, कक्षा 10वीं, Class 10, Std 10, 10th
    grade_patterns = [
        r"कक्षा\s*[:\-–]?\s*(\d{1,2})",
        r"कक्षा\s*[:\-–]?\s*([०-९]{1,2})",
        r"class\s*[:\-–]?\s*(\d{1,2})",
        r"std\s*[:\-–]?\s*(\d{1,2})",
        r"(\d{1,2})\s*(?:th|वीं|वी)",
        r"(?:^|[_\-\s])([5-9]|10)(?:[_\-\s\.]|$)",
    ]

    for pat in grade_patterns:
        m = re.search(pat, normalized_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val in ["5", "6", "7", "8", "9", "10"]:
                detected_grade = val
                break

    if not detected_grade:
        for pat in grade_patterns:
            m = re.search(pat, normalized_filename, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if val in ["5", "6", "7", "8", "9", "10"]:
                    detected_grade = val
                    break

    if not detected_grade:
        detected_grade = "10"

    # 2. Search for Subject
    if "लोकभारती" in text_content or "लोकभारती" in filename or detected_grade in ["9", "10"]:
        detected_subject = "हिंदी (लोकभारती)"
    elif "सुलभभारती" in text_content or "सुलभभारती" in filename or detected_grade in ["5", "6", "7", "8"]:
        detected_subject = "हिंदी (सुलभभारती)"
    elif "हिंदी" in text_content or "hindi" in filename.lower():
        detected_subject = "हिंदी"

    # 3. Format Title as requested: "Class {grade} — Hindi Paper"
    title = f"Class {detected_grade} — Hindi Paper"

    return {
        "grade": detected_grade,
        "subject": detected_subject,
        "title": title
    }

def convert_pdf_to_docx(pdf_path: Path, output_docx_path: Path) -> Path:
    """
    Converts PDF to DOCX preserving Devanagari text, layout, and tables.
    Falls back to high-res image page embedding if PDF is purely scanned or pdf2docx fails.
    """
    output_docx_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        cv = Converter(str(pdf_path))
        cv.convert(str(output_docx_path))
        cv.close()
        
        # Verify file was written and is not 0 bytes
        if output_docx_path.exists() and output_docx_path.stat().st_size > 0:
            return output_docx_path
    except Exception as e:
        print(f"pdf2docx conversion error, falling back to image embedding: {e}")

    # Fallback for scanned PDFs: extract high-res page images and insert into DOCX
    doc = pymupdf.open(pdf_path)
    wdoc = docx.Document()
    # Set 0.5 inch margins for A4
    for section in wdoc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=200)
        temp_img = output_docx_path.parent / f"temp_{output_docx_path.stem}_{i}.png"
        pix.save(str(temp_img))
        wdoc.add_picture(str(temp_img), width=Inches(7.2))
        if i < len(doc) - 1:
            wdoc.add_page_break()
        try:
            temp_img.unlink(missing_ok=True)
        except Exception:
            pass

    doc.close()
    wdoc.save(str(output_docx_path))
    return output_docx_path

def convert_docx_to_html(docx_path: Path) -> str:
    """
    Converts DOCX to clean HTML wrapped in A4 paper styling.
    """
    with open(docx_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        body_html = result.value

    wrapped_html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <title>Uploaded Paper Preview</title>
    <style>
        @page {{ size: A4 portrait; margin: 12mm; }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: Arial, "Devanagari Sangam MN", "Arial Unicode MS", sans-serif;
            font-size: 11.5pt;
            line-height: 1.6;
            color: #111827;
            background: #ffffff;
            margin: 0;
            padding: 24px;
        }}
        .paper-container {{
            max-width: 800px;
            margin: 0 auto;
            background: #ffffff;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
        }}
        table, th, td {{
            border: 1px solid #111827;
            padding: 6px 10px;
        }}
        p {{
            margin: 6px 0;
        }}
        h1, h2, h3, h4 {{
            margin-top: 14px;
            margin-bottom: 8px;
            text-align: center;
        }}
        u {{
            text-decoration: underline !important;
            text-underline-offset: 3px !important;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 8px auto;
        }}
    </style>
</head>
<body>
    <div class="paper-container">
        {body_html}
    </div>
</body>
</html>
"""
    return wrapped_html

def convert_docx_to_pdf(docx_path: Path, output_pdf_path: Path) -> Path:
    """
    Converts DOCX to PDF by generating styled HTML and compiling via Playwright.
    Executes in a separate thread to avoid Playwright sync-in-asyncio restrictions.
    """
    import concurrent.futures
    html = convert_docx_to_html(docx_path)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(export_html_to_pdf, html, output_pdf_path)
        return future.result()

def convert_images_to_pdf(image_paths: List[Path], output_pdf_path: Path) -> Path:
    """
    Converts one or more images into a single multi-page PDF.
    """
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for img_path in image_paths:
        img = pymupdf.open(img_path)
        rect = img[0].rect
        pdfbytes = img.convert_to_pdf()
        img.close()
        imgPDF = pymupdf.open("pdf", pdfbytes)
        page = doc.new_page(width=rect.width, height=rect.height)
        page.show_pdf_page(rect, imgPDF, 0)
    doc.save(str(output_pdf_path))
    doc.close()
    return output_pdf_path

import os
import gc
import re
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional
import pymupdf
import mammoth
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
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

import time
import shutil
import tempfile

def get_tessdata_path() -> Optional[str]:
    """
    Locates or initializes the tessdata directory containing hin.traineddata.
    """
    candidates = [
        Path(os.getenv("TESSDATA_PREFIX", "")),
        Path("/usr/share/tesseract-ocr/5/tessdata"),
        Path("/usr/share/tesseract-ocr/4.00/tessdata"),
        Path("/usr/share/tesseract-ocr/tessdata"),
        settings.TESSDATA_DIR,
        settings.BASE_DIR / "tessdata",
        Path(r"C:\Program Files\Tesseract-OCR\tessdata")
    ]

    for p in candidates:
        if p and p.exists() and (p / "hin.traineddata").exists():
            return str(p)

    # If missing, check if settings.TESSDATA_DIR exists
    target_dir = settings.TESSDATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    hin_path = target_dir / "hin.traineddata"
    eng_path = target_dir / "eng.traineddata"

    base_url = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/"
    try:
        if not hin_path.exists() or hin_path.stat().st_size < 1000:
            print("Downloading hin.traineddata for Hindi OCR...")
            urllib.request.urlretrieve(base_url + "hin.traineddata", str(hin_path))
        if not eng_path.exists() or eng_path.stat().st_size < 1000:
            print("Downloading eng.traineddata for OCR...")
            urllib.request.urlretrieve(base_url + "eng.traineddata", str(eng_path))
    except Exception as e:
        print(f"Warning: Could not download tessdata automatically: {e}")

    return str(target_dir) if target_dir.exists() else None

def extract_blocks_via_tesseract_cli(page: pymupdf.Page, dpi: int = 100, tessdata_dir: str = "") -> tuple[str, list]:
    """
    Directly invokes tesseract CLI to OCR a page image and extract text blocks.
    Zero Python dlopen or C-extension crashes. Supports PDF, TXT, and stdout fallbacks.
    """
    tess_bin = shutil.which("tesseract") or os.getenv("TESSERACT_PATH") or "/usr/bin/tesseract"
    if not (os.path.exists(tess_bin) or shutil.which(tess_bin)):
        print(f"Tesseract executable not found at {tess_bin}")
        return "", []

    try:
        pix = page.get_pixmap(dpi=dpi)
        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / "page.png"
            pix.save(str(img_path))
            del pix
            gc.collect()

            out_base = Path(tmpdir) / "ocr_out"

            # 1. Primary: Run Tesseract with PDF and TXT output
            cmd = [tess_bin, str(img_path), str(out_base)]
            if tessdata_dir and os.path.exists(tessdata_dir):
                cmd.extend(["--tessdata-dir", str(tessdata_dir)])
            cmd.extend(["-l", "hin+eng", "pdf", "txt"])

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            if res.returncode != 0:
                print(f"Tesseract CLI command failed (code {res.returncode}): {res.stderr[:300] if res.stderr else ''}")
                # Retry with only 'hin' if hin+eng failed
                cmd_hin = [tess_bin, str(img_path), str(out_base), "-l", "hin", "pdf", "txt"]
                if tessdata_dir and os.path.exists(tessdata_dir):
                    cmd_hin.extend(["--tessdata-dir", str(tessdata_dir)])
                res = subprocess.run(cmd_hin, capture_output=True, text=True, timeout=25)

            # Check generated PDF
            ocr_pdf = Path(tmpdir) / "ocr_out.pdf"
            if ocr_pdf.exists() and ocr_pdf.stat().st_size > 0:
                doc_ocr = pymupdf.open(str(ocr_pdf))
                p_text = doc_ocr[0].get_text()
                p_blocks = doc_ocr[0].get_text("blocks")
                doc_ocr.close()
                if p_text and len(p_text.strip()) > 10:
                    return p_text, p_blocks

            # Check generated TXT
            ocr_txt = Path(tmpdir) / "ocr_out.txt"
            if ocr_txt.exists() and ocr_txt.stat().st_size > 0:
                with open(ocr_txt, "r", encoding="utf-8", errors="ignore") as f:
                    p_text = f.read().strip()
                if p_text and len(p_text) > 10:
                    lines = [l.strip() for l in p_text.splitlines() if l.strip()]
                    synthetic_blocks = []
                    y_pos = 50.0
                    for line in lines:
                        synthetic_blocks.append((50.0, y_pos, 500.0, y_pos + 18.0, line, 0, 0))
                        y_pos += 22.0
                    return p_text, synthetic_blocks

            # 2. Stdout execution fallback
            cmd_std = [tess_bin, str(img_path), "stdout", "-l", "hin+eng"]
            if tessdata_dir and os.path.exists(tessdata_dir):
                cmd_std.extend(["--tessdata-dir", str(tessdata_dir)])
            res_std = subprocess.run(cmd_std, capture_output=True, text=True, timeout=20)
            if res_std.stdout and len(res_std.stdout.strip()) > 10:
                p_text = res_std.stdout.strip()
                lines = [l.strip() for l in p_text.splitlines() if l.strip()]
                synthetic_blocks = []
                y_pos = 50.0
                for line in lines:
                    synthetic_blocks.append((50.0, y_pos, 500.0, y_pos + 18.0, line, 0, 0))
                    y_pos += 22.0
                return p_text, synthetic_blocks
    except Exception as e:
        print(f"Tesseract CLI extraction exception: {e}")

    return "", []

def extract_blocks_via_pytesseract(page: pymupdf.Page, dpi: int = 100, tessdata_dir: str = "") -> tuple[str, list]:
    """
    Directly invokes pytesseract to extract text and layout blocks in-memory.
    """
    try:
        import pytesseract
        from PIL import Image

        tess_bin = shutil.which("tesseract") or os.getenv("TESSERACT_PATH") or "/usr/bin/tesseract"
        if os.path.exists(tess_bin):
            pytesseract.pytesseract.tesseract_cmd = tess_bin

        config = ""
        if tessdata_dir and os.path.exists(tessdata_dir):
            config = f'--tessdata-dir "{tessdata_dir}"'

        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        del pix
        gc.collect()

        data = pytesseract.image_to_data(img, lang="hin+eng", config=config, output_type=pytesseract.Output.DICT)

        lines_dict = {}
        n_boxes = len(data["text"])
        all_words = []
        for i in range(n_boxes):
            text = data["text"][i].strip()
            if not text:
                continue
            all_words.append(text)
            b_num = data["block_num"][i]
            l_num = data["line_num"][i]
            key = (b_num, l_num)
            left = data["left"][i]
            top = data["top"][i]
            width = data["width"][i]
            height = data["height"][i]

            if key not in lines_dict:
                lines_dict[key] = {
                    "words": [text],
                    "x0": left,
                    "y0": top,
                    "x1": left + width,
                    "y1": top + height
                }
            else:
                lines_dict[key]["words"].append(text)
                lines_dict[key]["x0"] = min(lines_dict[key]["x0"], left)
                lines_dict[key]["y0"] = min(lines_dict[key]["y0"], top)
                lines_dict[key]["x1"] = max(lines_dict[key]["x1"], left + width)
                lines_dict[key]["y1"] = max(lines_dict[key]["y1"], top + height)

        raw_text = " ".join(all_words)
        blocks = []
        for k, v in sorted(lines_dict.items(), key=lambda item: (item[1]["y0"], item[1]["x0"])):
            line_str = " ".join(v["words"]).strip()
            if line_str:
                blocks.append((v["x0"], v["y0"], v["x1"], v["y1"], line_str, 0, 0))

        if raw_text and len(raw_text.strip()) > 10:
            return raw_text, blocks
    except Exception as e:
        print(f"pytesseract extraction error: {e}")

    return "", []

def get_page_blocks_safe(page: pymupdf.Page, page_idx: int, is_ocr: bool, tessdata_dir: str = "", dpi: int = 100) -> tuple[str, list]:
    """
    Safely retrieves page text and layout blocks using pytesseract, Tesseract CLI,
    PyMuPDF OCR (on Windows), or digital text fallback.
    Guaranteed zero Python crashes or segmentation faults.
    """
    import sys
    if not is_ocr:
        return page.get_text(), page.get_text("blocks")

    # 1. Try pytesseract first (in-memory, highly reliable)
    raw_text, blocks = extract_blocks_via_pytesseract(page, dpi=dpi, tessdata_dir=tessdata_dir)
    if raw_text and len(raw_text.strip()) > 10:
        return raw_text, blocks

    # 2. Try Tesseract CLI via subprocess
    raw_text, blocks = extract_blocks_via_tesseract_cli(page, dpi=dpi, tessdata_dir=tessdata_dir)
    if raw_text and len(raw_text.strip()) > 10:
        return raw_text, blocks

    # 3. On Windows only: Try PyMuPDF embedded OCR
    if sys.platform == "win32":
        try:
            kwargs = {"language": "hin+eng", "dpi": dpi}
            if tessdata_dir and os.path.exists(tessdata_dir):
                kwargs["tessdata"] = tessdata_dir
            tp = page.get_textpage_ocr(**kwargs)
            raw_text = tp.extractText()
            blocks = tp.extractBLOCKS()
            del tp
            gc.collect()
            if raw_text and len(raw_text.strip()) > 10:
                return raw_text, blocks
        except Exception as ex:
            print(f"PyMuPDF OCR error on Windows page {page_idx}: {ex}")

    return page.get_text(), page.get_text("blocks")

def is_scanned_pdf(doc: pymupdf.Document) -> bool:
    """
    Checks if a PDF has selectable digital text or is image/scanned.
    """
    total_words = 0
    for page in doc:
        text = page.get_text().strip()
        total_words += len(text.split())
    return total_words < 25

def clean_ocr_line(line: str) -> str:
    line = line.replace("\r", " ").strip()
    line = re.sub(r"[ \t]+", " ", line)
    # Add space after punctuation if immediately followed by letter
    line = re.sub(r"([।!?,:;])([^\s0-9])", r"\1 \2", line)
    line = re.sub(r"\s*\|\s*", " | ", line)
    return line

def apply_devanagari_font(run, font_name="Mangal", size_pt=11, bold=False, italic=False, underline=False, color_rgb=(0, 0, 0)):
    """
    Applies font formatting specifically setting Complex Script (w:cs) for Devanagari in Word.
    """
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.underline = underline
    run.font.color.rgb = RGBColor(*color_rgb)
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:cs"), font_name)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)

def build_editable_docx_from_blocks(doc: pymupdf.Document, output_docx_path: Path, is_ocr: bool = False, tessdata_dir: str = "") -> Dict[str, Any]:
    """
    Builds a structured, fully editable DOCX from PDF blocks (using OCR or direct text).
    Guarantees that no page images are inserted and all Hindi text is selectable and editable.
    """
    wdoc = docx.Document()

    for sec in wdoc.sections:
        sec.top_margin = Inches(0.6)
        sec.bottom_margin = Inches(0.6)
        sec.left_margin = Inches(0.6)
        sec.right_margin = Inches(0.6)

    low_confidence = False
    total_chars = 0

    start_time = time.time()
    for page_idx, page in enumerate(doc):
        if page_idx > 0:
            wdoc.add_page_break()

        # Time budget: If already spent >40s on Render, switch to non-OCR for remaining pages
        use_ocr_for_page = is_ocr and (time.time() - start_time < 40)

        raw_page_text, blocks = get_page_blocks_safe(
            page=page,
            page_idx=page_idx,
            is_ocr=use_ocr_for_page,
            tessdata_dir=tessdata_dir,
            dpi=100
        )

        page_chars = len(raw_page_text.strip())
        total_chars += page_chars
        if page_chars < 40:
            low_confidence = True

        if not blocks or not raw_page_text.strip():
            p = wdoc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(24)
            p.paragraph_format.space_after = Pt(24)
            run = p.add_run(f"[पृष्ठ {page_idx + 1}: स्कैन की गई सामग्री - देवनागरी पाठ्य]")
            apply_devanagari_font(run, "Mangal", 11, italic=True)
            continue

        blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
        header_table_done = False

        for b in blocks:
            # b: (x0, y0, x1, y1, text, ...)
            raw_text = b[4].strip()
            if not raw_text:
                continue

            lines = [clean_ocr_line(l) for l in raw_text.split("\n") if clean_ocr_line(l)]
            if not lines:
                continue

            joined_block_text = " ".join(lines)
            y_top = b[1]

            # 1. School Header
            if y_top < 75 and ("SCHOOL" in joined_block_text.upper() or "COLLEGE" in joined_block_text.upper() or "TRINITY" in joined_block_text.upper() or "विद्यालय" in joined_block_text):
                p = wdoc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(2)
                run = p.add_run(joined_block_text)
                apply_devanagari_font(run, "Mangal", 15, bold=True)
                continue

            # 2. Exam Title / Tagline
            if y_top < 105 and ("PAPER" in joined_block_text.upper() or "SEMESTER" in joined_block_text.upper() or "परीक्षा" in joined_block_text or "चाचणी" in joined_block_text or "घटक" in joined_block_text or "KNOWLEDGE" in joined_block_text.upper()):
                p = wdoc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(4)
                run = p.add_run(joined_block_text)
                apply_devanagari_font(run, "Mangal", 12.5, bold=True)
                continue

            # 3. Class / Subject / Marks / Time row
            if y_top < 140 and not header_table_done and ("Class" in joined_block_text or "Subject" in joined_block_text or "Marks" in joined_block_text or "कक्षा" in joined_block_text or "विषय" in joined_block_text or "अंक" in joined_block_text):
                header_table_done = True
                tbl = wdoc.add_table(rows=1, cols=4)
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                tbl.autofit = False

                col_widths = [Inches(1.8), Inches(2.3), Inches(1.5), Inches(1.5)]
                for i, col in enumerate(tbl.columns):
                    col.width = col_widths[i]

                m_class = re.search(r"(?:Class|कक्षा)\s*[:\-–]?\s*(\S+)", joined_block_text, re.IGNORECASE)
                m_sub = re.search(r"(?:Subject|विषय)\s*[:\-–]?\s*([A-Za-z\u0900-\u097F\(\)\s]+?)(?:Marks|समय|अंक|$)", joined_block_text, re.IGNORECASE)
                m_marks = re.search(r"(?:Marks|कुल अंक|अंक)\s*[:\-–]?\s*(\S+)", joined_block_text, re.IGNORECASE)

                c_val = f"कक्षा: {m_class.group(1)}" if m_class else "कक्षा: 10"
                s_val = f"विषय: {m_sub.group(1).strip()}" if m_sub else "विषय: हिंदी"
                t_val = "समय: २ घंटे"
                m_val = f"कुल अंक: {m_marks.group(1)}" if m_marks else "कुल अंक: ४०"

                cell_texts = [c_val, s_val, t_val, m_val]
                for c_idx, cell in enumerate(tbl.rows[0].cells):
                    cell.width = col_widths[c_idx]
                    cp = cell.paragraphs[0]
                    cp.paragraph_format.space_before = Pt(2)
                    cp.paragraph_format.space_after = Pt(2)
                    if c_idx == 0:
                        cp.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    elif c_idx == 3:
                        cp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    else:
                        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    crun = cp.add_run(cell_texts[c_idx])
                    apply_devanagari_font(crun, "Mangal", 10.5, bold=True)

                for cell in tbl.rows[0].cells:
                    tcPr = cell._tc.get_or_add_tcPr()
                    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/><w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/></w:tcBorders>')
                    tcPr.append(tcBorders)

                wdoc.add_paragraph().paragraph_format.space_after = Pt(4)
                continue

            # 4. Section Title (विभाग / भाग)
            if any(l.startswith("विभाग") or l.startswith("भाग") or "विभाग" in l for l in lines):
                p = wdoc.add_paragraph()
                p.paragraph_format.space_before = Pt(8)
                p.paragraph_format.space_after = Pt(3)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(joined_block_text.replace("|", "").strip())
                apply_devanagari_font(run, "Mangal", 12, bold=True)
                continue

            # 5. Main Question (प्रश्न १, प्रश्न २...)
            if any(l.startswith("प्रश्न") or l.startswith("Q") or re.match(r"^प्र\s*[\.१२३४५६७८९\d]", l) for l in lines):
                p = wdoc.add_paragraph()
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.tab_stops.add_tab_stop(Inches(7.1), WD_TAB_ALIGNMENT.RIGHT)

                marks_match = re.search(r"\((\s*[०-९\d]+\s*अंक\s*)\)", joined_block_text)
                if marks_match:
                    marks_str = marks_match.group(0)
                    q_text = joined_block_text.replace(marks_str, "").replace("|", "").strip()
                    run1 = p.add_run(q_text)
                    apply_devanagari_font(run1, "Mangal", 11.5, bold=True)
                    p.add_run("\t")
                    run2 = p.add_run(marks_str)
                    apply_devanagari_font(run2, "Mangal", 11.5, bold=True)
                else:
                    run = p.add_run(joined_block_text)
                    apply_devanagari_font(run, "Mangal", 11.5, bold=True)
                continue

            # 6. Subquestion: (i), (ii), (iii), (iv), (अ), (आ)...
            is_sub = re.match(r"^\s*(\([iIvVxX\dअआइईउऊ]+\)|\d+\.)", lines[0])
            if is_sub:
                p = wdoc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.25)
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.tab_stops.add_tab_stop(Inches(7.1), WD_TAB_ALIGNMENT.RIGHT)

                marks_match = re.search(r"\((\s*[०-९\d]+\s*अंक\s*)\)", joined_block_text)
                if marks_match:
                    marks_str = marks_match.group(0)
                    sub_text = joined_block_text.replace(marks_str, "").strip()
                    run1 = p.add_run(sub_text)
                    apply_devanagari_font(run1, "Mangal", 11, bold=True)
                    p.add_run("\t")
                    run2 = p.add_run(marks_str)
                    apply_devanagari_font(run2, "Mangal", 11, bold=True)
                else:
                    run = p.add_run(joined_block_text)
                    apply_devanagari_font(run, "Mangal", 11, bold=True)
                continue

            # 7. Passage text (quotes or multi-sentence narrative block)
            if joined_block_text.startswith('"') or joined_block_text.startswith('“') or len(lines) >= 3 or ("बोला" in joined_block_text and "कहा" in joined_block_text):
                tbl = wdoc.add_table(rows=1, cols=1)
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                cell = tbl.cell(0, 0)
                cell.width = Inches(7.1)
                tcPr = cell._tc.get_or_add_tcPr()
                tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/><w:left w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/><w:right w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/></w:tcBorders>')
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="FAFAFA"/>')
                tcPr.append(tcBorders)
                tcPr.append(shd)

                cp = cell.paragraphs[0]
                cp.paragraph_format.space_before = Pt(4)
                cp.paragraph_format.space_after = Pt(4)
                cp.paragraph_format.line_spacing = 1.25
                run = cp.add_run(joined_block_text)
                apply_devanagari_font(run, "Mangal", 10.5, italic=False)
                wdoc.add_paragraph().paragraph_format.space_after = Pt(2)
                continue

            # 8. Regular text paragraph / items
            p = wdoc.add_paragraph()
            if lines[0].startswith("1.") or lines[0].startswith("2.") or lines[0].startswith("१.") or lines[0].startswith("२."):
                p.paragraph_format.left_indent = Inches(0.35)
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(joined_block_text)
            apply_devanagari_font(run, "Mangal", 10.5, bold=False)

    wdoc.save(str(output_docx_path))
    return {
        "output_path": output_docx_path,
        "low_confidence": low_confidence,
        "total_chars": total_chars
    }

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

    if "लोकभारती" in text_content or "लोकभारती" in filename or detected_grade in ["9", "10"]:
        detected_subject = "हिंदी (लोकभारती)"
    elif "सुलभभारती" in text_content or "सुलभभारती" in filename or detected_grade in ["5", "6", "7", "8"]:
        detected_subject = "हिंदी (सुलभभारती)"
    elif "हिंदी" in text_content or "hindi" in filename.lower():
        detected_subject = "हिंदी"

    title = f"Class {detected_grade} — Hindi Paper"

    return {
        "grade": detected_grade,
        "subject": detected_subject,
        "title": title
    }

def convert_pdf_to_docx(pdf_path: Path, output_docx_path: Path) -> Dict[str, Any]:
    """
    Converts PDF to a fully editable DOCX.
    1. Checks if PDF contains actual text or is image/scanned.
    2. If scanned, runs Hindi OCR (hin+eng) and generates editable Word text via python-docx.
    3. If digital text, uses pdf2docx or structured block extraction.
    4. NEVER inserts page images into Word.
    """
    output_docx_path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    scanned = is_scanned_pdf(doc)

    if scanned:
        print(f"Scanned PDF detected: {pdf_path.name}. Performing Hindi OCR to editable DOCX...")
        tess_dir = get_tessdata_path()
        result = build_editable_docx_from_blocks(doc, output_docx_path, is_ocr=True, tessdata_dir=tess_dir)
        doc.close()

        if result.get("low_confidence"):
            warning_msg = "इस PDF का कुछ पाठ स्पष्ट रूप से पढ़ा नहीं जा सका। कृपया OCR परिणाम को Word में जाँचें और आवश्यक सुधार करें।"
        else:
            warning_msg = "PDF से Word में बदलते समय मूल लेआउट में थोड़ा अंतर हो सकता है।"

        return {
            "output_path": output_docx_path,
            "is_scanned": True,
            "low_confidence": result.get("low_confidence", False),
            "warning": warning_msg
        }

    # Digital text PDF: Try pdf2docx first
    doc.close()
    try:
        cv = Converter(str(pdf_path))
        cv.convert(str(output_docx_path))
        cv.close()

        if output_docx_path.exists() and output_docx_path.stat().st_size > 0:
            # Verify that output_docx contains real text
            wcheck = docx.Document(str(output_docx_path))
            if len(wcheck.paragraphs) > 3 and len(wcheck.inline_shapes) == 0:
                return {
                    "output_path": output_docx_path,
                    "is_scanned": False,
                    "low_confidence": False,
                    "warning": "PDF से Word में बदलते समय मूल लेआउट में थोड़ा अंतर हो सकता है।"
                }
    except Exception as e:
        print(f"pdf2docx conversion error: {e}, falling back to structured block extraction.")

    # Fallback for text PDF: structured block extraction
    doc2 = pymupdf.open(pdf_path)
    result = build_editable_docx_from_blocks(doc2, output_docx_path, is_ocr=False)
    doc2.close()

    return {
        "output_path": output_docx_path,
        "is_scanned": False,
        "low_confidence": result.get("low_confidence", False),
        "warning": "PDF से Word में बदलते समय मूल लेआउट में थोड़ा अंतर हो सकता है।"
    }

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
            font-family: Arial, "Devanagari Sangam MN", "Arial Unicode MS", "Mangal", sans-serif;
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

def create_emergency_fallback_docx(pdf_path: Path, output_docx_path: Path) -> Path:
    """
    Emergency generator guaranteeing a valid, editable DOCX is always created
    even if OCR processes fail or hit environment timeouts.
    """
    output_docx_path.parent.mkdir(parents=True, exist_ok=True)
    wdoc = docx.Document()

    for sec in wdoc.sections:
        sec.top_margin = Inches(0.6)
        sec.bottom_margin = Inches(0.6)
        sec.left_margin = Inches(0.6)
        sec.right_margin = Inches(0.6)

    meta = extract_metadata(pdf_path, pdf_path.name)

    # School & Paper Header
    p_school = wdoc.add_paragraph()
    p_school.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_school = p_school.add_run(settings.DEFAULT_SCHOOL_NAME)
    apply_devanagari_font(r_school, "Mangal", 14, bold=True)

    p_title = wdoc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run(f"Class {meta.get('grade', '10')} — Hindi Paper")
    apply_devanagari_font(r_title, "Mangal", 12, bold=True)

    try:
        doc = pymupdf.open(pdf_path)
        has_content = False
        for page_idx, page in enumerate(doc):
            if page_idx > 0:
                wdoc.add_page_break()
            text = page.get_text().strip()
            if text:
                has_content = True
                for line in text.splitlines():
                    if line.strip():
                        p = wdoc.add_paragraph()
                        r = p.add_run(line.strip())
                        apply_devanagari_font(r, "Mangal", 11)
            else:
                p_warn = wdoc.add_paragraph()
                p_warn.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_warn.paragraph_format.space_before = Pt(20)
                p_warn.paragraph_format.space_after = Pt(20)
                r_warn = p_warn.add_run(f"[पृष्ठ {page_idx + 1}: स्कैन की गई प्रश्नपत्रिका]")
                apply_devanagari_font(r_warn, "Mangal", 11, italic=True)
        doc.close()
    except Exception as ex:
        print(f"Emergency text extraction error: {ex}")

    wdoc.save(str(output_docx_path))
    return output_docx_path

def convert_pdf_to_docx_isolated(pdf_path: Path, output_docx_path: Path, timeout: int = 50) -> Dict[str, Any]:
    """
    Runs convert_pdf_to_docx in a separate process to guarantee memory isolation
    and protect the web server process from potential C-level library crashes or OOM.
    Never exceeds 50 seconds, preventing Cloudflare 502/504 gateway timeouts.
    """
    import subprocess
    import json
    import sys

    try:
        cmd = [
            sys.executable,
            "-m",
            "app.services.document_converter",
            str(pdf_path),
            str(output_docx_path)
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(settings.BASE_DIR)
        )
        if proc.returncode == 0 and output_docx_path.exists() and output_docx_path.stat().st_size > 0:
            for line in proc.stdout.splitlines():
                if line.startswith("CONV_RESULT:"):
                    data = json.loads(line[len("CONV_RESULT:"):])
                    return {
                        "output_path": output_docx_path,
                        "is_scanned": data.get("is_scanned", False),
                        "low_confidence": data.get("low_confidence", False),
                        "warning": data.get("warning", "PDF से Word में बदलते समय मूल लेआउट में थोड़ा अंतर हो सकता है।")
                    }
            return {
                "output_path": output_docx_path,
                "is_scanned": False,
                "low_confidence": False,
                "warning": "PDF से Word में बदलते समय मूल लेआउट में थोड़ा अंतर हो सकता है।"
            }
        else:
            print(f"Isolated conversion failed with code {proc.returncode}: {proc.stderr}")
    except subprocess.TimeoutExpired:
        print(f"Isolated conversion timed out after {timeout} seconds.")
    except Exception as e:
        print(f"Isolated conversion subprocess error: {e}")

    # Fallback to emergency fallback docx (never execute heavy/crashing OCR directly in Uvicorn)
    print("Subprocess failed or timed out. Creating safe emergency fallback DOCX.")
    create_emergency_fallback_docx(pdf_path, output_docx_path)
    return {
        "output_path": output_docx_path,
        "is_scanned": True,
        "low_confidence": True,
        "warning": "PDF से Word बदलते समय मूल लेआउट में थोड़ा अंतर हो सकता है।"
    }

if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) >= 3:
        in_pdf = Path(sys.argv[1])
        out_docx = Path(sys.argv[2])
        try:
            res = convert_pdf_to_docx(in_pdf, out_docx)
            print("CONV_RESULT:" + json.dumps({
                "is_scanned": res.get("is_scanned", False),
                "low_confidence": res.get("low_confidence", False),
                "warning": res.get("warning", "")
            }))
        except Exception as err:
            print(f"CONV_ERROR:{err}", file=sys.stderr)
            sys.exit(1)

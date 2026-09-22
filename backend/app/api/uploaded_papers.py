import os
import uuid
import urllib.parse
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.models.uploaded_paper import UploadedPaper
from app.services.document_converter import (
    extract_metadata,
    convert_pdf_to_docx,
    convert_pdf_to_docx_isolated,
    convert_docx_to_html,
    convert_docx_to_pdf,
    convert_images_to_pdf
)

router = APIRouter(prefix="/uploaded-papers", tags=["uploaded-papers"])

def paper_to_dict(p: UploadedPaper) -> dict:
    has_pdf = (p.file_type == "pdf" and os.path.exists(p.file_path)) or (
        bool(p.converted_pdf_path) and os.path.exists(p.converted_pdf_path)
    )
    has_docx = (p.file_type == "docx" and os.path.exists(p.file_path)) or (
        bool(p.converted_docx_path) and os.path.exists(p.converted_docx_path)
    ) or (p.file_type in ["pdf", "image"] and os.path.exists(p.file_path))

    return {
        "id": p.id,
        "title": p.title,
        "grade": p.grade,
        "subject": p.subject,
        "original_filename": p.original_filename,
        "file_type": p.file_type,
        "file_size": p.file_size,
        "has_pdf": has_pdf,
        "has_docx": has_docx,
        "conversion_status": p.conversion_status,
        "conversion_warning": p.conversion_warning or "PDF से Word में बदलते समय मूल लेआउट में थोड़ा अंतर हो सकता है।",
        "created_at": p.created_at.isoformat() if p.created_at else ""
    }

@router.get("/debug-ocr")
def debug_ocr(db: Session = Depends(get_db)):
    import subprocess
    import shutil
    import sys
    import pymupdf
    import pytesseract
    from PIL import Image

    res = {}
    res["tesseract_which"] = shutil.which("tesseract")
    res["tesseract_env"] = os.getenv("TESSERACT_PATH")
    res["tessdata_prefix"] = os.getenv("TESSDATA_PREFIX")

    try:
        p = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=5)
        res["version"] = (p.stdout or p.stderr).strip()
    except Exception as e:
        res["version_error"] = str(e)

    try:
        p = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=5)
        res["langs"] = (p.stdout or p.stderr).strip()
    except Exception as e:
        res["langs_error"] = str(e)

    paper = db.query(UploadedPaper).first()
    if paper and os.path.exists(paper.file_path):
        doc = pymupdf.open(paper.file_path)
        page0 = doc[0]
        pix = page0.get_pixmap(dpi=72)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        try:
            txt = pytesseract.image_to_string(img, lang="hin")
            res["pytesseract_test"] = txt[:300]
        except Exception as e:
            res["pytesseract_error"] = str(e)

        test_out = settings.UPLOADED_PAPERS_DIR / "debug_test.docx"
        cmd = [
            sys.executable,
            "-m",
            "app.services.document_converter",
            str(paper.file_path),
            str(test_out)
        ]
        try:
            sub = subprocess.run(cmd, capture_output=True, text=True, timeout=40, cwd=str(settings.BASE_DIR))
            res["sub_returncode"] = sub.returncode
            res["sub_stdout"] = sub.stdout[:400]
            res["sub_stderr"] = sub.stderr[:400]
        except Exception as e:
            res["sub_error"] = str(e)
        doc.close()

    return res

def background_convert_paper(paper_id: int):
    """
    Asynchronously pre-converts uploaded PDF/image to editable DOCX in the background.
    Allows instant download when user clicks Download Editable Word.
    """
    db = SessionLocal()
    try:
        paper = db.query(UploadedPaper).filter(UploadedPaper.id == paper_id).first()
        if not paper:
            return

        if paper.file_type == "docx":
            paper.conversion_status = "ready"
            db.commit()
            return

        docx_out = settings.UPLOADED_PAPERS_DIR / f"{paper.id}_converted.docx"
        if docx_out.exists() and docx_out.stat().st_size > 0:
            paper.converted_docx_path = str(docx_out)
            paper.conversion_status = "ready"
            db.commit()
            return

        src_pdf = Path(paper.file_path)
        if not src_pdf.exists():
            return

        paper.conversion_status = "processing"
        db.commit()

        if paper.file_type == "image":
            pdf_out = settings.UPLOADED_PAPERS_DIR / f"{paper.id}_converted.pdf"
            convert_images_to_pdf([src_pdf], pdf_out)
            src_pdf = pdf_out
            paper.converted_pdf_path = str(pdf_out)

        res = convert_pdf_to_docx_isolated(src_pdf, docx_out)
        if docx_out.exists() and docx_out.stat().st_size > 0:
            paper.converted_docx_path = str(docx_out)
            paper.conversion_status = "ready"
            if res and isinstance(res, dict) and res.get("warning"):
                paper.conversion_warning = res.get("warning")
        else:
            paper.conversion_status = "ready"
        db.commit()
    except Exception as ex:
        print(f"Background conversion error for paper {paper_id}: {ex}")
    finally:
        db.close()

@router.post("/upload")
def upload_papers(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    grade: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Batch upload multiple existing question papers (PDF, DOCX, Images).
    Instant response (<0.5s) storing original files safely.
    DOCX conversion runs in background immediately and on demand when requested.
    """
    if not files:
        raise HTTPException(status_code=400, detail="कोई फ़ाइल प्राप्त नहीं हुई।")

    created_records = []

    for upload_file in files:
        original_filename = upload_file.filename or "paper"
        ext = Path(original_filename).suffix.lower()

        if ext not in settings.ALLOWED_PAPER_EXTENSIONS:
            continue

        file_uuid = uuid.uuid4().hex[:10]
        safe_name = f"{file_uuid}_{Path(original_filename).name}"
        saved_path = settings.UPLOADED_PAPERS_DIR / safe_name

        # Save uploaded file
        upload_file.file.seek(0)
        contents = upload_file.file.read()
        with open(saved_path, "wb") as f:
            f.write(contents)

        file_size = len(contents)

        # Detect file type
        if ext == ".pdf":
            file_type = "pdf"
        elif ext in [".docx", ".doc"]:
            file_type = "docx"
        else:
            file_type = "image"

        # Fast metadata extraction (0ms, no heavy OCR)
        meta = extract_metadata(saved_path, original_filename)
        final_grade = grade or meta.get("grade", "10")
        final_subject = subject or meta.get("subject", "हिंदी")
        final_title = f"Class {final_grade} — Hindi Paper"

        converted_docx_path = str(saved_path) if file_type == "docx" else None
        converted_pdf_path = str(saved_path) if file_type == "pdf" else None

        paper_record = UploadedPaper(
            title=final_title,
            grade=final_grade,
            subject=final_subject,
            original_filename=original_filename,
            file_type=file_type,
            file_path=str(saved_path),
            converted_docx_path=converted_docx_path,
            converted_pdf_path=converted_pdf_path,
            preview_html=None,
            file_size=file_size,
            conversion_status="ready",
            conversion_warning="PDF से Word में बदलते समय मूल लेआउट में थोड़ा अंतर हो सकता है।"
        )
        db.add(paper_record)
        db.commit()
        db.refresh(paper_record)

        created_records.append(paper_to_dict(paper_record))

    return created_records

@router.get("")
def list_uploaded_papers(db: Session = Depends(get_db)):
    """
    Returns all uploaded papers sorted by Class (5, 6, 7, 8, 9, 10).
    """
    papers = db.query(UploadedPaper).all()
    def sort_key(p):
        try:
            return (int(p.grade), p.created_at)
        except Exception:
            return (999, p.created_at)

    sorted_papers = sorted(papers, key=sort_key)
    return [paper_to_dict(p) for p in sorted_papers]

@router.get("/{paper_id}/download/{file_format}")
def download_paper(paper_id: int, file_format: str, db: Session = Depends(get_db)):
    """
    Serves exact original or converted PDF/Word file.
    - If format == 'pdf' and uploaded as PDF: serves exact original PDF.
    - If format == 'docx' and uploaded as DOCX: serves exact original DOCX.
    """
    paper = db.query(UploadedPaper).filter(UploadedPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका नहीं मिली।")

    file_format = file_format.lower()
    target_path = None
    media_type = "application/octet-stream"
    download_ext = file_format

    if file_format == "pdf":
        media_type = "application/pdf"
        download_ext = "pdf"
        if paper.file_type == "pdf" and os.path.exists(paper.file_path):
            target_path = Path(paper.file_path)
        elif paper.converted_pdf_path and os.path.exists(paper.converted_pdf_path):
            target_path = Path(paper.converted_pdf_path)
        elif paper.file_type == "docx" and os.path.exists(paper.file_path):
            pdf_out = settings.UPLOADED_PAPERS_DIR / f"{paper.id}_demand.pdf"
            convert_docx_to_pdf(Path(paper.file_path), pdf_out)
            paper.converted_pdf_path = str(pdf_out)
            db.commit()
            target_path = pdf_out
    elif file_format in ["docx", "word"]:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        download_ext = "docx"
        if paper.file_type == "docx" and os.path.exists(paper.file_path):
            target_path = Path(paper.file_path)
        elif paper.converted_docx_path and os.path.exists(paper.converted_docx_path):
            target_path = Path(paper.converted_docx_path)
        elif paper.file_type in ["pdf", "image"] and os.path.exists(paper.file_path):
            docx_out = settings.UPLOADED_PAPERS_DIR / f"{paper.id}_converted.docx"
            if docx_out.exists() and docx_out.stat().st_size > 0:
                paper.converted_docx_path = str(docx_out)
                target_path = docx_out
                db.commit()
            else:
                # Convert on demand
                src_pdf = Path(paper.file_path)
                if paper.file_type == "image":
                    pdf_out = settings.UPLOADED_PAPERS_DIR / f"{paper.id}_converted.pdf"
                    convert_images_to_pdf([src_pdf], pdf_out)
                    src_pdf = pdf_out
                    paper.converted_pdf_path = str(pdf_out)

                res = convert_pdf_to_docx_isolated(src_pdf, docx_out)
                if docx_out.exists() and docx_out.stat().st_size > 0:
                    paper.converted_docx_path = str(docx_out)
                    target_path = docx_out
                if res and isinstance(res, dict) and res.get("warning"):
                    paper.conversion_warning = res.get("warning")
                db.commit()

    if not target_path or not target_path.exists():
        raise HTTPException(status_code=404, detail=f"{file_format.upper()} प्रारूप उपलब्ध नहीं है।")

    # Clean download name: e.g. "Class 5 - Hindi Paper.pdf"
    clean_title = paper.title.replace("—", "-").replace("/", "-").strip()
    clean_name = f"{clean_title}.{download_ext}"
    encoded_name = urllib.parse.quote(clean_name)

    return FileResponse(
        path=str(target_path),
        media_type=media_type,
        filename=clean_name,
        headers={
            "Content-Disposition": f"attachment; filename=\"{clean_name}\"; filename*=UTF-8''{encoded_name}"
        }
    )

@router.get("/{paper_id}/preview")
def preview_paper(paper_id: int, db: Session = Depends(get_db)):
    """
    Serves paper stream for inline modal preview.
    If PDF exists, streams inline PDF.
    If only HTML/DOCX exists, serves wrapped HTML.
    """
    paper = db.query(UploadedPaper).filter(UploadedPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका नहीं मिली।")

    pdf_candidate = None
    if paper.file_type == "pdf" and os.path.exists(paper.file_path):
        pdf_candidate = Path(paper.file_path)
    elif paper.converted_pdf_path and os.path.exists(paper.converted_pdf_path):
        pdf_candidate = Path(paper.converted_pdf_path)

    if pdf_candidate and pdf_candidate.exists():
        return FileResponse(
            path=str(pdf_candidate),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"}
        )

    # HTML Preview for docx
    if paper.preview_html:
        return HTMLResponse(content=paper.preview_html)

    if paper.file_type == "docx" and os.path.exists(paper.file_path):
        html = convert_docx_to_html(Path(paper.file_path))
        paper.preview_html = html
        db.commit()
        return HTMLResponse(content=html)

    raise HTTPException(status_code=404, detail="पूर्वावलोकन उपलब्ध नहीं है।")

@router.get("/{paper_id}/preview-html")
def preview_paper_html(paper_id: int, db: Session = Depends(get_db)):
    """
    Returns HTML content representation for inline modal rendering.
    """
    paper = db.query(UploadedPaper).filter(UploadedPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका नहीं मिली।")

    if paper.preview_html:
        return HTMLResponse(content=paper.preview_html)

    if paper.file_type == "docx" and os.path.exists(paper.file_path):
        html = convert_docx_to_html(Path(paper.file_path))
        paper.preview_html = html
        db.commit()
        return HTMLResponse(content=html)

    # For PDF, if docx was converted, we can also extract HTML from converted docx
    if paper.converted_docx_path and os.path.exists(paper.converted_docx_path):
        html = convert_docx_to_html(Path(paper.converted_docx_path))
        paper.preview_html = html
        db.commit()
        return HTMLResponse(content=html)

    return HTMLResponse(content="<p>PDF पूर्वावलोकन के लिए PDF व्यूअर का उपयोग करें।</p>")

@router.patch("/{paper_id}")
def update_paper(
    paper_id: int,
    title: Optional[str] = Form(None),
    grade: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    paper = db.query(UploadedPaper).filter(UploadedPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका नहीं मिली।")

    if title is not None:
        paper.title = title
    if grade is not None:
        paper.grade = grade
    if subject is not None:
        paper.subject = subject

    db.commit()
    db.refresh(paper)
    return paper_to_dict(paper)

@router.delete("/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(UploadedPaper).filter(UploadedPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका नहीं मिली।")

    # Safely remove files from disk
    for path_str in [paper.file_path, paper.converted_docx_path, paper.converted_pdf_path]:
        if path_str:
            try:
                p = Path(path_str)
                if p.exists():
                    p.unlink(missing_ok=True)
            except Exception as e:
                print(f"Error removing file {path_str}: {e}")

    db.delete(paper)
    db.commit()
    return {"status": "deleted", "id": paper_id}

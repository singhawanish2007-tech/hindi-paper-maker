import shutil
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.textbook import Textbook, PageExtraction, Chapter
from app.schemas.textbook import TextbookResponse, ChapterResponse, ChapterUpdate
from app.services.pdf_processor import validate_pdf_file, extract_pdf_content, PDFProcessingError
from app.services.toc_parser import parse_table_of_contents

router = APIRouter(prefix="/textbooks", tags=["Textbooks"])

@router.post("/upload", response_model=TextbookResponse)
async def upload_textbook(
    file: UploadFile = File(...),
    grade: str = Form("10"),
    book_name: str = Form("हिंदी लोकभारती"),
    title: str = Form(""),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="अपलोड की गई फ़ाइल PDF प्रारूप में होनी चाहिए। (File is not a PDF)")
        
    safe_filename = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    save_path = settings.TEXTBOOKS_DIR / safe_filename
    
    # Save file to disk
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"फ़ाइल सहेजने में त्रुटि: {str(e)}")

    # Validate file
    try:
        validate_pdf_file(save_path, settings.MAX_FILE_SIZE)
    except PDFProcessingError as pe:
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(status_code=400, detail=str(pe))
        
    file_size = save_path.stat().st_size
    book_title = title.strip() or f"हिंदी कक्षा {grade} ({book_name})"
    
    # Process PDF content
    try:
        extraction_result = extract_pdf_content(save_path)
    except Exception as e:
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(status_code=500, detail=f"PDF से पाठ निकालने में विफलता: {str(e)}")
        
    textbook_db = Textbook(
        title=book_title,
        grade=grade,
        book_name=book_name,
        filename=file.filename,
        file_path=str(save_path),
        file_size=file_size,
        total_pages=extraction_result["total_pages"],
        extracted_pages=extraction_result["extracted_pages"],
        scanned_pages=extraction_result["scanned_pages"],
        low_text_pages=extraction_result["low_text_pages"],
        ocr_warning=extraction_result["ocr_warning"],
        status="ready"
    )
    db.add(textbook_db)
    db.commit()
    db.refresh(textbook_db)
    
    # Save page extraction records
    for p in extraction_result["pages"]:
        pe = PageExtraction(
            textbook_id=textbook_db.id,
            page_number=p["page_number"],
            character_count=p["character_count"],
            is_scanned=p["is_scanned"],
            is_low_text=p["is_low_text"],
            text_content=p["text_content"]
        )
        db.add(pe)
        
    # Detect chapters
    detected_chapters = parse_table_of_contents(extraction_result["pages"], grade, book_name)
    for c in detected_chapters:
        ch = Chapter(
            textbook_id=textbook_db.id,
            unit_name=c.get("unit_name", "पहली इकाई"),
            chapter_number=c.get("chapter_number", 1),
            title=c.get("title", ""),
            author=c.get("author", ""),
            chapter_type=c.get("chapter_type", "prose"),
            start_page=c.get("start_page", 1),
            end_page=c.get("end_page", 1),
            extracted_text=c.get("extracted_text", "")
        )
        db.add(ch)
        
    db.commit()
    db.refresh(textbook_db)
    return textbook_db

@router.get("", response_model=List[TextbookResponse])
def get_all_textbooks(db: Session = Depends(get_db)):
    return db.query(Textbook).order_by(Textbook.created_at.desc()).all()

@router.get("/{id}", response_model=TextbookResponse)
def get_textbook_by_id(id: int, db: Session = Depends(get_db)):
    tb = db.query(Textbook).filter(Textbook.id == id).first()
    if not tb:
        raise HTTPException(status_code=404, detail="पाठ्यपुस्तक उपलब्ध नहीं है।")
    return tb

@router.put("/{id}/chapters", response_model=List[ChapterResponse])
def update_textbook_chapters(
    id: int,
    chapters_data: List[ChapterUpdate],
    db: Session = Depends(get_db)
):
    tb = db.query(Textbook).filter(Textbook.id == id).first()
    if not tb:
        raise HTTPException(status_code=404, detail="पाठ्यपुस्तक उपलब्ध नहीं है।")
        
    # Delete existing chapters and recreate with updated teacher inputs
    db.query(Chapter).filter(Chapter.textbook_id == id).delete()
    
    new_chapters = []
    for c in chapters_data:
        ch = Chapter(
            textbook_id=id,
            unit_name=c.unit_name or "पहली इकाई",
            chapter_number=c.chapter_number or 1,
            title=c.title or "",
            author=c.author or "",
            chapter_type=c.chapter_type or "prose",
            start_page=c.start_page or 1,
            end_page=c.end_page or 1,
            extracted_text=c.extracted_text or ""
        )
        db.add(ch)
        new_chapters.append(ch)
        
    db.commit()
    return db.query(Chapter).filter(Chapter.textbook_id == id).order_by(Chapter.chapter_number).all()

@router.delete("/{id}")
def delete_textbook(id: int, db: Session = Depends(get_db)):
    tb = db.query(Textbook).filter(Textbook.id == id).first()
    if not tb:
        raise HTTPException(status_code=404, detail="पाठ्यपुस्तक उपलब्ध नहीं है।")
        
    # Delete physical file
    try:
        p = Path(tb.file_path)
        if p.exists():
            p.unlink()
    except Exception:
        pass
        
    db.delete(tb)
    db.commit()
    return {"message": "पाठ्यपुस्तक सफलतापूर्वक हटाई गई।"}

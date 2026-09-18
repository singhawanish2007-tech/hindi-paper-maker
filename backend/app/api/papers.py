import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.paper import Paper, AnswerKey
from app.models.textbook import Textbook, Chapter
from app.schemas.paper import (
    PaperGenerateRequest, PaperUpdateRequest, PaperData,
    BlueprintValidationRequest, BlueprintValidationResponse,
    AnswerKeyData
)
from app.services.paper_validator import validate_blueprint_data, validate_generated_or_edited_paper
from app.services.ai_generator import (
    generate_paper_with_gemini,
    generate_curriculum_paper_fallback,
    regenerate_single_question,
    regenerate_single_subquestion
)
from app.services.pdf_exporter import render_paper_html, export_html_to_pdf, render_answer_key_html
from app.services.docx_exporter import export_paper_to_docx
from app.services.answer_key_service import generate_answer_key_from_paper

router = APIRouter(prefix="/papers", tags=["Papers"])

@router.post("/validate-blueprint", response_model=BlueprintValidationResponse)
def validate_blueprint_endpoint(request: BlueprintValidationRequest):
    return validate_blueprint_data(request.total_marks, request.sections)

@router.post("/generate")
def generate_single_paper(
    req: PaperGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generates strictly ONE complete question paper based on textbook content and blueprint.
    DO NOT GENERATE MULTIPLE SETS.
    """
    # 1. Validate Blueprint Marks
    if req.blueprint and "sections" in req.blueprint:
        val = validate_blueprint_data(req.total_marks, req.blueprint["sections"])
        if not val["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"अमान्य ब्लूप्रिंट: {'; '.join(val['errors'])}"
            )
            
    # 2. Gather textbook text if textbook_id provided
    extracted_text = ""
    selected_chaps_info = []
    if req.textbook_id:
        tb = db.query(Textbook).filter(Textbook.id == req.textbook_id).first()
        if tb:
            chapters = db.query(Chapter).filter(
                Chapter.textbook_id == req.textbook_id,
                Chapter.title.in_(req.selected_chapters)
            ).all()
            for ch in chapters:
                selected_chaps_info.append({
                    "title": ch.title,
                    "unit": ch.unit_name,
                    "type": ch.chapter_type,
                    "start_page": ch.start_page,
                    "end_page": ch.end_page
                })
                if ch.extracted_text:
                    extracted_text += f"\n--- पाठ: {ch.title} ---\n" + ch.extracted_text[:2000]
    
    if not selected_chaps_info:
        for ch_title in req.selected_chapters:
            selected_chaps_info.append({"title": ch_title, "unit": req.unit_name or "पहली इकाई", "type": "prose"})

    # Prepare metadata
    exam_title = req.exam_title or f"{req.exam_type} ({'First Unit Test' if 'Unit' in req.exam_type else 'Examination'})"
    metadata = {
        "class_name": req.grade,
        "subject": f"हिंदी ({'लोकभारती' if int(req.grade) >= 9 else 'सुलभभारती'})",
        "book": req.book,
        "exam_type": req.exam_type,
        "duration": req.duration,
        "total_marks": req.total_marks,
        "difficulty": req.difficulty,
        "school_name": req.school_name,
        "tagline": req.tagline,
        "exam_title": exam_title,
        "has_logo": req.has_logo
    }

    # 3. Generate Paper (Gemini AI with Curriculum Fallback)
    paper_json = None
    generation_source = "gemini"
    
    if settings.GEMINI_API_KEY:
        try:
            paper_json = generate_paper_with_gemini(
                metadata=metadata,
                selected_chapters=selected_chaps_info,
                blueprint=req.blueprint or {},
                extracted_textbook_text=extracted_text
            )
        except Exception as e:
            print(f"Gemini generation failed, falling back: {e}")
            generation_source = "curriculum_engine"
            paper_json = generate_curriculum_paper_fallback(
                metadata=metadata,
                selected_chapters=selected_chaps_info,
                blueprint=req.blueprint or {},
                extracted_textbook_text=extracted_text
            )
            paper_json["warnings"].append(f"AI त्रुटि के कारण पाठ्यचर्या इंजन द्वारा निर्मित: {str(e)}")
    else:
        generation_source = "curriculum_engine"
        paper_json = generate_curriculum_paper_fallback(
            metadata=metadata,
            selected_chapters=selected_chaps_info,
            blueprint=req.blueprint or {},
            extracted_textbook_text=extracted_text
        )
        paper_json["warnings"].append("GEMINI_API_KEY सेट नहीं है। महाराष्ट्र बोर्ड अधिकृत प्रश्न बैंक द्वारा निर्मित।")

    # 4. Strict Validation
    validation = validate_generated_or_edited_paper(paper_json)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=422,
            detail=f"निर्मित प्रश्नपत्रिका में विसंगति: {'; '.join(validation['errors'])}"
        )

    # 5. Render HTML
    rendered_html = render_paper_html(paper_json)

    # 6. Save in SQLite
    paper_db = Paper(
        title=f"{exam_title} - कक्षा {req.grade}वीं ({req.total_marks} अंक)",
        grade=req.grade,
        subject=metadata["subject"],
        book=req.book,
        exam_type=req.exam_type,
        duration=req.duration,
        total_marks=req.total_marks,
        difficulty=req.difficulty,
        school_name=req.school_name,
        tagline=req.tagline,
        exam_title=exam_title,
        has_logo=req.has_logo,
        raw_blueprint_json=json.dumps(req.blueprint or {}, ensure_ascii=False),
        paper_data_json=json.dumps(paper_json, ensure_ascii=False),
        rendered_html=rendered_html,
        status="generated",
        warnings_json=json.dumps(paper_json.get("warnings", []), ensure_ascii=False)
    )
    db.add(paper_db)
    db.commit()
    db.refresh(paper_db)

    # 7. Generate matching Answer Key
    ans_key_dict = generate_answer_key_from_paper(paper_json)
    ans_db = AnswerKey(
        paper_id=paper_db.id,
        answer_key_json=json.dumps(ans_key_dict, ensure_ascii=False),
        notes=ans_key_dict.get("notes", "")
    )
    db.add(ans_db)
    db.commit()

    return {
        "id": paper_db.id,
        "title": paper_db.title,
        "total_marks": paper_db.total_marks,
        "paper_data": paper_json,
        "warnings": paper_json.get("warnings", []),
        "source": generation_source
    }

@router.get("")
@router.get("/")
def list_papers(db: Session = Depends(get_db)):
    papers = db.query(Paper).order_by(Paper.created_at.desc()).all()
    results = []
    for p in papers:
        results.append({
            "id": p.id,
            "title": p.title,
            "grade": p.grade,
            "subject": p.subject,
            "exam_type": p.exam_type,
            "duration": p.duration,
            "total_marks": p.total_marks,
            "school_name": p.school_name,
            "status": p.status,
            "created_at": p.created_at,
            "updated_at": p.updated_at
        })
    return results

@router.get("/{id}")
def get_paper(id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका उपलब्ध नहीं है।")
        
    try:
        data = json.loads(paper.paper_data_json)
    except Exception:
        data = {}
        
    try:
        warnings = json.loads(paper.warnings_json) if paper.warnings_json else []
    except Exception:
        warnings = []

    return {
        "id": paper.id,
        "title": paper.title,
        "grade": paper.grade,
        "subject": paper.subject,
        "book": paper.book,
        "exam_type": paper.exam_type,
        "duration": paper.duration,
        "total_marks": paper.total_marks,
        "difficulty": paper.difficulty,
        "school_name": paper.school_name,
        "tagline": paper.tagline,
        "exam_title": paper.exam_title,
        "has_logo": paper.has_logo,
        "status": paper.status,
        "paper_data": data,
        "warnings": warnings,
        "created_at": paper.created_at,
        "updated_at": paper.updated_at
    }

@router.put("/{id}")
def update_paper(
    id: int,
    req: PaperUpdateRequest,
    db: Session = Depends(get_db)
):
    paper = db.query(Paper).filter(Paper.id == id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका उपलब्ध नहीं है।")

    paper_dict = req.paper_data.model_dump(by_alias=True)

    if req.validate_marks:
        val = validate_generated_or_edited_paper(paper_dict)
        if not val["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"अंक असंगत: {'; '.join(val['errors'])}"
            )

    rendered_html = render_paper_html(paper_dict)
    
    if req.title:
        paper.title = req.title
    paper.paper_data_json = json.dumps(paper_dict, ensure_ascii=False)
    paper.rendered_html = rendered_html
    meta = paper_dict.get("metadata", {})
    paper.school_name = meta.get("school_name", paper.school_name)
    paper.tagline = meta.get("tagline", paper.tagline)
    paper.exam_title = meta.get("exam_title", paper.exam_title)
    paper.total_marks = paper_dict.get("total_marks", paper.total_marks)
    paper.status = "edited"
    
    ans_key_dict = generate_answer_key_from_paper(paper_dict)
    if paper.answer_key:
        paper.answer_key.answer_key_json = json.dumps(ans_key_dict, ensure_ascii=False)
    else:
        new_ak = AnswerKey(
            paper_id=paper.id,
            answer_key_json=json.dumps(ans_key_dict, ensure_ascii=False),
            notes=ans_key_dict.get("notes", "")
        )
        db.add(new_ak)

    db.commit()
    return {"message": "परिवर्तन सफलतापूर्वक सहेजे गए।", "total_marks": paper.total_marks}

from pydantic import BaseModel
class RegenerateQuestionRequest(BaseModel):
    section_index: int
    question_index: int
    question_id: Optional[str] = None
    class_name: Optional[str] = None
    textbook_id: Optional[int] = None
    selected_chapters: Optional[List[str]] = None
    section_title: Optional[str] = None
    question_type: Optional[str] = None
    marks: Optional[int] = None
    used_questions: Optional[List[str]] = None

@router.post("/{id}/regenerate-question")
def regenerate_question_endpoint(
    id: int,
    req: RegenerateQuestionRequest,
    db: Session = Depends(get_db)
):
    paper = db.query(Paper).filter(Paper.id == id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका उपलब्ध नहीं है।")

    try:
        paper_dict = json.loads(paper.paper_data_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"डेटा पार्सिंग त्रुटि: {str(e)}")

    sections = paper_dict.get("sections", [])
    if req.section_index < 0 or req.section_index >= len(sections):
        raise HTTPException(status_code=400, detail="अमान्य विभाग अनुक्रमणिका (section index)")

    questions = sections[req.section_index].get("questions", [])
    if req.question_index < 0 or req.question_index >= len(questions):
        raise HTTPException(status_code=400, detail="अमान्य प्रश्न अनुक्रमणिका (question index)")

    try:
        new_question = regenerate_single_question(
            paper_data=paper_dict,
            section_index=req.section_index,
            question_index=req.question_index,
            question_id=req.question_id,
            class_name=req.class_name or paper.grade or paper_dict.get("metadata", {}).get("class_name"),
            textbook_id=req.textbook_id or paper.textbook_id,
            selected_chapters=req.selected_chapters,
            section_title=req.section_title,
            question_type=req.question_type,
            marks=req.marks,
            used_questions=req.used_questions
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    questions[req.question_index] = new_question
    sections[req.section_index]["questions"] = questions
    paper_dict["sections"] = sections

    # Validate updated paper
    val = validate_generated_or_edited_paper(paper_dict)
    if not val["is_valid"]:
        raise HTTPException(status_code=422, detail=f"पुनर्जनन विसंगति: {'; '.join(val['errors'])}")

    paper.paper_data_json = json.dumps(paper_dict, ensure_ascii=False)
    paper.rendered_html = render_paper_html(paper_dict)
    db.commit()

    # Re-sync answer key if exists
    try:
        ans_key_dict = generate_answer_key_from_paper(paper_dict)
        ans_db = db.query(AnswerKey).filter(AnswerKey.paper_id == paper.id).first()
        if ans_db:
            ans_db.answer_key_json = json.dumps(ans_key_dict, ensure_ascii=False)
            db.commit()
    except Exception:
        pass

    return {
        "success": True,
        "section_index": req.section_index,
        "question_index": req.question_index,
        "question": new_question,
        "paper_data": paper_dict
    }

class RegenerateSubQuestionRequest(BaseModel):
    section_index: int
    question_index: int
    subquestion_index: int
    subquestion_id: Optional[str] = None
    class_name: Optional[str] = None
    textbook_id: Optional[int] = None
    selected_chapters: Optional[List[str]] = None
    section_title: Optional[str] = None
    question_type: Optional[str] = None
    marks: Optional[int] = None
    used_questions: Optional[List[str]] = None

@router.post("/{id}/regenerate-subquestion")
def regenerate_subquestion_endpoint(
    id: int,
    req: RegenerateSubQuestionRequest,
    db: Session = Depends(get_db)
):
    paper = db.query(Paper).filter(Paper.id == id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका उपलब्ध नहीं है।")

    try:
        paper_dict = json.loads(paper.paper_data_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"डेटा पार्सिंग त्रुटि: {str(e)}")

    sections = paper_dict.get("sections", [])
    if req.section_index < 0 or req.section_index >= len(sections):
        raise HTTPException(status_code=400, detail="अमान्य विभाग अनुक्रमणिका (section index)")

    questions = sections[req.section_index].get("questions", [])
    if req.question_index < 0 or req.question_index >= len(questions):
        raise HTTPException(status_code=400, detail="अमान्य प्रश्न अनुक्रमणिका (question index)")

    subs = questions[req.question_index].get("sub_questions", [])
    if req.subquestion_index < 0 or req.subquestion_index >= len(subs):
        raise HTTPException(status_code=400, detail="अमान्य उपप्रश्न अनुक्रमणिका (subquestion index)")

    try:
        paper_dict = regenerate_single_subquestion(
            paper_data=paper_dict,
            section_index=req.section_index,
            question_index=req.question_index,
            subquestion_index=req.subquestion_index,
            subquestion_id=req.subquestion_id,
            class_name=req.class_name or paper.grade or paper_dict.get("metadata", {}).get("class_name"),
            textbook_id=req.textbook_id or paper.textbook_id,
            selected_chapters=req.selected_chapters,
            section_title=req.section_title,
            question_type=req.question_type,
            marks=req.marks,
            used_questions=req.used_questions
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate updated paper
    val = validate_generated_or_edited_paper(paper_dict)
    if not val["is_valid"]:
        raise HTTPException(status_code=422, detail=f"उपप्रश्न पुनर्जनन विसंगति: {'; '.join(val['errors'])}")

    paper.paper_data_json = json.dumps(paper_dict, ensure_ascii=False)
    paper.rendered_html = render_paper_html(paper_dict)
    db.commit()

    # Re-sync answer key if exists
    try:
        ans_key_dict = generate_answer_key_from_paper(paper_dict)
        ans_db = db.query(AnswerKey).filter(AnswerKey.paper_id == paper.id).first()
        if ans_db:
            ans_db.answer_key_json = json.dumps(ans_key_dict, ensure_ascii=False)
            db.commit()
    except Exception:
        pass

    new_sub = paper_dict["sections"][req.section_index]["questions"][req.question_index]["sub_questions"][req.subquestion_index]

    return {
        "success": True,
        "section_index": req.section_index,
        "question_index": req.question_index,
        "subquestion_index": req.subquestion_index,
        "sub_question": new_sub,
        "paper_data": paper_dict
    }

@router.delete("/{id}")
def delete_paper(id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका उपलब्ध नहीं है।")
    db.delete(paper)
    db.commit()
    return {"message": "प्रश्नपत्रिका सफलतापूर्वक हटाई गई।"}

@router.get("/{id}/render", response_class=HTMLResponse)
def render_paper_page(id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका उपलब्ध नहीं है।")
    if not paper.rendered_html:
        try:
            data = json.loads(paper.paper_data_json)
            paper.rendered_html = render_paper_html(data)
            db.commit()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"HTML निर्माण में त्रुटि: {str(e)}")
    return HTMLResponse(content=paper.rendered_html)

@router.get("/{id}/answer-key")
def get_answer_key(id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="प्रश्नपत्रिका उपलब्ध नहीं है।")
        
    if not paper.answer_key:
        try:
            data = json.loads(paper.paper_data_json)
            ans_dict = generate_answer_key_from_paper(data)
            ak = AnswerKey(
                paper_id=paper.id,
                answer_key_json=json.dumps(ans_dict, ensure_ascii=False),
                notes=ans_dict.get("notes", "")
            )
            db.add(ak)
            db.commit()
            db.refresh(paper)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"उत्तरतालिका निर्माण में त्रुटि: {str(e)}")

    return json.loads(paper.answer_key.answer_key_json)

# Helper function for PDF export
def _process_pdf_export(id: int, db: Session):
    paper = db.query(Paper).filter(Paper.id == id).first()
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper with ID {id} not found.")

    try:
        data = json.loads(paper.paper_data_json)
        val = validate_generated_or_edited_paper(data)
        if not val["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"अंक असंगत होने के कारण PDF निर्यात नहीं हो सकता: {'; '.join(val['errors'])}"
            )
            
        html_content = render_paper_html(data)
        safe_name = f"paper_{paper.id}_{uuid.uuid4().hex[:6]}.pdf"
        output_path = settings.EXPORTS_DIR / safe_name
        
        export_html_to_pdf(html_content, output_path)
        filename = f"hindi-paper-{paper.id}.pdf"
        
        return FileResponse(
            path=str(output_path),
            filename=filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")

# Helper function for Word export
async def _process_docx_export(id: int, include_answer_key: bool, db: Session, request: Optional[Request] = None):
    paper = db.query(Paper).filter(Paper.id == id).first()
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper with ID {id} not found.")

    # Also check if include_answer_key passed in JSON body
    if request:
        try:
            body = await request.json()
            if isinstance(body, dict) and "include_answer_key" in body:
                include_answer_key = bool(body["include_answer_key"])
        except Exception:
            pass

    try:
        data = json.loads(paper.paper_data_json)
        val = validate_generated_or_edited_paper(data)
        if not val["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"अंक असंगत होने के कारण DOCX निर्यात नहीं हो सकता: {'; '.join(val['errors'])}"
            )

        ak_data = None
        if include_answer_key and paper.answer_key:
            ak_data = json.loads(paper.answer_key.answer_key_json)

        safe_name = f"paper_{paper.id}_{uuid.uuid4().hex[:6]}.docx"
        output_path = settings.EXPORTS_DIR / safe_name
        
        export_paper_to_docx(
            paper_data=data,
            output_path=output_path,
            include_answer_key=include_answer_key,
            answer_key_data=ak_data
        )
        
        filename = f"hindi-paper-{paper.id}.docx"
        return FileResponse(
            path=str(output_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX export failed: {str(e)}")

# POST & GET routes for PDF export (supporting both POST and GET for maximum reliability)
@router.post("/{id}/export/pdf")
def export_paper_pdf_post(id: int, db: Session = Depends(get_db)):
    return _process_pdf_export(id, db)

@router.get("/{id}/export/pdf")
def export_paper_pdf_get(id: int, db: Session = Depends(get_db)):
    return _process_pdf_export(id, db)

# POST & GET routes for Word DOCX export (supporting both POST and GET)
@router.post("/{id}/export/word")
async def export_paper_docx_post(
    id: int,
    request: Request,
    include_answer_key: bool = Query(False),
    db: Session = Depends(get_db)
):
    return await _process_docx_export(id, include_answer_key, db, request)

@router.get("/{id}/export/word")
async def export_paper_docx_get(
    id: int,
    include_answer_key: bool = Query(False),
    db: Session = Depends(get_db)
):
    return await _process_docx_export(id, include_answer_key, db, None)

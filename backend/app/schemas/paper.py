from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime

class PaperMetadata(BaseModel):
    class_name: str = Field(..., alias="class")
    subject: str = "हिंदी (लोकभारती)"
    book: str = "हिंदी लोकभारती"
    exam_type: str = "प्रथम घटक चाचणी"
    duration: str = "२ घंटे"
    total_marks: int = 40
    difficulty: str = "Medium"
    school_name: str = "TRINITY HIGH SCHOOL & JUNIOR COLLEGE"
    tagline: str = "KNOWLEDGE IS WISDOM"
    exam_title: str = "प्रथम घटक चाचणी (First Unit Test)"
    academic_year: Optional[str] = "2026-2027"
    exam_date: Optional[str] = ""
    teacher_name: Optional[str] = ""
    has_logo: bool = True

    class Config:
        populate_by_name = True

class SubQuestion(BaseModel):
    sub_number: str = "(i)"
    sub_text: str
    marks: int = 1
    items: List[str] = []
    answer: Optional[str] = ""

class QuestionItem(BaseModel):
    question_number: str
    question_text: str
    marks: int
    source_type: Literal["textbook", "ai_generated", "teacher_created"] = "textbook"
    chapter: str = ""
    source_page: str = ""
    source_confidence: Literal["high", "medium", "low"] = "high"
    answer: str = ""
    passage: Optional[str] = ""
    is_poem: Optional[bool] = False
    sub_questions: Optional[List[SubQuestion]] = []

class SectionItem(BaseModel):
    section_number: int
    section_title: str
    section_marks: int
    questions: List[QuestionItem]

class PaperData(BaseModel):
    metadata: PaperMetadata
    general_instructions: Optional[List[str]] = [
        "सभी प्रश्न हल करना अनिवार्य है ।",
        "दाहिनी ओर दिए गए अंक प्रश्नों के पूर्णांक दर्शाते हैं ।",
        "सुवाच्य तथा शुद्ध लेखन अपेक्षित है ।"
    ]
    sections: List[SectionItem]
    total_marks: int
    warnings: List[str] = []

class BlueprintValidationRequest(BaseModel):
    total_marks: int
    sections: List[dict]

class BlueprintValidationResponse(BaseModel):
    is_valid: bool
    configured_total: int
    calculated_total: int
    difference: int
    errors: List[str]
    warnings: List[str]

class PaperGenerateRequest(BaseModel):
    textbook_id: Optional[int] = None
    grade: str
    book: str
    exam_type: str
    total_marks: int
    duration: str = "२ घंटे"
    difficulty: str = "Medium"
    unit_name: Optional[str] = "पहली इकाई"
    selected_chapters: List[str]
    school_name: str = "TRINITY HIGH SCHOOL & JUNIOR COLLEGE"
    tagline: str = "KNOWLEDGE IS WISDOM"
    exam_title: Optional[str] = None
    blueprint: Optional[dict] = None
    has_logo: bool = True

class PaperUpdateRequest(BaseModel):
    title: Optional[str] = None
    paper_data: PaperData
    validate_marks: bool = True

class AnswerKeyItem(BaseModel):
    section_title: str
    question_number: str
    question_text: str
    expected_answer: str
    marks: int
    points: List[str] = []
    teacher_verification_required: bool = False

class AnswerKeyData(BaseModel):
    paper_id: int
    exam_title: str
    total_marks: int
    answers: List[AnswerKeyItem]
    notes: Optional[str] = ""

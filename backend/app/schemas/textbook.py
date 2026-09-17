from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class ChapterBase(BaseModel):
    unit_name: str = "पहली इकाई"
    chapter_number: int
    title: str
    author: Optional[str] = ""
    chapter_type: str = "prose"  # prose, poetry, supplementary, grammar, writing
    start_page: int = 1
    end_page: int = 1
    extracted_text: Optional[str] = ""

class ChapterCreate(ChapterBase):
    pass

class ChapterUpdate(BaseModel):
    id: Optional[int] = None
    unit_name: Optional[str] = None
    chapter_number: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    chapter_type: Optional[str] = None
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    extracted_text: Optional[str] = None

class ChapterResponse(ChapterBase):
    id: int
    textbook_id: int
    class Config:
        from_attributes = True

class PageExtractionResponse(BaseModel):
    id: int
    page_number: int
    character_count: int
    is_scanned: bool
    is_low_text: bool
    text_content: str
    class Config:
        from_attributes = True

class TextbookResponse(BaseModel):
    id: int
    title: str
    grade: str
    book_name: str
    filename: str
    file_size: int
    total_pages: int
    extracted_pages: int
    scanned_pages: int
    low_text_pages: int
    ocr_warning: bool
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    chapters: List[ChapterResponse] = []
    class Config:
        from_attributes = True

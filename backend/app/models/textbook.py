from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Textbook(Base):
    __tablename__ = "textbooks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    grade = Column(String(10), nullable=False)  # "5", "6", ..., "10"
    book_name = Column(String(100), nullable=False)  # "हिंदी सुलभभारती" or "हिंदी लोकभारती"
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    total_pages = Column(Integer, default=0)
    extracted_pages = Column(Integer, default=0)
    scanned_pages = Column(Integer, default=0)
    low_text_pages = Column(Integer, default=0)
    ocr_warning = Column(Boolean, default=False)
    status = Column(String(50), default="ready")  # uploaded, processing, ready, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    pages = relationship("PageExtraction", back_populates="textbook", cascade="all, delete-orphan")
    chapters = relationship("Chapter", back_populates="textbook", cascade="all, delete-orphan")

class PageExtraction(Base):
    __tablename__ = "page_extractions"
    
    id = Column(Integer, primary_key=True, index=True)
    textbook_id = Column(Integer, ForeignKey("textbooks.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    character_count = Column(Integer, default=0)
    is_scanned = Column(Boolean, default=False)
    is_low_text = Column(Boolean, default=False)
    text_content = Column(Text, default="")
    
    textbook = relationship("Textbook", back_populates="pages")

class Chapter(Base):
    __tablename__ = "chapters"
    
    id = Column(Integer, primary_key=True, index=True)
    textbook_id = Column(Integer, ForeignKey("textbooks.id", ondelete="CASCADE"), nullable=False)
    unit_name = Column(String(100), default="पहली इकाई")
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    author = Column(String(255), default="")
    chapter_type = Column(String(50), default="prose")  # prose, poetry, supplementary, grammar, writing
    start_page = Column(Integer, default=1)
    end_page = Column(Integer, default=1)
    extracted_text = Column(Text, default="")
    
    textbook = relationship("Textbook", back_populates="chapters")

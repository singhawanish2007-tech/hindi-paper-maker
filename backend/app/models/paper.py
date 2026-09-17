from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Paper(Base):
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    grade = Column(String(10), nullable=False)
    subject = Column(String(100), default="हिंदी (लोकभारती)")
    book = Column(String(100), default="हिंदी लोकभारती")
    exam_type = Column(String(100), nullable=False)
    duration = Column(String(50), default="२ घंटे")
    total_marks = Column(Integer, nullable=False)
    difficulty = Column(String(50), default="Medium")
    school_name = Column(String(255), default="TRINITY HIGH SCHOOL & JUNIOR COLLEGE")
    tagline = Column(String(255), default="KNOWLEDGE IS WISDOM")
    exam_title = Column(String(255), default="प्रथम घटक चाचणी")
    academic_year = Column(String(50), default="2026-2027")
    exam_date = Column(String(50), default="")
    teacher_name = Column(String(100), default="")
    has_logo = Column(Boolean, default=True)
    
    # Store complete structured paper JSON and rendered HTML
    raw_blueprint_json = Column(Text, nullable=False)
    paper_data_json = Column(Text, nullable=False)
    rendered_html = Column(Text, nullable=True)
    
    status = Column(String(50), default="draft")  # draft, generated, validated, exported
    warnings_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    answer_key = relationship("AnswerKey", back_populates="paper", uselist=False, cascade="all, delete-orphan")

class AnswerKey(Base):
    __tablename__ = "answer_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    answer_key_json = Column(Text, nullable=False)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    paper = relationship("Paper", back_populates="answer_key")

class CustomBlueprint(Base):
    __tablename__ = "custom_blueprints"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    grade = Column(String(10), nullable=False)
    total_marks = Column(Integer, nullable=False)
    duration = Column(String(50), default="२ घंटे")
    structure_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

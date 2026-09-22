from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.core.database import Base

class UploadedPaper(Base):
    __tablename__ = "uploaded_papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    grade = Column(String(20), nullable=False)
    subject = Column(String(100), default="हिंदी")
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # "pdf", "docx", "image"
    file_path = Column(String(500), nullable=False)
    converted_docx_path = Column(String(500), nullable=True)
    converted_pdf_path = Column(String(500), nullable=True)
    preview_html = Column(Text, nullable=True)
    file_size = Column(Integer, default=0)
    conversion_status = Column(String(50), default="ready")
    conversion_warning = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

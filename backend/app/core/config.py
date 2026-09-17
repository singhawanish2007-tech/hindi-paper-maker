import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "HINDI PAPER MAKER"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    TEXTBOOKS_DIR: Path = STORAGE_DIR / "textbooks"
    EXPORTS_DIR: Path = STORAGE_DIR / "exports"
    ASSETS_DIR: Path = STORAGE_DIR / "assets"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/hindi_paper_maker.db")
    
    # AI Engine
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Frontend URL for CORS in production
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "")
    
    # File Limits (100 MB)
    MAX_FILE_SIZE: int = 100 * 1024 * 1024
    ALLOWED_EXTENSIONS: list[str] = [".pdf"]
    
    # Mandatory Default Settings
    DEFAULT_SCHOOL_NAME: str = "TRINITY HIGH SCHOOL & JUNIOR COLLEGE"
    DEFAULT_TAGLINE: str = "KNOWLEDGE IS WISDOM"
    MANDATORY_FOOTER: str = "---------ALL THE BEST!!!----------"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.TEXTBOOKS_DIR.mkdir(parents=True, exist_ok=True)
settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.ASSETS_DIR.mkdir(parents=True, exist_ok=True)

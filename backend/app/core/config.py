import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "HINDI PAPER MAKER"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Environment detection
    IS_VERCEL: bool = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = Path("/tmp/storage") if bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) else BASE_DIR / "storage"
    TEXTBOOKS_DIR: Path = STORAGE_DIR / "textbooks"
    EXPORTS_DIR: Path = STORAGE_DIR / "exports"
    ASSETS_DIR: Path = STORAGE_DIR / "assets"
    UPLOADED_PAPERS_DIR: Path = STORAGE_DIR / "uploaded_papers"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:////tmp/hindi_paper_maker.db" if bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) else f"sqlite:///{Path(__file__).resolve().parent.parent.parent}/hindi_paper_maker.db"
    )
    
    # AI Engine
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Frontend URL for CORS in production
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "")
    
    # File Limits (100 MB)
    MAX_FILE_SIZE: int = 100 * 1024 * 1024
    ALLOWED_EXTENSIONS: list[str] = [".pdf"]
    ALLOWED_PAPER_EXTENSIONS: list[str] = [".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"]
    
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
settings.UPLOADED_PAPERS_DIR.mkdir(parents=True, exist_ok=True)


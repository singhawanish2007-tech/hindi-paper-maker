import os
import shutil
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api.textbooks import router as textbooks_router
from app.api.papers import router as papers_router
from app.api.blueprints import router as blueprints_router
from app.models.textbook import Textbook, Chapter
from app.core.curriculum_data import CURRICULUM_DATABASE

# Create Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Online AI-powered Hindi question paper generator for teachers following Maharashtra State Board curriculum."
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local and deployed use
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount storage directory for static assets (logo, etc.)
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")

# Include API Routers
app.include_router(textbooks_router, prefix=settings.API_V1_STR)
app.include_router(papers_router, prefix=settings.API_V1_STR)
app.include_router(blueprints_router, prefix=settings.API_V1_STR)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "gemini_configured": bool(settings.GEMINI_API_KEY)
    }

# Frontend Production Serving & Single-Page-App (SPA) Fallback
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", str(settings.BASE_DIR.parent / "frontend" / "dist")))

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def serve_root():
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Frontend build not found. Run 'npm run build' in frontend directory."}

    @app.get("/{full_path:path}")
    async def serve_spa_routes(full_path: str):
        # Exclude API, storage, and docs routes
        if full_path.startswith("api/") or full_path.startswith("storage/") or full_path in ["docs", "redoc", "openapi.json"]:
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        
        static_file = FRONTEND_DIST / full_path
        if static_file.is_file():
            return FileResponse(static_file)
        
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse(status_code=404, content={"detail": "Page not found"})

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"आंतरिक सर्वर त्रुटि: {str(exc)}"}
    )

def seed_initial_data():
    """
    Seeds initial textbook references from C:/Users/User/Hindi paper if available.
    """
    db = SessionLocal()
    try:
        count = db.query(Textbook).count()
        if count == 0:
            print("Pre-seeding Maharashtra State Board textbooks...")
            source_dir = Path(r"C:/Users/User/Hindi paper")
            
            for grade_str, cur_data in CURRICULUM_DATABASE.items():
                book_name = cur_data.get("book", "हिंदी लोकभारती")
                pdf_filename = f"हिंदी - कक्षा {grade_str}.pdf"
                source_pdf = source_dir / pdf_filename
                dest_pdf = settings.TEXTBOOKS_DIR / pdf_filename
                
                if source_pdf.exists() and not dest_pdf.exists():
                    try:
                        shutil.copy2(source_pdf, dest_pdf)
                    except Exception:
                        pass
                        
                file_size = dest_pdf.stat().st_size if dest_pdf.exists() else 1800000
                
                tb = Textbook(
                    title=f"हिंदी कक्षा {grade_str} ({book_name})",
                    grade=grade_str,
                    book_name=book_name,
                    filename=pdf_filename,
                    file_path=str(dest_pdf if dest_pdf.exists() else source_pdf),
                    file_size=file_size,
                    total_pages=60,
                    extracted_pages=55,
                    scanned_pages=0,
                    low_text_pages=0,
                    ocr_warning=False,
                    status="ready"
                )
                db.add(tb)
                db.commit()
                db.refresh(tb)
                
                # Add chapters
                for unit in cur_data.get("units", []):
                    u_name = unit.get("name", "पहली इकाई")
                    for ch in unit.get("chapters", []):
                        chap = Chapter(
                            textbook_id=tb.id,
                            unit_name=u_name,
                            chapter_number=ch["number"],
                            title=ch["title"],
                            author=ch.get("author", ""),
                            chapter_type=ch.get("type", "prose"),
                            start_page=1,
                            end_page=4,
                            extracted_text=""
                        )
                        db.add(chap)
                db.commit()
                
            print("Textbooks and chapters pre-seeded successfully.")
    except Exception as e:
        print(f"Initial seeding note: {e}")
        db.rollback()
    finally:
        db.close()

seed_initial_data()

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting HINDI PAPER MAKER production server on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False)


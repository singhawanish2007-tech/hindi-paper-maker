import base64
import os
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
import pymupdf
from playwright.sync_api import sync_playwright
from app.core.config import settings

TEMPLATES_DIR = settings.BASE_DIR / "app" / "templates"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)

def get_logo_data_uri() -> str:
    logo_path = settings.ASSETS_DIR / "1000358221.png"
    if not logo_path.exists():
        # Check source directory
        src_path = Path(r"C:\Users\User\Hindi paper\1000358221.png")
        if src_path.exists():
            logo_path = src_path
            
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
    return ""

def render_paper_html(paper_data: Dict[str, Any]) -> str:
    """
    Renders paper HTML using Jinja2 template and paper JSON.
    """
    template = jinja_env.get_template("paper_template.html")
    metadata = paper_data.get("metadata", {})
    
    # Ensure class_name is set for template
    class_val = metadata.get("class_name") or metadata.get("class") or "10"
    meta_dict = dict(metadata)
    meta_dict["class_name"] = class_val
    
    logo_data_uri = get_logo_data_uri() if meta_dict.get("has_logo", True) else ""
    
    html = template.render(
        metadata=meta_dict,
        general_instructions=paper_data.get("general_instructions", []),
        sections=paper_data.get("sections", []),
        total_marks=paper_data.get("total_marks", 0),
        logo_url=logo_data_uri
    )
    return html

def render_answer_key_html(answer_key_data: Dict[str, Any]) -> str:
    template = jinja_env.get_template("answer_key_template.html")
    html = template.render(
        exam_title=answer_key_data.get("exam_title", "परीक्षा"),
        total_marks=answer_key_data.get("total_marks", 0),
        answers=answer_key_data.get("answers", []),
        notes=answer_key_data.get("notes", "")
    )
    return html

def export_html_to_pdf(html_content: str, output_path: Path) -> Path:
    """
    Exports HTML content to A4 PDF using Playwright + Chrome/Edge.
    Validates the generated PDF with PyMuPDF.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Determine browser executable (Windows, Linux, Docker, or Playwright bundled)
    env_browser = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or os.environ.get("CHROME_BIN")
    candidate_paths = [
        env_browser,
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    
    browser_exe = None
    for path_str in candidate_paths:
        if path_str and os.path.exists(path_str):
            browser_exe = path_str
            break

    with sync_playwright() as p:
        launch_kwargs = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        }
        if browser_exe:
            launch_kwargs["executable_path"] = browser_exe
            
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page()
        page.set_content(html_content, wait_until="load")
        
        page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
            margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"}
        )
        browser.close()
        
    # Validate PDF integrity with PyMuPDF
    doc = pymupdf.open(output_path)
    page_count = len(doc)
    doc.close()
    
    if page_count == 0:
        raise ValueError("Generated PDF is empty or invalid.")
        
    return output_path

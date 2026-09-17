import re
from typing import List, Dict, Any, Optional
from app.core.curriculum_data import CURRICULUM_DATABASE

def parse_table_of_contents(extracted_pages: List[Dict[str, Any]], grade: str, book_name: str) -> List[Dict[str, Any]]:
    """
    Parses Table of Contents (अनुक्रमणिका) from extracted text.
    Combines parsed cues with Maharashtra State Board curriculum database.
    """
    detected_chapters: List[Dict[str, Any]] = []
    
    # Check if we have preloaded curriculum for this grade
    curriculum = CURRICULUM_DATABASE.get(str(grade))
    
    # Look through first 10 pages for अनुक्रमणिका keywords
    toc_text = ""
    for page in extracted_pages[:10]:
        text = page.get("text_content", "")
        if "अनुक्रमणिका" in text or "पहली इकाई" in text or "पाठ" in text or "कविता" in text:
            toc_text += "\n" + text

    # If we have preloaded curriculum, use it as baseline
    if curriculum:
        for unit in curriculum.get("units", []):
            unit_name = unit.get("name", "पहली इकाई")
            for chap in unit.get("chapters", []):
                # Try to refine page numbers if found in toc_text
                title = chap["title"]
                start_p = 1
                end_p = 1
                
                # Check if title appears in toc_text with page numbers
                if title in toc_text:
                    match = re.search(rf"{re.escape(title)}.*?(\d+)", toc_text)
                    if match:
                        try:
                            start_p = int(match.group(1))
                            end_p = start_p + 4
                        except Exception:
                            pass
                else:
                    # Parse from default range e.g. "5-10"
                    pr = chap.get("page_range", "1-4")
                    parts = pr.split("-")
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        start_p = int(parts[0])
                        end_p = int(parts[1])

                detected_chapters.append({
                    "unit_name": unit_name,
                    "chapter_number": chap["number"],
                    "title": chap["title"],
                    "author": chap.get("author", ""),
                    "chapter_type": chap.get("type", "prose"),
                    "start_page": start_p,
                    "end_page": end_p,
                    "extracted_text": ""
                })
    else:
        # Fallback generic parsing if unknown grade
        # Regex search for chapter-like patterns
        lines = toc_text.splitlines()
        current_unit = "पहली इकाई"
        c_num = 1
        for line in lines:
            line_s = line.strip()
            if "दूसरी इकाई" in line_s:
                current_unit = "दूसरी इकाई"
                c_num = 1
            elif "पहली इकाई" in line_s:
                current_unit = "पहली इकाई"
                c_num = 1
                
            m = re.match(r"^([०-९\d]+)[\.\s\-]+([^\d]+)\s*(\d+)?", line_s)
            if m and len(m.group(2).strip()) > 2:
                detected_chapters.append({
                    "unit_name": current_unit,
                    "chapter_number": c_num,
                    "title": m.group(2).strip(),
                    "author": "",
                    "chapter_type": "prose",
                    "start_page": int(m.group(3)) if m.group(3) else c_num * 4,
                    "end_page": (int(m.group(3)) + 4) if m.group(3) else (c_num * 4 + 4),
                    "extracted_text": ""
                })
                c_num += 1

    return detected_chapters

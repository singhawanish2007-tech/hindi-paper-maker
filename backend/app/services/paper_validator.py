import re
from typing import Dict, Any, List, Tuple

PROHIBITED_POETRY_PATTERNS = [
    r"तुकांत",
    r"तुक\s*मिलाने",
    r"तुकबंदी",
    r"rhym(e|ing)",
    r"समान\s*ध्वनि\s*वाले\s*शब्द"
]

class PaperValidationError(Exception):
    def __init__(self, message: str, errors: List[str], difference: int = 0):
        super().__init__(message)
        self.errors = errors
        self.difference = difference

def check_prohibited_poetry_content(text: str) -> List[str]:
    """
    Checks if text contains prohibited 'तुकांत शब्द' or rhyming words requests.
    """
    found_violations = []
    for pattern in PROHIBITED_POETRY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found_violations.append(
                f"प्रतिबंधित प्रश्न: 'तुकांत शब्द' या तुक मिलाने वाले प्रश्न वर्जित हैं। इसके स्थान पर 'शब्दार्थ', 'समानार्थी', 'विलोम', 'शब्द संपदा' या 'भावार्थ' का प्रयोग करें।"
            )
            break
    return found_violations

def validate_blueprint_data(configured_total: int, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates blueprint before paper generation.
    Checks section total vs question sum vs configured total.
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    if configured_total <= 0:
        errors.append("कुल अंक शून्य अथवा धनात्मक संख्या होने चाहिए।")
        
    calculated_total = 0
    section_sum_total = 0
    
    for s_idx, section in enumerate(sections):
        s_title = section.get("section_title", f"विभाग {s_idx + 1}")
        s_marks = section.get("section_marks", 0)
        section_sum_total += s_marks
        
        q_sum = 0
        questions = section.get("questions", [])
        if not questions:
            errors.append(f"'{s_title}' में कोई प्रश्न सम्मिलित नहीं है।")
            
        for q_idx, q in enumerate(questions):
            q_num = q.get("question_number", f"प्रश्न {q_idx + 1}")
            marks = q.get("marks", 0)
            if marks <= 0:
                errors.append(f"'{s_title}' के '{q_num}' में वैध अंक (धनात्मक संख्या) नहीं हैं।")
            q_sum += marks
            
        if q_sum != s_marks:
            diff = abs(s_marks - q_sum)
            errors.append(
                f"'{s_title}' के प्रश्नों का योग ({q_sum} अंक) विभाग के निर्धारित अंक ({s_marks} अंक) के बराबर नहीं है। (अंतर: {diff} अंक)"
            )
            
        calculated_total += q_sum
        
    diff_total = abs(configured_total - calculated_total)
    if calculated_total != configured_total:
        errors.append(
            f"कॉन्फ़िगर किए गए कुल अंक: {configured_total} अंक, गणना किए गए कुल अंक: {calculated_total} अंक। अंतर: {diff_total} अंक।"
        )
        
    is_valid = (len(errors) == 0)
    return {
        "is_valid": is_valid,
        "configured_total": configured_total,
        "calculated_total": calculated_total,
        "difference": diff_total,
        "errors": errors,
        "warnings": warnings
    }

def validate_generated_or_edited_paper(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates generated or edited paper before preview / export.
    Enforces Section 5 & 13 requirements.
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    metadata = paper_data.get("metadata", {})
    configured_total = metadata.get("total_marks") or paper_data.get("total_marks", 0)
    sections = paper_data.get("sections", [])
    
    if not sections:
        errors.append("प्रश्नपत्रिका में कोई विभाग उपलब्ध नहीं है।")
        return {"is_valid": False, "difference": configured_total, "errors": errors, "warnings": warnings}
        
    calculated_total = 0
    section_sum_total = 0
    
    # 1. Prohibition & marks check
    for s_idx, section in enumerate(sections):
        s_title = section.get("section_title", f"विभाग {s_idx + 1}")
        s_marks = section.get("section_marks", 0)
        section_sum_total += s_marks
        
        # Check section title for prohibited words
        prohib = check_prohibited_poetry_content(s_title)
        if prohib:
            errors.extend(prohib)
            
        q_sum = 0
        questions = section.get("questions", [])
        for q_idx, q in enumerate(questions):
            q_num = q.get("question_number", f"प्रश्न {q_idx + 1}")
            q_text = q.get("question_text", "")
            q_marks = q.get("marks", 0)
            
            if not q_text.strip():
                errors.append(f"'{s_title}' - '{q_num}': प्रश्न का विवरण रिक्त नहीं हो सकता।")
                
            if q_marks <= 0:
                errors.append(f"'{s_title}' - '{q_num}': अंक धनात्मक संख्या होनी चाहिए।")
                
            # Prohibited phrases in question
            prohib = check_prohibited_poetry_content(q_text)
            if prohib:
                errors.extend([f"'{s_title}' - '{q_num}': {p}" for p in prohib])
                
            # Prohibited phrases in passage or subquestions
            passage = q.get("passage", "")
            if passage:
                pass_prohib = check_prohibited_poetry_content(passage)
                if pass_prohib:
                    errors.extend([f"'{s_title}' - '{q_num}' परिच्छेद: {p}" for p in pass_prohib])
                    
            for sub in q.get("sub_questions", []) or []:
                sub_text = sub.get("sub_text", "")
                sub_prohib = check_prohibited_poetry_content(sub_text)
                if sub_prohib:
                    errors.extend([f"'{s_title}' - उपप्रश्न: {p}" for p in sub_prohib])
                    
            q_sum += q_marks
            
        if q_sum != s_marks:
            errors.append(
                f"'{s_title}': प्रश्नों के अंकों का योग ({q_sum}) विभाग के कुल अंक ({s_marks}) से मेल नहीं खाता। (अंतर: {abs(s_marks - q_sum)} अंक)"
            )
            
        calculated_total += q_sum
        
    difference = abs(configured_total - calculated_total)
    if calculated_total != configured_total:
        errors.append(
            f"कुल अंक असंगत: कॉन्फ़िगर किए गए कुल अंक = {configured_total}, वर्तमान कुल अंक = {calculated_total}। कृपया {difference} अंक ठीक करें।"
        )
        
    # Check for prohibited multi-set keys or text
    paper_str = str(paper_data)
    if "Set A" in paper_str or "Set B" in paper_str or "Set C" in paper_str or "सेट अ" in paper_str:
        errors.append("बहु-सेट (Set A, Set B, Set C) वर्जित हैं। केवल एक प्रश्नपत्रिका अनुमत है।")
        
    # Check for duplicate questions across all sections
    from app.services.question_uniqueness import validate_paper_question_uniqueness
    uniqueness_errors = validate_paper_question_uniqueness(paper_data)
    if uniqueness_errors:
        errors.extend(uniqueness_errors)

    return {
        "is_valid": len(errors) == 0,
        "configured_total": configured_total,
        "calculated_total": calculated_total,
        "difference": difference,
        "errors": errors,
        "warnings": warnings
    }

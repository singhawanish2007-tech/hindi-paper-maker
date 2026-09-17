import re
from typing import Dict, Any, List, Set, Tuple, Optional, Union

# Mapping of Devanagari numerals to standard digits
DEVANAGARI_DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}

def normalize_question(text: str) -> str:
    """
    Normalizes question text for robust cross-section duplicate detection:
    - Removes HTML tags
    - Converts Devanagari digits to standard digits
    - Removes question numbering prefixes (e.g. प्रश्न १., (i), 1., (अ))
    - Normalizes punctuation and multiple whitespaces
    - Lowercases any English text
    """
    if not text:
        return ""
    
    # 1. Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", text)
    
    # 2. Convert Devanagari digits
    for dev_d, std_d in DEVANAGARI_DIGITS.items():
        cleaned = cleaned.replace(dev_d, std_d)
        
    # 3. Lowercase English characters
    cleaned = cleaned.lower()
    
    # 4. Remove common question prefixes (e.g. प्रश्न 1., (i), (1), (अ), 1., 2.)
    cleaned = re.sub(r"^(प्रश्न\s*\d*[\.\:\-\)]*|\(\s*[\d\wivxlca-z]+\s*\)|\d+[\.\:\-\)])\s*", "", cleaned.strip())
    
    # 5. Remove punctuation symbols
    cleaned = re.sub(r"[\.,\:;\-\—\–\?!\'\"`\(\)\[\]\{\}।॥_]", " ", cleaned)
    
    # 6. Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def get_tokens(text: str) -> Set[str]:
    """Returns a set of normalized non-trivial tokens (length >= 2)."""
    norm = normalize_question(text)
    # Filter out single-character particles if appropriate
    return {w for w in norm.split() if len(w) >= 2}

def get_question_signature(question: Union[Dict[str, Any], str]) -> str:
    """
    Constructs a composite normalized signature for a question including subquestions.
    """
    if isinstance(question, str):
        return normalize_question(question)
    parts = []
    q_text = question.get("question_text", "")
    if q_text:
        parts.append(normalize_question(q_text))
        
    for sub in question.get("sub_questions", []) or []:
        if isinstance(sub, dict):
            st = sub.get("sub_text", "")
        else:
            st = str(sub)
        if st:
            parts.append(normalize_question(st))
            
    return " | ".join(parts)

def compute_similarity(tokens1: Set[str], tokens2: Set[str]) -> float:
    """Computes Jaccard word-token similarity between two token sets."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union) if union else 0.0

def is_duplicate_question(
    candidate: Union[Dict[str, Any], str],
    existing_questions: Union[List[Union[Dict[str, Any], str]], Dict[str, Any], str],
    threshold: float = 0.82
) -> Tuple[bool, Optional[str]]:
    """
    Checks if candidate question is an exact or near-duplicate of any existing question.
    Returns (is_duplicate, description_of_match).
    """
    if isinstance(existing_questions, (dict, str)):
        existing_questions = [existing_questions]

    cand_sig = get_question_signature(candidate)
    cand_tokens = get_tokens(cand_sig)
    
    cand_subs = []
    if isinstance(candidate, dict):
        for s in candidate.get("sub_questions", []) or []:
            if isinstance(s, dict) and s.get("sub_text"):
                cand_subs.append(normalize_question(s.get("sub_text", "")))
    
    for ex in existing_questions:
        ex_sig = get_question_signature(ex)
        ex_tokens = get_tokens(ex_sig)
        ex_label = ex.get("question_number", "प्रश्न") if isinstance(ex, dict) else "प्रश्न"
        
        # 1. Exact signature match
        if cand_sig and ex_sig and cand_sig == ex_sig:
            return True, f"समान प्रश्न: '{ex_label}' से हूबहू मिलता है।"
            
        # 2. Token Jaccard similarity threshold for full question
        sim = compute_similarity(cand_tokens, ex_tokens)
        if sim >= threshold:
            return True, f"समान प्रश्न: '{ex_label}' से {int(sim * 100)}% समानता रखता है।"
            
        # 3. Check individual subquestion overlaps (especially in grammar/comprehension)
        ex_subs = []
        if isinstance(ex, dict):
            for s in ex.get("sub_questions", []) or []:
                if isinstance(s, dict) and s.get("sub_text"):
                    ex_subs.append(normalize_question(s.get("sub_text", "")))
        for c_sub in cand_subs:
            c_sub_tokens = get_tokens(c_sub)
            if len(c_sub_tokens) < 3:
                continue
            for e_sub in ex_subs:
                e_sub_tokens = get_tokens(e_sub)
                sub_sim = compute_similarity(c_sub_tokens, e_sub_tokens)
                if sub_sim >= 0.85:
                    return True, f"उपप्रश्न समानता: '{e_sub[:40]}' से मिलता-जुलता प्रश्न पहले से मौजूद है।"
                    
    return False, None

def validate_paper_question_uniqueness(paper_data: Dict[str, Any]) -> List[str]:
    """
    Traverses all sections and questions in the paper to verify complete uniqueness.
    Returns a list of violation messages if any duplicate question is detected.
    """
    errors: List[str] = []
    seen_questions: List[Dict[str, Any]] = []
    
    for s_idx, section in enumerate(paper_data.get("sections", [])):
        s_title = section.get("section_title", f"विभाग {s_idx + 1}")
        for q in section.get("questions", []):
            q_num = q.get("question_number", "प्रश्न")
            
            is_dup, reason = is_duplicate_question(q, seen_questions)
            if is_dup:
                errors.append(f"पुनरावृत्ति त्रुटि ({s_title} - {q_num}): {reason}")
            else:
                # Add copy with section tag for traceability
                q_copy = dict(q)
                q_copy["_section_title"] = s_title
                seen_questions.append(q_copy)
                
    return errors

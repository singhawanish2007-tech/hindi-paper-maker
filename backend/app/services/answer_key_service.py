from typing import Dict, Any, List

def generate_answer_key_from_paper(paper_data: Dict[str, Any]) -> Dict[str, Any]:
    metadata = paper_data.get("metadata", {})
    sections = paper_data.get("sections", [])
    
    answers: List[Dict[str, Any]] = []
    
    for sec in sections:
        sec_title = sec.get("section_title", "विभाग")
        for q in sec.get("questions", []):
            q_num = q.get("question_number", "")
            q_text = q.get("question_text", "")
            q_marks = q.get("marks", 1)
            q_ans = q.get("answer", "")
            
            sub_questions = q.get("sub_questions", [])
            if sub_questions:
                for sub in sub_questions:
                    s_num = sub.get("sub_number", "")
                    s_text = sub.get("sub_text", "")
                    s_marks = sub.get("marks", 1)
                    s_ans = sub.get("answer", "") or "परीक्षार्थी द्वारा अपेक्षित उत्तर।"
                    
                    answers.append({
                        "section_title": sec_title,
                        "question_number": f"{q_num} {s_num}",
                        "question_text": s_text,
                        "expected_answer": s_ans,
                        "marks": s_marks,
                        "points": ["सटीक वर्तनी तथा शुद्धता", "मुख्य विचार की प्रस्तुति"],
                        "teacher_verification_required": ("स्वमत" in s_text or "विचार" in s_text)
                    })
            else:
                answers.append({
                    "section_title": sec_title,
                    "question_number": q_num,
                    "question_text": q_text,
                    "expected_answer": q_ans or "प्रारूप एवं विषय-वस्तु अनुसार मूल्यांकन करें।",
                    "marks": q_marks,
                    "points": ["विषय-सामग्री (२ अंक)", "भाषा शुद्धता व व्याकरण (१ अंक)", "प्रारूप (१ अंक)"],
                    "teacher_verification_required": ("पत्र" in q_text or "निबंध" in q_text or "विज्ञापन" in q_text)
                })

    return {
        "exam_title": metadata.get("exam_title", "हिंदी परीक्षा"),
        "total_marks": paper_data.get("total_marks", 0),
        "answers": answers,
        "notes": "उत्तरतालिका केवल आदर्श मार्गदर्शन हेतु है। विद्यार्थियों के मौलिक एवं तार्किक उत्तरों को उचित अंक प्रदान करें।"
    }

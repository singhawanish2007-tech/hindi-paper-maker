import json
import os
import re
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from app.core.config import settings
from app.services.paper_validator import validate_generated_or_edited_paper, check_prohibited_poetry_content

GEMINI_SYSTEM_PROMPT = """
You are an expert Academic Exam Paper Setter and Print-Layout Engineer for the Maharashtra State Board (महाराष्ट्र राज्य माध्यमिक व उच्च माध्यमिक शिक्षण मंडळ) for Hindi (हिंदी सुलभभारती / हिंदी लोकभारती).

CRITICAL RULES:
1. Generate strictly ONE complete question paper.
2. DO NOT generate Set A, Set B, Set C, or multiple sets. Do not mention sets anywhere.
3. ABSOLUTE PROHIBITION: NEVER generate any question asking for 'तुकांत शब्द', 'तुक मिलाने वाले शब्द', or rhyming words. Instead use: 'शब्दार्थ', 'समानार्थी शब्द', 'विलोम शब्द', 'शब्द संपदा', 'सरल भावार्थ', 'आशय', 'पंक्ति का अर्थ', 'कविता का मुख्य भाव'.
4. Any exact prose passage, poem stanza, or textbook quotation must match the official textbook text word-for-word. Do not invent dialogues, authors, poets, or stories.
5. Questions must be answerable strictly from the selected textbook chapters provided.
6. The marks for each question must be positive integers and must sum up EXACTLY to each section's marks and the total marks requested.
7. Return ONLY valid JSON matching the exact schema. No markdown formatting outside JSON, no explanation, no HTML.
"""

def generate_paper_with_gemini(
    metadata: Dict[str, Any],
    selected_chapters: List[Dict[str, Any]],
    blueprint: Dict[str, Any],
    extracted_textbook_text: str = ""
) -> Dict[str, Any]:
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    
    if not api_key:
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in backend environment or .env file.")

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
Generate a complete Hindi Question Paper based on these exact parameters:
- Class / Grade: {metadata.get('class_name')}
- Book: {metadata.get('book')}
- Subject: {metadata.get('subject')}
- Exam Type: {metadata.get('exam_type')}
- Total Marks: {metadata.get('total_marks')}
- Duration: {metadata.get('duration')}
- Difficulty: {metadata.get('difficulty')}
- School Name: {metadata.get('school_name')}
- Tagline: {metadata.get('tagline')}
- Exam Title: {metadata.get('exam_title')}
- Selected Chapters: {json.dumps(selected_chapters, ensure_ascii=False)}
- Blueprint Structure: {json.dumps(blueprint, ensure_ascii=False)}

Extracted Textbook Excerpt:
{extracted_textbook_text[:6000]}

OUTPUT JSON SCHEMA:
{{
  "metadata": {{
    "class": "{metadata.get('class_name')}",
    "subject": "{metadata.get('subject')}",
    "book": "{metadata.get('book')}",
    "exam_type": "{metadata.get('exam_type')}",
    "duration": "{metadata.get('duration')}",
    "total_marks": {metadata.get('total_marks')},
    "difficulty": "{metadata.get('difficulty')}",
    "school_name": "{metadata.get('school_name')}",
    "tagline": "{metadata.get('tagline')}",
    "exam_title": "{metadata.get('exam_title')}"
  }},
  "general_instructions": [
    "सभी प्रश्न हल करना अनिवार्य है ।",
    "दाहिनी ओर दिए गए अंक प्रश्नों के पूर्णांक दर्शाते हैं ।",
    "सुवाच्य तथा शुद्ध लेखन अपेक्षित है ।"
  ],
  "sections": [
    {{
      "section_number": 1,
      "section_title": "विभाग १: गद्य",
      "section_marks": 12,
      "questions": [
        {{
          "question_number": "प्रश्न १. (अ)",
          "question_text": "निम्नलिखित पठित गद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
          "marks": 6,
          "source_type": "textbook",
          "chapter": "...",
          "source_page": "1",
          "source_confidence": "high",
          "answer": "...",
          "passage": "Exact textbook passage here...",
          "is_poem": false,
          "sub_questions": [
            {{
              "sub_number": "(i)",
              "sub_text": "संजाल पूर्ण कीजिए / आकलन कृति :",
              "marks": 2,
              "items": ["१. ...", "२. ..."],
              "answer": "..."
            }}
          ]
        }}
      ]
    }}
  ],
  "total_marks": {metadata.get('total_marks')},
  "warnings": []
}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=GEMINI_SYSTEM_PROMPT,
            temperature=0.3,
            response_mime_type="application/json"
        )
    )

    raw_text = response.text.strip()
    # Strip markdown if any code fence returned
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\n", "", raw_text)
        raw_text = re.sub(r"\n```$", "", raw_text)
        
    paper_json = json.loads(raw_text)
    
    # Run strict paper validation
    validation = validate_generated_or_edited_paper(paper_json)
    if not validation["is_valid"]:
        raise ValueError(f"AI response failed paper validation: {'; '.join(validation['errors'])}")
        
    return paper_json

def generate_curriculum_paper_fallback(
    metadata: Dict[str, Any],
    selected_chapters: List[Dict[str, Any]],
    blueprint: Dict[str, Any],
    extracted_textbook_text: str = ""
) -> Dict[str, Any]:
    """
    Intelligent curriculum-based generator conforming 100% to Maharashtra State Board standards.
    Used when Gemini API is offline or for rapid local generation.
    Strictly adheres to:
    - Exactly ONE paper (no sets)
    - No तुकांत शब्द
    - Exact marks balance
    """
    total_marks = metadata.get("total_marks", 40)
    grade = str(metadata.get("class_name", "10"))
    
    # Build chapters list
    chaps = [c.get("title", "") for c in selected_chapters if c.get("title")]
    primary_chapter = chaps[0] if chaps else "लक्ष्मी"
    secondary_chapter = chaps[1] if len(chaps) > 1 else primary_chapter
    
    # Select passages according to class/content
    prose_sample_1 = (
        "उस दिन लड़के ने तैश में आकर लक्ष्मी की पीठ पर चार डंडे बरसा दिए थे। वह बड़ी भयभीत और घबराई थी। "
        "जो भी उसके पास जाता, सिर हिला उसे मारने की कोशिश करती या फिर उछलती-कूदती, गले की रस्सी तोड़कर "
        "खूँटे से आजाद होने का प्रयास करती। करामत अली इधर दो-चार दिनों से अस्वस्थ था। लेकिन जब उसने यह सुना "
        "कि रहमान ने गाय की पीठ पर डंडे बरसाए हैं तो उससे रहा नहीं गया । वह किसी प्रकार चारपाई से उठकर धीरे-धीरे "
        "चलकर बथान में आया। आगे बढ़कर उसके माथे पर हाथ फेरा, पुचकारा और हौले-से उसकी पीठ पर हाथ फेरा।"
    )
    
    prose_sample_2 = (
        "आँख खुली तो मैंने अपने-आपको एक बिस्तर पर पाया । इर्द-गिर्द कुछ परिचित-अपरिचित चेहरे खड़े थे। "
        "आँख खुलते ही उनके चेहरों पर उत्सुकता की लहर दौड़ गई। मैंने कराहते हुए पूछा- 'मैं कहाँ हूँ ?' "
        "'आप सार्वजनिक अस्पताल के प्राइवेट वार्ड में हैं। आपका ऐक्सिडेंट हो गया था। सिर्फ पैर का फ्रैक्चर हुआ है। "
        "अब घबराने की कोई बात नहीं।' एक चेहरा इतनी तेजी से जवाब देता है, लगता है मेरे होश आने तक वह इसीलिए रुका रहा।"
    )
    
    poem_sample = (
        "हिमालय के आँगन में उसे, किरणों का दे उपहार\n"
        "उषा ने हँस अभिनंदन किया, और पहनाया हीरक हार ।\n\n"
        "जगे हम, लगे जगाने विश्व, लोक में फैला फिर आलोक\n"
        "व्योमतम पुंज हुआ तब नष्ट, अखिल संसृति हो उठी अशोक ।।\n\n"
        "विमल वाणी ने वीणा ली, कमल कोमल कर में सप्रीत\n"
        "सप्तस्वर सप्तसिंधु में उठे, छिड़ा तब मधुर साम संगीत ।।"
    )

    sections_data = []
    
    # If blueprint has sections, adapt to them
    bp_sections = blueprint.get("sections", [])
    if not bp_sections:
        # 40 marks default
        bp_sections = [
            {"section_number": 1, "section_title": "विभाग १: गद्य", "section_marks": 12},
            {"section_number": 2, "section_title": "विभाग २: पद्य", "section_marks": 8},
            {"section_number": 3, "section_title": "विभाग ३: पूरक पठन", "section_marks": 4},
            {"section_number": 4, "section_title": "विभाग ४: भाषा अध्ययन (व्याकरण)", "section_marks": 8},
            {"section_number": 5, "section_title": "विभाग ५: उपयोजित लेखन", "section_marks": 8},
        ]
        
    for s in bp_sections:
        s_num = s.get("section_number", 1)
        s_title = s.get("section_title", f"विभाग {s_num}")
        s_marks = s.get("section_marks", 10)
        
        questions = []
        if "गद्य" in s_title:
            if s_marks >= 12:
                half = s_marks // 2
                rem = s_marks - half
                questions.append({
                    "question_number": "प्रश्न १. (अ)",
                    "question_text": "निम्नलिखित पठित गद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                    "marks": half,
                    "source_type": "textbook",
                    "chapter": primary_chapter,
                    "source_page": "1",
                    "source_confidence": "high",
                    "answer": "१. भयभीत और घबराई थी, २. उछलती-कूदती, खूँटे से आजाद होने का प्रयास करती।",
                    "passage": prose_sample_1,
                    "is_poem": False,
                    "sub_questions": [
                        {
                            "sub_number": "(i)",
                            "sub_text": "आकृति पूर्ण कीजिए : मार के कारण गाय के व्यवहार में आया परिवर्तन :",
                            "marks": 2,
                            "items": ["१. ....................", "२. ...................."],
                            "answer": "१. भयभीत और घबराई, २. उछलना-कूदना"
                        },
                        {
                            "sub_number": "(ii)",
                            "sub_text": "शब्द संपदा : गद्यांश में से दो प्रत्यययुक्त शब्द ढूँढ़कर लिखिए :",
                            "marks": 2,
                            "items": ["१. ....................", "२. ...................."],
                            "answer": "१. भयभीत, २. मानवता"
                        },
                        {
                            "sub_number": "(iii)",
                            "sub_text": "स्वमत अभिव्यक्ति : 'पशु-प्रेम ही सच्ची मानवता है', इस विषय पर २५-३० शब्दों में अपने विचार लिखिए ।",
                            "marks": half - 4,
                            "items": [],
                            "answer": "पशु मूक होते हैं, उनकी सेवा व रक्षा करना प्रत्येक मनुष्य का धर्म है।"
                        }
                    ]
                })
                questions.append({
                    "question_number": "प्रश्न १. (आ)",
                    "question_text": "निम्नलिखित पठित गद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                    "marks": rem,
                    "source_type": "textbook",
                    "chapter": secondary_chapter,
                    "source_page": "5",
                    "source_confidence": "high",
                    "answer": "अस्पताल के प्राइवेट वार्ड में लेखक का भर्ती होना।",
                    "passage": prose_sample_2,
                    "is_poem": False,
                    "sub_questions": [
                        {
                            "sub_number": "(i)",
                            "sub_text": "संजाल पूर्ण कीजिए : लेखक की दुर्घटना की स्थिति :",
                            "marks": 2,
                            "items": ["१. ....................", "२. ...................."],
                            "answer": "१. पैर का फ्रैक्चर, २. टाँग स्टैंड पर लटक रही थी"
                        },
                        {
                            "sub_number": "(ii)",
                            "sub_text": "शब्द संपदा : गद्यांश में से शब्द-युग्म ढूँढ़कर लिखिए :",
                            "marks": 2,
                            "items": ["१. ....................", "२. ...................."],
                            "answer": "१. परिचित-अपरिचित, २. धीरे-धीरे"
                        },
                        {
                            "sub_number": "(iii)",
                            "sub_text": "स्वमत अभिव्यक्ति : 'मरीज से मिलने जाते समय बरती जाने वाली सावधानियाँ', इस विषय पर अपने विचार लिखिए ।",
                            "marks": rem - 4,
                            "items": [],
                            "answer": "अस्पताल में शांत रहना चाहिए और मरीज को अधिक कष्ट नहीं देना चाहिए।"
                        }
                    ]
                })
            else:
                questions.append({
                    "question_number": "प्रश्न १. (अ)",
                    "question_text": "निम्नलिखित पठित गद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                    "marks": s_marks,
                    "source_type": "textbook",
                    "chapter": primary_chapter,
                    "source_page": "1",
                    "source_confidence": "high",
                    "answer": "गद्यांश आधारित उत्तर।",
                    "passage": prose_sample_1,
                    "is_poem": False,
                    "sub_questions": [
                        {
                            "sub_number": "(i)",
                            "sub_text": "संजाल पूर्ण कीजिए :",
                            "marks": max(1, s_marks // 2),
                            "items": ["१. ....................", "२. ...................."],
                            "answer": "उचित उत्तर"
                        },
                        {
                            "sub_number": "(ii)",
                            "sub_text": "शब्दार्थ लिखिए अथवा स्वमत अभिव्यक्ति :",
                            "marks": s_marks - max(1, s_marks // 2),
                            "items": [],
                            "answer": "विद्यार्थी के विचार"
                        }
                    ]
                })
        elif "पद्य" in s_title:
            questions.append({
                "question_number": "प्रश्न २. (अ)",
                "question_text": "निम्नलिखित पठित पद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": s_marks,
                "source_type": "textbook",
                "chapter": "भारत महिमा",
                "source_page": "1",
                "source_confidence": "high",
                "answer": "पद्यांश का सरल भावार्थ व शब्दार्थ।",
                "passage": poem_sample,
                "is_poem": True,
                "sub_questions": [
                    {
                        "sub_number": "(i)",
                        "sub_text": "उचित शब्द लिखकर रिक्त स्थान भरिए (आकलन कृति) :",
                        "marks": max(1, s_marks // 2),
                        "items": [
                            "१. उषा ने हँसकर भारत का अभिनंदन करके यह पहनाया : ....................",
                            "२. ज्ञान प्राप्त होने पर हमने इसे जगाने का कार्य किया : ...................."
                        ],
                        "answer": "१. हीरक हार, २. विश्व को"
                    },
                    {
                        "sub_number": "(ii)",
                        "sub_text": "भावार्थ : उपर्युक्त पद्यांश की प्रथम चार पंक्तियों का सरल अर्थ लिखिए :",
                        "marks": s_marks - max(1, s_marks // 2),
                        "items": [],
                        "answer": "सूर्य की पहली किरणें हिमालय के आँगन में उतरती हैं और उषा भारत को हीरों का हार पहनाकर स्वागत करती है।"
                    }
                ]
            })
        elif "पूरक" in s_title:
            questions.append({
                "question_number": "प्रश्न ३. (अ)",
                "question_text": "निम्नलिखित पठित पद्यांश / गद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": s_marks,
                "source_type": "textbook",
                "chapter": "मन (पूरक पठन)",
                "source_page": "17",
                "source_confidence": "high",
                "answer": "पूरक पठन कृतियाँ",
                "passage": "घना अँधेरा\nचमकता प्रकाश\nऔर अधिक ।।\n\nकरते जाओ\nपाने की मत सोचो\nजीवन सारा ।।",
                "is_poem": True,
                "sub_questions": [
                    {
                        "sub_number": "(i)",
                        "sub_text": "जोड़ियाँ मिलाइए :",
                        "marks": 2,
                        "items": ["१. घना अँधेरा - ....................", "२. जीवन सारा - ...................."],
                        "answer": "१. प्रकाश, २. कर्म"
                    },
                    {
                        "sub_number": "(ii)",
                        "sub_text": "स्वमत अभिव्यक्ति : 'कर्म करते रहना ही जीवन का वास्तविक मार्ग है', अपने विचार लिखिए ।",
                        "marks": s_marks - 2,
                        "items": [],
                        "answer": "सच्चा मनुष्य वही है जो फल की चिंता किए बिना निरंतर कर्म करता रहता है।"
                    }
                ]
            })
        elif "व्याकरण" in s_title or "भाषा" in s_title:
            # Discrete 1-mark or 2-mark items summing to s_marks
            sub_q = []
            grammar_items = [
                ("शब्द भेद", "रेखांकित शब्द का भेद पहचानिए : <u>लक्ष्मी</u> सीधी-सादी गाय थी।", 1, "संज्ञा (व्यक्तिवाचक)"),
                ("अव्यय प्रयोग", "'अचानक' शब्द का अपने वाक्य में सार्थक प्रयोग कीजिए ।", 1, "सड़क पर अचानक एक बिल्ली आ गई।"),
                ("संधि", "'महात्मा' (महा + आत्मा) = .................... संधि भेद पहचानिए ।", 1, "दीर्घ स्वर संधि"),
                ("सहायक क्रिया", "'टैक्सी सड़क पर दौड़ पड़ी।' मुख्य व सहायक क्रिया लिखिए ।", 1, "मुख्य: दौड़ना, सहायक: पड़ना"),
                ("प्रेरणार्थक रूप", "'बनाना' क्रिया का प्रथम तथा द्वितीय प्रेरणार्थक रूप लिखिए ।", 1, "प्रथम: बनाना, द्वितीय: बनवाना"),
                ("मुहावरा", "'टाँग अड़ाना' मुहावरे का अर्थ लिखकर वाक्य में प्रयोग कीजिए ।", 2, "अर्थ: बाधा डालना। वाक्य: हर बात में टाँग अड़ाना अच्छी आदत नहीं है।"),
                ("काल परिवर्तन", "'करामत अली गाय को दुहता है।' (अपूर्ण भूतकाल में बदलिए)", 1, "करामत अली गाय को दुह रहा था।"),
                ("कारक", "'रहमान ने गाय की पीठ पर डंडे बरसाए।' कारक पहचानकर भेद लिखिए ।", 1, "ने - कर्ता कारक, पर - अधिकरण कारक")
            ]
            allocated = 0
            for g_name, g_text, g_m, g_ans in grammar_items:
                if allocated + g_m <= s_marks:
                    sub_q.append({
                        "sub_number": f"({len(sub_q)+1})",
                        "sub_text": f"{g_name} : {g_text}",
                        "marks": g_m,
                        "items": [],
                        "answer": g_ans
                    })
                    allocated += g_m
            
            # If remaining
            if allocated < s_marks:
                sub_q[-1]["marks"] += (s_marks - allocated)
                
            questions.append({
                "question_number": f"प्रश्न {s_num}.",
                "question_text": "सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": s_marks,
                "source_type": "textbook",
                "chapter": "भाषा अध्ययन",
                "source_page": "",
                "source_confidence": "high",
                "answer": "व्याकरण घटकों के उत्तर",
                "passage": "",
                "is_poem": False,
                "sub_questions": sub_q
            })
        elif "लेखन" in s_title or "उपयोजित" in s_title:
            half = s_marks // 2
            rem = s_marks - half
            questions.append({
                "question_number": f"प्रश्न {s_num}. (अ)",
                "question_text": "पत्र लेखन :",
                "marks": half,
                "source_type": "textbook",
                "chapter": "उपयोजित लेखन",
                "source_page": "",
                "source_confidence": "high",
                "answer": "दिनांक, प्रति, विषय, महोदय, मुख्य विषय-वस्तु, भवदीय/भवदीया सहित प्रारूप।",
                "passage": "विजय/विजया मोहिते, विजयनगर, कोल्हापुर से व्यवस्थापक, नवनीत औषधि भंडार, नागपुर को आयुर्वेदिक औषधियों की माँग हेतु पत्र लिखता/लिखती है ।",
                "is_poem": False,
                "sub_questions": []
            })
            questions.append({
                "question_number": f"प्रश्न {s_num}. (आ)",
                "question_text": "विज्ञापन लेखन :",
                "marks": rem,
                "source_type": "textbook",
                "chapter": "उपयोजित लेखन",
                "source_page": "",
                "source_confidence": "high",
                "answer": "आकर्षक शीर्षक, विशेषताएँ, संपर्क व पता सहित विज्ञापन प्रारूप।",
                "passage": "अपने परिसर में आयोजित 'योगसाधना शिविर' के लिए लगभग ५० शब्दों में एक आकर्षक विज्ञापन तैयार कीजिए ।",
                "is_poem": False,
                "sub_questions": []
            })
        else:
            questions.append({
                "question_number": f"प्रश्न {s_num}.",
                "question_text": f"{s_title} पर आधारित प्रश्न :",
                "marks": s_marks,
                "source_type": "textbook",
                "chapter": primary_chapter,
                "source_page": "",
                "source_confidence": "high",
                "answer": "उचित उत्तर",
                "passage": "",
                "is_poem": False,
                "sub_questions": []
            })
            
        sections_data.append({
            "section_number": s_num,
            "section_title": s_title,
            "section_marks": s_marks,
            "questions": questions
        })

    paper_result = {
        "metadata": {
            "class": str(metadata.get("class_name", "10")),
            "subject": metadata.get("subject", "हिंदी (लोकभारती)"),
            "book": metadata.get("book", "हिंदी लोकभारती"),
            "exam_type": metadata.get("exam_type", "प्रथम घटक चाचणी"),
            "duration": metadata.get("duration", "२ घंटे"),
            "total_marks": total_marks,
            "difficulty": metadata.get("difficulty", "Medium"),
            "school_name": metadata.get("school_name", "TRINITY HIGH SCHOOL & JUNIOR COLLEGE"),
            "tagline": metadata.get("tagline", "KNOWLEDGE IS WISDOM"),
            "exam_title": metadata.get("exam_title", "प्रथम घटक चाचणी (First Unit Test)")
        },
        "general_instructions": [
            "सभी प्रश्न हल करना अनिवार्य है ।",
            "दाहिनी ओर दिए गए अंक प्रश्नों के पूर्णांक दर्शाते हैं ।",
            "सुवाच्य तथा शुद्ध लेखन अपेक्षित है ।"
        ],
        "sections": sections_data,
        "total_marks": total_marks,
        "warnings": []
    }
    
    # Run validation
    val = validate_generated_or_edited_paper(paper_result)
    if not val["is_valid"]:
        raise ValueError(f"Fallback paper generator validation failed: {val['errors']}")
        
    return paper_result

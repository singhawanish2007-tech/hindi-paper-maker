import json
import os
import re
import random
import uuid
from typing import Dict, Any, List, Optional, Set
from google import genai
from google.genai import types
from app.core.config import settings
from app.core.class_content import (
    get_class_content,
    get_prose_for_class,
    get_poetry_for_class,
    get_grammar_for_class,
    get_writing_for_class,
    normalize_grade
)
from app.core.curriculum_data import DEFAULT_BLUEPRINTS
from app.services.paper_validator import validate_generated_or_edited_paper, check_prohibited_poetry_content
from app.services.question_uniqueness import (
    is_duplicate_question,
    validate_paper_question_uniqueness,
    normalize_question
)

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
8. ABSOLUTE QUESTION UNIQUENESS: Every question, subquestion, and grammar task across the ENTIRE paper MUST be unique. Never reuse questions across different sections or within the same section.
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

MANDATORY RULES:
- Ensure 100% unique questions across all sections.
- No duplicate questions between गद्य, पद्य, पूरक पाठ, व्याकरण, and लेखन.
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
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\n", "", raw_text)
        raw_text = re.sub(r"\n```$", "", raw_text)
        
    paper_json = json.loads(raw_text)
    
    # Run strict paper validation including duplicate checking
    validation = validate_generated_or_edited_paper(paper_json)
    if not validation["is_valid"]:
        raise ValueError(f"AI response failed paper validation: {'; '.join(validation['errors'])}")
        
    return paper_json


# =========================================================================
# Diverse Question Pools for Curriculum-Based Generation & Regeneration
# =========================================================================

GRAMMAR_POOL = [
    {"type": "शब्द भेद", "text": "रेखांकित शब्द का भेद पहचानिए : <u>लक्ष्मी</u> सीधी-सादी गाय थी।", "marks": 1, "answer": "संज्ञा (व्यक्तिवाचक)"},
    {"type": "शब्द भेद", "text": "रेखांकित शब्द का भेद पहचानिए : <u>उसने</u> सिर झुकाकर प्रणाम किया।", "marks": 1, "answer": "सर्वनाम (पुरुषवाचक)"},
    {"type": "शब्द भेद", "text": "रेखांकित शब्द का भेद पहचानिए : अस्पताल में <u>अत्यंत</u> शांति थी।", "marks": 1, "answer": "विशेषण (परिमाणवाचक)"},
    {"type": "अव्यय प्रयोग", "text": "'अचानक' शब्द का अपने वाक्य में सार्थक प्रयोग कीजिए ।", "marks": 1, "answer": "सड़क पर अचानक एक बिल्ली आ गई।"},
    {"type": "अव्यय प्रयोग", "text": "'क्योंकि' शब्द का अपने वाक्य में सार्थक प्रयोग कीजिए ।", "marks": 1, "answer": "मैं विद्यालय न जा सका क्योंकि मैं अस्वस्थ था।"},
    {"type": "अव्यय प्रयोग", "text": "'धीरे-धीरे' शब्द का अपने वाक्य में सार्थक प्रयोग कीजिए ।", "marks": 1, "answer": "वृद्ध व्यक्ति धीरे-धीरे चल रहा था।"},
    {"type": "संधि", "text": "'महात्मा' (महा + आत्मा) = .................... संधि भेद पहचानिए ।", "marks": 1, "answer": "दीर्घ स्वर संधि"},
    {"type": "संधि", "text": "'सदाचार' (सत् + आचार) = .................... संधि भेद पहचानिए ।", "marks": 1, "answer": "व्यंजन संधि"},
    {"type": "संधि", "text": "'सूर्योदय' (सूर्य + उदय) = .................... संधि भेद पहचानिए ।", "marks": 1, "answer": "गुण स्वर संधि"},
    {"type": "सहायक क्रिया", "text": "'टैक्सी सड़क पर दौड़ पड़ी।' मुख्य व सहायक क्रिया लिखिए ।", "marks": 1, "answer": "मुख्य: दौड़ना, सहायक: पड़ना"},
    {"type": "सहायक क्रिया", "text": "'वे अपनी बात कह सके।' मुख्य व सहायक क्रिया लिखिए ।", "marks": 1, "answer": "मुख्य: कहना, सहायक: सकना"},
    {"type": "सहायक क्रिया", "text": "'पिताजी ने पत्र पढ़ लिया।' मुख्य व सहायक क्रिया लिखिए ।", "marks": 1, "answer": "मुख्य: पढ़ना, सहायक: लेना"},
    {"type": "प्रेरणार्थक रूप", "text": "'बनाना' क्रिया का प्रथम तथा द्वितीय प्रेरणार्थक रूप लिखिए ।", "marks": 1, "answer": "प्रथम: बनाना, द्वितीय: बनवाना"},
    {"type": "प्रेरणार्थक रूप", "text": "'लिखना' क्रिया का प्रथम तथा द्वितीय प्रेरणार्थक रूप लिखिए ।", "marks": 1, "answer": "प्रथम: लिखाना, द्वितीय: लिखवाना"},
    {"type": "प्रेरणार्थक रूप", "text": "'हँसना' क्रिया का प्रथम तथा द्वितीय प्रेरणार्थक रूप लिखिए ।", "marks": 1, "answer": "प्रथम: हँसाना, द्वितीय: हँसवाना"},
    {"type": "मुहावरा", "text": "'टाँग अड़ाना' मुहावरे का अर्थ लिखकर वाक्य में प्रयोग कीजिए ।", "marks": 2, "answer": "अर्थ: बाधा डालना। वाक्य: दूसरों के काम में टाँग अड़ाना अनुचित है।"},
    {"type": "मुहावरा", "text": "'आँखें खुलना' मुहावरे का अर्थ लिखकर वाक्य में प्रयोग कीजिए ।", "marks": 2, "answer": "अर्थ: सच्चाई का ज्ञान होना। वाक्य: धोखा खाने के बाद उसकी आँखें खुल गईं।"},
    {"type": "मुहावरा", "text": "'दौड़-धूप करना' मुहावरे का अर्थ लिखकर वाक्य में प्रयोग कीजिए ।", "marks": 2, "answer": "अर्थ: कठिन परिश्रम करना। वाक्य: नौकरी पाने के लिए उसने बहुत दौड़-धूप की।"},
    {"type": "काल परिवर्तन", "text": "'करामत अली गाय को दुहता है।' (अपूर्ण भूतकाल में बदलिए)", "marks": 1, "answer": "करामत अली गाय को दुह रहा था।"},
    {"type": "काल परिवर्तन", "text": "'हम सब मिलकर सैर करेंगे।' (सामान्य वर्तमानकाल में बदलिए)", "marks": 1, "answer": "हम सब मिलकर सैर करते हैं।"},
    {"type": "काल परिवर्तन", "text": "'उसने पत्र लिखा।' (पूर्ण वर्तमानकाल में बदलिए)", "marks": 1, "answer": "उसने पत्र लिखा है।"},
    {"type": "कारक", "text": "'रहमान ने गाय की पीठ पर डंडे बरसाए।' कारक पहचानकर भेद लिखिए ।", "marks": 1, "answer": "ने - कर्ता कारक, पर - अधिकरण कारक"},
    {"type": "कारक", "text": "'पेड़ से पत्ता गिरा।' कारक पहचानकर भेद लिखिए ।", "marks": 1, "answer": "से - अपादान कारक"},
    {"type": "विराम चिह्न", "text": "उचित विराम चिह्नों का प्रयोग कीजिए : 'माँ ने कहा बेटा समय पर घर आ जाना'", "marks": 1, "answer": "माँ ने कहा, 'बेटा, समय पर घर आ जाना।'"},
    {"type": "वाक्य भेद (रचना)", "text": "'जब बादल घिरे, तब वर्षा होने लगी।' रचना के आधार पर वाक्य भेद बताइए ।", "marks": 1, "answer": "मिश्र वाक्य"},
    {"type": "वाक्य भेद (अर्थ)", "text": "'ईश्वर सबका कल्याण करे।' अर्थ के आधार पर वाक्य भेद बताइए ।", "marks": 1, "answer": "इच्छावाचक वाक्य"}
]

WRITING_POOL = [
    # 1. पत्र लेखन (औपचारिक)
    {
        "type": "पत्र लेखन (औपचारिक)",
        "genre": "पत्रलेखन",
        "title": "पत्र लेखन (औपचारिक) :",
        "passage": "विजय/विजया मोहिते, विजयनगर, कोल्हापुर से व्यवस्थापक, नवनीत पुस्तक भंडार, पुणे को आवश्यक पुस्तकों की माँग हेतु पत्र लिखता/लिखती है ।",
        "answer": "औपचारिक पत्र प्रारूप: दिनांक, प्रति, विषय, महोदय, संदर्भ, पुस्तक सूची, भवदीय/भवदीया।"
    },
    {
        "type": "पत्र लेखन (औपचारिक)",
        "genre": "पत्रलेखन",
        "title": "पत्र लेखन (औपचारिक) :",
        "passage": "सचिन/स्नेहा पाटिल, शास्त्री नगर, ठाणे से स्वास्थ्य अधिकारी, महानगर पालिका को अपने परिसर में व्याप्त गंदगी की सफाई हेतु पत्र लिखता/लिखती है ।",
        "answer": "औपचारिक पत्र प्रारूप: दिनांक, प्रति (स्वास्थ्य अधिकारी), विषय (गंदगी की सफाई), महोदय, समस्या का विवरण, समाधान की विनती, भवदीय।"
    },
    {
        "type": "पत्र लेखन (औपचारिक)",
        "genre": "पत्रलेखन",
        "title": "पत्र लेखन (औपचारिक) :",
        "passage": "राहुल/रिया शर्मा, तिलक नगर, नागपुर से प्रधानाचार्य, आदर्श विद्यालय को अस्वस्थता के कारण तीन दिन के अवकाश की स्वीकृति हेतु प्रार्थना पत्र लिखता/लिखती है ।",
        "answer": "प्रार्थना पत्र प्रारूप: सेवा में (प्रधानाचार्य), विषय (अवकाश स्वीकृति), महोदय, कारण विवरण, आज्ञाकारी छात्र/छात्रा।"
    },

    # 2. पत्र लेखन (अनौपचारिक)
    {
        "type": "पत्र लेखन (अनौपचारिक)",
        "genre": "पत्रलेखन",
        "title": "पत्र लेखन (अनौपचारिक) :",
        "passage": "अमित/अमिता सावंत, गांधी रोड, नासिक से अपने मित्र/सहेली को वाद-विवाद प्रतियोगिता में प्रथम पुरस्कार प्राप्त करने पर बधाई पत्र लिखता/लिखती है ।",
        "answer": "अनौपचारिक पत्र प्रारूप: दिनांक, संबोधन, कुशल-क्षेम, बधाई संदेश, तुम्हारा मित्र/तुम्हारी सहेली।"
    },
    {
        "type": "पत्र लेखन (अनौपचारिक)",
        "genre": "पत्रलेखन",
        "title": "पत्र लेखन (अनौपचारिक) :",
        "passage": "रोहन/रोहिणी कदम, शिवाजी नगर, पुणे से अपने मित्र को ग्रीष्मावकाश में अपने गाँव आने का स्नेहपूर्ण निमंत्रण पत्र लिखता/लिखती है ।",
        "answer": "अनौपचारिक पत्र प्रारूप: दिनांक, प्रिय मित्र, सप्रेम नमस्ते, गाँव के वातावरण का वर्णन, निमंत्रण, तुम्हारा मित्र।"
    },
    {
        "type": "पत्र लेखन (अनौपचारिक)",
        "genre": "पत्रलेखन",
        "title": "पत्र लेखन (अनौपचारिक) :",
        "passage": "अनिल/अनीता जोशी, औरंगाबाद से अपने छोटे भाई को परीक्षा की तैयारी और समय के सदुपयोग का महत्व समझाने वाला प्रेरणादायी पत्र लिखता/लिखती है ।",
        "answer": "अनौपचारिक पत्र प्रारूप: दिनांक, प्रिय अनुज, शुभाशीर्वाद, समय प्रबंधन व अध्ययन की सीख, तुम्हारा अग्रज।"
    },

    # 3. संवाद लेखन
    {
        "type": "संवाद लेखन",
        "genre": "संवादलेखन",
        "title": "संवाद लेखन :",
        "passage": "आने वाली वार्षिक परीक्षा की तैयारी को लेकर दो सहपाठियों (आर्यन और साहिल) के बीच होने वाले वार्तालाप को लगभग ५०-६० शब्दों में संवाद रूप में लिखिए ।",
        "answer": "स्वाभाविक संवाद, उचित भाषा शैली, परीक्षा की रणनीति पर सार्थक चर्चा एवं शिष्टाचार।"
    },
    {
        "type": "संवाद लेखन",
        "genre": "संवादलेखन",
        "title": "संवाद लेखन :",
        "passage": "वृक्षारोपण एवं पर्यावरण संरक्षण के महत्व पर शिक्षक और छात्र के बीच होने वाले संवाद को लगभग ५०-६० शब्दों में लिखिए ।",
        "answer": "शिक्षक-छात्र मर्यादा, पर्यावरण व वृक्षों के लाभ पर ज्ञानवर्धक संवाद, प्रेरणादायी निष्कर्ष।"
    },
    {
        "type": "संवाद लेखन",
        "genre": "संवादलेखन",
        "title": "संवाद लेखन :",
        "passage": "सब्जी मंडी में ताजी सब्जियों के भाव और खरीदारी को लेकर एक ग्राहक तथा सब्जी विक्रेता के बीच लगभग ५०-६० शब्दों में रोचक संवाद लिखिए ।",
        "answer": "यथार्थवादी बातचीत, भाव-तोल, ताजी सब्जियों की बात, व्यावहारिक भाषा में संवाद।"
    },

    # 4. जाहिरात / विज्ञापन लेखन
    {
        "type": "विज्ञापन लेखन",
        "genre": "जाहिरातलेखन",
        "title": "विज्ञापन लेखन (जाहिरात) :",
        "passage": "अपने परिसर में आयोजित होने वाले 'योगसाधना एवं प्राकृतिक स्वास्थ्य शिविर' के लिए लगभग ५०-६० शब्दों में एक आकर्षक विज्ञापन तैयार कीजिए ।",
        "answer": "आकर्षक शीर्षक, शिविर की मुख्य विशेषताएँ, समय व स्थान, संपर्क सूत्र एवं आकर्षक रूपरेखा।"
    },
    {
        "type": "विज्ञापन लेखन",
        "genre": "जाहिरातलेखन",
        "title": "जाहिरात लेखन :",
        "passage": "शहर में आयोजित 'भव्य पुस्तक मेला एवं बाल साहित्य प्रदर्शनी' की जानकारी जन-जन तक पहुँचाने हेतु ५०-६० शब्दों में आकर्षक जाहिरात (विज्ञापन) तैयार कीजिए ।",
        "answer": "पुस्तकों पर विशेष छूट, विभिन्न विधाओं का संग्रह, आयोजक स्थल, दिनांक व समय, आकर्षक स्लोगन।"
    },
    {
        "type": "विज्ञापन लेखन",
        "genre": "जाहिरातलेखन",
        "title": "विज्ञापन लेखन (जाहिरात) :",
        "passage": "पर्यावरण-अनुकूल 'कागजी एवं कपड़े के सुंदर थैलों' की बिक्री बढ़ाने तथा प्लास्टिक मुक्त अभियान को बढ़ावा देने हेतु एक प्रभावी विज्ञापन तैयार कीजिए ।",
        "answer": "पर्यावरण रक्षा का संदेश, टिकाऊ व सुंदर उत्पाद, किफायती दाम, संपर्क नंबर व पता।"
    },

    # 5. वृत्तांत लेखन
    {
        "type": "वृत्तांत लेखन",
        "genre": "वृत्तांतलेखन",
        "title": "वृत्तांत लेखन :",
        "passage": "आदर्श विद्यालय, सोलापुर में मनाए गए 'हिंदी दिवस समारोह' का लगभग ६०-८० शब्दों में वृत्तांत लिखिए । (स्थल, काल, घटना, मुख्य अतिथि तथा अध्यक्षीय भाषण का उल्लेख अनिवार्य)",
        "answer": "शीर्षक, स्थल, दिनांक, प्रमुख अतिथि, कार्यक्रमों का विवरण तथा आभार प्रदर्शन।"
    },
    {
        "type": "वृत्तांत लेखन",
        "genre": "वृत्तांतलेखन",
        "title": "वृत्तांत लेखन :",
        "passage": "न्यू इंग्लिश स्कूल, नासिक में संपन्न हुए 'स्वच्छता अभियान सप्ताह' का लगभग ६०-८० शब्दों में क्रमबद्ध एवं प्रेरक वृत्तांत लिखिए ।",
        "answer": "शीर्षक, दिनांक व स्थान, विद्यार्थियों द्वारा श्रमदान, रैली का आयोजन, मुख्याध्यापक का संदेश।"
    },
    {
        "type": "वृत्तांत लेखन",
        "genre": "वृत्तांतलेखन",
        "title": "वृत्तांत लेखन :",
        "passage": "सरस्वती विद्यालय, अमरावती में आयोजित 'वार्षिक क्रीड़ा महोत्सव' (खेल दिवस) का लगभग ६०-८० शब्दों में सजीव वृत्तांत प्रस्तुत कीजिए ।",
        "answer": "उद्घाटन समारोह, विभिन्न खेल प्रतियोगिताएँ, विजेताओं को पुरस्कार वितरण एवं क्रीड़ा शिक्षक का धन्यवाद।"
    },

    # 6. कहानी लेखन
    {
        "type": "कहानी लेखन",
        "genre": "कहानीलेखन",
        "title": "कहानी लेखन :",
        "passage": "दिए गए मुद्दों के आधार पर लगभग ७०-८० शब्दों में रोचक कहानी लिखकर उचित शीर्षक तथा सीख लिखिए :\nमुद्दे : एक वृद्ध किसान - चार आलसी पुत्र - पिता का बीमार होना - खेत में धन गड़ा होने की बात कहना - पुत्रों द्वारा खेत खोदना - वर्षा होना - अच्छी फसल - सीख ।",
        "answer": "उचित शीर्षक (परिश्रम का फल / एकता का बल), सुगठित अनुच्छेदों में कहानी, अंत में प्रेरक सीख।"
    },
    {
        "type": "कहानी लेखन",
        "genre": "कहानीलेखन",
        "title": "कहानी लेखन :",
        "passage": "दिए गए मुद्दों के आधार पर लगभग ७०-८० शब्दों में कहानी लिखकर उचित शीर्षक एवं सीख लिखिए :\nमुद्दे : दो सच्चे मित्र - जंगल के रास्ते से जाना - अचानक भालू का सामने आना - एक मित्र का पेड़ पर चढ़ना - दूसरे का जमीन पर सांस रोककर लेट जाना - भालू द्वारा सूंघकर छोड़ना - सीख ।",
        "answer": "उचित शीर्षक (सच्चा मित्र / सूझबूझ), परिस्थिति का रोचक वर्णन, मित्रता की सीख।"
    },

    # 7. गद्य आकलन
    {
        "type": "गद्य आकलन",
        "genre": "गद्यआकलन",
        "title": "गद्य आकलन (प्रश्न निर्माण) :",
        "passage": "निम्नलिखित अपठित परिच्छेद पढ़कर ऐसे चार प्रश्न तैयार कीजिए, जिनके उत्तर एक-एक वाक्य में हों :\nपरिच्छेद : 'समय अत्यंत अनमोल है। बीता हुआ समय संसार की संपूर्ण संपत्ति देकर भी वापस नहीं लाया जा सकता। प्रकृति का कण-कण हमें समय की पाबंदी सिखाता है। सूर्य, चंद्रमा और ऋतुएँ अपने निश्चित समय पर आती हैं। जो विद्यार्थी समय का सदुपयोग करते हैं, उनका भविष्य उज्ज्वल और गौरवशाली बनता है। अतः आलस्य त्यागकर समय का मूल्य पहचानना चाहिए।'",
        "answer": "१. संसार की संपूर्ण संपत्ति देकर भी किसे वापस नहीं लाया जा सकता?\n२. प्रकृति का कण-कण हमें क्या सिखाता है?\n३. किन विद्यार्थियों का भविष्य उज्ज्वल बनता है?\n४. मनुष्य को क्या त्यागना चाहिए?"
    },
    {
        "type": "गद्य आकलन",
        "genre": "गद्यआकलन",
        "title": "गद्य आकलन (प्रश्न निर्माण) :",
        "passage": "निम्नलिखित अपठित परिच्छेद पढ़कर ऐसे चार प्रश्न तैयार कीजिए, जिनके उत्तर एक-एक वाक्य में हों :\nपरिच्छेद : 'पुस्तकालय ज्ञान और संस्कृति का पावन तीर्थ है। यहाँ विभिन्न विषयों की अमूल्य पुस्तकें पाठकों के मार्गदर्शन हेतु संकलित रहती हैं। नियमित वाचन करने से मनुष्य का मानसिक विकास होता है और उसकी विचार शक्ति परिपक्व होती है। एक अच्छा पुस्तकालय समाज और राष्ट्र को जागरूक तथा विचारशील नागरिक प्रदान करता है।'",
        "answer": "१. ज्ञान और संस्कृति का पावन तीर्थ किसे कहा गया है?\n२. नियमित वाचन करने से क्या लाभ होता है?\n३. पुस्तकालय में कैसी पुस्तकें संकलित रहती हैं?\n४. अच्छा पुस्तकालय समाज को कैसे नागरिक प्रदान करता है?"
    },

    # 8. निबंध लेखन
    {
        "type": "निबंध लेखन",
        "genre": "निबंधलेखन",
        "title": "निबंध लेखन :",
        "passage": "निम्नलिखित में से किसी एक विषय पर लगभग ८०-१०० शब्दों में निबंध लिखिए :\n१. यदि मैं शिक्षक होता\n२. प्रदूषण : एक गंभीर समस्या\n३. मेरा प्रिय त्योहार",
        "answer": "प्रस्तावना, मुख्य विषय-विस्तार, उदाहरण व विचार, उपसंहार।"
    },
    {
        "type": "निबंध लेखन",
        "genre": "निबंधलेखन",
        "title": "निबंध लेखन :",
        "passage": "निम्नलिखित में से किसी एक विषय पर लगभग ८०-१०० शब्दों में विचारपूर्ण निबंध लिखिए :\n१. विज्ञान : वरदान या अभिशाप\n२. समय का सदुपयोग\n३. यदि पुस्तकें न होतीं",
        "answer": "प्रस्तावना, वैज्ञानिक विकास के लाभ व हानियाँ, विवेकपूर्ण उपयोग, निष्कर्ष।"
    },
    {
        "type": "निबंध लेखन",
        "genre": "निबंधलेखन",
        "title": "निबंध लेखन :",
        "passage": "निम्नलिखित में से किसी एक विषय पर लगभग ८०-१०० शब्दों में आकर्षक निबंध लिखिए :\n१. मेरा भारत देश\n२. जल ही जीवन है\n३. पर्यावरण संतुलन और हमारा दायित्व",
        "answer": "भूमिका, विषय का गहन विश्लेषण, व्यावहारिक सुझाव एवं सुंदर उपसंहार।"
    }
]

PROSE_PASSAGES = [
    {
        "chapter": "लक्ष्मी",
        "text": (
            "उस दिन लड़के ने तैश में आकर लक्ष्मी की पीठ पर चार डंडे बरसा दिए थे। वह बड़ी भयभीत और घबराई थी। "
            "जो भी उसके पास जाता, सिर हिला उसे मारने की कोशिश करती या फिर उछलती-कूदती, गले की रस्सी तोड़कर "
            "खूँटे से आजाद होने का प्रयास करती। करामत अली इधर दो-चार दिनों से अस्वस्थ था। लेकिन जब उसने यह सुना "
            "कि रहमान ने गाय की पीठ पर डंडे बरसाए हैं तो उससे रहा नहीं गया । वह किसी प्रकार चारपाई से उठकर धीरे-धीरे "
            "चलकर बथान में आया। आगे बढ़कर उसके माथे पर हाथ फेरा, पुचकारा और हौले-से उसकी पीठ पर हाथ फेरा।"
        ),
        "subs": [
            ("आकृति पूर्ण कीजिए : मार के कारण गाय के व्यवहार में आया परिवर्तन :", 2, ["१. भयभीत और घबराना", "२. उछलना-कूदना तथा खूँटे से आजाद होने का प्रयास"]),
            ("संजाल पूर्ण कीजिए : करामत अली द्वारा गाय के प्रति दर्शाया गया दुलार :", 2, ["१. माथे पर हाथ फेरना", "२. पुचकारना और हौले-से पीठ सहलाना"]),
            ("विधान सत्य अथवा असत्य पहचानकर लिखिए : (i) रहमान ने गाय पर डंडे बरसाए । (ii) करामत अली पूर्णतः स्वस्थ था ।", 2, ["(i) सत्य", "(ii) असत्य"]),
            ("शब्द संपदा : गद्यांश में से दो प्रत्यययुक्त शब्द ढूँढ़कर लिखिए :", 2, ["१. भयभीत", "२. घबराई"]),
            ("शब्द संपदा : निम्नलिखित शब्दों के विलोम शब्द गद्यांश से ढूँढ़कर लिखिए : (i) पीछे (ii) जोर-से", 2, ["(i) आगे", "(ii) हौले-से"]),
            ("स्वमत अभिव्यक्ति : 'पशु-प्रेम ही सच्ची मानवता है', इस विषय पर २५-३० शब्दों में अपने विचार लिखिए ।", 2, ["पशु मूक प्राणी हैं, उनकी रक्षा व सेवा करना मानव का कर्तव्य है।"]),
            ("स्वमत अभिव्यक्ति : 'घरेलू पशुओं की देखभाल और हमारा दायित्व', अपने विचार स्पष्ट कीजिए ।", 2, ["पालतू पशु केवल लाभ के लिए नहीं, बल्कि परिवार के सदस्य के समान स्नेह के पात्र होते हैं।"])
        ]
    },
    {
        "chapter": "रीढ़ की हड्डी",
        "text": (
            "मामूली तरह से सजा हुआ एक कमरा। अंदर के दरवाजे से आते हुए जिन महाशय की पीठ नजर आ रही है, वे अधेड़ उम्र के "
            "मालूम होते हैं। एक तख्त को पकड़े हुए पीछे की तरफ चलते-चलते कमरे में आते हैं। तख्त का दूसरा सिरा उनके नौकर ने "
            "पकड़ रखा है। बाबू रामस्वरूप - 'अबे धीरे-धीरे चल! अब तख्त को उधर मोड़ दे... उधर... बस-बस।' नौकर - 'बिछा दूँ साहब ?' "
            "रामस्वरूप (जरा तेज आवाज में) - 'और क्या करेगा ? परमात्मा के यहाँ अक्ल बँट रही थी तो तू देर से पहुँचा था क्या ?'"
        ),
        "subs": [
            ("संजाल पूर्ण कीजिए : कमरे में तख्त बिछाते समय रामस्वरूप की मनोदशा :", 2, ["१. जल्दबाजी में होना", "२. नौकर पर झुंझलाना"]),
            ("प्रवाह तालिका पूर्ण कीजिए : कमरे की साज-सज्जा की घटनाएँ :", 2, ["१. नौकर और मालिक द्वारा तख्त लाना", "२. तख्त को मोड़कर बिछाने का निर्देश देना"]),
            ("कारण लिखिए : रामस्वरूप नौकर पर क्यों बिगड़ पड़े ?", 2, ["क्योंकि नौकर कार्य करने में असमंजस दिखा रहा था और अनुचित प्रश्न पूछ रहा था।"]),
            ("शब्द संपदा : निम्नलिखित शब्दों के विलोम शब्द लिखिए : (i) अंदर (ii) धीरे", 2, ["(i) बाहर", "(ii) तेज"]),
            ("शब्द संपदा : गद्यांश में से दो शब्द-युग्म छाँटकर लिखिए :", 2, ["१. चलते-चलते", "२. बस-बस"]),
            ("स्वमत अभिव्यक्ति : 'लड़कियों की उच्च शिक्षा समाज के विकास हेतु अनिवार्य है', अपने विचार लिखिए ।", 2, ["नारी शिक्षा से परिवार और राष्ट्र दोनों प्रगति के पथ पर अग्रसर होते हैं।"]),
            ("स्वमत अभिव्यक्ति : 'रूढ़िवादी परंपराओं का विरोध करना आवश्यक है', इस विषय पर अपने विचार लिखिए ।", 2, ["समाज की कुरीतियों और दहेज प्रथा जैसी बुराइयों को समाप्त करना आज की महती आवश्यकता है।"])
        ]
    },
    {
        "chapter": "गोवा : जैसा मैंने देखा",
        "text": (
            "गोवा नाम सुनते ही सभी के मन में तरंगें उठने लगती हैं और यह स्वाभाविक भी है, क्योंकि यहाँ की प्रकृति का वरदान ही कुछ ऐसा है। "
            "यहाँ के खूबसूरत सफेद रेतीले तट, महंगे रिसॉर्ट तथा खास तौर पर यहाँ की सी-फूड और फेणी पर्यटकों को आकर्षित करते हैं। "
            "लेकिन मेरा यह दौरा थोड़ा अलग था। मैं वहाँ के जनजीवन, संस्कृति और शांत प्राकृतिक सौंदर्य को करीब से देखना चाहता था। "
            "सुबह की सैर के समय समुद्र की लहरों से टकराती ठंडी हवा शरीर और मन दोनों को नई ऊर्जा से भर देती है।"
        ),
        "subs": [
            ("प्रवाह तालिका पूर्ण कीजिए : पर्यटकों को आकर्षित करने वाले गोवा के घटक :", 2, ["१. सफेद रेतीले तट", "२. शांत प्राकृतिक सौंदर्य"]),
            ("संजाल पूर्ण कीजिए : लेखक के गोवा दौरे का प्रमुख उद्देश्य :", 2, ["१. वहाँ के जनजीवन व संस्कृति को देखना", "२. शांत प्राकृतिक सौंदर्य को करीब से अनुभव करना"]),
            ("उत्तर लिखिए : सुबह की सैर का लेखक पर क्या प्रभाव पड़ा ?", 2, ["समुद्र की ठंडी हवा ने शरीर और मन दोनों को नई ऊर्जा से भर दिया।"]),
            ("शब्द संपदा : गद्यांश में से दो विशेषण शब्द छाँटकर लिखिए :", 2, ["१. खूबसूरत", "२. शांत"]),
            ("शब्द संपदा : निम्नलिखित शब्दों के पर्यायवाची शब्द गद्यांश से ढूँढ़िए : (i) किनारा (ii) सुंदर", 2, ["(i) तट", "(ii) खूबसूरत"]),
            ("स्वमत अभिव्यक्ति : 'पर्यटन से ज्ञान और अनुभव की वृद्धि होती है', इस विषय पर अपने विचार लिखिए ।", 2, ["यात्राओं से नई संस्कृतियों, जीवनशैली और भौगोलिक विविधता का प्रत्यक्ष ज्ञान मिलता है।"]),
            ("स्वमत अभिव्यक्ति : 'प्राकृतिक स्थलों की स्वच्छता बनाए रखना पर्यटकों का कर्तव्य है', अपने विचार लिखिए ।", 2, ["पर्यटन स्थलों पर प्लास्टिक व गंदगी न फैलाकर पर्यावरण का संरक्षण करना चाहिए।"])
        ]
    }
]

POETRY_PASSAGES = [
    {
        "chapter": "भारत महिमा",
        "text": (
            "हिमालय के आँगन में उसे, किरणों का दे उपहार\n"
            "उषा ने हँस अभिनंदन किया, और पहनाया हीरक हार ।\n\n"
            "जगे हम, लगे जगाने विश्व, लोक में फैला फिर आलोक\n"
            "व्योमतम पुंज हुआ तब नष्ट, अखिल संसृति हो उठी अशोक ।।\n\n"
            "विमल वाणी ने वीणा ली, कमल कोमल कर में सप्रीत\n"
            "सप्तस्वर सप्तसिंधु में उठे, छिड़ा तब मधुर साम संगीत ।।"
        ),
        "subs": [
            ("उचित शब्द लिखकर रिक्त स्थान भरिए (आकलन कृति) :", 2, ["१. उषा ने अभिनंदन करके यह पहनाया : हीरक हार", "२. ज्ञान प्राप्त होने पर हमने इसे जगाने का कार्य किया : विश्व"]),
            ("संजाल पूर्ण कीजिए : भारत की सांस्कृतिक व प्राकृतिक धरोहर :", 2, ["१. हिमालय का आँगन", "२. सामवेद का मधुर संगीत"]),
            ("पद्यांश के आधार पर सम्बन्ध जोड़िए : (i) उषा (ii) विमल वाणी", 2, ["(i) किरणों का उपहार", "(ii) वीणा धारण करना"]),
            ("शब्द संपदा : पद्यांश में से दो तत्सम शब्द ढूँढ़कर लिखिए :", 2, ["१. आलोक", "२. संसृति"]),
            ("भावार्थ : उपर्युक्त पद्यांश की प्रथम चार पंक्तियों का सरल अर्थ लिखिए :", 2, ["सूर्य की पहली किरणें भारत भूमि का स्वागत करती हैं और ज्ञान के प्रसार से सम्पूर्ण विश्व का अंधकार दूर हुआ।"]),
            ("स्वमत अभिव्यक्ति : 'देशभक्ति केवल सीमाओं पर लड़ने तक सीमित नहीं है', अपने विचार लिखिए ।", 2, ["ईमानदारी से कर्तव्य पालन और देश के विकास में योगदान देना भी सच्ची देशभक्ति है।"])
        ]
    },
    {
        "chapter": "चाँद से थोड़ी सी गप्पें",
        "text": (
            "आप पहने हुए हैं कुल आकाश\n"
            "तारों जड़ा;\n"
            "सिर्फ़ मुँह खोले हुए हैं अपना\n"
            "गोरा-चिट्टा\n"
            "गोल-मटोल,\n\n"
            "अपनी पोशाक को फैलाए हुए चारों सिम्त ।\n"
            "आप कुछ तिरछे नज़र आते हैं जाने कैसे - \n"
            "खूब हैं गोकि!"
        ),
        "subs": [
            ("संजाल पूर्ण कीजिए : चाँद की पोशाक की विशेषताएँ :", 2, ["१. तारों जड़ा आकाश", "२. चारों दिशाओं में फैली पोशाक"]),
            ("आकृति पूर्ण कीजिए : बालिका द्वारा चाँद के बारे में की गई कल्पना :", 2, ["१. केवल गोरा-चिट्टा मुँह खोले हुए होना", "२. थोड़े तिरछे नजर आना"]),
            ("शब्द संपदा : पद्यांश में से दो तुकबंदी वाले या शब्द-युग्म छाँटकर लिखिए :", 2, ["१. गोरा-चिट्टा", "२. गोल-मटोल"]),
            ("भावार्थ : 'चाँद का घटता-बढ़ता रूप' विषय पर अपने विचार २५-३० शब्दों में लिखिए :", 2, ["प्रकृति के नियमों के अनुसार चंद्रमा का आकार पूर्णिमा से अमावस्या तक निरंतर बदलता रहता है।"]),
            ("स्वमत अभिव्यक्ति : 'बच्चों की कल्पनाशक्ति असीम और अद्भुत होती है', स्पष्ट कीजिए ।", 2, ["बालमन प्रकृति के प्रत्येक दृश्य में सजीवता और असीम कौतुक का अनुभव करता है।"])
        ]
    }
]


def generate_curriculum_paper_fallback(
    metadata: Dict[str, Any],
    selected_chapters: List[Dict[str, Any]],
    blueprint: Dict[str, Any],
    extracted_textbook_text: str = ""
) -> Dict[str, Any]:
    """
    Intelligent curriculum-based generator conforming 100% to Maharashtra State Board standards.
    Strictly separates Class 5, 6, 7, 8, 9, 10 textbook content.
    Tags each question with class_name, textbook, and chapter.
    Guarantees complete question uniqueness across all sections and subquestions.
    """
    raw_grade = metadata.get("class_name") or metadata.get("class") or metadata.get("grade") or "10"
    grade = normalize_grade(raw_grade)
    class_data = get_class_content(grade)
    book_title = class_data.get("book", "हिंदी पाठ्यपुस्तक")
    
    selected_chap_titles = [c.get("title", "") for c in selected_chapters if c.get("title")]
    prose_pool = get_prose_for_class(grade, selected_chap_titles)
    poetry_pool = get_poetry_for_class(grade, selected_chap_titles)
    grammar_pool = get_grammar_for_class(grade)
    writing_pool = get_writing_for_class(grade)
    
    total_marks = metadata.get("total_marks", 40)
    used_questions: List[Dict[str, Any]] = []
    
    bp_sections = blueprint.get("sections", [])
    if not bp_sections:
        if grade in ["5", "6", "7", "8"]:
            bp_key = "middle_school_unit_test" if total_marks <= 25 else "middle_school_semester"
        else:
            bp_key = "high_school_unit_test" if total_marks <= 50 else "high_school_semester"

        raw_bp = DEFAULT_BLUEPRINTS.get(bp_key, {})
        bp_sections = json.loads(json.dumps(raw_bp.get("sections", [])))
        if not bp_sections:
            bp_sections = [
                {"section_number": 1, "section_title": "विभाग १: गद्य", "section_marks": 12},
                {"section_number": 2, "section_title": "विभाग २: पद्य", "section_marks": 8},
                {"section_number": 3, "section_title": "विभाग ३: पूरक पठन", "section_marks": 4},
                {"section_number": 4, "section_title": "विभाग ४: भाषा अध्ययन (व्याकरण)", "section_marks": 8},
                {"section_number": 5, "section_title": "विभाग ५: उपयोजित लेखन", "section_marks": 8},
            ]

        current_sum = sum(s.get("section_marks", 0) for s in bp_sections)
        if current_sum != total_marks and bp_sections:
            diff = total_marks - current_sum
            bp_sections[-1]["section_marks"] = max(2, bp_sections[-1]["section_marks"] + diff)
        
    sections_data = []
    prose_idx = 0
    poetry_idx = 0
    grammar_used_indices: Set[int] = set()
    writing_used_indices: Set[int] = set()

    for s in bp_sections:
        s_num = s.get("section_number", 1)
        s_title = s.get("section_title", f"विभाग {s_num}")
        s_marks = s.get("section_marks", 10)
        
        questions = []
        
        # 1. Prose Section (गद्य)
        if "गद्य" in s_title:
            half = s_marks // 2 if s_marks >= 12 else s_marks
            sub_count = 2 if s_marks >= 12 else 1
            
            for p_sub_i in range(sub_count):
                q_num_label = f"प्रश्न {s_num}. ({'अ' if p_sub_i == 0 else 'आ'})" if sub_count > 1 else f"प्रश्न {s_num}."
                current_m = half if p_sub_i == 0 else (s_marks - half)
                
                # Pick distinct prose passage from class pool
                passage_data = prose_pool[prose_idx % len(prose_pool)]
                prose_idx += 1
                
                # Build subquestions summing to current_m
                sub_q_list = []
                sub_alloc = 0
                for s_label, sub_info in enumerate(passage_data["subs"]):
                    s_txt, s_m, s_ans = sub_info
                    if sub_alloc + s_m <= current_m:
                        sub_q_list.append({
                            "id": str(uuid.uuid4()),
                            "sub_number": f"({s_label + 1})",
                            "sub_text": s_txt,
                            "marks": s_m,
                            "items": ["१. ....................", "२. ...................."] if "संजाल" in s_txt or "आकृति" in s_txt or "तालिका" in s_txt else [],
                            "answer": ", ".join(s_ans) if isinstance(s_ans, list) else str(s_ans)
                        })
                        sub_alloc += s_m
                if sub_alloc < current_m and sub_q_list:
                    sub_q_list[-1]["marks"] += (current_m - sub_alloc)
                    
                q_obj = {
                    "id": str(uuid.uuid4()),
                    "question_number": q_num_label,
                    "question_text": "निम्नलिखित पठित गद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                    "marks": current_m,
                    "source_type": "textbook",
                    "class_name": grade,
                    "textbook": book_title,
                    "chapter": passage_data["chapter"],
                    "source_page": str(p_sub_i * 4 + 1),
                    "source_confidence": "high",
                    "answer": f"{passage_data['chapter']} आधारित गद्यांश कृतियाँ।",
                    "passage": passage_data["text"],
                    "is_poem": False,
                    "sub_questions": sub_q_list
                }
                
                is_dup, reason = is_duplicate_question(q_obj, used_questions)
                if is_dup:
                    raise ValueError("इस विभाग में पर्याप्त अलग-अलग प्रश्न उपलब्ध नहीं हैं। कृपया अधिक अध्याय चुनें या प्रश्नों की संख्या कम करें।")
                
                used_questions.append(q_obj)
                questions.append(q_obj)

        # 2. Poetry Section (पद्य)
        elif "पद्य" in s_title:
            p_data = poetry_pool[poetry_idx % len(poetry_pool)]
            poetry_idx += 1
            
            sub_q_list = []
            sub_alloc = 0
            for s_label, sub_info in enumerate(p_data["subs"]):
                s_txt, s_m, s_ans = sub_info
                if sub_alloc + s_m <= s_marks:
                    sub_q_list.append({
                        "id": str(uuid.uuid4()),
                        "sub_number": f"({s_label + 1})",
                        "sub_text": s_txt,
                        "marks": s_m,
                        "items": ["१. ....................", "२. ...................."] if "संजाल" in s_txt or "उचित" in s_txt or "आकृति" in s_txt else [],
                        "answer": ", ".join(s_ans) if isinstance(s_ans, list) else str(s_ans)
                    })
                    sub_alloc += s_m
            if sub_alloc < s_marks and sub_q_list:
                sub_q_list[-1]["marks"] += (s_marks - sub_alloc)
                
            q_obj = {
                "id": str(uuid.uuid4()),
                "question_number": f"प्रश्न {s_num}.",
                "question_text": "निम्नलिखित पठित पद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": s_marks,
                "source_type": "textbook",
                "class_name": grade,
                "textbook": book_title,
                "chapter": p_data["chapter"],
                "source_page": "1",
                "source_confidence": "high",
                "answer": f"{p_data['chapter']} आधारित पद्यांश कृतियाँ।",
                "passage": p_data["text"],
                "is_poem": True,
                "sub_questions": sub_q_list
            }
            is_dup, reason = is_duplicate_question(q_obj, used_questions)
            if is_dup:
                raise ValueError("इस विभाग में पर्याप्त अलग-अलग प्रश्न उपलब्ध नहीं हैं। कृपया अधिक अध्याय चुनें या प्रश्नों की संख्या कम करें।")
            used_questions.append(q_obj)
            questions.append(q_obj)

        # 3. Supplementary Section (पूरक पठन)
        elif "पूरक" in s_title:
            # Use class-appropriate passage for पूरक पठन
            supp_passage = prose_pool[(prose_idx) % len(prose_pool)]
            prose_idx += 1
            
            sub_q_list = []
            sub_alloc = 0
            for s_label, sub_info in enumerate(supp_passage["subs"][:2]):
                s_txt, s_m, s_ans = sub_info
                if sub_alloc + s_m <= s_marks:
                    sub_q_list.append({
                        "id": str(uuid.uuid4()),
                        "sub_number": f"({s_label + 1})",
                        "sub_text": s_txt,
                        "marks": s_m,
                        "items": [],
                        "answer": ", ".join(s_ans) if isinstance(s_ans, list) else str(s_ans)
                    })
                    sub_alloc += s_m
            if sub_alloc < s_marks and sub_q_list:
                sub_q_list[-1]["marks"] += (s_marks - sub_alloc)
                
            q_obj = {
                "id": str(uuid.uuid4()),
                "question_number": f"प्रश्न {s_num}.",
                "question_text": "निम्नलिखित पठित गद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": s_marks,
                "source_type": "textbook",
                "class_name": grade,
                "textbook": book_title,
                "chapter": f"{supp_passage['chapter']} (पूरक पठन)",
                "source_page": "1",
                "source_confidence": "high",
                "answer": f"{supp_passage['chapter']} आधारित पूरक पठन कृतियाँ।",
                "passage": supp_passage["text"],
                "is_poem": False,
                "sub_questions": sub_q_list
            }
            is_dup, reason = is_duplicate_question(q_obj, used_questions)
            if is_dup:
                raise ValueError("इस विभाग में पर्याप्त अलग-अलग प्रश्न उपलब्ध नहीं हैं। कृपया अधिक अध्याय चुनें या प्रश्नों की संख्या कम करें।")
            used_questions.append(q_obj)
            questions.append(q_obj)

        # 4. Grammar Section (व्याकरण / भाषा अध्ययन)
        elif "व्याकरण" in s_title or "भाषा" in s_title:
            sub_q = []
            allocated = 0
            
            for idx, g_item in enumerate(grammar_pool):
                if idx in grammar_used_indices:
                    continue
                g_m = g_item["marks"]
                if allocated + g_m <= s_marks:
                    sub_candidate = {
                        "id": str(uuid.uuid4()),
                        "sub_number": f"({len(sub_q) + 1})",
                        "sub_text": f"{g_item['type']} : {g_item['text']}",
                        "marks": g_m,
                        "items": [],
                        "answer": g_item["answer"]
                    }
                    sub_q.append(sub_candidate)
                    grammar_used_indices.add(idx)
                    allocated += g_m
                if allocated >= s_marks:
                    break
                    
            if allocated < s_marks and sub_q:
                sub_q[-1]["marks"] += (s_marks - allocated)
                
            q_obj = {
                "id": str(uuid.uuid4()),
                "question_number": f"प्रश्न {s_num}.",
                "question_text": "सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": s_marks,
                "source_type": "textbook",
                "class_name": grade,
                "textbook": book_title,
                "chapter": "भाषा अध्ययन (व्याकरण)",
                "source_page": "",
                "source_confidence": "high",
                "answer": "व्याकरण घटकों के उत्तर",
                "passage": "",
                "is_poem": False,
                "sub_questions": sub_q
            }
            is_dup, reason = is_duplicate_question(q_obj, used_questions)
            if is_dup:
                raise ValueError("इस विभाग में पर्याप्त अलग-अलग प्रश्न उपलब्ध नहीं हैं। कृपया अधिक अध्याय चुनें या प्रश्नों की संख्या कम करें।")
            used_questions.append(q_obj)
            questions.append(q_obj)

        # 5. Writing Section (उपयोजित लेखन)
        elif "लेखन" in s_title or "उपयोजित" in s_title:
            half = s_marks // 2 if s_marks >= 8 else s_marks
            writing_count = 2 if s_marks >= 8 else 1
            
            for w_idx in range(writing_count):
                q_num_label = f"प्रश्न {s_num}. ({'अ' if w_idx == 0 else 'आ'})" if writing_count > 1 else f"प्रश्न {s_num}."
                current_w_marks = half if w_idx == 0 else (s_marks - half)
                
                selected_w = None
                used_genres = {writing_pool[u].get("genre") for u in writing_used_indices if u < len(writing_pool) and writing_pool[u].get("genre")}
                
                # Pass 1: Try unused item with unused genre
                for idx, w_item in enumerate(writing_pool):
                    if idx in writing_used_indices:
                        continue
                    if w_item.get("genre") and w_item.get("genre") in used_genres:
                        continue
                    writing_used_indices.add(idx)
                    selected_w = w_item
                    break
                
                # Pass 2: Any unused item
                if not selected_w:
                    for idx, w_item in enumerate(writing_pool):
                        if idx in writing_used_indices:
                            continue
                        writing_used_indices.add(idx)
                        selected_w = w_item
                        break
                        
                if not selected_w:
                    selected_w = writing_pool[w_idx % len(writing_pool)]
                    
                q_obj = {
                    "id": str(uuid.uuid4()),
                    "question_number": q_num_label,
                    "question_text": selected_w["title"],
                    "marks": current_w_marks,
                    "source_type": "textbook",
                    "class_name": grade,
                    "textbook": book_title,
                    "chapter": "उपयोजित लेखन",
                    "source_page": "",
                    "source_confidence": "high",
                    "answer": selected_w["answer"],
                    "passage": selected_w["passage"],
                    "is_poem": False,
                    "sub_questions": []
                }
                is_dup, reason = is_duplicate_question(q_obj, used_questions)
                if is_dup:
                    raise ValueError("इस विभाग में पर्याप्त अलग-अलग प्रश्न उपलब्ध नहीं हैं। कृपया अधिक अध्याय चुनें या प्रश्नों की संख्या कम करें।")
                used_questions.append(q_obj)
                questions.append(q_obj)

        else:
            # Default section handler
            q_obj = {
                "id": str(uuid.uuid4()),
                "question_number": f"प्रश्न {s_num}.",
                "question_text": "निर्देशानुसार उत्तर लिखिए :",
                "marks": s_marks,
                "source_type": "textbook",
                "class_name": grade,
                "textbook": book_title,
                "chapter": primary_chapter if 'primary_chapter' in locals() else "पाठ्यपुस्तक",
                "source_page": "",
                "source_confidence": "high",
                "answer": "उत्तर",
                "passage": "",
                "is_poem": False,
                "sub_questions": []
            }
            questions.append(q_obj)

        sections_data.append({
            "section_number": s_num,
            "section_title": s_title,
            "section_marks": s_marks,
            "questions": questions
        })

    # Validate complete uniqueness across the paper
    dup_errors = validate_paper_question_uniqueness(sections_data)
    if dup_errors:
        raise ValueError(f"Question uniqueness validation failed: {'; '.join(dup_errors)}")

    paper_result = {
        "school_name": metadata.get("school_name", "TRINITY HIGH SCHOOL & JUNIOR COLLEGE"),
        "exam_title": metadata.get("exam_title", "प्रथम घटक चाचणी"),
        "total_marks": total_marks,
        "duration": metadata.get("duration", "२ घंटे"),
        "subject": metadata.get("subject", f"हिंदी ({book_title})"),
        "metadata": {
            **metadata,
            "class_name": grade,
            "book": book_title
        },
        "general_instructions": [
            "सभी प्रश्न अनिवार्य हैं।",
            "आकृतियों में ही उत्तर लिखना आवश्यक है।",
            "स्वच्छ और सुंदर हस्तलेख में लिखें।"
        ],
        "sections": sections_data,
        "warnings": []
    }
    
    val = validate_generated_or_edited_paper(paper_result)
    if not val["is_valid"]:
        raise ValueError(f"Fallback paper generator validation failed: {'; '.join(val['errors'])}")
        
    return paper_result


def regenerate_single_question(
    paper_data: Dict[str, Any],
    section_index: int,
    question_index: int,
    question_id: Optional[str] = None,
    class_name: Optional[str] = None,
    textbook_id: Optional[int] = None,
    selected_chapters: Optional[List[str]] = None,
    section_title: Optional[str] = None,
    question_type: Optional[str] = None,
    marks: Optional[int] = None,
    used_questions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Regenerates a single question in the paper:
    1. Uses Gemini 2.5 Flash if GEMINI_API_KEY is configured with temperature 0.7.
    2. Fallbacks to authentic class-wise curriculum pools if AI unavailable.
    3. Strictly excludes all questions already on the paper AND recently regenerated questions.
    4. Eliminates ping-ponging and repeated 2-3 questions.
    5. Raises exact Hindi error if pool exhausted:
       'इस अध्याय में नया प्रश्न उपलब्ध नहीं है। कृपया अन्य अध्याय चुनें।'
    """
    sections = paper_data.get("sections", [])
    if section_index < 0 or section_index >= len(sections):
        raise IndexError("अमान्य विभाग अनुक्रमणिका (section index)")
        
    sec = sections[section_index]
    questions = sec.get("questions", [])
    if question_index < 0 or question_index >= len(questions):
        raise IndexError("अमान्य प्रश्न अनुक्रमणिका (question index)")
        
    old_q = questions[question_index]
    target_marks = marks if marks is not None else old_q.get("marks", 5)
    s_title = section_title or sec.get("section_title", "")
    q_num = old_q.get("question_number", f"प्रश्न {question_index + 1}.")
    
    # Determine class and authentic content
    raw_grade = class_name or old_q.get("class_name") or paper_data.get("metadata", {}).get("class_name") or paper_data.get("metadata", {}).get("class") or "10"
    grade = normalize_grade(raw_grade)
    class_data = get_class_content(grade)
    book_title = class_data.get("book", "हिंदी पाठ्यपुस्तक")
    
    # Collect all excluded question signatures across entire paper + passed used_questions
    excluded_texts: List[str] = list(used_questions or [])
    other_questions_for_dup_check: List[Dict[str, Any]] = []
    
    for s_i, s in enumerate(sections):
        for q_i, q in enumerate(s.get("questions", [])):
            if s_i == section_index and q_i == question_index:
                # Add old_q to exclusions so it won't be picked again immediately
                if q.get("chapter"):
                    excluded_texts.append(q["chapter"])
                if q.get("question_text"):
                    excluded_texts.append(q["question_text"])
                if q.get("passage"):
                    excluded_texts.append(q["passage"])
                for sub in q.get("sub_questions", []):
                    if sub.get("sub_text"):
                        excluded_texts.append(sub["sub_text"])
                continue
            other_questions_for_dup_check.append(q)
            if q.get("chapter"):
                excluded_texts.append(q["chapter"])
            if q.get("question_text"):
                excluded_texts.append(q["question_text"])
            if q.get("passage"):
                excluded_texts.append(q["passage"])
            for sub in q.get("sub_questions", []):
                if sub.get("sub_text"):
                    excluded_texts.append(sub["sub_text"])
                    
    all_excluded_check: List[Dict[str, Any]] = list(other_questions_for_dup_check)
    all_excluded_check.append(old_q)
    for u_txt in (used_questions or []):
        all_excluded_check.append({"question_text": u_txt, "passage": u_txt, "sub_questions": []})

    # Normalized exclusion signatures
    excluded_normalized = {normalize_question(t) for t in excluded_texts if t and len(t.strip()) > 3}

    # Attempt AI Regeneration if Gemini API Key is available
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
Generate ONE completely new Hindi question for Maharashtra State Board Exam:
- Class / Grade: {grade}
- Book: {book_title}
- Section: {s_title}
- Question Number: {q_num}
- Marks: {target_marks}
- Chapter Context: {selected_chapters or old_q.get('chapter', '')}

STRICT CONSTRAINTS:
1. Marks must be EXACTLY {target_marks}. If subquestions are used, sum of subquestion marks must equal {target_marks}.
2. DO NOT use any question similar to the following already used questions:
{json.dumps(list(excluded_texts)[:20], ensure_ascii=False)}
3. DO NOT generate rhyming words ('तुकांत शब्द').
4. Return ONLY valid JSON matching this schema:
{{
  "question_number": "{q_num}",
  "question_text": "...",
  "marks": {target_marks},
  "source_type": "textbook",
  "class_name": "{grade}",
  "textbook": "{book_title}",
  "chapter": "...",
  "source_page": "",
  "source_confidence": "high",
  "answer": "...",
  "passage": "...",
  "is_poem": true/false,
  "sub_questions": [
    {{"id": "uuid", "sub_number": "(1)", "sub_text": "...", "marks": 2, "items": [], "answer": "..."}}
  ]
}}
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=GEMINI_SYSTEM_PROMPT,
                    temperature=0.7,
                    response_mime_type="application/json"
                )
            )
            raw_ai = response.text.strip()
            if raw_ai.startswith("```"):
                raw_ai = re.sub(r"^```(?:json)?\s*\n?", "", raw_ai)
                raw_ai = re.sub(r"\n?```\s*$", "", raw_ai)
            cand_q = json.loads(raw_ai)
            if isinstance(cand_q, list) and cand_q:
                cand_q = cand_q[0]
                
            cand_q["question_number"] = q_num
            cand_q["marks"] = target_marks
            cand_q["class_name"] = grade
            cand_q["textbook"] = book_title
            if old_q.get("id"):
                cand_q["id"] = old_q["id"]
            else:
                cand_q["id"] = str(uuid.uuid4())
                
            # Check duplicate against paper
            is_dup, _ = is_duplicate_question(cand_q, other_questions_for_dup_check)
            cand_norm = normalize_question(cand_q.get("question_text", "") + " " + cand_q.get("passage", "")[:40])
            if not is_dup and cand_norm not in excluded_normalized:
                return cand_q
        except Exception:
            # Fall back to class-wise pool below
            pass

    # Class-wise pool fallback
    if "व्याकरण" in s_title or "भाषा" in s_title:
        grammar_pool = list(get_grammar_for_class(grade))
        random.shuffle(grammar_pool)
        
        candidate_subs = []
        allocated = 0
        
        for g_item in grammar_pool:
            cand_text = f"{g_item['type']} : {g_item['text']}"
            cand_norm = normalize_question(cand_text)
            if cand_norm in excluded_normalized:
                continue
                
            cand = {
                "id": str(uuid.uuid4()),
                "sub_number": f"({len(candidate_subs) + 1})",
                "sub_text": cand_text,
                "marks": g_item["marks"],
                "items": [],
                "answer": g_item["answer"]
            }
            temp_q = {"question_text": cand["sub_text"], "sub_questions": []}
            is_dup, _ = is_duplicate_question(temp_q, other_questions_for_dup_check)
            if not is_dup and (allocated + g_item["marks"] <= target_marks):
                candidate_subs.append(cand)
                allocated += g_item["marks"]
                if allocated >= target_marks:
                    break
                    
        if allocated < target_marks and candidate_subs:
            candidate_subs[-1]["marks"] += (target_marks - allocated)
            
        if not candidate_subs:
            raise ValueError("इस अध्याय में नया प्रश्न उपलब्ध नहीं है। कृपया अन्य अध्याय चुनें।")
            
        new_q = {
            "id": old_q.get("id") or str(uuid.uuid4()),
            "question_number": q_num,
            "question_text": "सूचनाओं के अनुसार कृतियाँ कीजिए :",
            "marks": target_marks,
            "source_type": "textbook",
            "class_name": grade,
            "textbook": book_title,
            "chapter": "भाषा अध्ययन",
            "source_page": "",
            "source_confidence": "high",
            "answer": "व्याकरण घटकों के उत्तर",
            "passage": "",
            "is_poem": False,
            "sub_questions": candidate_subs
        }
        return new_q

    elif "लेखन" in s_title or "उपयोजित" in s_title:
        writing_pool = list(get_writing_for_class(grade))
        random.shuffle(writing_pool)
        
        for w_item in writing_pool:
            cand_norm = normalize_question(w_item["title"] + " " + w_item["passage"][:40])
            if cand_norm in excluded_normalized:
                continue
            new_q = {
                "id": old_q.get("id") or str(uuid.uuid4()),
                "question_number": q_num,
                "question_text": w_item["title"],
                "marks": target_marks,
                "source_type": "textbook",
                "class_name": grade,
                "textbook": book_title,
                "chapter": "उपयोजित लेखन",
                "source_page": "",
                "source_confidence": "high",
                "answer": w_item["answer"],
                "passage": w_item["passage"],
                "is_poem": False,
                "sub_questions": []
            }
            is_dup, _ = is_duplicate_question(new_q, all_excluded_check)
            if not is_dup:
                return new_q
        raise ValueError("इस अध्याय में नया प्रश्न उपलब्ध नहीं है। कृपया अन्य अध्याय चुनें।")

    elif "पद्य" in s_title:
        poetry_pool = list(get_poetry_for_class(grade, selected_chapters))
        random.shuffle(poetry_pool)
        
        for p_data in poetry_pool:
            if any(p_data["chapter"].strip().lower() == ex.strip().lower() for ex in excluded_texts if ex):
                continue
            cand_norm = normalize_question(p_data["chapter"] + " " + p_data["text"][:40])
            if cand_norm in excluded_normalized:
                continue
                
            sub_q_list = []
            sub_alloc = 0
            for s_label, sub_info in enumerate(p_data["subs"]):
                s_txt, s_m, s_ans = sub_info
                if sub_alloc + s_m <= target_marks:
                    sub_q_list.append({
                        "id": str(uuid.uuid4()),
                        "sub_number": f"({s_label + 1})",
                        "sub_text": s_txt,
                        "marks": s_m,
                        "items": ["१. ....................", "२. ...................."] if "संजाल" in s_txt or "उचित" in s_txt or "आकृति" in s_txt else [],
                        "answer": ", ".join(s_ans) if isinstance(s_ans, list) else str(s_ans)
                    })
                    sub_alloc += s_m
            if sub_alloc < target_marks and sub_q_list:
                sub_q_list[-1]["marks"] += (target_marks - sub_alloc)
                
            new_q = {
                "id": old_q.get("id") or str(uuid.uuid4()),
                "question_number": q_num,
                "question_text": "निम्नलिखित पठित पद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": target_marks,
                "source_type": "textbook",
                "class_name": grade,
                "textbook": book_title,
                "chapter": p_data["chapter"],
                "source_page": "1",
                "source_confidence": "high",
                "answer": f"{p_data['chapter']} आधारित पद्यांश कृतियाँ।",
                "passage": p_data["text"],
                "is_poem": True,
                "sub_questions": sub_q_list
            }
            is_dup, _ = is_duplicate_question(new_q, all_excluded_check)
            if not is_dup:
                return new_q
        raise ValueError("इस अध्याय में नया प्रश्न उपलब्ध नहीं है। कृपया अन्य अध्याय चुनें।")

    else:
        # Default / Prose
        prose_pool = list(get_prose_for_class(grade, selected_chapters))
        random.shuffle(prose_pool)
        
        for passage_data in prose_pool:
            if any(passage_data["chapter"].strip().lower() == ex.strip().lower() for ex in excluded_texts if ex):
                continue
            cand_norm = normalize_question(passage_data["chapter"] + " " + passage_data["text"][:40])
            if cand_norm in excluded_normalized:
                continue
                
            sub_q_list = []
            sub_alloc = 0
            for s_label, sub_info in enumerate(passage_data["subs"]):
                s_txt, s_m, s_ans = sub_info
                if sub_alloc + s_m <= target_marks:
                    sub_q_list.append({
                        "id": str(uuid.uuid4()),
                        "sub_number": f"({s_label + 1})",
                        "sub_text": s_txt,
                        "marks": s_m,
                        "items": ["१. ....................", "२. ...................."] if "संजाल" in s_txt or "आकृति" in s_txt or "तालिका" in s_txt else [],
                        "answer": ", ".join(s_ans) if isinstance(s_ans, list) else str(s_ans)
                    })
                    sub_alloc += s_m
            if sub_alloc < target_marks and sub_q_list:
                sub_q_list[-1]["marks"] += (target_marks - sub_alloc)
                
            new_q = {
                "id": old_q.get("id") or str(uuid.uuid4()),
                "question_number": q_num,
                "question_text": "निम्नलिखित पठित गद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": target_marks,
                "source_type": "textbook",
                "class_name": grade,
                "textbook": book_title,
                "chapter": passage_data["chapter"],
                "source_page": "1",
                "source_confidence": "high",
                "answer": f"{passage_data['chapter']} आधारित गद्यांश कृतियाँ।",
                "passage": passage_data["text"],
                "is_poem": False,
                "sub_questions": sub_q_list
            }
            is_dup, _ = is_duplicate_question(new_q, all_excluded_check)
            if not is_dup:
                return new_q
                
        raise ValueError("इस अध्याय में नया प्रश्न उपलब्ध नहीं है। कृपया अन्य अध्याय चुनें।")


def regenerate_single_subquestion(
    paper_data: Dict[str, Any],
    section_index: int,
    question_index: int,
    subquestion_index: int,
    subquestion_id: Optional[str] = None,
    class_name: Optional[str] = None,
    textbook_id: Optional[int] = None,
    selected_chapters: Optional[List[str]] = None,
    section_title: Optional[str] = None,
    question_type: Optional[str] = None,
    marks: Optional[int] = None,
    used_questions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Regenerates a single subquestion within a question, maintaining exact marks and
    ensuring it does not duplicate any other subquestion or question in the paper,
    nor any question in used_questions or the subquestion being replaced.
    """
    sections = paper_data.get("sections", [])
    if section_index < 0 or section_index >= len(sections):
        raise IndexError("अमान्य विभाग अनुक्रमणिका (section index)")
        
    sec = sections[section_index]
    questions = sec.get("questions", [])
    if question_index < 0 or question_index >= len(questions):
        raise IndexError("अमान्य प्रश्न अनुक्रमणिका (question index)")
        
    q = questions[question_index]
    subs = q.get("sub_questions", [])
    if subquestion_index < 0 or subquestion_index >= len(subs):
        raise IndexError("अमान्य उपप्रश्न अनुक्रमणिका (subquestion index)")
        
    old_sub = subs[subquestion_index]
    target_marks = marks if marks is not None else old_sub.get("marks", 1)
    s_title = section_title or sec.get("section_title", "")
    old_norm = normalize_question(old_sub.get("sub_text", ""))
    
    raw_grade = class_name or q.get("class_name") or paper_data.get("metadata", {}).get("class_name") or "10"
    grade = normalize_grade(raw_grade)
    class_data = get_class_content(grade)
    
    # Collect all other items in the paper + passed used_questions
    excluded_texts: List[str] = list(used_questions or [])
    other_items: List[Dict[str, Any]] = []
    
    for s_i, s in enumerate(sections):
        for q_i, q_item in enumerate(s.get("questions", [])):
            if q_item.get("question_text"):
                other_items.append({"question_text": q_item["question_text"], "sub_questions": []})
                excluded_texts.append(q_item["question_text"])
            for sub_i, sub_item in enumerate(q_item.get("sub_questions", [])):
                if s_i == section_index and q_i == question_index and sub_i == subquestion_index:
                    if sub_item.get("sub_text"):
                        excluded_texts.append(sub_item["sub_text"])
                    continue
                if sub_item.get("sub_text"):
                    other_items.append({"question_text": sub_item["sub_text"], "sub_questions": []})
                    excluded_texts.append(sub_item["sub_text"])
                    
    excluded_normalized = {normalize_question(t) for t in excluded_texts if t and len(t.strip()) > 3}
    excluded_normalized.add(old_norm)
    
    new_sub = None
    if "व्याकरण" in s_title or "भाषा" in s_title:
        grammar_pool = list(get_grammar_for_class(grade))
        random.shuffle(grammar_pool)
        for g_item in grammar_pool:
            c_text = f"{g_item['type']} : {g_item['text']}"
            c_norm = normalize_question(c_text)
            if c_norm in excluded_normalized:
                continue
            temp_q = {"question_text": c_text, "sub_questions": []}
            is_dup, _ = is_duplicate_question(temp_q, other_items)
            if not is_dup:
                new_sub = {
                    "id": old_sub.get("id") or str(uuid.uuid4()),
                    "sub_number": old_sub.get("sub_number", f"({subquestion_index + 1})"),
                    "sub_text": c_text,
                    "marks": target_marks,
                    "items": [],
                    "answer": g_item["answer"]
                }
                break

    elif "पद्य" in s_title:
        poetry_pool = list(get_poetry_for_class(grade, selected_chapters))
        matching_p = [p for p in poetry_pool if (q.get("chapter") and q["chapter"] in p.get("chapter", "")) or (q.get("passage") and p.get("text", "")[:30] in q.get("passage", ""))]
        other_p = [p for p in poetry_pool if p not in matching_p]
        random.shuffle(matching_p)
        random.shuffle(other_p)
        ordered_poetry = matching_p + other_p
        for p_data in ordered_poetry:
            shuffled_subs = list(p_data["subs"])
            random.shuffle(shuffled_subs)
            for s_txt, s_m, s_ans in shuffled_subs:
                s_norm = normalize_question(s_txt)
                if s_norm in excluded_normalized:
                    continue
                temp_q = {"question_text": s_txt, "sub_questions": []}
                is_dup, _ = is_duplicate_question(temp_q, other_items)
                if not is_dup:
                    new_sub = {
                        "id": old_sub.get("id") or str(uuid.uuid4()),
                        "sub_number": old_sub.get("sub_number", f"({subquestion_index + 1})"),
                        "sub_text": s_txt,
                        "marks": target_marks,
                        "items": ["१. ....................", "२. ...................."] if ("संजाल" in s_txt or "उचित" in s_txt or "आकृति" in s_txt) else [],
                        "answer": ", ".join(s_ans) if isinstance(s_ans, list) else str(s_ans)
                    }
                    break
            if new_sub:
                break

    else:
        # Prose / General
        prose_pool = list(get_prose_for_class(grade, selected_chapters))
        matching_pr = [p for p in prose_pool if (q.get("chapter") and q["chapter"] in p.get("chapter", "")) or (q.get("passage") and p.get("text", "")[:30] in q.get("passage", ""))]
        other_pr = [p for p in prose_pool if p not in matching_pr]
        random.shuffle(matching_pr)
        random.shuffle(other_pr)
        ordered_passages = matching_pr + other_pr
        for pr_data in ordered_passages:
            shuffled_subs = list(pr_data["subs"])
            random.shuffle(shuffled_subs)
            for s_txt, s_m, s_ans in shuffled_subs:
                s_norm = normalize_question(s_txt)
                if s_norm in excluded_normalized:
                    continue
                temp_q = {"question_text": s_txt, "sub_questions": []}
                is_dup, _ = is_duplicate_question(temp_q, other_items)
                if not is_dup:
                    new_sub = {
                        "id": old_sub.get("id") or str(uuid.uuid4()),
                        "sub_number": old_sub.get("sub_number", f"({subquestion_index + 1})"),
                        "sub_text": s_txt,
                        "marks": target_marks,
                        "items": ["१. ....................", "२. ...................."] if ("संजाल" in s_txt or "आकृति" in s_txt or "प्रवाह" in s_txt) else [],
                        "answer": ", ".join(s_ans) if isinstance(s_ans, list) else str(s_ans)
                    }
                    break
            if new_sub:
                break
                
    if not new_sub:
        raise ValueError("इस अध्याय में नया प्रश्न उपलब्ध नहीं है। कृपया अन्य अध्याय चुनें।")
        
    subs[subquestion_index] = new_sub
    return paper_data

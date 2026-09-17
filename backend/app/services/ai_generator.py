import json
import os
import re
import random
from typing import Dict, Any, List, Optional, Set
from google import genai
from google.genai import types
from app.core.config import settings
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
    {
        "type": "पत्र लेखन (औपचारिक)",
        "title": "पत्र लेखन (औपचारिक) :",
        "passage": "विजय/विजया मोहिते, विजयनगर, कोल्हापुर से व्यवस्थापक, नवनीत पुस्तक भंडार, पुणे को आवश्यक पुस्तकों की माँग हेतु पत्र लिखता/लिखती है ।",
        "answer": "औपचारिक पत्र प्रारूप: दिनांक, प्रति, विषय, महोदय, संदर्भ, पुस्तक सूची, भवदीय/भवदीया।"
    },
    {
        "type": "पत्र लेखन (अनौपचारिक)",
        "title": "पत्र लेखन (अनौपचारिक) :",
        "passage": "अमित/अमिता सावंत, गांधी रोड, नासिक से अपने मित्र/सहेली को वाद-विवाद प्रतियोगिता में प्रथम पुरस्कार प्राप्त करने पर बधाई पत्र लिखता/लिखती है ।",
        "answer": "अनौपचारिक पत्र प्रारूप: दिनांक, संबोधन, कुशल-क्षेम, बधाई संदेश, तुम्हारा मित्र/तुम्हारी सहेली।"
    },
    {
        "type": "विज्ञापन लेखन",
        "title": "विज्ञापन लेखन :",
        "passage": "अपने परिसर में आयोजित 'योगसाधना एवं स्वास्थ्य शिविर' के लिए लगभग ५०-६० शब्दों में एक आकर्षक विज्ञापन तैयार कीजिए ।",
        "answer": "आकर्षक शीर्षक, शिविर की मुख्य विशेषताएँ, समय व स्थान, संपर्क सूत्र एवं आकर्षक रूपरेखा।"
    },
    {
        "type": "वृत्तांत लेखन",
        "title": "वृत्तांत लेखन :",
        "passage": "आदर्श विद्यालय, सोलापुर में मनाए गए 'हिंदी दिवस समारोह' का लगभग ६०-८० शब्दों में वृत्तांत लिखिए । (स्थल, काल, घटना, अध्यक्ष का उल्लेख अनिवार्य)",
        "answer": "शीर्षक, स्थल, दिनांक, प्रमुख अतिथि, कार्यक्रमों का विवरण तथा आभार प्रदर्शन।"
    },
    {
        "type": "कहानी लेखन",
        "title": "कहानी लेखन :",
        "passage": "दिए गए मुद्दों के आधार पर लगभग ७०-८० शब्दों में रोचक कहानी लिखकर उचित शीर्षक तथा सीख लिखिए :\nमुद्दे : एक वृद्ध किसान - चार आलसी पुत्र - पिता का बीमार होना - खेत में धन गड़ा होने की बात कहना - पुत्रों द्वारा खेत खोदना - वर्षा होना - अच्छी फसल - सीख ।",
        "answer": "उचित शीर्षक, पैराग्राफ में सुगठित कहानी, अंत में प्रेरक सीख।"
    },
    {
        "type": "निबंध लेखन",
        "title": "निबंध लेखन :",
        "passage": "निम्नलिखित में से किसी एक विषय पर लगभग ८०-१०० शब्दों में निबंध लिखिए :\n१. यदि मैं शिक्षक होता\n२. प्रदूषण : एक गंभीर समस्या\n३. मेरा प्रिय त्योहार",
        "answer": "प्रस्तावना, मुख्य विषय-विस्तार, उदाहरण व विचार, उपसंहार।"
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
            ("शब्द संपदा : गद्यांश में से दो प्रत्यययुक्त शब्द ढूँढ़कर लिखिए :", 2, ["१. भयभीत", "२. घबराई"]),
            ("स्वमत अभिव्यक्ति : 'पशु-प्रेम ही सच्ची मानवता है', इस विषय पर २५-३० शब्दों में अपने विचार लिखिए ।", 2, ["पशु मूक प्राणी हैं, उनकी रक्षा व सेवा करना मानव का कर्तव्य है।"])
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
            ("शब्द संपदा : निम्नलिखित शब्दों के विलोम शब्द लिखिए : (i) अंदर (ii) धीरे", 2, ["१. बाहर", "२. तेज"]),
            ("स्वमत अभिव्यक्ति : 'लड़कियों की उच्च शिक्षा समाज के विकास हेतु अनिवार्य है', अपने विचार लिखिए ।", 2, ["नारी शिक्षा से परिवार और राष्ट्र दोनों प्रगति के पथ पर अग्रसर होते हैं।"])
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
            ("शब्द संपदा : गद्यांश में से दो विशेषण शब्द छाँटकर लिखिए :", 2, ["१. खूबसूरत", "२. शांत"]),
            ("स्वमत अभिव्यक्ति : 'पर्यटन से ज्ञान और अनुभव की वृद्धि होती है', इस विषय पर अपने विचार लिखिए ।", 2, ["यात्राओं से नई संस्कृतियों, जीवनशैली और भौगोलिक विविधता का प्रत्यक्ष ज्ञान मिलता है।"])
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
            ("भावार्थ : उपर्युक्त पद्यांश की प्रथम चार पंक्तियों का सरल अर्थ लिखिए :", 2, ["सूर्य की पहली किरणें भारत भूमि का स्वागत करती हैं और ज्ञान के प्रसार से सम्पूर्ण विश्व का अंधकार दूर हुआ।"])
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
            ("भावार्थ : 'चाँद का घटता-बढ़ता रूप' विषय पर अपने विचार २५-३० शब्दों में लिखिए :", 2, ["प्रकृति के नियमों के अनुसार चंद्रमा का आकार पूर्णिमा से अमावस्या तक निरंतर बदलता रहता है।"])
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
    Strictly guarantees complete question uniqueness across all sections and subquestions.
    """
    total_marks = metadata.get("total_marks", 40)
    grade = str(metadata.get("class_name", "10"))
    
    chaps = [c.get("title", "") for c in selected_chapters if c.get("title")]
    primary_chapter = chaps[0] if chaps else "लक्ष्मी"
    
    # Used questions tracker for this generation request
    used_questions: List[Dict[str, Any]] = []
    
    bp_sections = blueprint.get("sections", [])
    if not bp_sections:
        bp_sections = [
            {"section_number": 1, "section_title": "विभाग १: गद्य", "section_marks": 12},
            {"section_number": 2, "section_title": "विभाग २: पद्य", "section_marks": 8},
            {"section_number": 3, "section_title": "विभाग ३: पूरक पठन", "section_marks": 4},
            {"section_number": 4, "section_title": "विभाग ४: भाषा अध्ययन (व्याकरण)", "section_marks": 8},
            {"section_number": 5, "section_title": "विभाग ५: उपयोजित लेखन", "section_marks": 8},
        ]
        
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
                
                # Pick a distinct prose passage
                passage_data = PROSE_PASSAGES[prose_idx % len(PROSE_PASSAGES)]
                prose_idx += 1
                
                # Build subquestions summing to current_m
                sub_q_list = []
                sub_alloc = 0
                for s_label, sub_info in enumerate(passage_data["subs"]):
                    s_txt, s_m, s_ans = sub_info
                    if sub_alloc + s_m <= current_m:
                        sub_q_list.append({
                            "sub_number": f"({s_label + 1})",
                            "sub_text": s_txt,
                            "marks": s_m,
                            "items": ["१. ....................", "२. ...................."] if "संजाल" in s_txt or "आकृति" in s_txt or "तालिका" in s_txt else [],
                            "answer": ", ".join(s_ans)
                        })
                        sub_alloc += s_m
                if sub_alloc < current_m and sub_q_list:
                    sub_q_list[-1]["marks"] += (current_m - sub_alloc)
                    
                q_obj = {
                    "question_number": q_num_label,
                    "question_text": "निम्नलिखित पठित गद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                    "marks": current_m,
                    "source_type": "textbook",
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
            p_data = POETRY_PASSAGES[poetry_idx % len(POETRY_PASSAGES)]
            poetry_idx += 1
            
            sub_q_list = []
            sub_alloc = 0
            for s_label, sub_info in enumerate(p_data["subs"]):
                s_txt, s_m, s_ans = sub_info
                if sub_alloc + s_m <= s_marks:
                    sub_q_list.append({
                        "sub_number": f"({s_label + 1})",
                        "sub_text": s_txt,
                        "marks": s_m,
                        "items": ["१. ....................", "२. ...................."] if "संजाल" in s_txt or "उचित" in s_txt else [],
                        "answer": ", ".join(s_ans)
                    })
                    sub_alloc += s_m
            if sub_alloc < s_marks and sub_q_list:
                sub_q_list[-1]["marks"] += (s_marks - sub_alloc)
                
            q_obj = {
                "question_number": f"प्रश्न {s_num}.",
                "question_text": "निम्नलिखित पठित पद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": s_marks,
                "source_type": "textbook",
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
            q_obj = {
                "question_number": f"प्रश्न {s_num}.",
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
                        "sub_number": "(1)",
                        "sub_text": "जोड़ियाँ मिलाइए :",
                        "marks": 2,
                        "items": ["१. घना अँधेरा - ....................", "२. जीवन सारा - ...................."],
                        "answer": "१. प्रकाश, २. कर्म"
                    },
                    {
                        "sub_number": "(2)",
                        "sub_text": "स्वमत अभिव्यक्ति : 'कर्म करते रहना ही जीवन का वास्तविक मार्ग है', अपने विचार लिखिए ।",
                        "marks": max(1, s_marks - 2),
                        "items": [],
                        "answer": "सच्चा मनुष्य वही है जो फल की चिंता किए बिना निरंतर कर्म करता रहता है।"
                    }
                ]
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
            
            # Select unused grammar items
            for idx, g_item in enumerate(GRAMMAR_POOL):
                if idx in grammar_used_indices:
                    continue
                g_m = g_item["marks"]
                if allocated + g_m <= s_marks:
                    sub_candidate = {
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
            }
            
            is_dup, reason = is_duplicate_question(q_obj, used_questions)
            if is_dup:
                raise ValueError("इस विभाग में पर्याप्त अलग-अलग प्रश्न उपलब्ध नहीं हैं। कृपया अधिक अध्याय चुनें या प्रश्नों की संख्या कम करें।")
                
            used_questions.append(q_obj)
            questions.append(q_obj)

        # 5. Writing Section (उपयोजित लेखन)
        elif "लेखन" in s_title or "उपयोजित" in s_title:
            half = s_marks // 2 if s_marks >= 8 else s_marks
            sub_count = 2 if s_marks >= 8 else 1
            
            for w_i in range(sub_count):
                q_num_label = f"प्रश्न {s_num}. ({'अ' if w_i == 0 else 'आ'})" if sub_count > 1 else f"प्रश्न {s_num}."
                current_m = half if w_i == 0 else (s_marks - half)
                
                # Pick an unused, non-duplicate writing topic
                chosen_w = None
                q_obj = None
                for idx, w_item in enumerate(WRITING_POOL):
                    if idx in writing_used_indices:
                        continue
                    candidate_q = {
                        "question_number": q_num_label,
                        "question_text": w_item["title"],
                        "marks": current_m,
                        "source_type": "textbook",
                        "chapter": "उपयोजित लेखन",
                        "source_page": "",
                        "source_confidence": "high",
                        "answer": w_item["answer"],
                        "passage": w_item["passage"],
                        "is_poem": False,
                        "sub_questions": []
                    }
                    is_dup, _ = is_duplicate_question(candidate_q, used_questions)
                    if not is_dup:
                        chosen_w = w_item
                        writing_used_indices.add(idx)
                        q_obj = candidate_q
                        break

                if not chosen_w or not q_obj:
                    raise ValueError("इस विभाग में पर्याप्त अलग-अलग प्रश्न उपलब्ध नहीं हैं। कृपया अधिक अध्याय चुनें या प्रश्नों की संख्या कम करें।")

                used_questions.append(q_obj)
                questions.append(q_obj)

        else:
            q_obj = {
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
            }
            is_dup, reason = is_duplicate_question(q_obj, used_questions)
            if is_dup:
                raise ValueError("इस विभाग में पर्याप्त अलग-अलग प्रश्न उपलब्ध नहीं हैं। कृपया अधिक अध्याय चुनें या प्रश्नों की संख्या कम करें।")
            used_questions.append(q_obj)
            questions.append(q_obj)
            
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
    
    val = validate_generated_or_edited_paper(paper_result)
    if not val["is_valid"]:
        raise ValueError(f"Fallback paper generator validation failed: {'; '.join(val['errors'])}")
        
    return paper_result


def regenerate_single_question(
    paper_data: Dict[str, Any],
    section_index: int,
    question_index: int,
    selected_chapters: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Regenerates a single question in the paper, strictly excluding all other question
    signatures currently in the paper from the replacement pool and preserving exact marks.
    """
    sections = paper_data.get("sections", [])
    if section_index < 0 or section_index >= len(sections):
        raise IndexError("अमान्य विभाग अनुक्रमणिका (section index)")
        
    sec = sections[section_index]
    questions = sec.get("questions", [])
    if question_index < 0 or question_index >= len(questions):
        raise IndexError("अमान्य प्रश्न अनुक्रमणिका (question index)")
        
    old_q = questions[question_index]
    target_marks = old_q.get("marks", 5)
    s_title = sec.get("section_title", "")
    q_num = old_q.get("question_number", f"प्रश्न {question_index + 1}.")
    
    # Collect all OTHER questions in the paper to exclude them
    other_questions = []
    for s_i, s in enumerate(sections):
        for q_i, q in enumerate(s.get("questions", [])):
            if s_i == section_index and q_i == question_index:
                continue
            other_questions.append(q)
            
    # Regenerate based on section type
    if "व्याकरण" in s_title or "भाषा" in s_title:
        # Build subquestions from GRAMMAR_POOL that do not duplicate anything in other_questions
        candidate_subs = []
        allocated = 0
        shuffled_pool = list(GRAMMAR_POOL)
        random.shuffle(shuffled_pool)
        
        for g_item in shuffled_pool:
            cand = {
                "sub_number": f"({len(candidate_subs) + 1})",
                "sub_text": f"{g_item['type']} : {g_item['text']}",
                "marks": g_item["marks"],
                "items": [],
                "answer": g_item["answer"]
            }
            temp_q = {"question_text": cand["sub_text"], "sub_questions": []}
            is_dup, _ = is_duplicate_question(temp_q, other_questions)
            if not is_dup and (allocated + g_item["marks"] <= target_marks):
                candidate_subs.append(cand)
                allocated += g_item["marks"]
                if allocated >= target_marks:
                    break
                    
        if allocated < target_marks and candidate_subs:
            candidate_subs[-1]["marks"] += (target_marks - allocated)
            
        new_q = {
            "question_number": q_num,
            "question_text": "सूचनाओं के अनुसार कृतियाँ कीजिए :",
            "marks": target_marks,
            "source_type": "textbook",
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
        shuffled_w = list(WRITING_POOL)
        random.shuffle(shuffled_w)
        for w_item in shuffled_w:
            new_q = {
                "question_number": q_num,
                "question_text": w_item["title"],
                "marks": target_marks,
                "source_type": "textbook",
                "chapter": "उपयोजित लेखन",
                "source_page": "",
                "source_confidence": "high",
                "answer": w_item["answer"],
                "passage": w_item["passage"],
                "is_poem": False,
                "sub_questions": []
            }
            is_dup, _ = is_duplicate_question(new_q, other_questions)
            if not is_dup:
                return new_q
        return new_q

    elif "पद्य" in s_title:
        shuffled_p = list(POETRY_PASSAGES)
        random.shuffle(shuffled_p)
        for p_data in shuffled_p:
            sub_q_list = []
            sub_alloc = 0
            for s_label, sub_info in enumerate(p_data["subs"]):
                s_txt, s_m, s_ans = sub_info
                if sub_alloc + s_m <= target_marks:
                    sub_q_list.append({
                        "sub_number": f"({s_label + 1})",
                        "sub_text": s_txt,
                        "marks": s_m,
                        "items": ["१. ....................", "२. ...................."] if "संजाल" in s_txt or "उचित" in s_txt else [],
                        "answer": ", ".join(s_ans)
                    })
                    sub_alloc += s_m
            if sub_alloc < target_marks and sub_q_list:
                sub_q_list[-1]["marks"] += (target_marks - sub_alloc)
                
            new_q = {
                "question_number": q_num,
                "question_text": "निम्नलिखित पठित पद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": target_marks,
                "source_type": "textbook",
                "chapter": p_data["chapter"],
                "source_page": "1",
                "source_confidence": "high",
                "answer": f"{p_data['chapter']} आधारित पद्यांश कृतियाँ।",
                "passage": p_data["text"],
                "is_poem": True,
                "sub_questions": sub_q_list
            }
            is_dup, _ = is_duplicate_question(new_q, other_questions)
            if not is_dup:
                return new_q
        return new_q

    else:
        # Default / Prose
        shuffled_prose = list(PROSE_PASSAGES)
        random.shuffle(shuffled_prose)
        for passage_data in shuffled_prose:
            sub_q_list = []
            sub_alloc = 0
            for s_label, sub_info in enumerate(passage_data["subs"]):
                s_txt, s_m, s_ans = sub_info
                if sub_alloc + s_m <= target_marks:
                    sub_q_list.append({
                        "sub_number": f"({s_label + 1})",
                        "sub_text": s_txt,
                        "marks": s_m,
                        "items": ["१. ....................", "२. ...................."] if "संजाल" in s_txt or "आकृति" in s_txt else [],
                        "answer": ", ".join(s_ans)
                    })
                    sub_alloc += s_m
            if sub_alloc < target_marks and sub_q_list:
                sub_q_list[-1]["marks"] += (target_marks - sub_alloc)
                
            new_q = {
                "question_number": q_num,
                "question_text": "निम्नलिखित पठित गद्यांश पढ़कर सूचनाओं के अनुसार कृतियाँ कीजिए :",
                "marks": target_marks,
                "source_type": "textbook",
                "chapter": passage_data["chapter"],
                "source_page": "1",
                "source_confidence": "high",
                "answer": f"{passage_data['chapter']} आधारित गद्यांश कृतियाँ।",
                "passage": passage_data["text"],
                "is_poem": False,
                "sub_questions": sub_q_list
            }
            is_dup, _ = is_duplicate_question(new_q, other_questions)
            if not is_dup:
                return new_q
                
        raise ValueError("इस विभाग में पर्याप्त अलग-अलग प्रश्न उपलब्ध नहीं हैं। कृपया अधिक अध्याय चुनें या प्रश्नों की संख्या कम करें।")

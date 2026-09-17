# HINDI PAPER MAKER (हिंदी प्रश्नपत्रिका निर्माता)
### महाराष्ट्र राज्य माध्यमिक व उच्च माध्यमिक शिक्षण मंडळ (Maharashtra State Board)

An online AI-powered Hindi question paper generator for teachers following the Maharashtra State Board curriculum (Classes 5 to 10 - Hindi Sulabhbharati and Hindi Lokbharati).

---

## 🌟 Core Features

1. **Textbook PDF Processing & OCR Detection**:
   - Accepts textbooks up to 100 MB with strict validation (magic signature, MIME type, structure).
   - Page-by-page text extraction with PyMuPDF.
   - Low-text density detection (< 50 chars threshold flags "Scanned / Low Text" with OCR warnings).
   - Automatic Table of Contents (अनुक्रमणिका) parsing with Maharashtra State Board curriculum database.

2. **Curriculum & Blueprint Standards**:
   - Classes 5 to 8: Hindi Sulabhbharati (Unit Test: 20 marks; Semester Exam: 50 marks).
   - Classes 9 & 10: Hindi Lokbharati (Unit Test: 40 marks; Semester/Annual: 80 marks).
   - Custom blueprint builder with live recalculation and marks difference validation.

3. **Strict Academic & Quality Rules**:
   - **Single Paper Generation**: Generates strictly ONE complete question paper per request (NO Set A, Set B, or Set C).
   - **Poetry Rule (Absolute Prohibition)**: Never generates questions asking for "तुकांत शब्द" or rhyming words. Uses "शब्दार्थ", "समानार्थी", "विलोम", "शब्द संपदा", "सरल भावार्थ", "आशय".
   - **Quotation Accuracy**: Word-for-word accuracy with extracted textbook text.

4. **Canva-Style Visual Paper Editor**:
   - Interactive live A4 canvas matching real paper dimensions.
   - Direct inline editing of school name, tagline, exam title, duration, marks, instructions, questions, and passages.
   - Question actions: Add (+), Duplicate, Delete, Move Up/Down.
   - Undo / Redo history.
   - Real-time marks difference validator prevents saving/exporting mismatched marks.

5. **A4 PDF & Editable Word (DOCX) Export**:
   - High-fidelity A4 portrait PDF rendering with headless Chrome/Playwright and mandatory CSS.
   - Fully editable Word (.docx) export with native tables, Devanagari fonts, and optional Answer Key.

---

## 🚀 Production Deployment & Running

### Option 1: 1-Click Production Server (Windows)
Double-click `start_production.bat` or run:
```powershell
.\start_production.ps1
```
This automatically builds the React frontend (if needed), starts the unified production server on port 8000, outputs the school local network URL (`http://<LAN-IP>:8000`), and launches your browser.

### Option 2: Docker Container Deployment (Cloud & Server)
Run the application in a portable, self-contained Docker container:
```bash
docker compose up --build -d
```
The application will be accessible on `http://localhost:8000` with persistent storage volumes for textbooks, exports, and the database.

### Option 3: Free Cloud Deployment (Render / Railway)
- **Render**: Connect your GitHub repository to [Render.com](https://render.com) and deploy using the included `render.yaml`.
- **Railway / Fly.io**: Uses the included `Dockerfile` and `Procfile` for automatic detection and deployment.

### Option 4: Developer Mode in VS Code (F5)
1. Open folder `D:\hindi-paper-maker` in VS Code:
   ```powershell
   code D:\hindi-paper-maker
   ```
2. Press **F5** or select **"Full Stack: Hindi Paper Maker"** in Run & Debug.
3. Open `http://localhost:5173` in your browser.

---

## 🔑 Environment Variables
Configure your `backend/.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key_here
PORT=8000
HOST=127.0.0.1
```
*Note: If `GEMINI_API_KEY` is not set, the application automatically uses its intelligent Maharashtra State Board curriculum engine to generate valid papers.*

---

## 📁 Directory Structure
```
D:\hindi-paper-maker\
├── backend/
│   ├── app/
│   │   ├── api/            # REST API endpoints (textbooks, papers, blueprints)
│   │   ├── core/           # Config, database, curriculum data
│   │   ├── models/         # SQLAlchemy models (Textbook, Paper, AnswerKey)
│   │   ├── schemas/        # Pydantic schemas with strict validation
│   │   ├── services/       # PyMuPDF extraction, Gemini generator, PDF/DOCX exporters
│   │   └── templates/      # Mandatory A4 print HTML CSS templates
│   ├── storage/            # Textbooks, exports, and assets (school logo)
│   ├── .venv/              # Python virtual environment
│   ├── requirements.txt
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/     # Navbar, MarksValidatorBadge, OcrWarningModal
│   │   ├── pages/          # Dashboard, Upload, PaperGenerator, CanvaEditor, Export
│   │   ├── services/       # Axios API client
│   │   ├── types/          # TypeScript definitions
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
└── .vscode/
    ├── launch.json         # VS Code debug launcher
    └── settings.json
```

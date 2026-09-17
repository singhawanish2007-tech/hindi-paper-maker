import React, { useState, useEffect } from "react";
import {
  Sparkles,
  BookOpen,
  Calendar,
  Clock,
  Layers,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Loader2,
  Plus,
  Trash2,
  Sliders,
  FileCheck
} from "lucide-react";
import { textbookService, blueprintService, paperService } from "../services/api";
import { Textbook, Chapter, BlueprintValidationResult } from "../types";
import { MarksValidatorBadge } from "../components/MarksValidatorBadge";
import { translations, Language } from "../services/translations";

interface PaperGeneratorProps {
  setCurrentTab: (tab: string) => void;
  setActivePaperId: (id: number) => void;
  lang?: Language;
}

export const PaperGenerator: React.FC<PaperGeneratorProps> = ({
  setCurrentTab,
  setActivePaperId,
  lang = "hi"
}) => {
  const [step, setStep] = useState<number>(1);
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [selectedTextbookId, setSelectedTextbookId] = useState<number | null>(null);

  const t = translations[lang] || translations.hi;

  // Configuration
  const [grade, setGrade] = useState("10");
  const [bookName, setBookName] = useState("हिंदी लोकभारती");
  const [selectedUnit, setSelectedUnit] = useState("पहली इकाई");
  const [availableChapters, setAvailableChapters] = useState<Chapter[]>([]);
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);

  // Exam Details
  const [examType, setExamType] = useState("Unit Test 1");
  const [totalMarks, setTotalMarks] = useState<number>(40);
  const [duration, setDuration] = useState("२ घंटे");
  const [difficulty, setDifficulty] = useState("Medium");
  const [schoolName, setSchoolName] = useState("TRINITY HIGH SCHOOL & JUNIOR COLLEGE");
  const [tagline, setTagline] = useState("KNOWLEDGE IS WISDOM");
  const [examTitle, setExamTitle] = useState("प्रथम घटक चाचणी (First Unit Test)");
  const [hasLogo, setHasLogo] = useState(true);

  // Blueprint
  const [blueprints, setBlueprints] = useState<any[]>([]);
  const [activeBlueprint, setActiveBlueprint] = useState<any>(null);
  const [validationResult, setValidationResult] = useState<BlueprintValidationResult>({
    is_valid: true,
    configured_total: 40,
    calculated_total: 40,
    difference: 0,
    errors: [],
    warnings: []
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  useEffect(() => {
    loadTextbooks();
  }, []);

  useEffect(() => {
    loadBlueprintsForGrade(grade);
  }, [grade]);

  const loadTextbooks = async () => {
    try {
      const list = await textbookService.getAll();
      setTextbooks(list);
      const match = list.find((tb) => tb.grade === grade);
      if (match) {
        setSelectedTextbookId(match.id);
        setAvailableChapters(match.chapters || []);
        const chTitles = (match.chapters || []).slice(0, 3).map((c) => c.title);
        setSelectedChapters(chTitles);
      }
    } catch (e) {
      console.error("Failed to load textbooks", e);
    }
  };

  const loadBlueprintsForGrade = async (g: string) => {
    try {
      const data = await blueprintService.getBlueprints(g);
      const defaults = data.default_blueprints || [];
      setBlueprints(defaults);
      if (defaults.length > 0) {
        const defaultBp = defaults[0];
        setActiveBlueprint(defaultBp);
        setTotalMarks(defaultBp.total_marks);
        setDuration(defaultBp.duration);
        validateCurrentBlueprint(defaultBp.total_marks, defaultBp.sections);
      }
    } catch (e) {
      console.error("Failed to load blueprints", e);
    }
  };

  const handleGradeChange = (newGrade: string) => {
    setGrade(newGrade);
    const g = parseInt(newGrade, 10);
    const newBook = g <= 8 ? "हिंदी सुलभभारती" : "हिंदी लोकभारती";
    setBookName(newBook);

    const match = textbooks.find((tb) => tb.grade === newGrade);
    if (match) {
      setSelectedTextbookId(match.id);
      setAvailableChapters(match.chapters || []);
      const chTitles = (match.chapters || []).slice(0, 3).map((c) => c.title);
      setSelectedChapters(chTitles);
    } else {
      setSelectedChapters([]);
    }
  };

  const handleExamTypeChange = (newType: string) => {
    setExamType(newType);
    let defaultTitle = "";
    let marks = 40;
    let dur = "२ घंटे";
    const g = parseInt(grade, 10);

    if (newType === "Unit Test 1") {
      defaultTitle = "प्रथम घटक चाचणी (First Unit Test)";
      marks = g <= 8 ? 20 : 40;
      dur = g <= 8 ? "१ घंटा" : "२ घंटे";
    } else if (newType === "Unit Test 2") {
      defaultTitle = "द्वितीय घटक चाचणी (Second Unit Test)";
      marks = g <= 8 ? 20 : 40;
      dur = g <= 8 ? "१ घंटा" : "२ घंटे";
    } else if (newType === "Semester 1") {
      defaultTitle = "प्रथम सत्रांत परीक्षा (Semester 1 Exam)";
      marks = g <= 8 ? 50 : 80;
      dur = g <= 8 ? "२ घंटे" : "३ घंटे";
    } else if (newType === "Semester 2") {
      defaultTitle = "द्वितीय सत्रांत परीक्षा (Semester 2 Exam)";
      marks = g <= 8 ? 50 : 80;
      dur = g <= 8 ? "२ घंटे" : "३ घंटे";
    } else if (newType === "Annual Examination") {
      defaultTitle = "वार्षिक परीक्षा (Annual Examination)";
      marks = g <= 8 ? 50 : 80;
      dur = g <= 8 ? "२ घंटे" : "३ घंटे";
    } else {
      defaultTitle = "घटक चाचणी परीक्षा";
      marks = 20;
      dur = "१ घंटा";
    }

    setExamTitle(defaultTitle);
    setTotalMarks(marks);
    setDuration(dur);

    const matchBp = blueprints.find((b) => b.total_marks === marks) || blueprints[0];
    if (matchBp) {
      setActiveBlueprint(matchBp);
      validateCurrentBlueprint(marks, matchBp.sections);
    }
  };

  const handleTotalMarksChange = (marks: number) => {
    setTotalMarks(marks);
    const matchBp = blueprints.find((b) => b.total_marks === marks);
    if (matchBp) {
      setActiveBlueprint(matchBp);
      validateCurrentBlueprint(marks, matchBp.sections);
    } else if (activeBlueprint) {
      validateCurrentBlueprint(marks, activeBlueprint.sections);
    }
  };

  const validateCurrentBlueprint = async (marks: number, sections: any[]) => {
    try {
      const res = await blueprintService.validate(marks, sections);
      setValidationResult(res);
    } catch (e) {
      console.error(e);
    }
  };

  const handleChapterToggle = (title: string) => {
    if (selectedChapters.includes(title)) {
      setSelectedChapters(selectedChapters.filter((t) => t !== title));
    } else {
      setSelectedChapters([...selectedChapters, title]);
    }
  };

  const handleSectionMarksChange = (secIdx: number, newMarks: number) => {
    if (!activeBlueprint) return;
    const updatedSecs = [...activeBlueprint.sections];
    updatedSecs[secIdx].section_marks = Number(newMarks);
    const updatedBp = { ...activeBlueprint, sections: updatedSecs };
    setActiveBlueprint(updatedBp);
    validateCurrentBlueprint(totalMarks, updatedSecs);
  };

  const handleGeneratePaper = async () => {
    if (selectedChapters.length === 0) {
      alert(lang === "hi" ? "कृपया कम से कम एक पाठ का चयन करें।" : "Please select at least one chapter.");
      return;
    }

    if (!validationResult.is_valid) {
      alert(
        lang === "hi"
          ? `अंक असंगत हैं! अंतर: ${validationResult.difference} अंक। कृपया ब्लूप्रिंट ठीक करें।`
          : `Marks mismatch! Difference: ${validationResult.difference} marks. Please correct the blueprint.`
      );
      return;
    }

    setIsGenerating(true);
    setGenerationError(null);

    const payload = {
      textbook_id: selectedTextbookId,
      grade,
      book: bookName,
      exam_type: examType,
      total_marks: totalMarks,
      duration,
      difficulty,
      unit_name: selectedUnit,
      selected_chapters: selectedChapters,
      school_name: schoolName,
      tagline,
      exam_title: examTitle,
      blueprint: activeBlueprint,
      has_logo: hasLogo
    };

    try {
      const res = await paperService.generate(payload);
      setActivePaperId(res.id);
      setCurrentTab("editor");
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Generation failed.";
      setGenerationError(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-16">
      {/* Wizard Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-blue-600" />
            {t.wizardTitle}
          </h2>
          <p className="text-xs text-slate-500 mt-1">{t.wizardDesc}</p>
        </div>

        {/* Step Navigation Indicators */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setStep(1)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
              step === 1 ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {t.step1}
          </button>
          <span className="text-slate-300">→</span>
          <button
            onClick={() => setStep(2)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
              step === 2 ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {t.step2}
          </button>
          <span className="text-slate-300">→</span>
          <button
            onClick={() => setStep(3)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
              step === 3 ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {t.step3}
          </button>
        </div>
      </div>

      {/* STEP 1: CLASS & CHAPTER SELECTION */}
      {step === 1 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 sm:p-8 space-y-6 animate-in fade-in">
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-bold text-base text-slate-900">{lang === "hi" ? "कक्षा, पुस्तक एवं पाठ चयन" : "Select Class, Book & Chapters"}</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {lang === "hi" ? "जिन अध्यायों से प्रश्न पूछे जाने हैं, उनका चयन करें।" : "Select the chapters you want to include in the question paper."}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">{t.bookClass}</label>
              <select
                value={grade}
                onChange={(e) => handleGradeChange(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:outline-hidden"
              >
                <option value="5">{lang === "hi" ? "कक्षा ५वीं (5th Standard)" : "Class 5th"}</option>
                <option value="6">{lang === "hi" ? "कक्षा ६वीं (6th Standard)" : "Class 6th"}</option>
                <option value="7">{lang === "hi" ? "कक्षा ७वीं (7th Standard)" : "Class 7th"}</option>
                <option value="8">{lang === "hi" ? "कक्षा ८वीं (8th Standard)" : "Class 8th"}</option>
                <option value="9">{lang === "hi" ? "कक्षा ९वीं (9th Standard)" : "Class 9th"}</option>
                <option value="10">{lang === "hi" ? "कक्षा १०वीं (10th Standard)" : "Class 10th"}</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">{t.curriculumBook}</label>
              <input
                type="text"
                readOnly
                value={bookName}
                className="w-full px-3 py-2 bg-slate-100 border border-slate-300 rounded-lg text-sm text-slate-600 font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">{t.unitLabel}</label>
              <select
                value={selectedUnit}
                onChange={(e) => setSelectedUnit(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:outline-hidden"
              >
                <option value="पहली इकाई">{t.unit1}</option>
                <option value="दूसरी इकाई">{t.unit2}</option>
                <option value="संपूर्ण पुस्तक">{t.fullBook}</option>
              </select>
            </div>
          </div>

          {/* Chapters Checklist */}
          <div>
            <div className="flex justify-between items-center mb-3">
              <label className="text-xs font-bold text-slate-700">
                {t.availableChapters} ({selectedChapters.length} {t.selectedCount}) :
              </label>
              <div className="flex gap-2 text-xs">
                <button
                  type="button"
                  onClick={() => setSelectedChapters(availableChapters.map((c) => c.title))}
                  className="text-blue-600 hover:underline cursor-pointer"
                >
                  {t.selectAll}
                </button>
                <span>•</span>
                <button
                  type="button"
                  onClick={() => setSelectedChapters([])}
                  className="text-slate-500 hover:underline cursor-pointer"
                >
                  {t.clearAll}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto p-1">
              {availableChapters
                .filter(
                  (c) =>
                    selectedUnit === "संपूर्ण पुस्तक" || c.unit_name === selectedUnit
                )
                .map((ch, idx) => {
                  const isChecked = selectedChapters.includes(ch.title);
                  return (
                    <label
                      key={idx}
                      className={`flex items-start gap-3 p-3.5 rounded-xl border transition-all cursor-pointer ${
                        isChecked
                          ? "bg-blue-50/70 border-blue-300 text-blue-950"
                          : "bg-white border-slate-200 text-slate-700 hover:border-slate-300"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleChapterToggle(ch.title)}
                        className="mt-1 w-4 h-4 text-blue-600 rounded-sm border-slate-300 focus:ring-blue-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-sm">
                            {ch.chapter_number}. {ch.title}
                          </span>
                          <span
                            className={`text-2xs font-bold px-2 py-0.5 rounded-md ${
                              ch.chapter_type === "poetry"
                                ? "bg-purple-100 text-purple-700"
                                : ch.chapter_type === "prose"
                                ? "bg-amber-100 text-amber-700"
                                : ch.chapter_type === "supplementary"
                                ? "bg-teal-100 text-teal-700"
                                : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {ch.chapter_type === "poetry"
                              ? "पद्य"
                              : ch.chapter_type === "prose"
                              ? "गद्य"
                              : ch.chapter_type === "supplementary"
                              ? "पूरक पठन"
                              : "व्याकरण"}
                          </span>
                        </div>
                        {ch.author && (
                          <div className="text-xs text-slate-500 mt-0.5">
                            {t.authorPoet}: {ch.author}
                          </div>
                        )}
                      </div>
                    </label>
                  );
                })}
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-100">
            <button
              onClick={() => setStep(2)}
              disabled={selectedChapters.length === 0}
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
            >
              {t.nextConfigureExam}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: EXAM CONFIGURATION & BLUEPRINT BUILDER */}
      {step === 2 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 sm:p-8 space-y-6 animate-in fade-in">
          <div className="border-b border-slate-100 pb-4 flex justify-between items-center">
            <div>
              <h3 className="font-bold text-base text-slate-900">{t.examAndBlueprint}</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {lang === "hi"
                  ? "स्कूल विवरण, समय, कुल अंक व विभागवार अंक वितरण को अनुकूलित करें।"
                  : "Customize school details, duration, total marks and section-wise marks distribution."}
              </p>
            </div>
            <MarksValidatorBadge
              configuredTotal={totalMarks}
              calculatedTotal={validationResult.calculated_total}
              errors={validationResult.errors}
              compact
            />
          </div>

          {/* School & Exam Header Settings */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-4">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">{t.schoolAndExamHeader}</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-2xs font-semibold text-slate-600 mb-1">{t.schoolName}</label>
                <input
                  type="text"
                  value={schoolName}
                  onChange={(e) => setSchoolName(e.target.value)}
                  className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-medium text-slate-800"
                />
              </div>
              <div>
                <label className="block text-2xs font-semibold text-slate-600 mb-1">{t.tagline}</label>
                <input
                  type="text"
                  value={tagline}
                  onChange={(e) => setTagline(e.target.value)}
                  className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-medium text-slate-800"
                />
              </div>
              <div>
                <label className="block text-2xs font-semibold text-slate-600 mb-1">{t.examName}</label>
                <input
                  type="text"
                  value={examTitle}
                  onChange={(e) => setExamTitle(e.target.value)}
                  className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-medium text-slate-800"
                />
              </div>
              <div className="flex items-center gap-4 pt-4">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={hasLogo}
                    onChange={(e) => setHasLogo(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded-sm"
                  />
                  {t.includeLogo}
                </label>
              </div>
            </div>
          </div>

          {/* Exam Type & Total Marks Picker */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">{t.examType}</label>
              <select
                value={examType}
                onChange={(e) => handleExamTypeChange(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-800"
              >
                <option value="Unit Test 1">Unit Test 1 (प्रथम घटक चाचणी)</option>
                <option value="Unit Test 2">Unit Test 2 (द्वितीय घटक चाचणी)</option>
                <option value="Semester 1">Semester 1 (प्रथम सत्रांत परीक्षा)</option>
                <option value="Semester 2">Semester 2 (द्वितीय सत्रांत परीक्षा)</option>
                <option value="Annual Examination">Annual Examination (वार्षिक परीक्षा)</option>
                <option value="Class Test">Class Test (वर्ग चाचणी)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">{t.totalMarks}</label>
              <div className="flex gap-1.5">
                {[20, 40, 50, 80].map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => handleTotalMarksChange(m)}
                    className={`flex-1 py-1.5 text-xs font-bold rounded-lg border transition-colors cursor-pointer ${
                      totalMarks === m
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">{t.duration}</label>
              <input
                type="text"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-800"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">{t.difficulty}</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-800"
              >
                <option value="Easy">{t.easy}</option>
                <option value="Medium">{t.medium}</option>
                <option value="Hard">{t.hard}</option>
              </select>
            </div>
          </div>

          {/* Blueprint Section Marks Editor */}
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                {t.sectionsAndMarks}
              </h4>
              <span className="text-xs text-slate-500">
                {t.sectionsSumRule}
              </span>
            </div>

            {activeBlueprint?.sections?.map((sec: any, sIdx: number) => (
              <div
                key={sIdx}
                className="p-3.5 bg-white border border-slate-200 rounded-xl flex items-center justify-between gap-4"
              >
                <div className="flex-1">
                  <div className="font-bold text-xs text-slate-800">{sec.section_title}</div>
                  <div className="text-2xs text-slate-400 mt-0.5">
                    {sec.questions?.length || 1} {t.mainQuestionsCount}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">{t.marksColon}</span>
                  <input
                    type="number"
                    min="1"
                    value={sec.section_marks}
                    onChange={(e) => handleSectionMarksChange(sIdx, parseInt(e.target.value, 10) || 0)}
                    className="w-20 px-2.5 py-1 bg-slate-50 border border-slate-300 rounded-lg text-xs font-bold text-right"
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Full Marks Validation Box */}
          <MarksValidatorBadge
            configuredTotal={totalMarks}
            calculatedTotal={validationResult.calculated_total}
            errors={validationResult.errors}
          />

          <div className="flex justify-between pt-4 border-t border-slate-100">
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 border border-slate-300 text-slate-700 font-semibold text-xs rounded-xl hover:bg-slate-50 cursor-pointer"
            >
              {t.backChapterSelect}
            </button>
            <button
              onClick={() => setStep(3)}
              disabled={!validationResult.is_valid}
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
            >
              {t.nextReview}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: FINAL REVIEW & GENERATION */}
      {step === 3 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6 sm:p-8 space-y-6 animate-in fade-in">
          <div className="border-b border-slate-100 pb-4">
            <h3 className="font-bold text-base text-slate-900">{t.finalReviewTitle}</h3>
            <p className="text-xs text-slate-500 mt-0.5">{t.finalReviewDesc}</p>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <div className="font-bold text-slate-800 border-b border-slate-200 pb-1.5">
                {t.schoolAndExamSummary}
              </div>
              <div><span className="text-slate-500">{t.schoolName}:</span> <span className="font-semibold text-slate-800">{schoolName}</span></div>
              <div><span className="text-slate-500">{t.examName}:</span> <span className="font-semibold text-slate-800">{examTitle}</span></div>
              <div><span className="text-slate-500">{t.bookClass}:</span> <span className="font-semibold text-slate-800">Class {grade}th - {bookName}</span></div>
              <div><span className="text-slate-500">{t.duration}:</span> <span className="font-semibold text-slate-800">{duration}</span></div>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <div className="font-bold text-slate-800 border-b border-slate-200 pb-1.5">
                {t.marksAndScopeSummary}
              </div>
              <div><span className="text-slate-500">{t.totalMarks}:</span> <span className="font-bold text-blue-700">{totalMarks} Marks</span></div>
              <div><span className="text-slate-500">{t.unitLabel}:</span> <span className="font-semibold text-slate-800">{selectedUnit}</span></div>
              <div>
                <span className="text-slate-500">{t.availableChapters} ({selectedChapters.length}):</span>{" "}
                <span className="font-semibold text-slate-800">{selectedChapters.join(", ")}</span>
              </div>
              <div><span className="text-slate-500">Sets:</span> <span className="font-bold text-emerald-700">{t.singleSetOnly}</span></div>
            </div>
          </div>

          <MarksValidatorBadge
            configuredTotal={totalMarks}
            calculatedTotal={validationResult.calculated_total}
            errors={validationResult.errors}
          />

          {generationError && (
            <div className="bg-rose-50 border border-rose-300 p-4 rounded-xl text-xs text-rose-800 flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold">Error:</div>
                <div className="mt-0.5">{generationError}</div>
              </div>
            </div>
          )}

          <div className="flex justify-between items-center pt-4 border-t border-slate-100">
            <button
              onClick={() => setStep(2)}
              className="px-4 py-2 border border-slate-300 text-slate-700 font-semibold text-xs rounded-xl hover:bg-slate-50 cursor-pointer"
            >
              {t.backEditBlueprint}
            </button>

            <button
              onClick={handleGeneratePaper}
              disabled={isGenerating || !validationResult.is_valid}
              className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold text-sm rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {t.generatingWait}
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  {t.generatePaperBtn}
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

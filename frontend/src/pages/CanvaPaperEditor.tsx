import React, { useState, useEffect } from "react";
import {
  Save,
  Undo2,
  Redo2,
  Plus,
  Copy,
  Trash2,
  ArrowUp,
  ArrowDown,
  Download,
  CheckCircle2,
  AlertTriangle,
  RefreshCw
} from "lucide-react";
import { PaperData, QuestionItem } from "../types";
import { paperService } from "../services/api";
import { MarksValidatorBadge } from "../components/MarksValidatorBadge";
import { translations, Language } from "../services/translations";

interface CanvaPaperEditorProps {
  paperId: number | null;
  setCurrentTab: (tab: string) => void;
  lang?: Language;
}

export const CanvaPaperEditor: React.FC<CanvaPaperEditorProps> = ({
  paperId,
  setCurrentTab,
  lang = "hi"
}) => {
  const [paperData, setPaperData] = useState<PaperData | null>(null);
  const [history, setHistory] = useState<PaperData[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [regeneratingKey, setRegeneratingKey] = useState<string | null>(null);

  const t = translations[lang] || translations.hi;

  // Normalize text for duplicate checking
  const normalizeText = (text: string): string => {
    if (!text) return "";
    return text
      .toLowerCase()
      .replace(/[^\u0900-\u097F\w\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  };

  const getTokens = (text: string): Set<string> => {
    const norm = normalizeText(text);
    const words = norm.split(" ").filter((w) => w.length > 2);
    return new Set(words);
  };

  const areSimilarQuestions = (t1: string, t2: string): boolean => {
    const s1 = normalizeText(t1);
    const s2 = normalizeText(t2);
    if (!s1 || !s2) return false;
    if (s1 === s2) return true;
    if ((s1.includes(s2) || s2.includes(s1)) && Math.min(s1.length, s2.length) > 15) {
      return true;
    }
    const tok1 = getTokens(t1);
    const tok2 = getTokens(t2);
    if (tok1.size === 0 || tok2.size === 0) return false;
    let intersection = 0;
    tok1.forEach((tok) => {
      if (tok2.has(tok)) intersection++;
    });
    const union = new Set([...tok1, ...tok2]).size;
    return union > 0 && intersection / union >= 0.75;
  };

  const duplicateQuestionKeys = React.useMemo(() => {
    if (!paperData) return new Set<string>();
    const dupes = new Set<string>();
    const allQs: { key: string; text: string }[] = [];
    paperData.sections.forEach((sec, sIdx) => {
      sec.questions.forEach((q, qIdx) => {
        allQs.push({ key: `${sIdx}-${qIdx}`, text: q.question_text || "" });
      });
    });
    for (let i = 0; i < allQs.length; i++) {
      for (let j = i + 1; j < allQs.length; j++) {
        if (areSimilarQuestions(allQs[i].text, allQs[j].text)) {
          dupes.add(allQs[i].key);
          dupes.add(allQs[j].key);
        }
      }
    }
    return dupes;
  }, [paperData]);

  // Recalculate marks on each change
  const currentTotal = paperData
    ? paperData.sections.reduce(
        (acc, sec) =>
          acc +
          sec.questions.reduce((qAcc, q) => qAcc + (Number(q.marks) || 0), 0),
        0
      )
    : 0;

  const configuredTotal = paperData?.metadata?.total_marks || paperData?.total_marks || 0;
  const marksDifference = Math.abs(configuredTotal - currentTotal);
  const isMarksValid = marksDifference === 0;

  const handleRegenerateQuestion = async (sIdx: number, qIdx: number) => {
    if (!paperId) return;
    const key = `${sIdx}-${qIdx}`;
    setRegeneratingKey(key);
    try {
      const res = await paperService.regenerateQuestion(paperId, sIdx, qIdx);
      if (res.paper_data) {
        updateState(res.paper_data);
        setSaveMessage(
          lang === "hi"
            ? "प्रश्न सफलतापूर्वक पुनः उत्पन्न हुआ!"
            : "Question regenerated successfully!"
        );
        setTimeout(() => setSaveMessage(null), 3000);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Failed to regenerate question");
    } finally {
      setRegeneratingKey(null);
    }
  };

  useEffect(() => {
    if (paperId) {
      loadPaper(paperId);
    }
  }, [paperId]);

  const loadPaper = async (id: number) => {
    try {
      setLoading(true);
      const res = await paperService.getById(id);
      setPaperData(res.paper_data);
      setHistory([res.paper_data]);
      setHistoryIndex(0);
    } catch (e) {
      console.error("Failed to load paper", e);
    } finally {
      setLoading(false);
    }
  };

  const updateState = (newData: PaperData) => {
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push(newData);
    if (newHistory.length > 20) newHistory.shift();
    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
    setPaperData(newData);
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      setHistoryIndex(historyIndex - 1);
      setPaperData(history[historyIndex - 1]);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      setHistoryIndex(historyIndex + 1);
      setPaperData(history[historyIndex + 1]);
    }
  };

  const handleMetadataChange = (field: string, value: any) => {
    if (!paperData) return;
    const updated = {
      ...paperData,
      metadata: {
        ...paperData.metadata,
        [field]: value
      }
    };
    updateState(updated);
  };

  const handleQuestionTextChange = (sIdx: number, qIdx: number, text: string) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    newSections[sIdx].questions[qIdx].question_text = text;
    updateState({ ...paperData, sections: newSections });
  };

  const handleQuestionMarksChange = (sIdx: number, qIdx: number, marks: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    newSections[sIdx].questions[qIdx].marks = Number(marks);
    
    // Auto update section marks to match its questions
    const secSum = newSections[sIdx].questions.reduce((sum, q) => sum + (Number(q.marks) || 0), 0);
    newSections[sIdx].section_marks = secSum;
    
    updateState({ ...paperData, sections: newSections });
  };

  const handlePassageChange = (sIdx: number, qIdx: number, text: string) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    newSections[sIdx].questions[qIdx].passage = text;
    updateState({ ...paperData, sections: newSections });
  };

  const handleAddQuestion = (sIdx: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const qCount = newSections[sIdx].questions.length + 1;
    const newQ: QuestionItem = {
      question_number: `प्रश्न ${qCount}.`,
      question_text: "नया प्रश्न पाठ्यपुस्तक अनुसार लिखिए...",
      marks: 2,
      source_type: "teacher_created",
      chapter: "",
      source_confidence: "high",
      answer: ""
    };
    newSections[sIdx].questions.push(newQ);
    newSections[sIdx].section_marks += 2;
    updateState({ ...paperData, sections: newSections });
  };

  const handleDuplicateQuestion = (sIdx: number, qIdx: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const targetQ = newSections[sIdx].questions[qIdx];
    const dupQ: QuestionItem = {
      ...JSON.parse(JSON.stringify(targetQ)),
      question_number: `${targetQ.question_number} (प्रतिलिपि)`
    };
    newSections[sIdx].questions.splice(qIdx + 1, 0, dupQ);
    newSections[sIdx].section_marks += dupQ.marks;
    updateState({ ...paperData, sections: newSections });
  };

  const handleDeleteQuestion = (sIdx: number, qIdx: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const deletedMarks = newSections[sIdx].questions[qIdx].marks;
    newSections[sIdx].questions.splice(qIdx, 1);
    newSections[sIdx].section_marks = Math.max(0, newSections[sIdx].section_marks - deletedMarks);
    updateState({ ...paperData, sections: newSections });
  };

  const handleMoveQuestion = (sIdx: number, qIdx: number, direction: "up" | "down") => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const targetIdx = direction === "up" ? qIdx - 1 : qIdx + 1;
    if (targetIdx < 0 || targetIdx >= newSections[sIdx].questions.length) return;

    const temp = newSections[sIdx].questions[qIdx];
    newSections[sIdx].questions[qIdx] = newSections[sIdx].questions[targetIdx];
    newSections[sIdx].questions[targetIdx] = temp;
    updateState({ ...paperData, sections: newSections });
  };

  const handleSavePaper = async () => {
    if (!paperId || !paperData) return;

    if (!isMarksValid) {
      if (
        !window.confirm(
          lang === "hi"
            ? `चेतावनी: अंक असंगत हैं (अंतर: ${marksDifference} अंक)। क्या आप इसे प्रारूप (Draft) के रूप में सहेजना चाहते हैं?`
            : `Warning: Marks mismatch (difference: ${marksDifference} marks). Do you want to save as Draft?`
        )
      ) {
        return;
      }
    }

    setIsSaving(true);
    setSaveMessage(null);

    try {
      await paperService.update(paperId, paperData, isMarksValid);
      setSaveMessage(t.savedSuccess);
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (e: any) {
      alert("Save failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setIsSaving(false);
    }
  };

  const handleExportClick = () => {
    if (duplicateQuestionKeys.size > 0) {
      if (
        !window.confirm(
          lang === "hi"
            ? "चेतावनी: इस प्रश्नपत्रिका में दोहराए गए प्रश्न पाए गए हैं। क्या आप फिर भी निर्यात पृष्ठ पर जाना चाहते हैं?"
            : "Warning: Repeated questions detected in this paper. Do you still want to proceed to export?"
        )
      ) {
        return;
      }
    }
    setCurrentTab("export");
  };

  if (loading || !paperData) {
    return (
      <div className="p-12 text-center text-slate-500">
        {lang === "hi" ? "प्रश्नपत्रिका संपादक लोड हो रहा है..." : "Loading paper editor..."}
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-20 max-w-5xl mx-auto">
      {/* Editor Sticky Action Bar */}
      <div className="sticky top-18 z-40 bg-white/95 backdrop-blur-md border border-slate-200 shadow-sm rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center border border-slate-200 rounded-lg p-0.5 bg-slate-50">
            <button
              onClick={handleUndo}
              disabled={historyIndex <= 0}
              className="p-1.5 hover:bg-white rounded-md text-slate-700 disabled:opacity-30 cursor-pointer"
              title={t.undoTooltip}
            >
              <Undo2 className="w-4 h-4" />
            </button>
            <button
              onClick={handleRedo}
              disabled={historyIndex >= history.length - 1}
              className="p-1.5 hover:bg-white rounded-md text-slate-700 disabled:opacity-30 cursor-pointer"
              title={t.redoTooltip}
            >
              <Redo2 className="w-4 h-4" />
            </button>
          </div>

          <MarksValidatorBadge
            configuredTotal={configuredTotal}
            calculatedTotal={currentTotal}
            compact
          />
        </div>

        <div className="flex items-center gap-2">
          {saveMessage && (
            <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4" /> {saveMessage}
            </span>
          )}

          <button
            onClick={handleSavePaper}
            disabled={isSaving}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <Save className="w-4 h-4" />
            {isSaving ? t.savingWait : t.saveChanges}
          </button>

          <button
            onClick={handleExportClick}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <Download className="w-4 h-4" />
            {t.exportPdfWord}
          </button>
        </div>
      </div>

      {/* Duplicate Questions Warning Banner */}
      {duplicateQuestionKeys.size > 0 && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 flex items-start gap-3 shadow-xs animate-in fade-in">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-xs font-bold text-amber-900">
              {lang === "hi" ? "प्रश्न पुनरावृत्ति पाई गई" : "Duplicate Questions Detected"} ({duplicateQuestionKeys.size} {lang === "hi" ? "प्रश्न चिह्नित" : "questions flagged"})
            </h4>
            <p className="text-xs text-amber-800 mt-0.5">
              {t.duplicateWarningBanner}
            </p>
          </div>
        </div>
      )}

      {/* Canva-Style Visual A4 Sheet Container */}
      <div className="bg-slate-100 p-4 sm:p-8 rounded-2xl flex justify-center overflow-x-auto">
        <div
          className="bg-white text-black shadow-2xl rounded-xs p-8 sm:p-12 w-full max-w-[210mm] min-h-[297mm] border border-slate-300"
          style={{
            fontFamily: 'Arial, "Devanagari Sangam MN", "Arial Unicode MS", sans-serif'
          }}
        >
          {/* Header Block */}
          <div className="border-b-2 border-black pb-2 mb-3">
            <div className="flex items-center gap-4">
              {paperData.metadata?.has_logo && (
                <div className="w-20 shrink-0">
                  <img
                    src="/1000358221.png"
                    alt="Logo"
                    className="w-full h-auto object-contain"
                  />
                </div>
              )}
              <div className="flex-1 text-center">
                <input
                  type="text"
                  value={paperData.metadata?.school_name || ""}
                  onChange={(e) => handleMetadataChange("school_name", e.target.value)}
                  className="w-full text-center font-bold text-lg sm:text-xl font-serif text-black border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-hidden"
                />
                <input
                  type="text"
                  value={paperData.metadata?.tagline || ""}
                  onChange={(e) => handleMetadataChange("tagline", e.target.value)}
                  className="w-full text-center italic font-bold text-xs text-slate-700 border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-hidden mt-0.5"
                />
                <input
                  type="text"
                  value={paperData.metadata?.exam_title || ""}
                  onChange={(e) => handleMetadataChange("exam_title", e.target.value)}
                  className="w-full text-center font-bold text-sm sm:text-base text-black border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-hidden mt-1"
                />
              </div>
            </div>
          </div>

          {/* Details Table */}
          <div className="border-b-1.5 border-black pb-2 mb-4">
            <div className="grid grid-cols-4 text-xs font-bold text-black gap-2">
              <div>
                कक्षा:{" "}
                <input
                  type="text"
                  value={paperData.metadata?.class || "10"}
                  onChange={(e) => handleMetadataChange("class", e.target.value)}
                  className="w-16 border-b border-slate-300 focus:outline-hidden px-1 font-bold text-xs"
                />
                वीं
              </div>
              <div className="text-center">
                विषय:{" "}
                <input
                  type="text"
                  value={paperData.metadata?.subject || "हिंदी"}
                  onChange={(e) => handleMetadataChange("subject", e.target.value)}
                  className="w-32 border-b border-slate-300 focus:outline-hidden px-1 font-bold text-xs text-center"
                />
              </div>
              <div className="text-center">
                समय:{" "}
                <input
                  type="text"
                  value={paperData.metadata?.duration || "२ घंटे"}
                  onChange={(e) => handleMetadataChange("duration", e.target.value)}
                  className="w-20 border-b border-slate-300 focus:outline-hidden px-1 font-bold text-xs text-center"
                />
              </div>
              <div className="text-right">
                कुल अंक:{" "}
                <span className="text-blue-700 font-extrabold">{currentTotal}</span> /{" "}
                <input
                  type="number"
                  value={configuredTotal}
                  onChange={(e) => handleMetadataChange("total_marks", parseInt(e.target.value, 10) || 0)}
                  className="w-14 border-b border-slate-300 focus:outline-hidden px-1 font-bold text-xs text-right"
                />
              </div>
            </div>
          </div>

          {/* General Instructions Block */}
          <div className="border border-dashed border-slate-400 p-2.5 rounded-xs bg-slate-50 text-2xs mb-4">
            <div className="font-bold text-slate-800 mb-1">सूचनाएँ :</div>
            <ul className="list-disc pl-4 space-y-0.5 text-slate-700">
              {paperData.general_instructions?.map((inst, i) => (
                <li key={i}>{inst}</li>
              ))}
            </ul>
          </div>

          {/* Sections & Questions */}
          <div className="space-y-6">
            {paperData.sections.map((sec, sIdx) => (
              <div key={sIdx} className="space-y-3">
                {/* Section Title Banner */}
                <div className="bg-slate-100 border border-black p-1.5 flex justify-between items-center text-xs font-bold">
                  <input
                    type="text"
                    value={sec.section_title}
                    onChange={(e) => {
                      const newSecs = [...paperData.sections];
                      newSecs[sIdx].section_title = e.target.value;
                      updateState({ ...paperData, sections: newSecs });
                    }}
                    className="flex-1 bg-transparent font-bold text-center focus:outline-hidden"
                  />
                  <span className="text-slate-800 shrink-0">
                    ({sec.section_marks} अंक)
                  </span>
                </div>

                {/* Questions */}
                {sec.questions.map((q, qIdx) => {
                  const qKey = `${sIdx}-${qIdx}`;
                  const isDuplicate = duplicateQuestionKeys.has(qKey);
                  const isRegenerating = regeneratingKey === qKey;

                  return (
                    <div
                      key={qIdx}
                      className={`group relative border rounded-lg p-3 transition-all ${
                        isDuplicate
                          ? "border-amber-400 bg-amber-50/30 ring-1 ring-amber-400"
                          : "border-slate-200 hover:border-blue-400 bg-white"
                      }`}
                    >
                      {/* Floating Question Action Buttons */}
                      <div className="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-white/95 backdrop-blur-xs p-1 rounded-md border border-slate-200 shadow-xs z-10">
                        <button
                          onClick={() => handleRegenerateQuestion(sIdx, qIdx)}
                          disabled={isRegenerating}
                          className="p-1 text-slate-500 hover:text-indigo-600 disabled:opacity-30 cursor-pointer"
                          title={t.regenerateQuestionBtn}
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? "animate-spin text-indigo-600" : ""}`} />
                        </button>
                        <button
                          onClick={() => handleMoveQuestion(sIdx, qIdx, "up")}
                          disabled={qIdx === 0}
                          className="p-1 text-slate-500 hover:text-slate-800 disabled:opacity-30 cursor-pointer"
                          title="Move Up"
                        >
                          <ArrowUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleMoveQuestion(sIdx, qIdx, "down")}
                          disabled={qIdx === sec.questions.length - 1}
                          className="p-1 text-slate-500 hover:text-slate-800 disabled:opacity-30 cursor-pointer"
                          title="Move Down"
                        >
                          <ArrowDown className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDuplicateQuestion(sIdx, qIdx)}
                          className="p-1 text-slate-500 hover:text-blue-600 cursor-pointer"
                          title="Duplicate"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteQuestion(sIdx, qIdx)}
                          className="p-1 text-slate-500 hover:text-rose-600 cursor-pointer"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Duplicate Warning Tag on Question Card */}
                      {isDuplicate && (
                        <div className="mb-2 flex items-center justify-between bg-amber-100/90 border border-amber-300 text-amber-900 px-2.5 py-1 rounded text-2xs font-semibold">
                          <span className="flex items-center gap-1.5 font-bold">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                            {t.duplicateQuestionBadge}
                          </span>
                          <button
                            onClick={() => handleRegenerateQuestion(sIdx, qIdx)}
                            disabled={isRegenerating}
                            className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-500 hover:bg-amber-600 text-white rounded font-bold text-2xs transition-colors cursor-pointer"
                          >
                            <RefreshCw className={`w-2.5 h-2.5 ${isRegenerating ? "animate-spin" : ""}`} />
                            {isRegenerating ? t.regeneratingQuestion : t.regenerateQuestionBtn}
                          </button>
                        </div>
                      )}

                      {/* Question Row */}
                      <div className="flex justify-between items-start gap-3">
                        <div className="flex-1 flex gap-2">
                          <span className="font-bold text-xs text-slate-900 shrink-0">
                            {q.question_number}
                          </span>
                          <textarea
                            rows={2}
                            value={q.question_text}
                            onChange={(e) => handleQuestionTextChange(sIdx, qIdx, e.target.value)}
                            className="w-full text-xs font-bold text-slate-900 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-hidden resize-none"
                          />
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <input
                            type="number"
                            min="1"
                            value={q.marks}
                            onChange={(e) => handleQuestionMarksChange(sIdx, qIdx, parseInt(e.target.value, 10) || 0)}
                            className="w-12 px-1 py-0.5 border border-slate-300 rounded text-right text-xs font-bold"
                          />
                          <span className="text-xs font-bold text-slate-700">अंक</span>
                        </div>
                      </div>

                      {/* Passage / Stanza if present */}
                      {q.passage !== undefined && (
                        <div className="mt-2.5">
                          <label className="block text-2xs font-semibold text-slate-500 mb-0.5">
                            {q.is_poem ? "पद्यांश पंक्तियाँ (Poem Stanza):" : "पठित गद्यांश (Prose Passage):"}
                          </label>
                          <textarea
                            rows={4}
                            value={q.passage}
                            onChange={(e) => handlePassageChange(sIdx, qIdx, e.target.value)}
                            className={`w-full p-2.5 text-xs rounded-md border border-black bg-slate-50/50 leading-relaxed focus:bg-white focus:outline-hidden ${
                              q.is_poem ? "text-center" : "text-justify"
                            }`}
                          />
                        </div>
                      )}

                      {/* Sub-questions display */}
                      {q.sub_questions && q.sub_questions.length > 0 && (
                        <div className="mt-2.5 pl-3 border-l-2 border-slate-200 space-y-2">
                          {q.sub_questions.map((sub, subIdx) => (
                            <div key={subIdx} className="text-xs space-y-1">
                              <div className="flex justify-between items-start">
                                <span className="font-semibold text-slate-800">
                                  {sub.sub_number} {sub.sub_text}
                                </span>
                                <span className="text-slate-600 font-bold">({sub.marks} अंक)</span>
                              </div>
                              {sub.items && sub.items.length > 0 && (
                                <ul className="pl-4 list-disc text-2xs text-slate-600 space-y-0.5">
                                  {sub.items.map((it, itIdx) => (
                                    <li key={itIdx}>{it}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Add Question Button in Section */}
                <div className="flex justify-center pt-1">
                  <button
                    onClick={() => handleAddQuestion(sIdx)}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-2xs font-bold rounded-md transition-colors cursor-pointer"
                  >
                    <Plus className="w-3 h-3" /> {t.addQuestionToSection}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Mandatory Paper Footer */}
          <div className="text-center font-bold text-sm mt-8 pt-4 border-t border-slate-200 text-black">
            {t.allTheBestFooter}
          </div>
        </div>
      </div>
    </div>
  );
};

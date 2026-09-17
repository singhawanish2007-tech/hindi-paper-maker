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
  RefreshCw,
  FileText
} from "lucide-react";
import { PaperData, QuestionItem } from "../types";
import { paperService } from "../services/api";
import { MarksValidatorBadge } from "../components/MarksValidatorBadge";
import { translations, Language } from "../services/translations";
import { FormattedText } from "../components/FormattedText";

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
  const [regeneratingSubKey, setRegeneratingSubKey] = useState<string | null>(null);

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

  const handleRegenerateSubQuestion = async (sIdx: number, qIdx: number, subIdx: number) => {
    if (!paperId) return;
    const key = `${sIdx}-${qIdx}-${subIdx}`;
    setRegeneratingSubKey(key);
    try {
      const res = await paperService.regenerateSubQuestion(paperId, sIdx, qIdx, subIdx);
      if (res.paper_data) {
        updateState(res.paper_data);
        setSaveMessage(
          lang === "hi"
            ? "उपप्रश्न सफलतापूर्वक पुनः उत्पन्न हुआ!"
            : "Subquestion regenerated successfully!"
        );
        setTimeout(() => setSaveMessage(null), 3000);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Failed to regenerate subquestion");
    } finally {
      setRegeneratingSubKey(null);
    }
  };

  const handleSubQuestionTextChange = (sIdx: number, qIdx: number, subIdx: number, text: string) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const targetSub = newSections[sIdx].questions[qIdx].sub_questions?.[subIdx];
    if (targetSub) {
      targetSub.sub_text = text;
      updateState({ ...paperData, sections: newSections });
    }
  };

  const handleSubQuestionNumberChange = (sIdx: number, qIdx: number, subIdx: number, num: string) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const targetSub = newSections[sIdx].questions[qIdx].sub_questions?.[subIdx];
    if (targetSub) {
      targetSub.sub_number = num;
      updateState({ ...paperData, sections: newSections });
    }
  };

  const handleSubQuestionMarksChange = (sIdx: number, qIdx: number, subIdx: number, marks: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const q = newSections[sIdx].questions[qIdx];
    if (q.sub_questions && q.sub_questions[subIdx]) {
      q.sub_questions[subIdx].marks = Number(marks) || 0;
      q.marks = q.sub_questions.reduce((sum, s) => sum + (Number(s.marks) || 0), 0);
      newSections[sIdx].section_marks = newSections[sIdx].questions.reduce((sum, item) => sum + (Number(item.marks) || 0), 0);
      updateState({ ...paperData, sections: newSections });
    }
  };

  const handleAddSubQuestion = (sIdx: number, qIdx: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const q = newSections[sIdx].questions[qIdx];
    if (!q.sub_questions) {
      q.sub_questions = [];
    }
    const devanagariNums = ["(१)", "(२)", "(३)", "(४)", "(५)", "(६)", "(७)", "(८)", "(९)", "(१०)"];
    const nextIdx = q.sub_questions.length;
    const label = nextIdx < devanagariNums.length ? devanagariNums[nextIdx] : `(${nextIdx + 1})`;
    
    q.sub_questions.push({
      id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `sub-${Date.now()}-${Math.random()}`,
      sub_number: label,
      sub_text: "नया उपप्रश्न यहाँ लिखें...",
      marks: 1,
      items: [],
      answer: ""
    });
    q.marks = q.sub_questions.reduce((sum, s) => sum + (Number(s.marks) || 0), 0);
    newSections[sIdx].section_marks = newSections[sIdx].questions.reduce((sum, item) => sum + (Number(item.marks) || 0), 0);
    updateState({ ...paperData, sections: newSections });
  };

  const handleDeleteSubQuestion = (sIdx: number, qIdx: number, subIdx: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const q = newSections[sIdx].questions[qIdx];
    if (q.sub_questions) {
      q.sub_questions.splice(subIdx, 1);
      q.marks = q.sub_questions.reduce((sum, s) => sum + (Number(s.marks) || 0), 0);
      newSections[sIdx].section_marks = newSections[sIdx].questions.reduce((sum, item) => sum + (Number(item.marks) || 0), 0);
      updateState({ ...paperData, sections: newSections });
    }
  };

  const handleDuplicateSubQuestion = (sIdx: number, qIdx: number, subIdx: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const q = newSections[sIdx].questions[qIdx];
    if (q.sub_questions && q.sub_questions[subIdx]) {
      const source = q.sub_questions[subIdx];
      const cloned = {
        ...JSON.parse(JSON.stringify(source)),
        id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `sub-${Date.now()}-${Math.random()}`,
        sub_number: `${source.sub_number} (प्रतिलिपि)`
      };
      q.sub_questions.splice(subIdx + 1, 0, cloned);
      q.marks = q.sub_questions.reduce((sum, s) => sum + (Number(s.marks) || 0), 0);
      newSections[sIdx].section_marks = newSections[sIdx].questions.reduce((sum, item) => sum + (Number(item.marks) || 0), 0);
      updateState({ ...paperData, sections: newSections });
    }
  };

  const handleMoveSubQuestion = (sIdx: number, qIdx: number, subIdx: number, direction: "up" | "down") => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const q = newSections[sIdx].questions[qIdx];
    if (!q.sub_questions) return;
    const targetIdx = direction === "up" ? subIdx - 1 : subIdx + 1;
    if (targetIdx < 0 || targetIdx >= q.sub_questions.length) return;
    const temp = q.sub_questions[subIdx];
    q.sub_questions[subIdx] = q.sub_questions[targetIdx];
    q.sub_questions[targetIdx] = temp;
    updateState({ ...paperData, sections: newSections });
  };

  const handleTogglePoem = (sIdx: number, qIdx: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    newSections[sIdx].questions[qIdx].is_poem = !newSections[sIdx].questions[qIdx].is_poem;
    updateState({ ...paperData, sections: newSections });
  };

  const handleInstructionChange = (idx: number, text: string) => {
    if (!paperData) return;
    const newInsts = [...(paperData.general_instructions || [])];
    newInsts[idx] = text;
    updateState({ ...paperData, general_instructions: newInsts });
  };

  const handleAddInstruction = () => {
    if (!paperData) return;
    const newInsts = [...(paperData.general_instructions || []), "नई परीक्षा सूचना यहाँ लिखें..."];
    updateState({ ...paperData, general_instructions: newInsts });
  };

  const handleDeleteInstruction = (idx: number) => {
    if (!paperData) return;
    const newInsts = [...(paperData.general_instructions || [])];
    newInsts.splice(idx, 1);
    updateState({ ...paperData, general_instructions: newInsts });
  };

  const handleSubItemChange = (sIdx: number, qIdx: number, subIdx: number, itemIdx: number, text: string) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const sub = newSections[sIdx].questions[qIdx].sub_questions?.[subIdx];
    if (sub && sub.items) {
      sub.items[itemIdx] = text;
      updateState({ ...paperData, sections: newSections });
    }
  };

  const handleAddSubItem = (sIdx: number, qIdx: number, subIdx: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const sub = newSections[sIdx].questions[qIdx].sub_questions?.[subIdx];
    if (sub) {
      if (!sub.items) sub.items = [];
      sub.items.push(`घटक ${sub.items.length + 1} : ....................`);
      updateState({ ...paperData, sections: newSections });
    }
  };

  const handleDeleteSubItem = (sIdx: number, qIdx: number, subIdx: number, itemIdx: number) => {
    if (!paperData) return;
    const newSections = [...paperData.sections];
    const sub = newSections[sIdx].questions[qIdx].sub_questions?.[subIdx];
    if (sub && sub.items) {
      sub.items.splice(itemIdx, 1);
      updateState({ ...paperData, sections: newSections });
    }
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
          <div className="border border-dashed border-slate-400 p-3 rounded-xs bg-slate-50 text-2xs mb-4 space-y-2">
            <div className="flex justify-between items-center">
              <div className="font-bold text-slate-800">सूचनाएँ (General Instructions) :</div>
              <button
                type="button"
                onClick={handleAddInstruction}
                className="inline-flex items-center gap-1 text-2xs px-2 py-0.5 bg-white hover:bg-slate-200 border border-slate-300 rounded font-semibold text-slate-700 cursor-pointer"
              >
                <Plus className="w-3 h-3" /> {t.addInstruction}
              </button>
            </div>
            <div className="space-y-1.5">
              {paperData.general_instructions?.map((inst, i) => (
                <div key={i} className="flex items-start gap-2 group/inst">
                  <span className="font-bold text-slate-500 mt-1">•</span>
                  <div className="flex-1">
                    <input
                      type="text"
                      value={inst}
                      onChange={(e) => handleInstructionChange(i, e.target.value)}
                      placeholder={t.instructionPlaceholder}
                      className="w-full text-2xs text-slate-800 bg-white/70 border border-transparent hover:border-slate-300 focus:border-blue-500 rounded px-1.5 py-0.5 focus:outline-hidden"
                    />
                    {inst.includes("<") && (
                      <div className="text-3xs text-slate-500 pl-1 mt-0.5">
                        <FormattedText text={inst} />
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteInstruction(i)}
                    className="opacity-0 group-hover/inst:opacity-100 p-1 text-slate-400 hover:text-rose-600 transition-opacity cursor-pointer"
                    title="Delete Instruction"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
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
                        <div className="flex-1 flex flex-col gap-1">
                          <div className="flex items-start gap-2">
                            <span className="font-bold text-xs text-slate-900 shrink-0 mt-0.5">
                              {q.question_number}
                            </span>
                            <textarea
                              rows={2}
                              value={q.question_text}
                              onChange={(e) => handleQuestionTextChange(sIdx, qIdx, e.target.value)}
                              className="w-full text-xs font-bold text-slate-900 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-hidden resize-none"
                            />
                          </div>
                          {q.question_text?.includes("<") && (
                            <div className="text-2xs text-slate-600 bg-slate-50 px-2 py-1 rounded border border-slate-200 mt-0.5 flex items-center gap-1">
                              <span className="font-bold text-slate-400 text-3xs shrink-0">{t.formattedPreviewLabel}</span>
                              <FormattedText text={q.question_text} />
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <input
                            type="number"
                            min="0"
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
                          <div className="flex justify-between items-center mb-0.5">
                            <label className="text-2xs font-semibold text-slate-500">
                              {q.is_poem ? "पद्यांश पंक्तियाँ (Poem Stanza):" : "पठित गद्यांश (Prose Passage):"}
                            </label>
                            <button
                              type="button"
                              onClick={() => handleTogglePoem(sIdx, qIdx)}
                              className="text-3xs px-2 py-0.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-700 font-semibold cursor-pointer border border-slate-300"
                            >
                              {q.is_poem ? "गद्यांश रूप में बदलें" : "पद्यांश रूप में बदलें"}
                            </button>
                          </div>
                          <textarea
                            rows={4}
                            value={q.passage}
                            onChange={(e) => handlePassageChange(sIdx, qIdx, e.target.value)}
                            className={`w-full p-2.5 text-xs rounded-md border border-black bg-slate-50/50 leading-relaxed focus:bg-white focus:outline-hidden ${
                              q.is_poem ? "text-center" : "text-justify"
                            }`}
                          />
                          {q.passage?.includes("<") && (
                            <div className="text-2xs text-slate-600 bg-slate-50 p-2 rounded border border-slate-200 mt-1">
                              <span className="font-bold text-slate-400 text-3xs block mb-0.5">{t.formattedPreviewLabel}</span>
                              <FormattedText text={q.passage} />
                            </div>
                          )}
                        </div>
                      )}

                      {/* Sub-questions Section */}
                      <div className="mt-3 pl-3 border-l-2 border-indigo-200 space-y-2.5">
                        {q.sub_questions && q.sub_questions.map((sub, subIdx) => {
                          const subKey = `${sIdx}-${qIdx}-${subIdx}`;
                          const isSubRegenerating = regeneratingSubKey === subKey;

                          return (
                            <div
                              key={sub.id || subIdx}
                              className="group/sub relative bg-slate-50/80 hover:bg-slate-50 border border-slate-200 hover:border-indigo-300 rounded-lg p-2.5 transition-all text-xs"
                            >
                              {/* Subquestion Floating Actions */}
                              <div className="absolute top-1.5 right-1.5 flex items-center gap-0.5 opacity-0 group-hover/sub:opacity-100 transition-opacity bg-white/95 backdrop-blur-xs p-0.5 rounded border border-slate-200 shadow-xs z-10">
                                <button
                                  type="button"
                                  onClick={() => handleRegenerateSubQuestion(sIdx, qIdx, subIdx)}
                                  disabled={isSubRegenerating}
                                  className="p-1 text-slate-500 hover:text-indigo-600 disabled:opacity-30 cursor-pointer"
                                  title={t.regenerateSubQuestionBtn}
                                >
                                  <RefreshCw className={`w-3 h-3 ${isSubRegenerating ? "animate-spin text-indigo-600" : ""}`} />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleMoveSubQuestion(sIdx, qIdx, subIdx, "up")}
                                  disabled={subIdx === 0}
                                  className="p-1 text-slate-500 hover:text-slate-800 disabled:opacity-30 cursor-pointer"
                                  title="Move Up"
                                >
                                  <ArrowUp className="w-3 h-3" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleMoveSubQuestion(sIdx, qIdx, subIdx, "down")}
                                  disabled={subIdx === (q.sub_questions?.length || 0) - 1}
                                  className="p-1 text-slate-500 hover:text-slate-800 disabled:opacity-30 cursor-pointer"
                                  title="Move Down"
                                >
                                  <ArrowDown className="w-3 h-3" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDuplicateSubQuestion(sIdx, qIdx, subIdx)}
                                  className="p-1 text-slate-500 hover:text-blue-600 cursor-pointer"
                                  title="Duplicate"
                                >
                                  <Copy className="w-3 h-3" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteSubQuestion(sIdx, qIdx, subIdx)}
                                  className="p-1 text-slate-500 hover:text-rose-600 cursor-pointer"
                                  title="Delete"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </button>
                              </div>

                              {/* Subquestion Header & Inputs */}
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex items-start gap-1.5 flex-1">
                                  <input
                                    type="text"
                                    value={sub.sub_number}
                                    onChange={(e) => handleSubQuestionNumberChange(sIdx, qIdx, subIdx, e.target.value)}
                                    className="w-12 font-bold text-slate-800 border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-hidden shrink-0"
                                  />
                                  <div className="flex-1">
                                    <textarea
                                      rows={1}
                                      value={sub.sub_text}
                                      onChange={(e) => handleSubQuestionTextChange(sIdx, qIdx, subIdx, e.target.value)}
                                      className="w-full text-slate-900 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-hidden resize-none font-medium"
                                    />
                                    {sub.sub_text?.includes("<") && (
                                      <div className="text-3xs text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200 mt-0.5 flex items-center gap-1">
                                        <span className="font-bold text-slate-400 shrink-0">{t.formattedPreviewLabel}</span>
                                        <FormattedText text={sub.sub_text} />
                                      </div>
                                    )}
                                  </div>
                                </div>
                                <div className="flex items-center gap-1 shrink-0 ml-2">
                                  <input
                                    type="number"
                                    min="0"
                                    value={sub.marks}
                                    onChange={(e) => handleSubQuestionMarksChange(sIdx, qIdx, subIdx, parseInt(e.target.value, 10) || 0)}
                                    className="w-10 px-1 py-0.5 border border-slate-300 rounded text-right text-2xs font-bold"
                                  />
                                  <span className="text-2xs text-slate-500 font-semibold">अंक</span>
                                </div>
                              </div>

                              {/* Items list */}
                              {sub.items && sub.items.length > 0 && (
                                <div className="mt-2 pl-4 space-y-1">
                                  {sub.items.map((it, itIdx) => (
                                    <div key={itIdx} className="flex items-center gap-1.5 group/it">
                                      <span className="text-3xs text-slate-400">•</span>
                                      <input
                                        type="text"
                                        value={it}
                                        onChange={(e) => handleSubItemChange(sIdx, qIdx, subIdx, itIdx, e.target.value)}
                                        className="flex-1 text-2xs text-slate-700 bg-white/80 border border-transparent hover:border-slate-300 focus:border-blue-500 rounded px-1 py-0.5"
                                      />
                                      <button
                                        type="button"
                                        onClick={() => handleDeleteSubItem(sIdx, qIdx, subIdx, itIdx)}
                                        className="opacity-0 group-hover/it:opacity-100 p-0.5 text-slate-400 hover:text-rose-600 transition-opacity cursor-pointer"
                                      >
                                        <Trash2 className="w-2.5 h-2.5" />
                                      </button>
                                    </div>
                                  ))}
                                  <button
                                    type="button"
                                    onClick={() => handleAddSubItem(sIdx, qIdx, subIdx)}
                                    className="text-3xs text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-0.5 pt-0.5 cursor-pointer"
                                  >
                                    <Plus className="w-2.5 h-2.5" /> घटक जोड़ें
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        })}

                        {/* Add Subquestion Button */}
                        <div className="pt-1">
                          <button
                            type="button"
                            onClick={() => handleAddSubQuestion(sIdx, qIdx)}
                            className="inline-flex items-center gap-1 text-2xs px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold rounded-md transition-colors cursor-pointer border border-indigo-200"
                          >
                            <Plus className="w-3 h-3" /> {t.addSubQuestion}
                          </button>
                        </div>
                      </div>
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

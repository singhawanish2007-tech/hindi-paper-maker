import React, { useState, useEffect } from "react";
import { Key, Download, ArrowLeft, Edit3 } from "lucide-react";
import { AnswerKeyData } from "../types";
import { paperService } from "../services/api";
import { translations, Language } from "../services/translations";

interface AnswerKeyViewProps {
  paperId: number | null;
  setCurrentTab: (tab: string) => void;
  lang?: Language;
}

export const AnswerKeyView: React.FC<AnswerKeyViewProps> = ({
  paperId,
  setCurrentTab,
  lang = "hi"
}) => {
  const [keyData, setKeyData] = useState<AnswerKeyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const t = translations[lang] || translations.hi;

  useEffect(() => {
    if (paperId) {
      loadAnswerKey(paperId);
    }
  }, [paperId]);

  const loadAnswerKey = async (id: number) => {
    try {
      setLoading(true);
      const data = await paperService.getAnswerKey(id);
      setKeyData(data);
    } catch (e) {
      console.error("Failed to load answer key", e);
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (index: number, newAnswer: string) => {
    if (!keyData) return;
    const updated = [...keyData.answers];
    updated[index].expected_answer = newAnswer;
    setKeyData({ ...keyData, answers: updated });
  };

  if (loading || !keyData) {
    return (
      <div className="p-12 text-center text-slate-500">
        {lang === "hi" ? "उत्तरतालिका लोड हो रही है..." : "Loading answer key..."}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-16">
      {/* Header Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentTab("editor")}
              className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-600 transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Key className="w-5 h-5 text-indigo-600" />
              {t.modelAnswerKey}
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1 ml-8">
            {keyData.exam_title} • {lang === "hi" ? "कुल अंक" : "Total Marks"}: {keyData.total_marks}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentTab("export")}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
          >
            <Download className="w-4 h-4" />
            {lang === "hi" ? "उत्तरतालिका सहित DOCX डाउनलोड" : "Download DOCX with Answer Key"}
          </button>
        </div>
      </div>

      {/* Answer Cards */}
      <div className="space-y-4">
        {keyData.answers.map((item, idx) => (
          <div
            key={idx}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3 hover:border-indigo-300 transition-colors"
          >
            <div className="flex justify-between items-start">
              <div>
                <span className="text-xs font-bold text-indigo-600">
                  {item.section_title}
                </span>
                <h4 className="font-bold text-sm text-slate-900 mt-0.5">
                  {item.question_number} {item.question_text}
                </h4>
              </div>
              <div className="flex items-center gap-2">
                {item.teacher_verification_required && (
                  <span className="bg-amber-100 text-amber-800 text-2xs font-semibold px-2 py-0.5 rounded-md flex items-center gap-1">
                    {t.teacherVerificationRequired}
                  </span>
                )}
                <span className="bg-slate-100 text-slate-800 text-xs font-bold px-2 py-0.5 rounded-md">
                  {item.marks} {lang === "hi" ? "अंक" : "Marks"}
                </span>
              </div>
            </div>

            {/* Editable Answer Box */}
            <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200">
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-2xs font-bold text-slate-500 uppercase">
                  {lang === "hi" ? "अपेक्षित उत्तर (Model Answer):" : "Model Answer:"}
                </span>
                <button
                  onClick={() => setEditingIndex(editingIndex === idx ? null : idx)}
                  className="text-2xs font-semibold text-blue-600 hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <Edit3 className="w-3 h-3" />
                  {editingIndex === idx
                    ? (lang === "hi" ? "संपादन बंद करें" : "Done Editing")
                    : (lang === "hi" ? "संपादित करें" : "Edit Answer")}
                </button>
              </div>

              {editingIndex === idx ? (
                <textarea
                  rows={3}
                  value={item.expected_answer}
                  onChange={(e) => handleAnswerChange(idx, e.target.value)}
                  className="w-full text-xs text-slate-800 p-2 bg-white border border-blue-400 rounded-md focus:outline-hidden"
                />
              ) : (
                <p className="text-xs text-slate-800 leading-relaxed">
                  {item.expected_answer}
                </p>
              )}

              {item.points && item.points.length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-200/80">
                  <span className="text-2xs font-bold text-slate-500">
                    {lang === "hi" ? "मूल्यांकन बिंदु:" : "Marking Scheme Points:"}
                  </span>
                  <ul className="list-disc pl-4 text-2xs text-slate-600 mt-1 space-y-0.5">
                    {item.points.map((pt, pIdx) => (
                      <li key={pIdx}>{pt}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

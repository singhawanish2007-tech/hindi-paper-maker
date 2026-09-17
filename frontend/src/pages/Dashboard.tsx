import React, { useEffect, useState } from "react";
import {
  BookOpen,
  FileText,
  Clock,
  Download,
  Edit3,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  ArrowRight
} from "lucide-react";
import { Textbook, PaperSummary } from "../types";
import { textbookService, paperService } from "../services/api";
import { translations, Language } from "../services/translations";

interface DashboardProps {
  setCurrentTab: (tab: string) => void;
  setActivePaperId: (id: number) => void;
  lang?: Language;
}

export const Dashboard: React.FC<DashboardProps> = ({
  setCurrentTab,
  setActivePaperId,
  lang = "hi"
}) => {
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [papers, setPapers] = useState<PaperSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const t = translations[lang] || translations.hi;

  const loadData = async () => {
    try {
      setLoading(true);
      const [tbList, pList] = await Promise.all([
        textbookService.getAll(),
        paperService.getAll()
      ]);
      setTextbooks(tbList);
      setPapers(pList);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDeletePaper = async (id: number) => {
    if (!window.confirm(t.deleteConfirm)) return;
    try {
      await paperService.delete(id);
      loadData();
    } catch (err) {
      alert("Error deleting paper: " + err);
    }
  };

  return (
    <div className="space-y-6 sm:space-y-8 pb-12 w-full max-w-full overflow-hidden">
      {/* Hero Welcome Banner */}
      <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-sky-700 rounded-2xl p-5 sm:p-8 text-white shadow-lg relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/30 backdrop-blur-xs border border-blue-400/40 text-xs font-semibold mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{t.heroBadge}</span>
          </div>
          <h1 className="text-xl sm:text-2xl md:text-3xl font-extrabold tracking-tight break-words">
            {t.heroTitle}
          </h1>
          <p className="mt-2 text-blue-100 text-xs sm:text-sm md:text-base leading-relaxed">
            {t.heroDesc}
          </p>

          <div className="mt-5 sm:mt-6 flex flex-col sm:flex-row flex-wrap gap-2.5 sm:gap-3">
            <button
              onClick={() => setCurrentTab("generate")}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-white text-blue-800 font-bold text-sm rounded-xl shadow-md hover:bg-blue-50 transition-all cursor-pointer w-full sm:w-auto"
            >
              <Sparkles className="w-4 h-4 text-blue-600" />
              {t.startGenerating}
            </button>
            <button
              onClick={() => setCurrentTab("upload")}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-800/60 hover:bg-blue-800/80 border border-blue-400/30 text-white font-medium text-sm rounded-xl transition-all cursor-pointer w-full sm:w-auto"
            >
              <BookOpen className="w-4 h-4" />
              {t.uploadTextbookBtn}
            </button>
          </div>
        </div>
      </div>

      {/* Quick Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs flex items-center gap-3.5 sm:gap-4 min-w-0">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg shrink-0">
            <BookOpen className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <div className="text-2xl font-bold text-slate-800">{textbooks.length}</div>
            <div className="text-xs text-slate-500 truncate">{t.metricsBooks}</div>
          </div>
        </div>

        <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs flex items-center gap-3.5 sm:gap-4 min-w-0">
          <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg shrink-0">
            <FileText className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <div className="text-2xl font-bold text-slate-800">{papers.length}</div>
            <div className="text-xs text-slate-500 truncate">{t.metricsPapers}</div>
          </div>
        </div>

        <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-xs flex items-center gap-3.5 sm:gap-4 sm:col-span-2 lg:col-span-1 min-w-0">
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg shrink-0">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div className="min-w-0">
            <div className="text-2xl font-bold text-slate-800">100%</div>
            <div className="text-xs text-slate-500 truncate">{t.metricsStandard}</div>
          </div>
        </div>
      </div>

      {/* Recent Papers Section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-4 sm:px-6 py-3.5 sm:py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600 shrink-0" />
            <h2 className="font-bold text-sm sm:text-base text-slate-900 truncate">{t.recentPapers}</h2>
          </div>
          <button
            onClick={() => setCurrentTab("generate")}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer shrink-0"
          >
            <span className="hidden sm:inline">{t.newPaperLink}</span>
            <span className="sm:hidden">+</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="divide-y divide-slate-100">
          {papers.length === 0 ? (
            <div className="p-6 sm:p-8 text-center">
              <FileText className="w-10 sm:w-12 h-10 sm:h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-600 font-medium text-sm">{t.noPapersYet}</p>
              <p className="text-slate-400 text-xs mt-1">
                {t.noPapersDesc}
              </p>
              <button
                onClick={() => setCurrentTab("generate")}
                className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs rounded-lg transition-colors cursor-pointer"
              >
                {t.createFirstPaper}
              </button>
            </div>
          ) : (
            papers.map((p) => (
              <div key={p.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 hover:bg-slate-50 transition-colors min-w-0">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                    <span className="font-bold text-slate-900 text-sm sm:text-base break-words">
                      {p.title}
                    </span>
                    <span className="bg-slate-100 text-slate-700 text-2xs sm:text-xs px-2 py-0.5 rounded-full font-medium shrink-0">
                      {t.classLabel} {p.grade}
                    </span>
                    <span className="bg-blue-100 text-blue-800 text-2xs sm:text-xs px-2 py-0.5 rounded-full font-bold shrink-0">
                      {p.total_marks} {t.marksLabel}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-2.5 sm:gap-x-4 gap-y-1 text-2xs sm:text-xs text-slate-500 mt-1">
                    <span className="truncate max-w-[200px]">{p.school_name}</span>
                    <span>•</span>
                    <span>{t.durationLabel}: {p.duration}</span>
                    <span>•</span>
                    <span>{new Date(p.created_at).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-US")}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 pt-1 sm:pt-0">
                  <button
                    onClick={() => {
                      setActivePaperId(p.id);
                      setCurrentTab("editor");
                    }}
                    className="flex-1 sm:flex-none justify-center inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    {t.editBtn}
                  </button>

                  <button
                    onClick={() => {
                      setActivePaperId(p.id);
                      setCurrentTab("export");
                    }}
                    className="flex-1 sm:flex-none justify-center inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" />
                    {t.downloadBtn}
                  </button>

                  <button
                    onClick={() => handleDeletePaper(p.id)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer shrink-0"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Uploaded Textbooks Grid */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-4 sm:px-6 py-3.5 sm:py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-indigo-600 shrink-0" />
            <h2 className="font-bold text-sm sm:text-base text-slate-900 truncate">{t.textbooksAndUnits}</h2>
          </div>
          <button
            onClick={() => setCurrentTab("upload")}
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer shrink-0"
          >
            {t.newPdfUpload}
          </button>
        </div>

        <div className="p-4 sm:p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {textbooks.map((tb) => (
            <div key={tb.id} className="border border-slate-200 rounded-xl p-4 hover:border-blue-300 transition-colors bg-white min-w-0">
              <div className="flex justify-between items-start gap-2">
                <span className="bg-indigo-50 text-indigo-700 text-xs font-bold px-2 py-0.5 rounded-md shrink-0">
                  {t.classLabel} {tb.grade}
                </span>
                {tb.ocr_warning && (
                  <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 text-2xs sm:text-xs px-2 py-0.5 rounded-md font-semibold shrink-0">
                    <AlertTriangle className="w-3 h-3" /> OCR Notice
                  </span>
                )}
              </div>

              <h3 className="font-bold text-slate-900 text-sm mt-2 break-words">{tb.title}</h3>
              <p className="text-xs text-slate-500 mt-0.5 break-words">{tb.book_name}</p>

              <div className="mt-3 pt-3 border-t border-slate-100 flex justify-between text-2xs sm:text-xs text-slate-500">
                <span>{tb.chapters?.length || 0} {t.chaptersAvailable}</span>
                <span>{(tb.file_size / (1024 * 1024)).toFixed(1)} MB</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

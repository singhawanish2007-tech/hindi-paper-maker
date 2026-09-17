import React, { useState } from "react";
import { Download, FileText, Printer, CheckCircle2, AlertTriangle, ArrowLeft, Loader2 } from "lucide-react";
import { paperService } from "../services/api";
import { translations, Language } from "../services/translations";

interface ExportScreenProps {
  paperId: number | null;
  setCurrentTab: (tab: string) => void;
  lang?: Language;
}

export const ExportScreen: React.FC<ExportScreenProps> = ({
  paperId,
  setCurrentTab,
  lang = "hi"
}) => {
  const [includeAnswerKey, setIncludeAnswerKey] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isExportingDocx, setIsExportingDocx] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  const t = translations[lang] || translations.hi;

  if (!paperId) {
    return (
      <div className="p-12 text-center text-slate-500">
        {lang === "hi" ? "कृपया पहले एक प्रश्नपत्रिका चुनें या निर्मित करें।" : "Please select or generate a question paper first."}
      </div>
    );
  }

  const handleDownloadPdf = async (e: React.MouseEvent) => {
    e.preventDefault();
    setIsExportingPdf(true);
    setExportError(null);
    setExportSuccess(null);
    try {
      await paperService.downloadPdf(paperId, `hindi-paper-${paperId}.pdf`);
      setExportSuccess(t.exportSuccess || "File downloaded successfully!");
      setTimeout(() => setExportSuccess(null), 4000);
    } catch (e: any) {
      console.error("PDF download error:", e);
      setExportError(e.message || "PDF download failed.");
    } finally {
      setIsExportingPdf(false);
    }
  };

  const handleDownloadDocx = async (e: React.MouseEvent) => {
    e.preventDefault();
    setIsExportingDocx(true);
    setExportError(null);
    setExportSuccess(null);
    try {
      await paperService.downloadDocx(paperId, includeAnswerKey, `hindi-paper-${paperId}.docx`);
      setExportSuccess(t.exportSuccess || "File downloaded successfully!");
      setTimeout(() => setExportSuccess(null), 4000);
    } catch (e: any) {
      console.error("DOCX download error:", e);
      setExportError(e.message || "Word DOCX download failed.");
    } finally {
      setIsExportingDocx(false);
    }
  };

  const handlePrint = (e: React.MouseEvent) => {
    e.preventDefault();
    const iframe = document.getElementById("preview-frame") as HTMLIFrameElement;
    if (iframe && iframe.contentWindow) {
      iframe.contentWindow.print();
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-20 w-full min-w-0 overflow-hidden">
      {/* Header & Export Actions */}
      <div className="bg-white p-4 sm:p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col lg:flex-row justify-between lg:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentTab("editor")}
              className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-600 transition-colors cursor-pointer shrink-0"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2 truncate">
              <Download className="w-5 h-5 text-blue-600 shrink-0" />
              {t.exportHeader}
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1 sm:ml-8">
            {t.exportHeaderDesc}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2.5 sm:gap-3 w-full lg:w-auto">
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 bg-slate-50 px-3 py-2 rounded-xl border border-slate-200 cursor-pointer justify-center sm:justify-start">
            <input
              type="checkbox"
              checked={includeAnswerKey}
              onChange={(e) => setIncludeAnswerKey(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded-sm"
            />
            <span>{t.includeAnswerKeyInDocx}</span>
          </label>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleDownloadPdf}
              disabled={isExportingPdf || isExportingDocx}
              className="flex-1 sm:flex-none justify-center inline-flex items-center gap-1.5 px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              {isExportingPdf ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t.downloadingPdf}
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4" />
                  {t.downloadPdfBtn}
                </>
              )}
            </button>

            <button
              onClick={handleDownloadDocx}
              disabled={isExportingPdf || isExportingDocx}
              className="flex-1 sm:flex-none justify-center inline-flex items-center gap-1.5 px-4 py-2.5 bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50"
            >
              {isExportingDocx ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t.downloadingDocx}
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  {t.downloadDocxBtn}
                </>
              )}
            </button>

            <button
              onClick={handlePrint}
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2.5 bg-slate-800 hover:bg-slate-900 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
            >
              <Printer className="w-4 h-4" />
              <span className="hidden sm:inline">{t.printBtn}</span>
            </button>
          </div>
        </div>
      </div>

      {exportSuccess && (
        <div className="bg-emerald-50 border border-emerald-300 p-4 rounded-xl text-xs text-emerald-800 flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span className="font-semibold">{exportSuccess}</span>
        </div>
      )}

      {exportError && (
        <div className="bg-rose-50 border border-rose-300 p-4 rounded-xl text-xs text-rose-800 flex items-center gap-2 animate-in fade-in">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span className="font-semibold">{exportError}</span>
        </div>
      )}

      {/* Live Print Preview Iframe */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-4 sm:px-6 py-3 border-b border-slate-200 bg-slate-50 flex justify-between items-center text-xs">
          <span className="font-bold text-slate-700">{t.liveA4Preview}</span>
          <span className="text-slate-400 hidden sm:inline">{t.printStandardsHint}</span>
        </div>

        <div className="p-2 sm:p-8 bg-slate-100 flex justify-center overflow-x-auto w-full">
          <div className="w-full max-w-[210mm] min-w-[320px] sm:min-w-[600px] md:min-w-[750px] bg-white shadow-xl rounded-xs overflow-hidden border border-slate-300">
            <iframe
              id="preview-frame"
              src={paperService.getRenderUrl(paperId)}
              className="w-full min-h-[900px] border-none"
              title="Question Paper Preview"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

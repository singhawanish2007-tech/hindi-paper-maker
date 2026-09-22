import React, { useState, useEffect, useRef } from "react";
import {
  UploadCloud,
  FileText,
  Download,
  Eye,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  X,
  FileCheck,
  RefreshCw,
  ExternalLink
} from "lucide-react";
import { UploadedPaper } from "../types";
import { uploadedPaperService } from "../services/api";
import { translations, Language } from "../services/translations";

interface UploadedPapersProps {
  setCurrentTab: (tab: string) => void;
  lang?: Language;
}

export const UploadedPapers: React.FC<UploadedPapersProps> = ({
  setCurrentTab,
  lang = "hi"
}) => {
  const [papers, setPapers] = useState<UploadedPaper[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedGrade, setSelectedGrade] = useState<string>("");
  const [previewPaper, setPreviewPaper] = useState<UploadedPaper | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const t = translations[lang] || translations.hi;

  const loadPapers = async () => {
    try {
      setLoading(true);
      const data = await uploadedPaperService.getAll();
      setPapers(data);
    } catch (err) {
      console.error("Failed to load uploaded papers:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPapers();
  }, []);

  const handleFilesSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const fileArray = Array.from(files);

    try {
      setUploading(true);
      setUploadProgress(10);
      setStatusMessage("फ़ाइलें अपलोड एवं रूपांतरण प्रगति पर है...");

      await uploadedPaperService.uploadBatch(
        fileArray,
        selectedGrade || undefined,
        undefined,
        (pct) => setUploadProgress(Math.min(pct, 90))
      );

      setUploadProgress(100);
      setStatusMessage(t.uploadSuccessNotice);
      setTimeout(() => setStatusMessage(""), 4000);
      await loadPapers();
    } catch (err: any) {
      alert("अपलोड में त्रुटि: " + (err?.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelect(e.dataTransfer.files);
    }
  };

  const handleDelete = async (id: number, title: string) => {
    if (!window.confirm(`क्या आप वाकई "${title}" को हटाना चाहते हैं?`)) return;
    try {
      await uploadedPaperService.delete(id);
      await loadPapers();
    } catch (err) {
      alert("हटाने में त्रुटि: " + err);
    }
  };

  const handleDownloadPdf = async (paper: UploadedPaper) => {
    try {
      const cleanName = `${paper.title.replace("—", "-").trim()}.pdf`;
      await uploadedPaperService.downloadPdf(paper.id, cleanName);
    } catch (err) {
      alert("PDF डाउनलोड में त्रुटि: " + err);
    }
  };

  const handleDownloadWord = async (paper: UploadedPaper) => {
    try {
      const cleanName = `${paper.title.replace("—", "-").trim()}.docx`;
      await uploadedPaperService.downloadDocx(paper.id, cleanName);
    } catch (err) {
      alert("Word डाउनलोड में त्रुटि: " + err);
    }
  };

  return (
    <div className="space-y-6 sm:space-y-8 pb-16 max-w-7xl mx-auto w-full">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-indigo-700 via-blue-700 to-sky-700 rounded-2xl p-5 sm:p-7 text-white shadow-md relative overflow-hidden">
        <div className="relative z-10 max-w-3xl">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 backdrop-blur-xs text-xs font-semibold mb-2 text-white">
            <FileCheck className="w-3.5 h-3.5" />
            <span>महाराष्ट्र राज्य बोर्ड • कक्षा ५ से १०</span>
          </span>
          <h1 className="text-xl sm:text-2xl md:text-3xl font-extrabold tracking-tight">
            {lang === "hi"
              ? "मौजूदा प्रश्नपत्रिका अपलोड एवं प्रबंधन (Upload Existing Papers)"
              : "Upload & Manage Existing Question Papers"}
          </h1>
          <p className="mt-2 text-blue-100 text-xs sm:text-sm md:text-base leading-relaxed">
            {lang === "hi"
              ? "कक्षा ५, ६, ७, ८, ९ और १० के पूर्व-निर्मित प्रश्नपत्र अपलोड करें। मूल PDF सुरक्षित रहती है और Word (.docx) प्रारूप में तुरंत डाउनलोड करें।"
              : "Upload your pre-created question papers for Classes 5, 6, 7, 8, 9, and 10. Original PDF is preserved exactly, with instant Word (.docx) download options."}
          </p>
        </div>
      </div>

      {/* Mandatory Layout Notice */}
      <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-xl shadow-xs flex items-start gap-3.5">
        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs sm:text-sm text-amber-900">
          <p className="font-bold">{t.pdfToWordWarning}</p>
          <p className="text-amber-700 mt-0.5 text-xs">
            {lang === "hi"
              ? "मूल PDF को बिना किसी बदलाव के सुरक्षित रखा जाता है। Word (.docx) में तालिकाएँ, फ़ॉन्ट व देवनागरी पाठ्य सामग्री यथासंभव सटीक रखी जाती है।"
              : "The original PDF is preserved 100% untouched. For Word (.docx), tables, fonts, and Devanagari text are aligned as accurately as possible."}
          </p>
        </div>
      </div>

      {/* Batch Upload Section */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <h2 className="font-bold text-slate-900 text-base sm:text-lg flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-blue-600" />
              <span>
                {lang === "hi" ? "नए प्रश्नपत्र अपलोड करें (Batch Upload)" : "Upload New Papers (Batch)"}
              </span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">{t.batchUploadHelp}</p>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-slate-700 whitespace-nowrap">
              {t.classLabel}:
            </label>
            <select
              value={selectedGrade}
              onChange={(e) => setSelectedGrade(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-slate-50 text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
            >
              <option value="">{lang === "hi" ? "स्वतः पहचान (Auto-detect)" : "Auto-detect"}</option>
              <option value="5">कक्षा 5 (Class 5)</option>
              <option value="6">कक्षा 6 (Class 6)</option>
              <option value="7">कक्षा 7 (Class 7)</option>
              <option value="8">कक्षा 8 (Class 8)</option>
              <option value="9">कक्षा 9 (Class 9)</option>
              <option value="10">कक्षा 10 (Class 10)</option>
            </select>
          </div>
        </div>

        {/* Dropzone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-blue-200 hover:border-blue-500 rounded-xl p-6 sm:p-8 text-center cursor-pointer bg-blue-50/30 hover:bg-blue-50/60 transition-colors"
        >
          <input
            type="file"
            ref={fileInputRef}
            multiple
            accept=".pdf,.docx,.doc,.png,.jpg,.jpeg"
            className="hidden"
            onChange={(e) => handleFilesSelect(e.target.files)}
          />

          <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-3">
            <UploadCloud className="w-6 h-6" />
          </div>

          <p className="font-bold text-sm sm:text-base text-slate-800">
            {lang === "hi"
              ? "फ़ाइलें यहाँ खींचें (Drag & Drop) या चुनने के लिए क्लिक करें"
              : "Drag & drop files here, or click to browse"}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {lang === "hi"
              ? "समर्थित प्रारूप: PDF, DOCX, Word, Images • एक साथ कई फ़ाइलें अपलोड करें"
              : "Supported formats: PDF, DOCX, Word, Images • Multi-file batch upload"}
          </p>

          <button
            type="button"
            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg shadow-xs transition-colors"
          >
            {lang === "hi" ? "कंप्यूटर से फ़ाइलें चुनें" : "Select Files from Computer"}
          </button>
        </div>

        {/* Upload Status & Progress */}
        {uploading && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs space-y-2">
            <div className="flex justify-between font-semibold text-blue-900">
              <span className="flex items-center gap-1.5">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-600" />
                <span>{statusMessage || "अपलोड जारी है..."}</span>
              </span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-blue-600 h-full transition-all duration-300 rounded-full"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}

        {statusMessage && !uploading && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl p-3 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{statusMessage}</span>
          </div>
        )}
      </div>

      {/* Uploaded Papers List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-600" />
            <h2 className="font-bold text-slate-900 text-base">
              {t.uploadedPapers} ({papers.length})
            </h2>
          </div>
          <button
            onClick={loadPapers}
            className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
            title="Reload"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600 mb-2" />
            <span>लोड हो रहा है...</span>
          </div>
        ) : papers.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-2">
            <FileText className="w-12 h-12 text-slate-300 mx-auto" />
            <p className="font-semibold text-slate-700">{t.noUploadedPapers}</p>
            <p className="text-xs text-slate-400">
              ऊपर दिए गए बॉक्स में अपनी मौजूदा PDF या Word प्रश्नपत्रिकाएँ जोड़ें।
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {papers.map((paper) => (
              <div
                key={paper.id}
                className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/80 transition-colors"
              >
                {/* Left: Paper Info */}
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm sm:text-base">
                      {paper.title}
                    </span>
                    <span className="bg-indigo-50 text-indigo-700 border border-indigo-200 text-2xs sm:text-xs px-2.5 py-0.5 rounded-full font-bold">
                      {t.classLabel} {paper.grade}
                    </span>
                    <span className="bg-slate-100 text-slate-700 text-2xs sm:text-xs px-2 py-0.5 rounded-full font-medium">
                      {paper.subject}
                    </span>
                    {paper.file_type === "pdf" && (
                      <span className="bg-rose-50 text-rose-700 border border-rose-200 text-2xs px-2 py-0.5 rounded-full font-semibold">
                        PDF मूल
                      </span>
                    )}
                    {paper.has_docx && (
                      <span className="bg-blue-50 text-blue-700 border border-blue-200 text-2xs px-2 py-0.5 rounded-full font-semibold">
                        DOCX
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-2xs sm:text-xs text-slate-500">
                    <span className="truncate max-w-[250px]">{paper.original_filename}</span>
                    <span>•</span>
                    <span>{(paper.file_size / 1024).toFixed(1)} KB</span>
                    <span>•</span>
                    <span>
                      {new Date(paper.created_at).toLocaleDateString(
                        lang === "hi" ? "hi-IN" : "en-US",
                        { month: "short", day: "numeric", year: "numeric" }
                      )}
                    </span>
                  </div>
                </div>

                {/* Right: Actions [Preview] [Download PDF] [Download Word] [Delete] */}
                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  {/* [Preview] */}
                  <button
                    onClick={() => setPreviewPaper(paper)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                    title="पूर्वावलोकन देखें"
                  >
                    <Eye className="w-3.5 h-3.5 text-slate-600" />
                    <span>{t.previewBtn}</span>
                  </button>

                  {/* [Download PDF] */}
                  <button
                    onClick={() => handleDownloadPdf(paper)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors cursor-pointer"
                    title="PDF डाउनलोड करें"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download PDF</span>
                  </button>

                  {/* [Download Word] */}
                  <button
                    onClick={() => handleDownloadWord(paper)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors cursor-pointer"
                    title="Word (.docx) फ़ाइल डाउनलोड करें"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Word</span>
                  </button>

                  {/* [Delete] */}
                  <button
                    onClick={() => handleDelete(paper.id, paper.title)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors cursor-pointer"
                    title="हटाएँ"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {previewPaper && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white w-full max-w-5xl h-[90vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-slate-200">
            {/* Modal Header */}
            <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2.5 min-w-0">
                <FileText className="w-5 h-5 text-blue-600 shrink-0" />
                <div className="min-w-0">
                  <h3 className="font-bold text-slate-900 text-sm sm:text-base truncate">
                    {previewPaper.title}
                  </h3>
                  <p className="text-2xs sm:text-xs text-slate-500">
                    {previewPaper.original_filename} • {t.classLabel} {previewPaper.grade}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => handleDownloadPdf(previewPaper)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-lg transition-colors cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Download PDF</span>
                  <span className="sm:hidden">PDF</span>
                </button>

                <button
                  onClick={() => handleDownloadWord(previewPaper)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg transition-colors cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Download Word</span>
                  <span className="sm:hidden">Word</span>
                </button>

                <button
                  onClick={() => setPreviewPaper(null)}
                  className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition-colors cursor-pointer ml-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body / Viewer */}
            <div className="flex-1 bg-slate-100 p-2 sm:p-4 overflow-hidden flex flex-col">
              <div className="flex-1 bg-white rounded-xl shadow-inner border border-slate-200 overflow-hidden relative">
                <iframe
                  src={uploadedPaperService.getPreviewUrl(previewPaper.id)}
                  title="Document Preview"
                  className="w-full h-full border-0"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

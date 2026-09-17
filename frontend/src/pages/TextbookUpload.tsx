import React, { useState } from "react";
import { Upload, FileText, CheckCircle2, AlertTriangle, XCircle, ArrowRight, Loader2 } from "lucide-react";
import { textbookService } from "../services/api";
import { Textbook } from "../types";
import { OcrWarningModal } from "../components/OcrWarningModal";
import { translations, Language } from "../services/translations";

interface TextbookUploadProps {
  onUploadComplete?: (textbook: Textbook) => void;
  setCurrentTab: (tab: string) => void;
  lang?: Language;
}

export const TextbookUpload: React.FC<TextbookUploadProps> = ({
  onUploadComplete,
  setCurrentTab,
  lang = "hi"
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [grade, setGrade] = useState("10");
  const [bookName, setBookName] = useState("हिंदी लोकभारती");
  const [title, setTitle] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [uploadedResult, setUploadedResult] = useState<Textbook | null>(null);
  const [showOcrModal, setShowOcrModal] = useState(false);

  const t = translations[lang] || translations.hi;

  const handleGradeChange = (newGrade: string) => {
    setGrade(newGrade);
    const g = parseInt(newGrade, 10);
    if (g <= 8) {
      setBookName("हिंदी सुलभभारती");
    } else {
      setBookName("हिंदी लोकभारती");
    }
  };

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelected = (selectedFile: File) => {
    setError(null);
    setUploadedResult(null);

    // 1. File extension validation
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError(lang === "hi" ? "अमान्य प्रारूप: केवल PDF फ़ाइलें ही स्वीकार्य हैं।" : "Invalid format: Only PDF files are allowed.");
      setFile(null);
      return;
    }

    // 2. 100 MB limit validation
    const maxSizeBytes = 100 * 1024 * 1024;
    if (selectedFile.size > maxSizeBytes) {
      setError(
        lang === "hi"
          ? `फ़ाइल का आकार (${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB) अधिकतम 100 MB की सीमा से अधिक है।`
          : `File size (${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB) exceeds maximum allowed limit of 100 MB.`
      );
      setFile(null);
      return;
    }

    setFile(selectedFile);
    if (!title) {
      setTitle(selectedFile.name.replace(".pdf", ""));
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError(lang === "hi" ? "कृपया एक वैध PDF फ़ाइल चुनें।" : "Please select a valid PDF file.");
      return;
    }

    setIsUploading(true);
    setError(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("grade", grade);
    formData.append("book_name", bookName);
    formData.append("title", title);

    try {
      const result = await textbookService.upload(formData, (pct) => {
        setUploadProgress(pct);
      });
      setUploadedResult(result);
      if (result.ocr_warning) {
        setShowOcrModal(true);
      }
      if (onUploadComplete) {
        onUploadComplete(result);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Upload failed.";
      setError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 sm:p-8">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-slate-900">{t.uploadTitle}</h2>
          <p className="text-xs text-slate-500 mt-1">{t.uploadDesc}</p>
        </div>

        <form onSubmit={handleUploadSubmit} className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">{t.bookClass}</label>
              <select
                value={grade}
                onChange={(e) => handleGradeChange(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:border-blue-500 focus:outline-hidden"
              >
                <option value="5">{lang === "hi" ? "कक्षा ५वीं (5th)" : "Class 5th"}</option>
                <option value="6">{lang === "hi" ? "कक्षा ६वीं (6th)" : "Class 6th"}</option>
                <option value="7">{lang === "hi" ? "कक्षा ७वीं (7th)" : "Class 7th"}</option>
                <option value="8">{lang === "hi" ? "कक्षा ८वीं (8th)" : "Class 8th"}</option>
                <option value="9">{lang === "hi" ? "कक्षा ९वीं (9th)" : "Class 9th"}</option>
                <option value="10">{lang === "hi" ? "कक्षा १०वीं (10th)" : "Class 10th"}</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">{t.bookName}</label>
              <input
                type="text"
                value={bookName}
                onChange={(e) => setBookName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:border-blue-500 focus:outline-hidden"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">{t.bookTitle}</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Hindi Lokbharati Class 10th - Semester 1"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800 focus:bg-white focus:border-blue-500 focus:outline-hidden"
            />
          </div>

          {/* Drag & Drop Area */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">PDF (Max: 100 MB)</label>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              className="border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-8 text-center transition-colors bg-slate-50/50 cursor-pointer"
              onClick={() => document.getElementById("file-input")?.click()}
            >
              <input
                id="file-input"
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileSelected(e.target.files[0]);
                  }
                }}
              />
              <Upload className="w-10 h-10 text-slate-400 mx-auto mb-3" />
              {file ? (
                <div className="text-slate-800">
                  <p className="font-bold text-sm text-blue-600">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                </div>
              ) : (
                <div>
                  <p className="text-sm font-semibold text-slate-700">{t.dragDropText}</p>
                  <p className="text-xs text-slate-400 mt-1">{t.dragDropHint}</p>
                </div>
              )}
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="bg-rose-50 border border-rose-300 p-3.5 rounded-lg text-xs text-rose-800 flex items-start gap-2">
              <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">{lang === "hi" ? "त्रुटि: " : "Error: "}</span>
                {error}
              </div>
            </div>
          )}

          {/* Upload Progress Bar */}
          {isUploading && (
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-semibold text-slate-700">
                <span>{t.uploadingProgress}</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isUploading || !file}
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold text-sm rounded-xl shadow-xs transition-colors cursor-pointer"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t.processingWait}
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  {t.uploadAndExtract}
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Success Details Card */}
      {uploadedResult && (
        <div className="bg-white rounded-xl border border-emerald-200 shadow-xs p-6 space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-700 font-bold text-sm">
              <CheckCircle2 className="w-5 h-5" />
              {t.extractSuccess}
            </div>
            {uploadedResult.ocr_warning && (
              <button
                onClick={() => setShowOcrModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-100 text-amber-800 text-xs font-semibold rounded-lg border border-amber-300 cursor-pointer"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                {t.ocrWarningBtn}
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl text-center text-xs">
            <div>
              <div className="text-slate-400">{t.totalPages}</div>
              <div className="text-lg font-bold text-slate-800 mt-0.5">{uploadedResult.total_pages}</div>
            </div>
            <div>
              <div className="text-slate-400">{t.extractedPages}</div>
              <div className="text-lg font-bold text-emerald-600 mt-0.5">{uploadedResult.extracted_pages}</div>
            </div>
            <div>
              <div className="text-slate-400">{t.scannedPages}</div>
              <div className="text-lg font-bold text-amber-600 mt-0.5">{uploadedResult.scanned_pages}</div>
            </div>
            <div>
              <div className="text-slate-400">{t.detectedChapters}</div>
              <div className="text-lg font-bold text-blue-600 mt-0.5">{uploadedResult.chapters?.length || 0}</div>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setCurrentTab("generate")}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer"
            >
              {t.proceedToBlueprint}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* OCR Warning Modal */}
      <OcrWarningModal
        textbook={uploadedResult}
        isOpen={showOcrModal}
        onClose={() => setShowOcrModal(false)}
      />
    </div>
  );
};

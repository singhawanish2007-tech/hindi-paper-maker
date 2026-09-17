import React from "react";
import { AlertTriangle, FileText, Check, X } from "lucide-react";
import { Textbook } from "../types";

interface OcrWarningModalProps {
  textbook: Textbook | null;
  isOpen: boolean;
  onClose: () => void;
}

export const OcrWarningModal: React.FC<OcrWarningModalProps> = ({
  textbook,
  isOpen,
  onClose
}) => {
  if (!isOpen || !textbook) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="bg-amber-500 px-5 py-4 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-5 h-5" />
            <h3 className="font-bold text-base">स्कैन / कम पाठ्य सामग्री चेतावनी (OCR Notice)</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-amber-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <p className="text-sm text-slate-700 leading-relaxed">
            अपलोड की गई पाठ्यपुस्तक <strong>{textbook.title}</strong> के कुछ पृष्ठों में मुद्रित पाठ्य सामग्री 50 वर्णों से कम पाई गई है अथवा पृष्ठ छवि (स्कैन) के रूप में हैं।
          </p>

          <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3.5 rounded-lg border border-slate-200 text-xs">
            <div>
              <span className="text-slate-500">कुल पृष्ठ:</span>
              <span className="font-bold text-slate-800 ml-1.5">{textbook.total_pages}</span>
            </div>
            <div>
              <span className="text-slate-500">निकाले गए पृष्ठ:</span>
              <span className="font-bold text-emerald-600 ml-1.5">{textbook.extracted_pages}</span>
            </div>
            <div>
              <span className="text-slate-500">स्कैन पृष्ठ:</span>
              <span className="font-bold text-amber-600 ml-1.5">{textbook.scanned_pages}</span>
            </div>
            <div>
              <span className="text-slate-500">अल्प-पाठ्य पृष्ठ:</span>
              <span className="font-bold text-rose-600 ml-1.5">{textbook.low_text_pages}</span>
            </div>
          </div>

          <div className="bg-amber-50 border-l-4 border-amber-500 p-3 text-xs text-amber-900 rounded-r-md">
            <strong>निर्देश:</strong> अनिश्चित या स्कैन पाठ से सटीक उद्धरण उत्पन्न न करें। कृपया प्रश्नपत्रिका निर्माण से पूर्व चयनित पाठों और परिच्छेदों का भौतिक पुस्तक से सत्यापन अवश्य करें।
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition-colors"
            >
              समझ गया / सत्यापन जारी रखें
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

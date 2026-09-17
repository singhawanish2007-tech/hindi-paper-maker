import React from "react";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

interface MarksValidatorBadgeProps {
  configuredTotal: number;
  calculatedTotal: number;
  errors?: string[];
  compact?: boolean;
}

export const MarksValidatorBadge: React.FC<MarksValidatorBadgeProps> = ({
  configuredTotal,
  calculatedTotal,
  errors = [],
  compact = false
}) => {
  const difference = Math.abs(configuredTotal - calculatedTotal);
  const isValid = difference === 0 && errors.length === 0;

  if (compact) {
    if (isValid) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          अंक संतुलित: {configuredTotal}/{calculatedTotal}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300 animate-pulse">
        <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
        अंतर: {difference} अंक ({calculatedTotal}/{configuredTotal})
      </span>
    );
  }

  return (
    <div
      className={`rounded-lg p-3.5 border transition-all ${
        isValid
          ? "bg-emerald-50/80 border-emerald-200 text-emerald-900"
          : "bg-rose-50/90 border-rose-300 text-rose-900"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isValid ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
          )}
          <div>
            <div className="font-semibold text-sm">
              {isValid
                ? "अंक सत्यापन सफल (Marks Validated)"
                : `अंक असंगत! अंतर: ${difference} अंक (Marks Mismatch)`}
            </div>
            <div className="text-xs opacity-90 mt-0.5">
              निर्धारित कुल अंक: <span className="font-bold">{configuredTotal}</span> | वर्तमान गणना:{" "}
              <span className="font-bold">{calculatedTotal}</span>
            </div>
          </div>
        </div>

        <div className="text-right">
          <span
            className={`inline-block px-2.5 py-1 rounded-md text-xs font-bold ${
              isValid ? "bg-emerald-200 text-emerald-900" : "bg-rose-200 text-rose-900"
            }`}
          >
            {isValid ? "100% वैध" : `त्रुटि: ${difference} अंक`}
          </span>
        </div>
      </div>

      {!isValid && errors.length > 0 && (
        <div className="mt-2.5 pt-2.5 border-t border-rose-200/80 text-xs text-rose-800 space-y-1">
          {errors.slice(0, 3).map((err, idx) => (
            <div key={idx} className="flex items-start gap-1.5">
              <span className="text-rose-500">•</span>
              <span>{err}</span>
            </div>
          ))}
          {errors.length > 3 && (
            <div className="italic text-rose-600">...तथा {errors.length - 3} अन्य विसंगतियाँ</div>
          )}
        </div>
      )}
    </div>
  );
};

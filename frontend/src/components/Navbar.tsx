import React from "react";
import { BookOpen, FileText, PlusCircle, AlertCircle, Sparkles, Globe } from "lucide-react";
import { translations, Language } from "../services/translations";

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  activePaperId: number | null;
  lang: Language;
  setLang: (lang: Language) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  setCurrentTab,
  activePaperId,
  lang,
  setLang
}) => {
  const t = translations[lang] || translations.hi;

  const toggleLanguage = () => {
    setLang(lang === "hi" ? "en" : "hi");
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setCurrentTab("dashboard")}>
            <div className="w-10 h-10 rounded-lg overflow-hidden border border-slate-200 shadow-xs bg-slate-50 flex items-center justify-center">
              <img
                src="/1000358221.png"
                alt="Trinity High School Logo"
                className="w-full h-full object-contain"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = "none";
                }}
              />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-slate-900 tracking-tight">{t.appName}</span>
                <span className="bg-amber-100 text-amber-900 text-xs font-semibold px-2 py-0.5 rounded-full border border-amber-200">
                  {t.boardBadge}
                </span>
              </div>
              <p className="text-xs text-slate-500">{t.appSubtitle}</p>
            </div>
          </div>

          <nav className="flex items-center gap-1">
            <button
              onClick={() => setCurrentTab("dashboard")}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                currentTab === "dashboard"
                  ? "bg-blue-50 text-blue-700 font-bold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              {t.dashboard}
            </button>

            <button
              onClick={() => setCurrentTab("upload")}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                currentTab === "upload"
                  ? "bg-blue-50 text-blue-700 font-bold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              {t.uploadTextbook}
            </button>

            <button
              onClick={() => setCurrentTab("generate")}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                currentTab === "generate"
                  ? "bg-blue-50 text-blue-700 font-bold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              {t.generatePaper}
            </button>

            {activePaperId && (
              <>
                <button
                  onClick={() => setCurrentTab("editor")}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                    currentTab === "editor"
                      ? "bg-blue-50 text-blue-700 font-bold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  {t.editor}
                </button>
                <button
                  onClick={() => setCurrentTab("answer-key")}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                    currentTab === "answer-key"
                      ? "bg-blue-50 text-blue-700 font-bold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  {t.answerKey}
                </button>
                <button
                  onClick={() => setCurrentTab("export")}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                    currentTab === "export"
                      ? "bg-blue-50 text-blue-700 font-bold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  {t.export}
                </button>
              </>
            )}

            {/* Language Switcher Toggle */}
            <button
              onClick={toggleLanguage}
              className="ml-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-bold transition-all cursor-pointer"
              title="Switch Language / भाषा बदलें"
            >
              <Globe className="w-3.5 h-3.5 text-indigo-600" />
              <span>{lang === "hi" ? "English" : "हिंदी"}</span>
            </button>

            <button
              onClick={() => setCurrentTab("generate")}
              className="ml-2 inline-flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-xs transition-colors cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              {t.newPaperCTA}
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};

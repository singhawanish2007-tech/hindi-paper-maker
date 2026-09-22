import React, { useState } from "react";
import { BookOpen, FileText, Sparkles, Globe, Menu, X, CheckSquare, UploadCloud } from "lucide-react";
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const t = translations[lang] || translations.hi;

  const toggleLanguage = () => {
    setLang(lang === "hi" ? "en" : "hi");
  };

  const handleNavClick = (tab: string) => {
    setCurrentTab(tab);
    setMobileMenuOpen(false);
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo and Brand */}
          <div
            className="flex items-center gap-2 sm:gap-3 cursor-pointer min-w-0"
            onClick={() => handleNavClick("dashboard")}
          >
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg overflow-hidden border border-slate-200 shadow-xs bg-slate-50 flex items-center justify-center shrink-0">
              <img
                src="/1000358221.png"
                alt="Trinity High School Logo"
                className="w-full h-full object-contain"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = "none";
                }}
              />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 sm:gap-2">
                <span className="font-bold text-sm sm:text-lg text-slate-900 tracking-tight truncate">
                  {t.appName}
                </span>
                <span className="hidden sm:inline-block bg-amber-100 text-amber-900 text-2xs sm:text-xs font-semibold px-2 py-0.5 rounded-full border border-amber-200 shrink-0">
                  {t.boardBadge}
                </span>
              </div>
              <p className="hidden sm:block text-2xs sm:text-xs text-slate-500 truncate">
                {t.appSubtitle}
              </p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            <button
              onClick={() => handleNavClick("dashboard")}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                currentTab === "dashboard"
                  ? "bg-blue-50 text-blue-700 font-bold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              {t.dashboard}
            </button>

            <button
              onClick={() => handleNavClick("upload")}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                currentTab === "upload"
                  ? "bg-blue-50 text-blue-700 font-bold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              {t.uploadTextbook}
            </button>

            <button
              onClick={() => handleNavClick("uploaded-papers")}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                currentTab === "uploaded-papers"
                  ? "bg-blue-50 text-blue-700 font-bold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              {t.uploadExistingPaper}
            </button>

            <button
              onClick={() => handleNavClick("generate")}
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
                  onClick={() => handleNavClick("editor")}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                    currentTab === "editor"
                      ? "bg-blue-50 text-blue-700 font-bold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  {t.editor}
                </button>
                <button
                  onClick={() => handleNavClick("answer-key")}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
                    currentTab === "answer-key"
                      ? "bg-blue-50 text-blue-700 font-bold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  {t.answerKey}
                </button>
                <button
                  onClick={() => handleNavClick("export")}
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
              onClick={() => handleNavClick("generate")}
              className="ml-2 inline-flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-xs transition-colors cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              {t.newPaperCTA}
            </button>
          </nav>

          {/* Mobile Right Controls: Lang Toggle & Hamburger */}
          <div className="flex md:hidden items-center gap-1.5">
            <button
              onClick={toggleLanguage}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-bold transition-all cursor-pointer"
              title="Switch Language / भाषा बदलें"
            >
              <Globe className="w-3.5 h-3.5 text-indigo-600" />
              <span>{lang === "hi" ? "EN" : "हिं"}</span>
            </button>

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-700 hover:bg-slate-100 focus:outline-hidden cursor-pointer"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6 text-slate-800" />
              ) : (
                <Menu className="w-6 h-6 text-slate-800" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-5 space-y-1 shadow-lg animate-in slide-in-from-top-2 duration-150">
          <button
            onClick={() => handleNavClick("dashboard")}
            className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-3 ${
              currentTab === "dashboard"
                ? "bg-blue-50 text-blue-700 font-bold"
                : "text-slate-700 hover:bg-slate-50"
            }`}
          >
            <FileText className="w-4 h-4 text-blue-600" />
            {t.dashboard}
          </button>

          <button
            onClick={() => handleNavClick("upload")}
            className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-3 ${
              currentTab === "upload"
                ? "bg-blue-50 text-blue-700 font-bold"
                : "text-slate-700 hover:bg-slate-50"
            }`}
          >
            <BookOpen className="w-4 h-4 text-indigo-600" />
            {t.uploadTextbook}
          </button>

          <button
            onClick={() => handleNavClick("uploaded-papers")}
            className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-3 ${
              currentTab === "uploaded-papers"
                ? "bg-blue-50 text-blue-700 font-bold"
                : "text-slate-700 hover:bg-slate-50"
            }`}
          >
            <UploadCloud className="w-4 h-4 text-sky-600" />
            {t.uploadExistingPaper}
          </button>

          <button
            onClick={() => handleNavClick("generate")}
            className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-3 ${
              currentTab === "generate"
                ? "bg-blue-50 text-blue-700 font-bold"
                : "text-slate-700 hover:bg-slate-50"
            }`}
          >
            <Sparkles className="w-4 h-4 text-amber-500" />
            {t.generatePaper}
          </button>

          {activePaperId && (
            <>
              <button
                onClick={() => handleNavClick("editor")}
                className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-3 ${
                  currentTab === "editor"
                    ? "bg-blue-50 text-blue-700 font-bold"
                    : "text-slate-700 hover:bg-slate-50"
                }`}
              >
                <CheckSquare className="w-4 h-4 text-emerald-600" />
                {t.editor}
              </button>

              <button
                onClick={() => handleNavClick("answer-key")}
                className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-3 ${
                  currentTab === "answer-key"
                    ? "bg-blue-50 text-blue-700 font-bold"
                    : "text-slate-700 hover:bg-slate-50"
                }`}
              >
                <FileText className="w-4 h-4 text-purple-600" />
                {t.answerKey}
              </button>

              <button
                onClick={() => handleNavClick("export")}
                className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-3 ${
                  currentTab === "export"
                    ? "bg-blue-50 text-blue-700 font-bold"
                    : "text-slate-700 hover:bg-slate-50"
                }`}
              >
                <FileText className="w-4 h-4 text-rose-600" />
                {t.export}
              </button>
            </>
          )}

          <div className="pt-2 border-t border-slate-100 mt-2">
            <button
              onClick={() => handleNavClick("generate")}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold rounded-xl shadow-xs transition-colors cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              {t.newPaperCTA}
            </button>
          </div>
        </div>
      )}
    </header>
  );
};

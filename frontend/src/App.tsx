import React, { useState } from "react";
import { Navbar } from "./components/Navbar";
import { Dashboard } from "./pages/Dashboard";
import { TextbookUpload } from "./pages/TextbookUpload";
import { PaperGenerator } from "./pages/PaperGenerator";
import { CanvaPaperEditor } from "./pages/CanvaPaperEditor";
import { AnswerKeyView } from "./pages/AnswerKeyView";
import { ExportScreen } from "./pages/ExportScreen";
import { Language } from "./services/translations";

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>("dashboard");
  const [activePaperId, setActivePaperId] = useState<number | null>(null);
  const [lang, setLang] = useState<Language>("hi");

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col w-full min-w-0 overflow-x-hidden">
      <Navbar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        activePaperId={activePaperId}
        lang={lang}
        setLang={setLang}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {currentTab === "dashboard" && (
          <Dashboard
            setCurrentTab={setCurrentTab}
            setActivePaperId={(id) => {
              setActivePaperId(id);
              setCurrentTab("editor");
            }}
            lang={lang}
          />
        )}

        {currentTab === "upload" && (
          <TextbookUpload
            setCurrentTab={setCurrentTab}
            onUploadComplete={() => {
              setCurrentTab("generate");
            }}
            lang={lang}
          />
        )}

        {currentTab === "generate" && (
          <PaperGenerator
            setCurrentTab={setCurrentTab}
            setActivePaperId={(id) => {
              setActivePaperId(id);
              setCurrentTab("editor");
            }}
            lang={lang}
          />
        )}

        {currentTab === "editor" && (
          <CanvaPaperEditor
            paperId={activePaperId}
            setCurrentTab={setCurrentTab}
            lang={lang}
          />
        )}

        {currentTab === "answer-key" && (
          <AnswerKeyView
            paperId={activePaperId}
            setCurrentTab={setCurrentTab}
            lang={lang}
          />
        )}

        {currentTab === "export" && (
          <ExportScreen
            paperId={activePaperId}
            setCurrentTab={setCurrentTab}
            lang={lang}
          />
        )}
      </main>

      <footer className="bg-white border-t border-slate-200 py-4 px-4 text-center text-xs text-slate-500">
        <p className="break-words">
          महाराष्ट्र राज्य माध्यमिक व उच्च माध्यमिक शिक्षण मंडळ • HINDI PAPER MAKER © 2026 • Trinity High School & Junior College
        </p>
      </footer>
    </div>
  );
};

export default App;

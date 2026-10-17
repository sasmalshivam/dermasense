import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Footer from './components/Footer';
import HomeView from './components/HomeView';
import UploadView from './components/UploadView';
import ResultsView from './components/ResultsView';
import AboutView from './components/AboutView';
import ChatView from './components/ChatView';
import NearbyCareView from './components/NearbyCareView';
import AdminView from './components/AdminView';
import { fetchTranslations } from './api';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('home'); // 'home' | 'upload' | 'results' | 'chat' | 'nearby' | 'about' | 'admin'
  const [analysisResult, setAnalysisResult] = useState(null);
  const [originalImageSrc, setOriginalImageSrc] = useState(null);
  const [currentLanguage, setCurrentLanguage] = useState('en');
  const [translationsData, setTranslationsData] = useState(null);

  useEffect(() => {
    async function loadTranslations() {
      try {
        const data = await fetchTranslations();
        if (data && data.translations) {
          setTranslationsData(data.translations);
        }
      } catch (e) {
        console.warn('Could not load UI translations:', e);
      }
    }
    loadTranslations();
  }, []);

  const currentUiStrings = translationsData?.[currentLanguage] || {};

  const handleStartCheck = () => {
    setActiveTab('upload');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleAnalysisSuccess = (result, previewUrl) => {
    setAnalysisResult(result);
    setOriginalImageSrc(previewUrl);
    setActiveTab('results');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleReset = () => {
    setAnalysisResult(null);
    setOriginalImageSrc(null);
    setActiveTab('upload');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectCondition = (_conditionId) => {
    setActiveTab('upload');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const detectedConditionId = analysisResult?.top_condition_id || null;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 selection:bg-blue-600 selection:text-white">
      {/* Persistent Navigation Header with Language Selector */}
      <Header 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        currentLanguage={currentLanguage}
        onLanguageChange={setCurrentLanguage}
        uiStrings={currentUiStrings}
      />

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-5xl mx-auto px-4 py-6" id="main-content">
        {activeTab === 'home' && (
          <HomeView
            onStartCheck={handleStartCheck}
            onSelectCondition={handleSelectCondition}
            uiStrings={currentUiStrings}
          />
        )}

        {activeTab === 'upload' && (
          <UploadView
            onAnalysisSuccess={handleAnalysisSuccess}
            uiStrings={currentUiStrings}
          />
        )}

        {activeTab === 'results' && analysisResult && (
          <div className="space-y-6">
            <ResultsView
              result={analysisResult}
              originalImageSrc={originalImageSrc}
              onReset={handleReset}
              uiStrings={currentUiStrings}
              onNavigateNearby={() => {
                setActiveTab('nearby');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
            />

            {/* Quick Link to Chat about this detected condition */}
            <div className="max-w-4xl mx-auto px-4">
              <div className="bg-blue-600 text-white rounded-3xl p-6 shadow-md flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="space-y-1 text-center sm:text-left">
                  <h3 className="text-lg font-bold">Have questions about this condition?</h3>
                  <p className="text-xs sm:text-sm text-blue-100">
                    Ask our AI Health Assistant questions like "Is it contagious?" or "What should I avoid?".
                  </p>
                </div>
                <button
                  onClick={() => {
                    setActiveTab('chat');
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  className="bg-white hover:bg-blue-50 text-blue-900 font-bold px-6 py-3 rounded-2xl shadow transition cursor-pointer shrink-0"
                >
                  Open Health Chat
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'chat' && (
          <ChatView
            detectedCondition={detectedConditionId}
            language={currentLanguage}
            uiStrings={currentUiStrings}
          />
        )}

        {activeTab === 'nearby' && (
          <NearbyCareView />
        )}

        {activeTab === 'about' && (
          <AboutView 
            uiStrings={currentUiStrings}
          />
        )}

        {activeTab === 'admin' && (
          <AdminView />
        )}
      </main>

      {/* Persistent Footer with Clinical Disclaimer & SIH 2025 Attribution */}
      <Footer uiStrings={currentUiStrings} />
    </div>
  );
}

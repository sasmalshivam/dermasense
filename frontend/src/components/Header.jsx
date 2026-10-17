import React from 'react';
import { Activity, Home, Camera, Info, MessageSquare, Globe, MapPin, Lock } from 'lucide-react';

const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
  { code: 'or', label: 'ଓଡ଼ିଆ' },
  { code: 'bn', label: 'বাংলা' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'mr', label: 'मराठी' },
];

export default function Header({ 
  activeTab, 
  setActiveTab, 
  currentLanguage = 'en', 
  onLanguageChange,
  uiStrings = {} 
}) {
  return (
    <header className="bg-slate-900 text-white shadow-md border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        {/* Brand */}
        <button
          onClick={() => setActiveTab('home')}
          className="flex items-center gap-3 text-left focus:outline-none focus:ring-2 focus:ring-blue-400 rounded-lg p-1 cursor-pointer"
          aria-label="DermaSense Home"
        >
          <div className="bg-blue-600 text-white p-2 rounded-xl shadow-sm flex items-center justify-center">
            <Activity className="w-6 h-6" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-white">
                {uiStrings.app_title || 'DermaSense'}
              </span>
              <span className="text-xs bg-blue-900/80 text-blue-200 border border-blue-700/60 font-semibold px-2 py-0.5 rounded-full">
                SIH 2025
              </span>
            </div>
            <p className="text-xs text-slate-300">
              Team Healthnautix • {uiStrings.app_subtitle || 'Public Health Awareness'}
            </p>
          </div>
        </button>

        {/* Navigation Tabs & Language Dropdown */}
        <div className="flex items-center gap-2 sm:gap-3">
          <nav className="flex items-center gap-1 sm:gap-1.5" aria-label="Main Navigation">
            <button
              onClick={() => setActiveTab('home')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm sm:text-base font-semibold transition-colors cursor-pointer ${
                activeTab === 'home'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-200 hover:bg-slate-800 hover:text-white'
              }`}
              aria-current={activeTab === 'home' ? 'page' : undefined}
            >
              <Home className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
              <span className="hidden sm:inline">{uiStrings.nav_home || 'Home'}</span>
            </button>

            <button
              onClick={() => setActiveTab('upload')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm sm:text-base font-semibold transition-colors cursor-pointer ${
                activeTab === 'upload' || activeTab === 'results'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-200 hover:bg-slate-800 hover:text-white'
              }`}
              aria-current={activeTab === 'upload' || activeTab === 'results' ? 'page' : undefined}
            >
              <Camera className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
              <span>{uiStrings.nav_check || 'Check Skin'}</span>
            </button>

            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm sm:text-base font-semibold transition-colors cursor-pointer ${
                activeTab === 'chat'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-200 hover:bg-slate-800 hover:text-white'
              }`}
              aria-current={activeTab === 'chat' ? 'page' : undefined}
            >
              <MessageSquare className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
              <span>{uiStrings.nav_chat || 'Chat'}</span>
            </button>

            <button
              onClick={() => setActiveTab('nearby')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm sm:text-base font-semibold transition-colors cursor-pointer ${
                activeTab === 'nearby'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-200 hover:bg-slate-800 hover:text-white'
              }`}
              aria-current={activeTab === 'nearby' ? 'page' : undefined}
            >
              <MapPin className="w-4 h-4 sm:w-5 sm:h-5 text-red-400" aria-hidden="true" />
              <span>{uiStrings.nav_nearby || 'Nearby Care'}</span>
            </button>

            <button
              onClick={() => setActiveTab('about')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm sm:text-base font-semibold transition-colors cursor-pointer ${
                activeTab === 'about'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-200 hover:bg-slate-800 hover:text-white'
              }`}
              aria-current={activeTab === 'about' ? 'page' : undefined}
            >
              <Info className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
              <span className="hidden sm:inline">{uiStrings.nav_about || 'About'}</span>
            </button>

            <button
              onClick={() => setActiveTab('admin')}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm sm:text-base font-semibold transition-colors cursor-pointer ${
                activeTab === 'admin'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-200 hover:bg-slate-800 hover:text-white'
              }`}
              aria-current={activeTab === 'admin' ? 'page' : undefined}
              title="Public Health Surveillance Admin"
            >
              <Lock className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" aria-hidden="true" />
              <span className="hidden md:inline">Admin</span>
            </button>
          </nav>

          {/* Multilingual Selector */}
          <div className="flex items-center gap-1 bg-slate-800 border border-slate-700 rounded-xl px-2 py-1">
            <Globe className="w-4 h-4 text-blue-400 shrink-0" aria-hidden="true" />
            <select
              value={currentLanguage}
              onChange={(e) => onLanguageChange && onLanguageChange(e.target.value)}
              className="bg-transparent text-xs sm:text-sm text-white font-semibold focus:outline-none cursor-pointer pr-1"
              aria-label="Select Interface Language"
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code} className="bg-slate-900 text-white">
                  {lang.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </header>
  );
}

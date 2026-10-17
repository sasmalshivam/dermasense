import React, { useState, useEffect } from 'react';
import { 
  Camera, 
  ShieldCheck, 
  Sparkles, 
  BookOpen, 
  ArrowRight, 
  Lock, 
  MapPinOff, 
  HeartHandshake,
  Activity
} from 'lucide-react';
import { fetchConditions } from '../api';

export default function HomeView({ onStartCheck, onSelectCondition }) {
  const [conditions, setConditions] = useState([]);
  const [loadingConditions, setLoadingConditions] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchConditions();
        if (data && data.conditions) {
          setConditions(data.conditions);
        }
      } catch (e) {
        console.warn('Failed to load conditions catalog:', e);
      } finally {
        setLoadingConditions(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-10 py-6 max-w-4xl mx-auto px-4">
      {/* Hero Section */}
      <section className="text-center space-y-4 pt-4">
        <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-900 border border-blue-300 px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-semibold tracking-wide">
          <Activity className="w-4 h-4 text-blue-700" aria-hidden="true" />
          <span>Smart India Hackathon 2025 • PS 25049</span>
        </div>

        <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-slate-900 tracking-tight leading-tight">
          AI Skin Health Awareness <br className="hidden sm:inline" />
          <span className="text-blue-700">Made Simple & Private</span>
        </h1>

        <p className="text-base sm:text-xl text-slate-700 max-w-2xl mx-auto leading-relaxed">
          Upload or take a photo of a skin spot to receive immediate visual pattern analysis, 
          an explainable AI heatmap, and verified first-aid guidance from trusted health authorities.
        </p>

        {/* Big High-Contrast Call to Action */}
        <div className="pt-3">
          <button
            onClick={onStartCheck}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-3 bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg sm:text-xl px-8 py-4 rounded-2xl shadow-lg hover:shadow-xl transition-all transform active:scale-95 focus:ring-4 focus:ring-blue-300 cursor-pointer"
            aria-label="Start skin check now"
          >
            <Camera className="w-6 h-6 sm:w-7 sm:h-7" aria-hidden="true" />
            <span>Check My Skin Now</span>
            <ArrowRight className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
      </section>

      {/* What It Does (3-Step Icon-Led Guide) */}
      <section aria-labelledby="how-it-works-heading" className="bg-white rounded-3xl p-6 sm:p-8 shadow-sm border border-slate-200">
        <h2 id="how-it-works-heading" className="text-xl sm:text-2xl font-bold text-slate-900 text-center mb-6">
          How DermaSense Works in 3 Simple Steps
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Step 1 */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 flex flex-col items-center text-center space-y-3">
            <div className="w-14 h-14 bg-blue-100 text-blue-700 rounded-2xl flex items-center justify-center text-2xl font-black shadow-inner">
              <Camera className="w-7 h-7" aria-hidden="true" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">1. Take a Photo</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Snap a clear, focused photo of the skin lesion or rash using your phone in bright natural light.
            </p>
          </div>

          {/* Step 2 */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 flex flex-col items-center text-center space-y-3">
            <div className="w-14 h-14 bg-indigo-100 text-indigo-700 rounded-2xl flex items-center justify-center text-2xl font-black shadow-inner">
              <Sparkles className="w-7 h-7" aria-hidden="true" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">2. AI Visual Match</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Our neural network evaluates visual patterns, checks confidence, and generates a Grad-CAM heatmap showing what it analyzed.
            </p>
          </div>

          {/* Step 3 */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 flex flex-col items-center text-center space-y-3">
            <div className="w-14 h-14 bg-emerald-100 text-emerald-700 rounded-2xl flex items-center justify-center text-2xl font-black shadow-inner">
              <BookOpen className="w-7 h-7" aria-hidden="true" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">3. Verified Medical Guide</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Receive structured precautions, home care steps, red flags, and doctor triage criteria cited directly from WHO, NHS, and AAD.
            </p>
          </div>
        </div>
      </section>

      {/* Privacy & Safety Guarantee */}
      <section aria-labelledby="privacy-note-heading" className="bg-emerald-950 text-emerald-100 rounded-3xl p-6 sm:p-8 border-2 border-emerald-600/70 shadow-md">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-emerald-600 text-slate-950 rounded-xl">
            <ShieldCheck className="w-6 h-6" aria-hidden="true" />
          </div>
          <h2 id="privacy-note-heading" className="text-xl sm:text-2xl font-bold text-emerald-200">
            Strict Privacy & Confidentiality Guarantee
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div className="flex items-start gap-3 bg-emerald-900/60 p-4 rounded-xl border border-emerald-700/50">
            <Lock className="w-5 h-5 text-emerald-300 shrink-0 mt-0.5" aria-hidden="true" />
            <div className="text-sm">
              <span className="font-bold text-white block">100% In-Memory</span>
              Your photo is never saved to a disk or uploaded to any third-party cloud.
            </div>
          </div>

          <div className="flex items-start gap-3 bg-emerald-900/60 p-4 rounded-xl border border-emerald-700/50">
            <MapPinOff className="w-5 h-5 text-emerald-300 shrink-0 mt-0.5" aria-hidden="true" />
            <div className="text-sm">
              <span className="font-bold text-white block">EXIF / GPS Stripped</span>
              All location tags and device metadata are automatically purged before processing.
            </div>
          </div>

          <div className="flex items-start gap-3 bg-emerald-900/60 p-4 rounded-xl border border-emerald-700/50">
            <HeartHandshake className="w-5 h-5 text-emerald-300 shrink-0 mt-0.5" aria-hidden="true" />
            <div className="text-sm">
              <span className="font-bold text-white block">Free & Open Source</span>
              Zero paid API dependencies. Built with local PyTorch, ONNX, and FastAPI.
            </div>
          </div>
        </div>
      </section>

      {/* Condition Knowledge Base Explorer */}
      <section aria-labelledby="conditions-explorer-heading" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <h2 id="conditions-explorer-heading" className="text-xl sm:text-2xl font-bold text-slate-900">
              Browse Skin Condition Guides
            </h2>
            <p className="text-sm text-slate-600">
              Explore 12 clinically verified condition guides with symptoms, red flags, and doctor triage criteria.
            </p>
          </div>
        </div>

        {loadingConditions ? (
          <div className="text-center py-8 text-slate-500">Loading verified condition guides...</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {conditions.map((item) => (
              <button
                key={item.condition_id}
                onClick={() => onSelectCondition && onSelectCondition(item.condition_id)}
                className="bg-white hover:bg-blue-50/70 border border-slate-200 hover:border-blue-300 p-4 rounded-2xl text-left transition-all shadow-sm flex flex-col justify-between group cursor-pointer focus:ring-2 focus:ring-blue-400"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-slate-900 group-hover:text-blue-700 text-base">
                      {item.name}
                    </span>
                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                      item.severity_level === 'high'
                        ? 'bg-red-100 text-red-800 border border-red-200'
                        : item.severity_level === 'medium'
                        ? 'bg-amber-100 text-amber-800 border border-amber-200'
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    }`}>
                      {item.severity_level} risk
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 line-clamp-2 mt-2 leading-relaxed">
                    {item.description}
                  </p>
                </div>
                <div className="text-xs font-semibold text-blue-600 group-hover:text-blue-800 pt-3 flex items-center gap-1">
                  <span>Read precautions & symptoms</span>
                  <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

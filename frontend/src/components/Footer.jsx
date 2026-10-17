import React from 'react';
import { AlertTriangle, ShieldCheck } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-slate-900 text-slate-300 border-t border-slate-800 mt-12 py-8 px-4">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Prominent High-Contrast Disclaimer Banner */}
        <div 
          role="region" 
          aria-label="Clinical Disclaimer"
          className="bg-amber-950/80 border-2 border-amber-600 rounded-xl p-4 sm:p-5 text-amber-100 flex flex-col sm:flex-row items-start sm:items-center gap-4 shadow-sm"
        >
          <div className="p-2.5 bg-amber-600 text-slate-950 rounded-lg shrink-0">
            <AlertTriangle className="w-6 h-6" aria-hidden="true" />
          </div>
          <div className="space-y-1">
            <p className="font-bold text-amber-200 text-base sm:text-lg tracking-wide uppercase">
              Mandatory Public Health Disclaimer
            </p>
            <p className="text-xs sm:text-sm text-amber-100 leading-relaxed font-normal">
              DermaSense is an educational skin health awareness tool developed for the Smart India Hackathon 2025 
              (Team Healthnautix, PS 25049). It <strong>does NOT provide a medical diagnosis</strong>, clinical prognosis, 
              or treatment prescription. All outputs are statistical <em>possible conditions</em> based on visual patterns. 
              Always consult a licensed dermatologist or medical practitioner for formal clinical evaluation.
            </p>
          </div>
        </div>

        {/* Citations & Authorities */}
        <div className="flex flex-wrap items-center justify-between gap-4 text-xs sm:text-sm text-slate-400 pt-2 border-t border-slate-800/80">
          <div>
            <span className="font-semibold text-slate-200">Verified Medical Source Authorities:</span>{' '}
            <span className="text-slate-300">WHO • MoHFW / ICMR • AAD • NHS UK • CDC • DermNet NZ</span>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
            <ShieldCheck className="w-4 h-4 text-emerald-400" aria-hidden="true" />
            <span>Zero Data Stored • 100% In-Memory Processing</span>
          </div>
        </div>

        {/* Project Attribution */}
        <div className="text-center text-xs text-slate-300">
          <p>© 2026 Team Healthnautix • Smart India Hackathon 2025 • Public Health Chatbot (PS 25049)</p>
          <p className="mt-1 text-slate-300 font-medium">All clinical guidance records explicitly marked: <code className="bg-slate-800 px-1.5 py-0.5 rounded text-amber-300">reviewed_by_clinician: false</code></p>
        </div>
      </div>
    </footer>
  );
}

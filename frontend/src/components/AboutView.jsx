import React from 'react';
import { 
  ShieldAlert, 
  Scale, 
  Users, 
  ExternalLink, 
  BookOpen, 
  AlertTriangle, 
  Activity
} from 'lucide-react';

export default function AboutView() {
  return (
    <div className="space-y-8 py-4 max-w-4xl mx-auto px-4">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-900 border border-blue-300 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide">
          <Activity className="w-4 h-4 text-blue-700" aria-hidden="true" />
          <span>Team Healthnautix • SIH 2025 (PS 25049)</span>
        </div>
        <h1 className="text-2xl sm:text-4xl font-black text-slate-900 tracking-tight">
          About DermaSense & Clinical Limitations
        </h1>
        <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
          Full transparency on algorithmic limitations, dataset demographic distribution, and clinical scope.
        </p>
      </div>

      {/* 1. NOT A DIAGNOSIS - PRIMARY NOTICE */}
      <div 
        role="region" 
        aria-label="Clinical Scope Notice"
        className="bg-amber-50 border-2 border-amber-600 rounded-3xl p-6 sm:p-8 text-amber-950 shadow-sm space-y-3"
      >
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-600 text-slate-950 rounded-xl shrink-0">
            <AlertTriangle className="w-6 h-6" aria-hidden="true" />
          </div>
          <h2 className="text-xl font-bold text-amber-950">
            Why DermaSense Does NOT Provide a Diagnosis
          </h2>
        </div>
        <p className="text-sm sm:text-base text-amber-900 leading-relaxed font-medium">
          A definitive medical diagnosis of a skin condition requires physical palpation, dermoscopy with polarized lighting, 
          patient medical history, family risk factors, and frequently a formal histopathological biopsy evaluated by a pathologist. 
          DermaSense uses computer vision to detect visual similarities against public reference images; it cannot and does not replace 
          a licensed physician or clinical examination.
        </p>
      </div>

      {/* 2. DATASET BIAS & SKIN-TONE LIMITATIONS */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
        <div className="flex items-center gap-3 border-b border-slate-200 pb-4">
          <div className="p-2.5 bg-blue-100 text-blue-700 rounded-xl shrink-0">
            <Scale className="w-6 h-6" aria-hidden="true" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            Dataset Demographics & Skin-Tone Bias Disclosure
          </h2>
        </div>

        <div className="space-y-4 text-sm text-slate-700 leading-relaxed">
          <p>
            Public clinical datasets commonly used in academic research (including <strong>HAM10000</strong>, <strong>ISIC Archive</strong>, and <strong>DermNet</strong>) 
            disproportionately consist of dermatological photography from populations with lighter skin types 
            (Fitzpatrick skin phototypes I, II, and III, predominantly from North American, European, and Australian clinics).
          </p>

          <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-2">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-600" />
              <span>Implications for Darker Skin Tones (Fitzpatrick IV–VI)</span>
            </h3>
            <ul className="list-disc pl-5 space-y-1 text-xs sm:text-sm">
              <li>
                Erythema (redness) often presents differently on deep skin tones, appearing violaceous, hyperpigmented, brown, or grayish.
              </li>
              <li>
                Melanoma in darker-skinned individuals disproportionately presents as <strong>Acral Lentiginous Melanoma</strong> on the palms, 
                soles of feet, and under fingernails/toenails—areas underrepresented in standard dermoscopy archives.
              </li>
              <li>
                Our engineering architecture addresses this by implementing an <strong>Out-of-Distribution (OOD) safeguard</strong> with 
                max-softmax and energy score thresholds, returning <em>"unable to assess"</em> rather than generating high-confidence false predictions on unfamiliar visual distributions.
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* 3. NON-NEGOTIABLE SYSTEM RULES */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
        <div className="flex items-center gap-3 border-b border-slate-200 pb-4">
          <div className="p-2.5 bg-emerald-100 text-emerald-700 rounded-xl shrink-0">
            <ShieldAlert className="w-6 h-6" aria-hidden="true" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            Non-Negotiable System Ethics & Safety Standards
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
            <span className="font-bold text-slate-900 text-sm block">1. Zero Mock Data</span>
            <p className="text-xs text-slate-600">
              Predictions, metrics, and calibration values are computed dynamically from real execution pipelines.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
            <span className="font-bold text-slate-900 text-sm block">2. In-Memory Processing</span>
            <p className="text-xs text-slate-600">
              User photos are never persisted to disk or cloud databases. EXIF and GPS tags are purged immediately.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
            <span className="font-bold text-slate-900 text-sm block">3. Approved Medical Sources Only</span>
            <p className="text-xs text-slate-600">
              All clinical text is cited directly from WHO, MoHFW/ICMR, AAD, NHS UK, CDC, or DermNet NZ.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
            <span className="font-bold text-slate-900 text-sm block">4. Clinician Review Disclosure</span>
            <p className="text-xs text-slate-600">
              Every guidance record is explicitly marked <code className="bg-slate-200 px-1 rounded">reviewed_by_clinician: false</code> until licensed physicians certify it.
            </p>
          </div>
        </div>
      </div>

      {/* 4. APPROVED AUTHORITIES CITATION LIST */}
      <div className="bg-slate-900 text-white rounded-3xl p-6 sm:p-8 space-y-4">
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-blue-400" />
          <span>Approved Clinical Source Authorities</span>
        </h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          DermaSense knowledge base records link to the following accredited public health organizations:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <a
            href="https://www.who.int"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-3 rounded-xl bg-slate-800 hover:bg-slate-700 transition border border-slate-700 text-xs sm:text-sm font-semibold"
          >
            <span>World Health Organization (WHO)</span>
            <ExternalLink className="w-4 h-4 text-blue-400" />
          </a>

          <a
            href="https://www.mohfw.gov.in"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-3 rounded-xl bg-slate-800 hover:bg-slate-700 transition border border-slate-700 text-xs sm:text-sm font-semibold"
          >
            <span>Ministry of Health & Family Welfare (MoHFW India)</span>
            <ExternalLink className="w-4 h-4 text-blue-400" />
          </a>

          <a
            href="https://www.aad.org"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-3 rounded-xl bg-slate-800 hover:bg-slate-700 transition border border-slate-700 text-xs sm:text-sm font-semibold"
          >
            <span>American Academy of Dermatology (AAD)</span>
            <ExternalLink className="w-4 h-4 text-blue-400" />
          </a>

          <a
            href="https://www.nhs.uk"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-3 rounded-xl bg-slate-800 hover:bg-slate-700 transition border border-slate-700 text-xs sm:text-sm font-semibold"
          >
            <span>National Health Service (NHS UK)</span>
            <ExternalLink className="w-4 h-4 text-blue-400" />
          </a>

          <a
            href="https://www.cdc.gov"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-3 rounded-xl bg-slate-800 hover:bg-slate-700 transition border border-slate-700 text-xs sm:text-sm font-semibold"
          >
            <span>Centers for Disease Control and Prevention (CDC)</span>
            <ExternalLink className="w-4 h-4 text-blue-400" />
          </a>

          <a
            href="https://dermnetnz.org"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-3 rounded-xl bg-slate-800 hover:bg-slate-700 transition border border-slate-700 text-xs sm:text-sm font-semibold"
          >
            <span>DermNet New Zealand</span>
            <ExternalLink className="w-4 h-4 text-blue-400" />
          </a>
        </div>
      </div>
    </div>
  );
}

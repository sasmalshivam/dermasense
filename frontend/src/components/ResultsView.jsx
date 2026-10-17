import React, { useState } from 'react';
import { 
  AlertTriangle, 
  AlertOctagon, 
  CheckCircle2, 
  Layers, 
  Stethoscope, 
  FileText, 
  ChevronDown, 
  ChevronUp, 
  ExternalLink, 
  RefreshCw, 
  Star, 
  Send, 
  Flame, 
  Ban, 
  HeartHandshake, 
  Sparkles,
  Info,
  Download,
  MapPin,
  ShieldCheck,
} from 'lucide-react';
import { submitFeedback, submitTelemetryOptIn } from '../api';
import { generateClinicalPDF } from '../utils/pdfGenerator';

export default function ResultsView({ result, originalImageSrc, onReset, onNavigateNearby }) {
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [openSections, setOpenSections] = useState({
    about: true,
    firstAid: true,
    precautions: false,
    doNot: true,
    redFlags: true,
    whenToSeeDoctor: true,
    sources: true,
  });

  const [feedbackRating, setFeedbackRating] = useState(5);
  const [feedbackText, setFeedbackText] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);

  // Opt-in surveillance state
  const [telemetryConsent, setTelemetryConsent] = useState(false);
  const [telemetryRegion, setTelemetryRegion] = useState('Khurda (Bhubaneswar), Odisha');
  const [telemetrySubmitted, setTelemetrySubmitted] = useState(false);
  const [telemetrySubmitting, setTelemetrySubmitting] = useState(false);
  const [telemetryError, setTelemetryError] = useState('');
  const [pdfGenerating, setPdfGenerating] = useState(false);

  if (!result) return null;

  const {
    status,
    assessment_summary,
    top_conditions = [],
    top_condition_id,
    top_condition_name,
    confidence_score,
    is_skin,
    low_confidence,
    doctor_notice,
    gradcam_heatmap,
    knowledge_base,
    severity_level = 'low',
    disclaimer
  } = result;

  const isHighSeverity = severity_level === 'high' || !!doctor_notice;
  const isUnableToAssess = status === 'unable_to_assess' || low_confidence || !is_skin;

  const toggleSection = (key) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    setFeedbackSubmitting(true);
    try {
      await submitFeedback({
        condition_id: top_condition_id || 'unknown',
        rating: feedbackRating,
        feedback_text: feedbackText,
        clinician_reviewed: false,
      });
      setFeedbackSubmitted(true);
    } catch (err) {
      console.warn('Failed to submit feedback:', err);
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  const handleDownloadPDF = () => {
    setPdfGenerating(true);
    try {
      generateClinicalPDF(result, telemetryRegion);
    } catch (e) {
      console.error('Failed to generate PDF:', e);
      alert('Could not generate PDF summary. Please try again.');
    } finally {
      setPdfGenerating(false);
    }
  };

  const handleTelemetrySubmit = async (e) => {
    e.preventDefault();
    if (!telemetryConsent) {
      setTelemetryError('Please check the consent box to proceed.');
      return;
    }
    setTelemetrySubmitting(true);
    setTelemetryError('');
    try {
      await submitTelemetryOptIn(
        true,
        top_condition_id || 'unknown',
        top_condition_name || 'Unspecified Condition',
        telemetryRegion
      );
      setTelemetrySubmitted(true);
    } catch (err) {
      setTelemetryError(err.message || 'Failed to submit anonymized telemetry.');
    } finally {
      setTelemetrySubmitting(false);
    }
  };

  return (
    <div className="space-y-8 py-4 max-w-4xl mx-auto px-4">
      {/* 1. URGENT EMERGENCY BANNER (If High Severity / Melanoma / BCC / AK) */}
      {isHighSeverity && (
        <div 
          role="alert" 
          aria-live="assertive"
          className="bg-red-700 text-white rounded-3xl p-5 sm:p-6 shadow-xl border-4 border-red-900 flex flex-col sm:flex-row items-start sm:items-center gap-4 animate-bounce-subtle"
        >
          <div className="p-3 bg-red-900 text-white rounded-2xl shrink-0">
            <AlertOctagon className="w-8 h-8 sm:w-10 sm:h-10" aria-hidden="true" />
          </div>
          <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-black tracking-tight text-white uppercase">
              Urgent Clinical Notice
            </h2>
            <p className="text-sm sm:text-base text-red-100 font-medium leading-relaxed">
              {doctor_notice || 
                "This visual assessment detected patterns associated with a high-priority skin condition. Please schedule a clinical examination with a qualified dermatologist promptly. Do not attempt home excision or self-treatment."
              }
            </p>
          </div>
        </div>
      )}

      {/* 2. LOW-CONFIDENCE / UNABLE TO ASSESS WARNING STATE */}
      {isUnableToAssess && (
        <div 
          role="alert" 
          aria-live="polite"
          className="bg-amber-500 text-slate-950 rounded-3xl p-5 sm:p-6 shadow-md border-3 border-amber-600 flex flex-col sm:flex-row items-start gap-4"
        >
          <div className="p-3 bg-amber-600 text-slate-950 rounded-2xl shrink-0">
            <AlertTriangle className="w-8 h-8 sm:w-10 sm:h-10" aria-hidden="true" />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl sm:text-2xl font-black tracking-tight text-slate-950">
              Unable to Assess with High Confidence
            </h2>
            <p className="text-sm sm:text-base text-slate-900 font-semibold leading-relaxed">
              {assessment_summary}
            </p>
            <p className="text-xs sm:text-sm text-slate-800">
              The AI model could not identify with statistical certainty that this image contains human skin or a clear lesion. 
              Please retake a steady photo in bright natural light, 10-15 cm away, focusing only on the skin lesion.
            </p>
            <div className="pt-2">
              <button
                onClick={onReset}
                className="inline-flex items-center gap-2 bg-slate-950 hover:bg-slate-900 text-white font-bold text-sm px-5 py-2.5 rounded-xl shadow transition-all cursor-pointer"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                <span>Retake Photo</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Assessment Summary Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Primary Candidate
              </span>
              <span className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded-full ${
                severity_level === 'high'
                  ? 'bg-red-100 text-red-800 border border-red-300'
                  : severity_level === 'medium'
                  ? 'bg-amber-100 text-amber-800 border border-amber-300'
                  : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
              }`}>
                {severity_level} severity
              </span>
              {typeof confidence_score === 'number' && (
                <span className="text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200 px-2.5 py-0.5 rounded-full">
                  {(confidence_score * 100).toFixed(1)}% Match
                </span>
              )}
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mt-1">
              Possible Condition: {top_condition_name}
            </h1>
            {knowledge_base?.local_names?.length > 0 && (
              <p className="text-xs sm:text-sm text-slate-500 mt-1">
                Also known as: {knowledge_base.local_names.join(', ')}
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 self-start sm:self-center">
            <button
              type="button"
              onClick={handleDownloadPDF}
              disabled={pdfGenerating}
              className="inline-flex items-center gap-2 text-xs sm:text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 active:scale-95 px-3.5 py-2.5 rounded-xl transition-all shadow-sm cursor-pointer"
              aria-label="Download Clinical PDF Summary"
            >
              <Download className="w-4 h-4" aria-hidden="true" />
              <span>{pdfGenerating ? 'Generating PDF...' : 'Download PDF Summary'}</span>
            </button>

            {onNavigateNearby && (
              <button
                type="button"
                onClick={onNavigateNearby}
                className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-bold text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 active:scale-95 px-3 py-2.5 rounded-xl transition-all cursor-pointer"
                aria-label="Find Nearby Clinics and Dermatologists"
              >
                <MapPin className="w-4 h-4 text-red-600" aria-hidden="true" />
                <span>Nearby Care &amp; SOS</span>
              </button>
            )}

            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 active:scale-95 px-3 py-2.5 rounded-xl transition-all cursor-pointer"
              aria-label="Upload a new photo"
            >
              <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
              <span>New Photo</span>
            </button>
          </div>
        </div>

        {/* 3. IMAGE PREVIEW & GRAD-CAM HEATMAP COMPARISON CARD */}
        <div className="bg-slate-950 rounded-3xl p-4 sm:p-6 text-white space-y-4 shadow-inner">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-blue-400" aria-hidden="true" />
              <span className="text-sm font-bold text-slate-200">
                Explainable AI (Grad-CAM) Visual Attention
              </span>
            </div>

            {/* Toggle Switch */}
            {gradcam_heatmap && (
              <div className="flex items-center bg-slate-900 rounded-xl p-1 border border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowHeatmap(false)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    !showHeatmap
                      ? 'bg-blue-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  aria-pressed={!showHeatmap}
                >
                  Original Photo
                </button>
                <button
                  type="button"
                  onClick={() => setShowHeatmap(true)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    showHeatmap
                      ? 'bg-blue-600 text-white shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  aria-pressed={showHeatmap}
                >
                  AI Heatmap Overlay
                </button>
              </div>
            )}
          </div>

          {/* Visual Display */}
          <div className="relative flex items-center justify-center bg-slate-900 rounded-2xl overflow-hidden min-h-64 sm:min-h-80 max-h-96">
            <img
              src={showHeatmap && gradcam_heatmap ? gradcam_heatmap : originalImageSrc}
              alt={showHeatmap ? "Grad-CAM heatmap overlay" : "Original uploaded skin image"}
              className="max-h-92 w-auto object-contain rounded-xl"
            />
            <div className="absolute top-3 left-3 bg-slate-950/80 backdrop-blur text-xs px-3 py-1 rounded-lg border border-slate-700 font-semibold">
              {showHeatmap && gradcam_heatmap ? 'Grad-CAM Attention Map' : 'Original Skin Photo'}
            </div>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            <strong className="text-slate-200">What does this heatmap show?</strong> The warmer red and yellow regions indicate 
            the exact morphological features the neural network examined to compute this preliminary assessment.
          </p>
        </div>

        {/* 4. TOP-3 POSSIBLE CONDITIONS CARDS WITH CALIBRATED PROBABILITY BARS */}
        <div className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-600" aria-hidden="true" />
            <span>Top-3 Preliminary Statistical Matches</span>
          </h2>
          <p className="text-xs text-slate-500">
            Calibrated softmax probabilities scaled by temperature factor on validation data.
          </p>

          <div className="space-y-2.5 pt-1">
            {top_conditions.map((item, idx) => (
              <div 
                key={item.condition_id}
                className={`p-4 rounded-2xl border transition-all ${
                  idx === 0 
                    ? 'bg-blue-50/50 border-blue-200 ring-1 ring-blue-300'
                    : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div className="flex items-center justify-between text-sm sm:text-base font-bold text-slate-900 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-slate-200 text-slate-800 text-xs font-black flex items-center justify-center">
                      {idx + 1}
                    </span>
                    <span>{item.name}</span>
                    {idx === 0 && (
                      <span className="text-[10px] bg-blue-600 text-white font-black px-2 py-0.5 rounded-full uppercase">
                        Primary Match
                      </span>
                    )}
                  </div>
                  <span className="text-blue-700 font-black">{item.percentage}</span>
                </div>

                {/* Accessible Visual Progress Bar */}
                <div 
                  className="w-full bg-slate-200 h-3 rounded-full overflow-hidden" 
                  role="progressbar" 
                  aria-valuenow={Math.round(item.probability * 100)} 
                  aria-valuemin="0" 
                  aria-valuemax="100"
                  aria-label={`Probability for ${item.name}: ${item.percentage}`}
                >
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      idx === 0 
                        ? 'bg-blue-600' 
                        : 'bg-slate-500'
                    }`}
                    style={{ width: `${Math.max(item.probability * 100, 2)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 5. VERIFIED MEDICAL GUIDANCE ACCORDION SECTIONS */}
        {knowledge_base && (
          <div className="space-y-4 pt-4 border-t border-slate-200">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Stethoscope className="w-6 h-6 text-blue-600" aria-hidden="true" />
              <span>Verified Medical Guidance ({knowledge_base.name})</span>
            </h2>
            <p className="text-xs text-slate-500">
              Guidance cited from approved authorities (WHO, NHS, AAD, CDC, DermNet NZ). 
              Every entry marked <code className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded">reviewed_by_clinician: false</code>.
            </p>

            <div className="space-y-3 pt-2">
              {/* About Section */}
              <div className="border border-slate-200 rounded-2xl overflow-hidden bg-white">
                <button
                  type="button"
                  onClick={() => toggleSection('about')}
                  className="w-full px-5 py-4 flex items-center justify-between text-left font-bold text-slate-900 hover:bg-slate-50 cursor-pointer"
                  aria-expanded={openSections.about}
                >
                  <span className="flex items-center gap-2.5 text-base sm:text-lg">
                    <Info className="w-5 h-5 text-blue-600" aria-hidden="true" />
                    <span>Description & Common Symptoms</span>
                  </span>
                  {openSections.about ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {openSections.about && (
                  <div className="px-5 pb-5 pt-1 space-y-4 text-sm text-slate-700 border-t border-slate-100">
                    <p className="leading-relaxed font-medium">{knowledge_base.description}</p>
                    {knowledge_base.common_symptoms?.length > 0 && (
                      <div>
                        <h4 className="font-bold text-slate-900 text-sm mb-2">Common Signs:</h4>
                        <ul className="list-disc pl-5 space-y-1">
                          {knowledge_base.common_symptoms.map((sym, i) => (
                            <li key={i}>{sym}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* First Aid */}
              <div className="border border-slate-200 rounded-2xl overflow-hidden bg-white">
                <button
                  type="button"
                  onClick={() => toggleSection('firstAid')}
                  className="w-full px-5 py-4 flex items-center justify-between text-left font-bold text-slate-900 hover:bg-slate-50 cursor-pointer"
                  aria-expanded={openSections.firstAid}
                >
                  <span className="flex items-center gap-2.5 text-base sm:text-lg">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" aria-hidden="true" />
                    <span>Immediate First Aid & Safe Steps</span>
                  </span>
                  {openSections.firstAid ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {openSections.firstAid && (
                  <div className="px-5 pb-5 pt-1 space-y-2 text-sm text-slate-700 border-t border-slate-100">
                    <ul className="list-disc pl-5 space-y-1.5">
                      {knowledge_base.first_aid?.map((step, i) => (
                        <li key={i} className="leading-relaxed">{step}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Precautions & Home Care */}
              <div className="border border-slate-200 rounded-2xl overflow-hidden bg-white">
                <button
                  type="button"
                  onClick={() => toggleSection('precautions')}
                  className="w-full px-5 py-4 flex items-center justify-between text-left font-bold text-slate-900 hover:bg-slate-50 cursor-pointer"
                  aria-expanded={openSections.precautions}
                >
                  <span className="flex items-center gap-2.5 text-base sm:text-lg">
                    <HeartHandshake className="w-5 h-5 text-blue-600" aria-hidden="true" />
                    <span>Precautions & Home Care</span>
                  </span>
                  {openSections.precautions ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {openSections.precautions && (
                  <div className="px-5 pb-5 pt-1 space-y-3 text-sm text-slate-700 border-t border-slate-100">
                    <ul className="list-disc pl-5 space-y-1.5">
                      {knowledge_base.precautions?.map((prec, i) => (
                        <li key={i} className="leading-relaxed">{prec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* DO NOT SECTION (Harmful practices to strictly avoid) */}
              <div className="border-2 border-red-300 rounded-2xl overflow-hidden bg-red-50/40">
                <button
                  type="button"
                  onClick={() => toggleSection('doNot')}
                  className="w-full px-5 py-4 flex items-center justify-between text-left font-black text-red-950 hover:bg-red-100/50 cursor-pointer"
                  aria-expanded={openSections.doNot}
                >
                  <span className="flex items-center gap-2.5 text-base sm:text-lg">
                    <Ban className="w-5 h-5 text-red-600" aria-hidden="true" />
                    <span>What to Strictly Avoid (Do NOT)</span>
                  </span>
                  {openSections.doNot ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {openSections.doNot && (
                  <div className="px-5 pb-5 pt-1 space-y-2 text-sm text-red-900 border-t border-red-200">
                    <ul className="list-disc pl-5 space-y-1.5 font-medium">
                      {knowledge_base.do_not?.map((dont, i) => (
                        <li key={i} className="leading-relaxed">{dont}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Red Flags */}
              <div className="border-2 border-amber-300 rounded-2xl overflow-hidden bg-amber-50/40">
                <button
                  type="button"
                  onClick={() => toggleSection('redFlags')}
                  className="w-full px-5 py-4 flex items-center justify-between text-left font-bold text-amber-950 hover:bg-amber-100/50 cursor-pointer"
                  aria-expanded={openSections.redFlags}
                >
                  <span className="flex items-center gap-2.5 text-base sm:text-lg">
                    <Flame className="w-5 h-5 text-amber-600" aria-hidden="true" />
                    <span>Red Flag Warning Signs</span>
                  </span>
                  {openSections.redFlags ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {openSections.redFlags && (
                  <div className="px-5 pb-5 pt-1 space-y-2 text-sm text-amber-950 border-t border-amber-200">
                    <ul className="list-disc pl-5 space-y-1.5 font-medium">
                      {knowledge_base.red_flags?.map((flag, i) => (
                        <li key={i} className="leading-relaxed">{flag}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* When to See a Doctor */}
              <div className="border border-blue-200 rounded-2xl overflow-hidden bg-blue-50/40">
                <button
                  type="button"
                  onClick={() => toggleSection('whenToSeeDoctor')}
                  className="w-full px-5 py-4 flex items-center justify-between text-left font-bold text-blue-950 hover:bg-blue-100/50 cursor-pointer"
                  aria-expanded={openSections.whenToSeeDoctor}
                >
                  <span className="flex items-center gap-2.5 text-base sm:text-lg">
                    <Stethoscope className="w-5 h-5 text-blue-700" aria-hidden="true" />
                    <span>When to See a Doctor</span>
                  </span>
                  {openSections.whenToSeeDoctor ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {openSections.whenToSeeDoctor && (
                  <div className="px-5 pb-5 pt-1 space-y-2 text-sm text-blue-900 border-t border-blue-200">
                    <p className="leading-relaxed font-semibold">{knowledge_base.when_to_see_doctor}</p>
                  </div>
                )}
              </div>

              {/* Sources Section */}
              <div className="border border-slate-200 rounded-2xl overflow-hidden bg-white">
                <button
                  type="button"
                  onClick={() => toggleSection('sources')}
                  className="w-full px-5 py-4 flex items-center justify-between text-left font-bold text-slate-900 hover:bg-slate-50 cursor-pointer"
                  aria-expanded={openSections.sources}
                >
                  <span className="flex items-center gap-2.5 text-base sm:text-lg">
                    <FileText className="w-5 h-5 text-indigo-600" aria-hidden="true" />
                    <span>Authoritative Medical Sources & Citations</span>
                  </span>
                  {openSections.sources ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
                {openSections.sources && (
                  <div className="px-5 pb-5 pt-1 space-y-3 text-sm text-slate-700 border-t border-slate-100">
                    <div className="space-y-2">
                      {knowledge_base.sources?.map((src, i) => (
                        <div key={i} className="flex items-center justify-between gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
                          <span className="font-semibold text-slate-900 text-xs sm:text-sm">{src.title}</span>
                          <a
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-800 bg-white px-2.5 py-1.5 rounded-lg border border-slate-200 shrink-0"
                            aria-label={`View clinical guideline: ${src.title}`}
                          >
                            <span>Read Guideline</span>
                            <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 6. PERSISTENT MANDATORY DISCLAIMER */}
        <div 
          role="region" 
          aria-label="Result Disclaimer"
          className="bg-amber-50 border-2 border-amber-500 rounded-2xl p-4 sm:p-5 text-amber-950 text-xs sm:text-sm leading-relaxed"
        >
          <strong className="block text-amber-900 text-sm font-bold uppercase tracking-wide mb-1">
            Result Disclaimer
          </strong>
          {disclaimer}
        </div>

        {/* 7. CLINICIAN / USER FEEDBACK SECTION */}
        <div className="bg-slate-50 border border-slate-200 rounded-3xl p-5 sm:p-6 space-y-4">
          <h3 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
            <HeartHandshake className="w-5 h-5 text-blue-600" aria-hidden="true" />
            <span>Community & Clinician Feedback</span>
          </h3>

          {feedbackSubmitted ? (
            <div className="bg-emerald-100 border border-emerald-300 text-emerald-900 p-4 rounded-xl text-sm font-bold flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-700" />
              <span>Thank you! Your feedback has been recorded for active model monitoring.</span>
            </div>
          ) : (
            <form onSubmit={handleFeedbackSubmit} className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-700">Rating:</span>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setFeedbackRating(star)}
                      className="p-1 focus:outline-none cursor-pointer"
                      aria-label={`${star} star`}
                    >
                      <Star
                        className={`w-5 h-5 ${
                          star <= feedbackRating
                            ? 'text-amber-500 fill-amber-500'
                            : 'text-slate-300'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <textarea
                  rows="2"
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  placeholder="Optional: Provide feedback on guidance accuracy or usability..."
                  className="w-full text-xs sm:text-sm p-3 bg-white border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={feedbackSubmitting}
                className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs sm:text-sm px-4 py-2 rounded-xl transition-all cursor-pointer disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{feedbackSubmitting ? 'Submitting...' : 'Submit Feedback'}</span>
              </button>
            </form>
          )}
        </div>

        {/* 8. ANONYMIZED PUBLIC HEALTH TELEMETRY OPT-IN (ZERO PII) */}
        <div className="bg-blue-50/70 border border-blue-200 rounded-3xl p-5 sm:p-6 space-y-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 bg-blue-600 text-white rounded-xl shrink-0 mt-0.5">
              <ShieldCheck className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-bold text-slate-900">
                Help Track Skin Disease Trends in India (Opt-In)
              </h3>
              <p className="text-xs sm:text-sm text-slate-600 mt-0.5">
                Public health epidemiologists need aggregate data to identify skin disease outbreaks early.
                <strong> Zero photos, zero names, and zero IP addresses are ever stored.</strong>
              </p>
            </div>
          </div>

          {telemetrySubmitted ? (
            <div className="bg-emerald-100 border border-emerald-300 text-emerald-900 p-4 rounded-xl text-sm font-bold flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-700" />
              <span>Anonymized telemetry recorded. Thank you for contributing to Indian public health surveillance!</span>
            </div>
          ) : (
            <form onSubmit={handleTelemetrySubmit} className="space-y-3 pt-1">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Select Coarse District / Region
                </label>
                <select
                  value={telemetryRegion}
                  onChange={(e) => setTelemetryRegion(e.target.value)}
                  className="w-full text-xs sm:text-sm p-2.5 bg-white border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-none font-semibold text-slate-800"
                >
                  <option value="Khurda (Bhubaneswar), Odisha">Khurda (Bhubaneswar), Odisha</option>
                  <option value="Cuttack, Odisha">Cuttack, Odisha</option>
                  <option value="Bengaluru Urban, Karnataka">Bengaluru Urban, Karnataka</option>
                  <option value="Mumbai Suburban, Maharashtra">Mumbai Suburban, Maharashtra</option>
                  <option value="Delhi NCR">Delhi NCR</option>
                  <option value="Pune, Maharashtra">Pune, Maharashtra</option>
                  <option value="Kolkata, West Bengal">Kolkata, West Bengal</option>
                  <option value="Chennai, Tamil Nadu">Chennai, Tamil Nadu</option>
                  <option value="Hyderabad, Telangana">Hyderabad, Telangana</option>
                  <option value="Other District, India">Other District, India</option>
                </select>
              </div>

              <label className="flex items-start gap-2.5 cursor-pointer text-xs sm:text-sm text-slate-700 font-medium">
                <input
                  type="checkbox"
                  checked={telemetryConsent}
                  onChange={(e) => setTelemetryConsent(e.target.checked)}
                  className="mt-1 w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500 cursor-pointer"
                />
                <span>
                  I give explicit consent to share only this predicted condition (
                  <strong className="text-slate-900">{top_condition_name}</strong>) and my selected district for
                  anonymized disease surveillance.
                </span>
              </label>

              {telemetryError && (
                <div className="text-xs text-red-600 font-semibold">{telemetryError}</div>
              )}

              <button
                type="submit"
                disabled={telemetrySubmitting || !telemetryConsent}
                className="inline-flex items-center gap-2 bg-blue-700 hover:bg-blue-800 disabled:opacity-40 text-white font-bold text-xs sm:text-sm px-4 py-2.5 rounded-xl transition-all cursor-pointer shadow-xs"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>{telemetrySubmitting ? 'Recording...' : 'Contribute Anonymized Record'}</span>
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

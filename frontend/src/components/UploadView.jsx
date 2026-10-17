import React, { useState, useRef } from 'react';
import { 
  Camera, 
  Upload, 
  Sun, 
  Focus, 
  Crop, 
  Target, 
  AlertCircle, 
  CheckCircle2, 
  RefreshCw, 
  ArrowRight,
  Loader2,
  FileImage
} from 'lucide-react';
import { predictSkinCondition } from '../api';

export default function UploadView({ onAnalysisSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [consentChecked, setConsentChecked] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState('');
  const [errorMessage, setErrorMessage] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const handleFile = (file) => {
    if (!file) return;

    // Check file type
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setErrorMessage('Please select a JPG, PNG, or WEBP image file.');
      return;
    }

    // Check size limit (8 MB)
    if (file.size > 8 * 1024 * 1024) {
      setErrorMessage(`The selected file is too large (${(file.size / (1024 * 1024)).toFixed(1)} MB). Maximum allowed size is 8 MB.`);
      return;
    }

    setErrorMessage(null);
    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    setErrorMessage(null);
    setConsentChecked(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (cameraInputRef.current) cameraInputRef.current.value = '';
  };

  const handleSubmit = async () => {
    if (!selectedFile) {
      setErrorMessage('Please take or upload a photo first.');
      return;
    }
    if (!consentChecked) {
      setErrorMessage('Please check the confirmation box to proceed.');
      return;
    }

    setIsAnalyzing(true);
    setErrorMessage(null);
    setAnalysisStatus('Stripping EXIF/GPS tags & verifying image in memory...');

    try {
      setTimeout(() => {
        setAnalysisStatus('Running ONNX inference with temperature scaling...');
      }, 500);

      setTimeout(() => {
        setAnalysisStatus('Computing Grad-CAM explainability heatmap...');
      }, 1200);

      const result = await predictSkinCondition(selectedFile);
      setAnalysisStatus('Assessment complete!');
      onAnalysisSuccess(result, previewUrl);
    } catch (err) {
      console.error('Analysis error:', err);
      setErrorMessage(err.message || 'An unexpected error occurred while analyzing the image.');
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-8 py-4 max-w-3xl mx-auto px-4">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          Skin Photo Analysis
        </h1>
        <p className="text-sm sm:text-base text-slate-600 max-w-xl mx-auto">
          Capture or upload a clear, well-lit photo of your skin lesion. 
          Processed 100% in memory with zero storage.
        </p>
      </div>

      {/* Error Alert Box */}
      {errorMessage && (
        <div 
          role="alert" 
          aria-live="assertive"
          className="bg-red-50 border-2 border-red-500 rounded-2xl p-4 text-red-900 flex items-start gap-3 shadow-sm animate-fade-in"
        >
          <AlertCircle className="w-6 h-6 text-red-600 shrink-0 mt-0.5" aria-hidden="true" />
          <div className="space-y-1">
            <span className="font-bold text-red-950 text-base block">Notice</span>
            <p className="text-sm text-red-800 leading-relaxed font-medium">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Main Upload / Camera Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-6">
        {!previewUrl ? (
          <div>
            {/* Hidden native inputs */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => e.target.files && handleFile(e.target.files[0])}
              aria-label="Upload image from device"
            />
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => e.target.files && handleFile(e.target.files[0])}
              aria-label="Take photo with camera"
            />

            {/* Drag & Drop Box */}
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`border-3 border-dashed rounded-3xl p-8 sm:p-12 text-center transition-all ${
                isDragging
                  ? 'border-blue-600 bg-blue-50/70 scale-[0.99]'
                  : 'border-slate-300 hover:border-blue-400 bg-slate-50/50'
              }`}
            >
              <div className="flex flex-col items-center justify-center space-y-4">
                <div className="w-16 h-16 sm:w-20 sm:h-20 bg-blue-100 text-blue-700 rounded-3xl flex items-center justify-center shadow-inner">
                  <Camera className="w-8 h-8 sm:w-10 sm:h-10" aria-hidden="true" />
                </div>

                <div className="space-y-1">
                  <p className="text-lg sm:text-xl font-bold text-slate-800">
                    Take or Upload a Skin Photo
                  </p>
                  <p className="text-xs sm:text-sm text-slate-500">
                    Supports JPG, PNG, and WEBP formats (Max 8 MB)
                  </p>
                </div>

                {/* Primary Action Buttons */}
                <div className="flex flex-col sm:flex-row items-center gap-3 pt-2 w-full sm:w-auto">
                  <button
                    type="button"
                    onClick={() => cameraInputRef.current && cameraInputRef.current.click()}
                    className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-base px-6 py-3.5 rounded-xl shadow transition-all cursor-pointer focus:ring-4 focus:ring-blue-300 active:scale-95"
                    aria-label="Take photo using camera"
                  >
                    <Camera className="w-5 h-5" aria-hidden="true" />
                    <span>Use Camera</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => fileInputRef.current && fileInputRef.current.click()}
                    className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-900 text-white font-bold text-base px-6 py-3.5 rounded-xl shadow transition-all cursor-pointer focus:ring-4 focus:ring-slate-400 active:scale-95"
                    aria-label="Upload image from file manager"
                  >
                    <Upload className="w-5 h-5" aria-hidden="true" />
                    <span>Browse Files</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Image Preview State */
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <FileImage className="w-5 h-5 text-blue-600" aria-hidden="true" />
                <span className="font-bold text-slate-800 text-sm sm:text-base">
                  Selected Photo: {selectedFile?.name || 'Photo preview'}
                </span>
              </div>
              <button
                type="button"
                onClick={handleReset}
                disabled={isAnalyzing}
                className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-slate-600 hover:text-red-600 bg-slate-100 hover:bg-red-50 px-3 py-1.5 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                aria-label="Change selected photo"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                <span>Change Photo</span>
              </button>
            </div>

            <div className="flex flex-col items-center justify-center bg-slate-950 rounded-2xl overflow-hidden max-h-96 p-2 relative shadow-inner">
              <img
                src={previewUrl}
                alt="Uploaded skin photo preview"
                className="max-h-88 w-auto object-contain rounded-xl"
              />
              <div className="absolute bottom-4 left-4 bg-slate-900/80 backdrop-blur text-white text-xs px-3 py-1.5 rounded-lg border border-slate-700/60 font-medium">
                {(selectedFile.size / 1024).toFixed(0)} KB • Ready for in-memory analysis
              </div>
            </div>

            {/* Consent Checkbox */}
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 sm:p-5">
              <label className="flex items-start gap-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={consentChecked}
                  onChange={(e) => setConsentChecked(e.target.checked)}
                  disabled={isAnalyzing}
                  className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600 rounded border-slate-400 focus:ring-blue-500 mt-0.5 shrink-0 cursor-pointer"
                  aria-label="Informed consent confirmation"
                />
                <span className="text-xs sm:text-sm text-slate-700 leading-relaxed font-medium">
                  <strong>Informed Consent:</strong> I understand that DermaSense is an educational and skin health awareness tool. 
                  It <em>does not provide a medical diagnosis</em>. My photo is processed 100% in-memory with EXIF/GPS data stripped immediately.
                </span>
              </label>
            </div>

            {/* Submit / Analyze Button */}
            <div>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isAnalyzing || !consentChecked}
                className={`w-full inline-flex items-center justify-center gap-3 font-bold text-lg sm:text-xl py-4 rounded-2xl shadow-lg transition-all ${
                  isAnalyzing || !consentChecked
                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed shadow-none'
                    : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-500/20 hover:shadow-xl cursor-pointer active:scale-98'
                }`}
                aria-label="Analyze skin photo now"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-6 h-6 animate-spin" aria-hidden="true" />
                    <span>Analyzing Photo...</span>
                  </>
                ) : (
                  <>
                    <Camera className="w-6 h-6" aria-hidden="true" />
                    <span>Analyze Skin Photo</span>
                    <ArrowRight className="w-5 h-5" aria-hidden="true" />
                  </>
                )}
              </button>

              {/* Accessible Live Analysis Status */}
              {isAnalyzing && (
                <div 
                  role="status" 
                  aria-live="polite" 
                  className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl text-center space-y-2 animate-pulse"
                >
                  <p className="text-sm font-bold text-blue-900">{analysisStatus}</p>
                  <p className="text-xs text-blue-700">Please keep this window open while inference finishes.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Photo-Quality Tips (Icon-Led for Low-Literacy Accessibility) */}
      <section aria-labelledby="photo-tips-heading" className="bg-slate-50 rounded-3xl p-6 sm:p-8 border border-slate-200">
        <h2 id="photo-tips-heading" className="text-lg sm:text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-blue-600" aria-hidden="true" />
          <span>Photo Quality Tips for Accurate Awareness</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-start gap-3 bg-white p-4 rounded-xl border border-slate-200">
            <div className="p-2 bg-amber-100 text-amber-800 rounded-lg shrink-0">
              <Sun className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <span className="font-bold text-slate-900 text-sm block">1. Bright, Natural Light</span>
              <p className="text-xs text-slate-600 mt-0.5">
                Take photo near a window. Avoid dark rooms or heavy camera flash glare directly on the spot.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 bg-white p-4 rounded-xl border border-slate-200">
            <div className="p-2 bg-indigo-100 text-indigo-800 rounded-lg shrink-0">
              <Focus className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <span className="font-bold text-slate-900 text-sm block">2. Sharp, In Focus</span>
              <p className="text-xs text-slate-600 mt-0.5">
                Hold your camera steady. Tap the screen to focus directly on the mole or rash so it is not blurry.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 bg-white p-4 rounded-xl border border-slate-200">
            <div className="p-2 bg-emerald-100 text-emerald-800 rounded-lg shrink-0">
              <Crop className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <span className="font-bold text-slate-900 text-sm block">3. Close-Up View (10-15 cm)</span>
              <p className="text-xs text-slate-600 mt-0.5">
                Position camera 10 to 15 cm away so the lesion fills a clear part of the frame.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 bg-white p-4 rounded-xl border border-slate-200">
            <div className="p-2 bg-rose-100 text-rose-800 rounded-lg shrink-0">
              <Target className="w-5 h-5" aria-hidden="true" />
            </div>
            <div>
              <span className="font-bold text-slate-900 text-sm block">4. One Area Only</span>
              <p className="text-xs text-slate-600 mt-0.5">
                Capture skin only. Keep clothing, bedsheets, documents, and jewelry out of the photo.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

import React, { useState, useRef } from 'react';
import {
  Camera,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Trash2,
  Plus,
  Sparkles,
  ShieldCheck,
  Building2,
  Scale,
  ArrowRight,
  Eye,
  Layers,
  Image as ImageIcon
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { runInspectionAnalysis } from '../services/inspectionService';
import StatutoryInspectionReport from './StatutoryInspectionReport';

export default function MobileInspectionUpload({ user }) {
  const navigate = useNavigate();
  const cameraInputRef = useRef(null);
  const galleryInputRef = useRef(null);

  // Form Parameters
  const [productName, setProductName] = useState('');
  const [category, setCategory] = useState('Food & Beverages');
  const [pdpShape, setPdpShape] = useState('rectangular');
  const [location, setLocation] = useState(user?.zone_office || 'Northern Zonal Enforcement Office');
  const [inspectorName, setInspectorName] = useState(user?.name || 'Field Enforcement Inspector');

  // Multi-Angle Panels: [{ id: 1, title: 'Front Label', file, preview }]
  const [panels, setPanels] = useState([
    { id: 1, label: 'Front Panel (Principal Display)', file: null, preview: null, required: true },
    { id: 2, label: 'MRP & Net Quantity Panel', file: null, preview: null, required: false },
    { id: 3, label: 'Mfg / Expiry & Packer Panel', file: null, preview: null, required: false },
  ]);

  const [activePanelIndex, setActivePanelIndex] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [inspectionResult, setInspectionResult] = useState(null);

  // Camera Capture Handler
  const handleCameraCapture = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const preview = URL.createObjectURL(file);
      setPanels(prev => {
        const next = [...prev];
        next[activePanelIndex] = {
          ...next[activePanelIndex],
          file,
          preview
        };
        return next;
      });
      setErrorMessage('');
    }
  };

  const handleRemovePanelImage = (idx, e) => {
    e.stopPropagation();
    setPanels(prev => {
      const next = [...prev];
      next[idx] = {
        ...next[idx],
        file: null,
        preview: null
      };
      return next;
    });
  };

  const capturedCount = panels.filter(p => p.file !== null).length;

  const handleExecuteMobileAnalysis = async () => {
    const primaryFile = panels.find(p => p.file !== null)?.file;
    if (!primaryFile) {
      setErrorMessage('Please capture or upload at least the Front Package Panel to analyze.');
      return;
    }

    setProcessing(true);
    setErrorMessage('');

    try {
      const metadata = {
        product_name: productName.trim() || 'Pre-Packaged Retail Commodity',
        category,
        pdp_shape: pdpShape,
        location,
        inspector_name: inspectorName
      };

      const result = await runInspectionAnalysis(primaryFile, metadata);

      if (result && result.success) {
        setInspectionResult(result);
        localStorage.setItem('current_inspection', JSON.stringify(result.inspection || result));
      } else {
        setErrorMessage(result?.error || 'Analysis pipeline returned incomplete findings.');
      }
    } catch (err) {
      console.warn('Inspection execution error:', err);
      setErrorMessage(err.response?.data?.detail || err.message || 'Inspection pipeline failed to complete.');
    } finally {
      setProcessing(false);
    }
  };

  if (inspectionResult) {
    return (
      <div className="p-3 sm:p-6 space-y-4 max-w-5xl mx-auto">
        <div className="flex items-center justify-between bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <div>
            <h2 className="text-base font-black text-slate-900 font-display">
              Inspection Findings Completed
            </h2>
            <p className="text-xs text-slate-500 font-semibold">
              ID: {inspectionResult.inspection_id || inspectionResult.id}
            </p>
          </div>
          <button
            onClick={() => {
              setInspectionResult(null);
              setPanels([
                { id: 1, label: 'Front Panel (Principal Display)', file: null, preview: null, required: true },
                { id: 2, label: 'MRP & Net Quantity Panel', file: null, preview: null, required: false },
                { id: 3, label: 'Mfg / Expiry & Packer Panel', file: null, preview: null, required: false },
              ]);
            }}
            className="px-3.5 py-2 bg-[#7A1C1C] text-white text-xs font-black rounded-xl shadow-xs cursor-pointer touch-manipulation"
          >
            New Scan
          </button>
        </div>

        <StatutoryInspectionReport inspectionData={inspectionResult.inspection || inspectionResult} />
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 max-w-2xl mx-auto space-y-5 font-sans touch-manipulation pb-20">
      
      {/* Hidden File Inputs for Native Hardware Camera & Gallery */}
      <input
        type="file"
        ref={cameraInputRef}
        accept="image/*"
        capture="environment"
        onChange={handleCameraCapture}
        className="hidden"
      />

      <input
        type="file"
        ref={galleryInputRef}
        accept="image/*"
        onChange={handleCameraCapture}
        className="hidden"
      />

      {/* ── Mobile Top Banner ────────────────────────────────────────────────── */}
      <div className="bg-gradient-to-r from-[#5E1212] via-[#7A1C1C] to-[#4A1010] text-white p-4 sm:p-5 rounded-2xl shadow-md space-y-1.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 bg-amber-400 text-slate-950 font-black text-[10px] rounded uppercase font-mono tracking-wider">
              FIELD CAPTURE
            </span>
            <span className="text-red-200 text-xs font-bold">• Rapid Audit</span>
          </div>
          <span className="text-[11px] font-mono text-emerald-300 font-bold">
            {capturedCount}/3 PANELS
          </span>
        </div>

        <h1 className="text-xl font-black tracking-tight text-white font-display">
          Multi-Angle Retail Commodity Scan
        </h1>
        <p className="text-xs text-red-100/90 font-medium leading-relaxed">
          Snap clear photos of package label panels to extract statutory declarations and verify Rule 6 & 7 compliance.
        </p>
      </div>

      {/* ── Error Banner ────────────────────────────────────────────────────── */}
      {errorMessage && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 text-rose-900 rounded-xl text-xs font-bold flex items-center space-x-2 animate-fadeIn">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* ── Multi-Panel Snapping Cards (Swipeable / Stacked) ────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <span className="text-xs font-black uppercase text-slate-700 tracking-wider flex items-center gap-1.5">
            <Camera className="w-4 h-4 text-[#7A1C1C]" />
            <span>Packaging Label Panels ({capturedCount}/3)</span>
          </span>
          <span className="text-2xs font-bold text-slate-500">Tap to capture</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {panels.map((panel, idx) => {
            const hasImage = !!panel.preview;
            const isSelected = activePanelIndex === idx;

            return (
              <div
                key={panel.id}
                onClick={() => {
                  setActivePanelIndex(idx);
                  if (!hasImage && cameraInputRef.current) {
                    cameraInputRef.current.click();
                  }
                }}
                className={`p-3.5 rounded-2xl border-2 transition-all cursor-pointer relative flex flex-col justify-between min-h-[140px] touch-manipulation ${
                  hasImage
                    ? 'border-emerald-500/80 bg-emerald-50/30 shadow-xs'
                    : isSelected
                      ? 'border-[#7A1C1C] bg-red-50/40 shadow-sm'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-mono font-bold text-slate-500">
                      PANEL 0{panel.id}
                    </span>
                    {hasImage ? (
                      <span className="flex items-center gap-1 text-[10px] font-black text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        READY
                      </span>
                    ) : panel.required ? (
                      <span className="text-[10px] font-bold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                        MANDATORY
                      </span>
                    ) : (
                      <span className="text-[10px] font-medium text-slate-400">
                        OPTIONAL
                      </span>
                    )}
                  </div>

                  <h4 className="text-xs font-black text-slate-900 leading-tight">
                    {panel.label}
                  </h4>
                </div>

                {hasImage ? (
                  <div className="mt-2 relative rounded-xl overflow-hidden h-24 bg-slate-950 flex items-center justify-center border border-slate-200">
                    <img
                      src={panel.preview}
                      alt={panel.label}
                      className="max-h-full max-w-full object-contain"
                    />
                    <button
                      onClick={(e) => handleRemovePanelImage(idx, e)}
                      title="Retake image"
                      className="absolute top-1.5 right-1.5 p-1.5 bg-black/60 hover:bg-rose-600 text-white rounded-lg transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <div className="mt-2 py-3 bg-slate-50 border border-dashed border-slate-300 rounded-xl flex items-center justify-center gap-2 text-slate-600">
                    <Camera className="w-4 h-4 text-[#7A1C1C]" />
                    <span className="text-xs font-bold">Tap to Snap</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Action Trigger Buttons for Active Panel */}
        <div className="grid grid-cols-2 gap-2 pt-1">
          <button
            type="button"
            onClick={() => {
              if (cameraInputRef.current) cameraInputRef.current.click();
            }}
            className="min-h-[46px] px-3 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl border border-slate-200 flex items-center justify-center gap-2 transition cursor-pointer touch-manipulation"
          >
            <Camera className="w-4 h-4 text-[#7A1C1C]" />
            <span>Open Camera (Snap)</span>
          </button>

          <button
            type="button"
            onClick={() => {
              if (galleryInputRef.current) galleryInputRef.current.click();
            }}
            className="min-h-[46px] px-3 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl border border-slate-200 flex items-center justify-center gap-2 transition cursor-pointer touch-manipulation"
          >
            <ImageIcon className="w-4 h-4 text-sky-600" />
            <span>Choose from Gallery</span>
          </button>
        </div>
      </div>

      {/* ── Commodity Parameters ────────────────────────────────────────────── */}
      <div className="bg-white border border-slate-200 p-4 rounded-2xl shadow-card space-y-3.5">
        <h3 className="text-xs font-black uppercase text-slate-800 tracking-wider flex items-center gap-1.5 border-b border-slate-100 pb-2">
          <Building2 className="w-3.5 h-3.5 text-[#7A1C1C]" />
          <span>Inspection Metadata & Category</span>
        </h3>

        {/* Commodity Name */}
        <div className="space-y-1">
          <label className="block text-2xs font-black uppercase text-slate-700">
            Commodity / Product Name:
          </label>
          <input
            type="text"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            placeholder="e.g., Sambar Powder, Mustard Oil, Basmati Rice..."
            className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:border-[#7A1C1C] focus:bg-white transition"
          />
        </div>

        {/* Category Touch Pills */}
        <div className="space-y-1.5">
          <label className="block text-2xs font-black uppercase text-slate-700">
            Statutory Commodity Category:
          </label>
          <div className="grid grid-cols-2 gap-2">
            {['Food & Beverages', 'Personal Care', 'General Commodity', 'Agricultural Produce'].map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategory(cat)}
                className={`p-2.5 rounded-xl border text-xs font-bold transition text-left touch-manipulation min-h-[44px] flex items-center justify-between ${
                  category === cat
                    ? 'border-[#7A1C1C] bg-red-50 text-[#7A1C1C] shadow-xs'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                }`}
              >
                <span>{cat}</span>
                {category === cat && <CheckCircle2 className="w-3.5 h-3.5 text-[#7A1C1C]" />}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Full-Width Mobile Execution Button (Min Height 54px) ─────────────── */}
      <button
        onClick={handleExecuteMobileAnalysis}
        disabled={processing || capturedCount === 0}
        className="w-full min-h-[54px] px-6 py-3.5 bg-gradient-to-r from-[#7A1C1C] to-[#5E1212] hover:from-[#631515] hover:to-[#4A1010] active:scale-[0.98] text-white font-black text-sm rounded-2xl shadow-lg transition-all flex items-center justify-center gap-2.5 disabled:opacity-50 cursor-pointer touch-manipulation tracking-wide"
      >
        {processing ? (
          <>
            <RefreshCw className="w-5 h-5 animate-spin text-amber-300" />
            <span>Executing YOLOv8 + OCR Statutory Verification...</span>
          </>
        ) : (
          <>
            <Sparkles className="w-5 h-5 text-amber-300" />
            <span>ANALYZE PACKAGE UNDER PCR 2011</span>
            <ArrowRight className="w-4 h-4 ml-1" />
          </>
        )}
      </button>

    </div>
  );
}

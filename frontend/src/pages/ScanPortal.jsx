import React, { useState, useRef, useEffect } from 'react';
import { 
  UploadCloud, 
  Trash2, 
  ShieldAlert, 
  CheckCircle2, 
  Scale, 
  RefreshCw, 
  FileText, 
  Layers, 
  Search, 
  Image as ImageIcon,
  ChevronRight,
  Maximize2,
  Sparkles,
  Zap,
  ArrowRight,
  Eye,
  Sliders,
  Sun,
  Activity,
  AlertTriangle,
  XCircle,
  Tag,
  Download,
  ExternalLink
} from 'lucide-react';
import api from '../services/api';
import { runInspectionAnalysis } from '../services/inspectionService';
import StatutoryInspectionReport from '../components/StatutoryInspectionReport';
import { evaluateImageQuality, renderEnhancedPreview, render4KEnhancedPreview } from '../utils/imageEnhancer';

export default function ScanPortal() {
  // Uploaded Multi-Side Images
  const [images, setImages] = useState([]); // [{file, preview, type: 'front'|'back'|'side'|'top_bottom'}]
  const [activeImageIndex, setActiveImageIndex] = useState(0);

  // Vision Mode & Comparison State
  const [visionMode, setVisionMode] = useState('enhanced'); // 'enhanced' | 'standard' | 'document'
  const [showOriginal, setShowOriginal] = useState(false);
  const [qualityMetrics, setQualityMetrics] = useState(null);

  // Processing & Results State
  const [loading, setLoading] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [selectedField, setSelectedField] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [activeTab, setActiveTab] = useState('statutory_report'); // 'statutory_report' | 'visual_evidence' | 'ocr_raw'
  
  const fileInputRef = useRef(null);
  const canvasRef = useRef(null);
  const sourceImgRef = useRef(null);

  // Handle Image Additions
  const handleAddFiles = (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      const newImages = files.map((file, i) => ({
        file,
        preview: URL.createObjectURL(file),
        type: images.length === 0 && i === 0 ? 'front' : (i === 1 ? 'back' : 'side')
      }));
      const updated = [...images, ...newImages];
      setImages(updated);
      setActiveImageIndex(images.length); // switch to newly uploaded image
      setErrorMsg('');
    }
  };

  const handleRemoveImage = (index) => {
    const updated = images.filter((_, i) => i !== index);
    setImages(updated);
    if (activeImageIndex >= updated.length && updated.length > 0) {
      setActiveImageIndex(updated.length - 1);
    } else if (updated.length === 0) {
      setActiveImageIndex(0);
      setScanResult(null);
      setQualityMetrics(null);
    }
  };

  const handleTypeChange = (index, type) => {
    setImages(prev => prev.map((img, i) => i === index ? { ...img, type } : img));
  };

  // Run Real-Time Quality Gate & Canvas Enhancement on active image change
  const activeImage = images[activeImageIndex];

  useEffect(() => {
    if (!activeImage) {
      setQualityMetrics(null);
      return;
    }

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = activeImage.preview;
    sourceImgRef.current = img;

    img.onload = () => {
      // 1. Evaluate Image Quality
      const quality = evaluateImageQuality(img);
      setQualityMetrics(quality);

      // 2. Render Canvas 2D Vision Preview (4K UHD for Enhanced mode)
      if (canvasRef.current) {
        if (visionMode === 'enhanced' && !showOriginal) {
          render4KEnhancedPreview(img, canvasRef.current, 'enhanced');
        } else {
          renderEnhancedPreview(img, canvasRef.current, showOriginal ? 'standard' : visionMode);
        }
      }
    };
  }, [activeImageIndex, images, visionMode, showOriginal]);

  // Execute Statutory Compliance Processing
  const handleStartScan = async () => {
    if (images.length === 0) {
      setErrorMsg("Please upload at least one packaging image before starting the scan.");
      return;
    }
    
    setLoading(true);
    setErrorMsg('');
    setSelectedField(null);

    try {
      const rawFiles = images.map(img => img.file);
      const primaryTitle = images[0]?.file?.name?.replace(/\.[^/.]+$/, '') || 'Packaged Commodity Item';

      const data = await runInspectionAnalysis(rawFiles, {
        product_name: primaryTitle,
        category: 'Food & Beverages',
        pdp_shape: 'rectangular',
        location: 'Central Ministry Enforcement Wing'
      });

      setScanResult(data);
      setActiveTab('statutory_report');
    } catch (err) {
      console.error("Scan processing error:", err);
      setErrorMsg(err.message || "Failed to process packaging image. Please verify server connection.");
    } finally {
      setLoading(false);
    }
  };

  const formattedSides = images.map((img, idx) => ({
    side: idx + 1,
    snapshotUrl: img.preview,
    timestamp: new Date().toLocaleTimeString(),
    status: scanResult?.overall_status || '7A COMPLIANT'
  }));

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 font-sans">
      
      {/* 1. Header Banner */}
      <div className="bg-white border border-[#E2E8F0] p-6 rounded-3xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 bg-red-50 text-red-700 text-xs font-black rounded-lg border border-red-200 mb-2">
            <Layers className="w-3.5 h-3.5" />
            <span>Legal Metrology Label Inspection & Statutory Rule Engine</span>
          </div>
          <h1 className="text-2xl font-black text-[#1E293B] tracking-tight">
            Product Label Scanner & Statutory Analysis
          </h1>
          <p className="text-xs text-[#64748B] font-semibold mt-0.5">
            Upload packaging label images for automatic quality verification, client-side Canvas 2D vision enhancement, PaddleOCR extraction, dynamic rule matching, and complete compliance reports.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 text-xs font-black rounded-2xl flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* 2. Main Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Image Uploader & Multi-Side Manager (4 Cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="p-6 bg-white border border-[#E2E8F0] rounded-3xl shadow-sm space-y-4">
            <h3 className="text-xs font-black text-slate-800 uppercase tracking-wider flex items-center justify-between">
              <span>Upload Label Images</span>
              <span className="text-[10px] text-slate-400 font-mono">Multi-Side Support</span>
            </h3>
            
            {/* Drag & Drop Dropzone */}
            <div 
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 hover:border-red-500 rounded-2xl p-6 text-center cursor-pointer transition bg-slate-50 hover:bg-red-50/10 space-y-2"
            >
              <UploadCloud className="w-10 h-10 text-slate-400 mx-auto" />
              <p className="text-xs text-slate-700 font-black">Click or drag & drop to upload label image</p>
              <p className="text-[10px] text-slate-400 font-semibold">Supports JPG, JPEG, PNG, WEBP up to 25MB</p>
              <input 
                ref={fileInputRef}
                type="file" 
                multiple
                accept=".jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={handleAddFiles}
              />
            </div>

            {/* Uploaded Files Queue */}
            {images.length > 0 && (
              <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
                {images.map((img, idx) => (
                  <div 
                    key={idx} 
                    onClick={() => setActiveImageIndex(idx)}
                    className={`flex items-center justify-between p-2.5 rounded-xl border transition cursor-pointer gap-3 ${
                      activeImageIndex === idx 
                        ? 'bg-red-50/60 border-red-500 shadow-xs' 
                        : 'bg-slate-50 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    <img src={img.preview} alt="preview" className="w-10 h-10 object-cover rounded-lg border bg-white" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-slate-800 font-bold truncate">{img.file.name}</p>
                      <select 
                        value={img.type} 
                        onChange={(e) => {
                          e.stopPropagation();
                          handleTypeChange(idx, e.target.value);
                        }}
                        className="text-[10px] font-bold text-slate-600 bg-white border rounded p-1 mt-0.5 focus:outline-none"
                      >
                        <option value="front">Side 1 — Front Label</option>
                        <option value="back">Side 2 — Back Label</option>
                        <option value="side">Side 3 — Side Panel</option>
                        <option value="top_bottom">Side 4 — Top/Bottom</option>
                      </select>
                    </div>
                    <button 
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveImage(idx);
                      }}
                      className="p-1.5 text-slate-400 hover:text-red-600 transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Process Execution Button */}
            <button
              type="button"
              onClick={handleStartScan}
              disabled={loading || images.length === 0}
              className={`w-full py-3.5 rounded-xl text-white text-xs font-black tracking-wider transition uppercase shadow-md flex items-center justify-center space-x-2 ${
                loading || images.length === 0
                  ? 'bg-slate-300 cursor-not-allowed text-slate-500'
                  : 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 active:scale-[0.99]'
              }`}
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>RUNNING STATUTORY PIPELINE...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-amber-300" />
                  <span>PROCESS & EVALUATE RULES</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Large Enhanced Inspection Preview & Statutory Analysis (8 Cols) */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* Active Image Inspection Stage (Shown immediately when images.length > 0) */}
          {images.length > 0 ? (
            <div className="space-y-6">
              
              {/* 1. LARGE INSPECTION PREVIEW CARD */}
              <div className="bg-white border border-[#E2E8F0] p-6 rounded-3xl shadow-sm space-y-4">
                
                {/* Top Control Bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-black text-slate-900 uppercase tracking-wider">
                      Product Label Inspection Preview
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md font-bold">
                      Side {activeImageIndex + 1} of {images.length}
                    </span>
                  </div>

                  {/* Vision Mode & Comparison Controls */}
                  <div className="flex items-center space-x-2">
                    <div className="inline-flex rounded-xl p-0.5 bg-slate-100 border border-slate-200 text-[11px] font-bold">
                      <button
                        type="button"
                        onClick={() => {
                          setVisionMode('enhanced');
                          setShowOriginal(false);
                        }}
                        className={`px-3 py-1 rounded-lg transition flex items-center space-x-1 ${
                          visionMode === 'enhanced' && !showOriginal
                            ? 'bg-red-600 text-white font-black shadow-xs'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Enhanced (4K UHD)</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setVisionMode('document');
                          setShowOriginal(false);
                        }}
                        className={`px-3 py-1 rounded-lg transition ${
                          visionMode === 'document' && !showOriginal
                            ? 'bg-red-600 text-white font-black shadow-xs'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Document / Text
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setVisionMode('standard');
                          setShowOriginal(true);
                        }}
                        className={`px-3 py-1 rounded-lg transition ${
                          visionMode === 'standard' || showOriginal
                            ? 'bg-slate-800 text-white font-black shadow-xs'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Original Raw
                      </button>
                    </div>
                  </div>
                </div>

                {/* Image Quality Gate Assessment Bar */}
                {qualityMetrics && (
                  <div className={`p-3 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs ${
                    qualityMetrics.isQualityGood 
                      ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900' 
                      : 'bg-amber-50 border-amber-200 text-amber-900'
                  }`}>
                    <div className="flex items-center space-x-2">
                      {qualityMetrics.isQualityGood ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                      )}
                      <span className="font-bold">{qualityMetrics.guidance}</span>
                    </div>

                    <div className="flex items-center space-x-3 text-[11px] font-mono font-bold text-slate-700">
                      <span>Res: {qualityMetrics.resolution}</span>
                      <span>•</span>
                      <span>Bright: {qualityMetrics.brightness}/255</span>
                      <span>•</span>
                      <span>Sharp: {qualityMetrics.sharpness}/100</span>
                    </div>
                  </div>
                )}

                {/* Large Canvas Viewport */}
                <div className="relative aspect-[16/10] bg-slate-950 rounded-2xl overflow-hidden flex items-center justify-center border-2 border-slate-800 shadow-inner group">
                  <canvas 
                    ref={canvasRef} 
                    className="max-w-full max-h-full object-contain"
                  />

                  {/* Processing Scanning Beam if loading */}
                  {loading && (
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex flex-col items-center justify-center text-white space-y-3 z-10">
                      <div className="w-12 h-12 border-4 border-red-500 border-t-transparent rounded-full animate-spin"></div>
                      <div className="text-center space-y-1">
                        <span className="text-xs font-black tracking-wider uppercase block text-red-400">
                          PROCESSING STATUTORY PIPELINE
                        </span>
                        <span className="text-[11px] text-slate-300 font-medium block">
                          Extracting declarations & evaluating Legal Metrology rules...
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Ready for Analysis Badge prior to scan */}
                  {!scanResult && !loading && (
                    <div className="absolute bottom-4 inset-x-0 flex justify-center pointer-events-none">
                      <div className="px-4 py-1.5 bg-slate-900/90 backdrop-blur-md border border-slate-700 rounded-full text-white text-xs font-black shadow-lg flex items-center space-x-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                        <span>READY FOR ANALYSIS — Click "PROCESS & EVALUATE RULES"</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Multi-Side Thumbnails if multiple images uploaded */}
                {images.length > 1 && (
                  <div className="flex items-center space-x-2 pt-2 overflow-x-auto pb-1">
                    {images.map((img, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setActiveImageIndex(idx)}
                        className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl border text-xs font-bold transition flex-shrink-0 ${
                          activeImageIndex === idx
                            ? 'bg-red-600 text-white border-red-600 shadow-xs'
                            : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                        }`}
                      >
                        <img src={img.preview} alt="side" className="w-5 h-5 rounded object-cover border" />
                        <span>Side {idx + 1} ({img.type})</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* 2. STATUTORY RESULTS SECTION (Rendered after successful scan) */}
              {scanResult && (
                <div className="space-y-6">
                  
                  {/* Navigation View Tabs */}
                  <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
                    <button
                      type="button"
                      onClick={() => setActiveTab('statutory_report')}
                      className={`px-4 py-2 rounded-xl text-xs font-black transition flex items-center space-x-1.5 ${
                        activeTab === 'statutory_report'
                          ? 'bg-red-600 text-white shadow-sm'
                          : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
                      }`}
                    >
                      <Scale className="w-4 h-4" />
                      <span>Statutory Compliance Report</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveTab('ocr_raw')}
                      className={`px-4 py-2 rounded-xl text-xs font-black transition flex items-center space-x-1.5 ${
                        activeTab === 'ocr_raw'
                          ? 'bg-red-600 text-white shadow-sm'
                          : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
                      }`}
                    >
                      <FileText className="w-4 h-4" />
                      <span>Extracted Product Declarations</span>
                    </button>
                  </div>

                  {/* TAB 1: Complete Unified Statutory Report */}
                  {activeTab === 'statutory_report' && (
                    <div className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm">
                      <StatutoryInspectionReport 
                        inspection={scanResult} 
                        scannedSides={formattedSides} 
                      />
                    </div>
                  )}

                  {/* TAB 2: Extracted Declarations Table & Raw Text */}
                  {activeTab === 'ocr_raw' && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="md:col-span-2 p-6 bg-white border border-[#E2E8F0] rounded-3xl shadow-sm space-y-4">
                        <h3 className="text-xs font-black text-slate-800 uppercase tracking-wider flex items-center gap-2">
                          <Scale className="w-4 h-4 text-[#DC2626]" />
                          <span>Extracted Statutory Declarations</span>
                        </h3>
                        
                        <div className="overflow-x-auto">
                          <table className="min-w-full text-xs font-semibold">
                            <thead>
                              <tr className="border-b text-slate-400 uppercase text-[10px]">
                                <th className="py-2 text-left">Declaration Field</th>
                                <th className="py-2 text-left">Observed Value</th>
                                <th className="py-2 text-left">Confidence</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y text-slate-700">
                              {Object.entries(scanResult.extracted_declarations || scanResult.declarations || {}).map(([field, data]) => {
                                const val = data?.value !== undefined ? data.value : String(data);
                                const conf = data?.confidence || 90;
                                return (
                                  <tr key={field} className="transition hover:bg-slate-50">
                                    <td className="py-3 font-extrabold capitalize text-slate-900">
                                      {field.replace(/_/g, ' ')}
                                    </td>
                                    <td className="py-3 font-bold text-slate-600">
                                      {val || 'Not Detected / Needs Review'}
                                    </td>
                                    <td className="py-3 font-mono">
                                      {val ? `${Math.round(conf)}%` : '-'}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Full Raw OCR Text */}
                      <div className="p-6 bg-white border border-[#E2E8F0] rounded-3xl shadow-sm space-y-4">
                        <h3 className="text-xs font-black text-slate-800 uppercase tracking-wider flex items-center gap-2">
                          <FileText className="w-4 h-4 text-slate-600" />
                          <span>Raw Text Stream</span>
                        </h3>
                        <textarea
                          readOnly
                          value={scanResult.raw_text || scanResult.ocr?.full_text || ''}
                          className="w-full h-80 p-3 text-xs bg-slate-50 border rounded-2xl resize-none focus:outline-none font-semibold text-slate-600 leading-relaxed font-mono"
                        />
                      </div>
                    </div>
                  )}

                </div>
              )}

            </div>
          ) : (
            <div className="p-16 text-center bg-white border border-dashed border-slate-300 rounded-3xl space-y-3">
              <div className="p-4 bg-red-50 text-red-600 rounded-2xl inline-block border border-red-100">
                <ImageIcon className="w-10 h-10 mx-auto" />
              </div>
              <h3 className="text-base font-black text-slate-800">Upload Packaging Photo to Begin Inspection</h3>
              <p className="text-xs text-slate-500 font-medium max-w-md mx-auto">
                Select or drop a packaging label photo on the left to immediately inspect the large enhanced preview, verify image quality, and run the automated Legal Metrology rule analysis.
              </p>
            </div>
          )}

        </div>

      </div>

    </div>
  );
}

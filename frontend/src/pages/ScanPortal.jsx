import React, { useState, useRef } from 'react';
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
  Maximize2
} from 'lucide-react';
import axios from 'axios';

export default function ScanPortal() {
  const [images, setImages] = useState([]); // [{file, preview, type: 'front'|'back'|'side'|'top_bottom'}]
  const [loading, setLoading] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [selectedField, setSelectedField] = useState(null);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [errorMsg, setErrorMsg] = useState('');
  
  const fileInputRef = useRef(null);

  const handleAddFiles = (e) => {
    const files = Array.from(e.target.files);
    const newImages = files.map(file => ({
      file,
      preview: URL.createObjectURL(file),
      type: 'front' // Default category
    }));
    setImages(prev => [...prev, ...newImages]);
  };

  const handleRemoveImage = (index) => {
    setImages(prev => prev.filter((_, i) => i !== index));
    if (activeImageIndex >= images.length - 1 && activeImageIndex > 0) {
      setActiveImageIndex(images.length - 2);
    }
  };

  const handleTypeChange = (index, type) => {
    setImages(prev => prev.map((img, i) => i === index ? { ...img, type } : img));
  };

  const handleStartScan = async () => {
    if (images.length === 0) {
      setErrorMsg("Please upload at least one image before starting the scan.");
      return;
    }
    
    setLoading(true);
    setErrorMsg('');
    setSelectedField(null);
    setScanResult(null);

    const formData = new FormData();
    images.forEach(img => {
      formData.append("files", img.file);
    });

    try {
      const response = await axios.post("/api/scan", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setScanResult(response.data);
      setActiveImageIndex(0);
    } catch (err) {
      console.error(err);
      setErrorMsg("Failed to run image scanning and processing pipeline. Check backend connection.");
    } finally {
      setLoading(false);
    }
  };

  // Bounding box percentage scale helper
  const getBboxStyle = (bbox, originalSize) => {
    if (!bbox || !originalSize || bbox.every(v => v === 0)) return { display: 'none' };
    const [x1, y1, x2, y2] = bbox;
    const [w, h] = originalSize;
    
    return {
      left: `${(x1 / w) * 100}%`,
      top: `${(y1 / h) * 100}%`,
      width: `${((x2 - x1) / w) * 100}%`,
      height: `${((y2 - y1) / h) * 100}%`,
      position: 'absolute',
      border: '3px solid #EF4444',
      backgroundColor: 'rgba(239, 68, 68, 0.2)',
      pointerEvents: 'none',
      transition: 'all 0.2s ease'
    };
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      
      {/* 1. Header */}
      <div>
        <h1 className="text-3xl font-black text-[#1E293B] tracking-tight flex items-center gap-2">
          <Layers className="w-8 h-8 text-[#DC2626]" />
          <span>Product Label Scanner & Preprocessor</span>
        </h1>
        <p className="text-sm text-[#64748B] font-bold mt-1">
          Statutory label text extractor and preprocessor. Analyze resolution, blur, perspective correction, and OCR bounding boxes.
        </p>
      </div>

      {errorMsg && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 text-sm font-black rounded-xl flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* 2. Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Image Uploader & Actions */}
        <div className="lg:col-span-1 space-y-6">
          <div className="p-6 bg-white border border-[#E2E8F0] rounded-3xl shadow-sm space-y-4">
            <h3 className="text-base font-black text-slate-800 uppercase tracking-wider">
              Upload Label Images
            </h3>
            
            {/* Drag & Drop Box */}
            <div 
              onClick={() => fileInputRef.current.click()}
              className="border-2 border-dashed border-slate-300 hover:border-red-500 rounded-2xl p-6 text-center cursor-pointer transition bg-slate-50 hover:bg-red-50/10 space-y-2"
            >
              <UploadCloud className="w-10 h-10 text-slate-400 mx-auto" />
              <p className="text-xs text-slate-600 font-extrabold">Drag and drop or click to browse</p>
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

            {/* List of uploaded files */}
            {images.length > 0 && (
              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {images.map((img, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200 gap-3">
                    <img src={img.preview} alt="preview" className="w-12 h-12 object-cover rounded-lg border" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-slate-800 font-black truncate">{img.file.name}</p>
                      <select 
                        value={img.type} 
                        onChange={(e) => handleTypeChange(idx, e.target.value)}
                        className="text-[10px] font-black text-slate-600 bg-white border rounded p-1 mt-1 focus:outline-none"
                      >
                        <option value="front">Front Label</option>
                        <option value="back">Back Label</option>
                        <option value="side">Side Label</option>
                        <option value="top_bottom">Top/Bottom Label</option>
                      </select>
                    </div>
                    <button 
                      onClick={() => handleRemoveImage(idx)}
                      className="p-2 text-slate-400 hover:text-red-600 transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={handleStartScan}
              disabled={loading || images.length === 0}
              className={`w-full py-3.5 rounded-xl text-white text-xs font-black tracking-wider transition uppercase shadow-md flex items-center justify-center space-x-2 ${
                loading || images.length === 0
                  ? 'bg-slate-400 cursor-not-allowed shadow-none'
                  : 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800'
              }`}
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Processing Pipeline...</span>
                </>
              ) : (
                <>
                  <Layers className="w-4 h-4" />
                  <span>Execute Scan Pipeline</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Preprocessing Visualizer & Data Analysis */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Quality Indicator banner if scanned */}
          {scanResult && scanResult.quality && (
            <div className={`p-4 rounded-2xl border flex items-start gap-3 shadow-sm ${
              scanResult.quality.quality_score >= 70
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-amber-50 border-amber-200 text-amber-800'
            }`}>
              {scanResult.quality.quality_score >= 70 ? (
                <CheckCircle2 className="w-5 h-5 mt-0.5 text-emerald-600 flex-shrink-0" />
              ) : (
                <ShieldAlert className="w-5 h-5 mt-0.5 text-amber-600 flex-shrink-0" />
              )}
              <div className="space-y-1">
                <h4 className="text-sm font-black uppercase tracking-wider">
                  Quality Score: {scanResult.quality.quality_score}/100 
                  ({scanResult.quality.quality_score >= 70 ? 'Readability Good' : 'Readability Poor'})
                </h4>
                {scanResult.quality.warning && (
                  <p className="text-xs font-bold leading-relaxed">{scanResult.quality.warning}</p>
                )}
                <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1.5 text-[11px] font-black text-slate-600">
                  <span>Resolution: {scanResult.quality.metrics[activeImageIndex]?.resolution}</span>
                  <span>Blur: {scanResult.quality.metrics[activeImageIndex]?.blur ? 'YES' : 'NO'}</span>
                  <span>Brightness: {scanResult.quality.metrics[activeImageIndex]?.brightness}</span>
                </div>
              </div>
            </div>
          )}

          {/* Preprocessing Visualizer Comparison Panels */}
          {scanResult ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Original Image Panel */}
              <div className="p-4 bg-white border border-[#E2E8F0] rounded-3xl shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b pb-2">
                  <span className="text-xs font-black uppercase text-slate-500">Original Photograph</span>
                  <span className="text-[10px] font-black bg-slate-100 text-slate-600 px-2 py-0.5 rounded">Raw Input</span>
                </div>
                <div className="relative aspect-[4/3] bg-slate-900 rounded-2xl overflow-hidden flex items-center justify-center border">
                  <img 
                    src={scanResult.original_urls[activeImageIndex]} 
                    alt="Original" 
                    className="max-w-full max-h-full object-contain"
                  />
                </div>
              </div>

              {/* Enhanced Processed Image Panel */}
              <div className="p-4 bg-white border border-[#E2E8F0] rounded-3xl shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b pb-2">
                  <span className="text-xs font-black uppercase text-[#DC2626]">Enhanced Processed Preview</span>
                  <span className="text-[10px] font-black bg-red-100 text-[#DC2626] px-2 py-0.5 rounded">OpenCV Pipeline</span>
                </div>
                <div className="relative aspect-[4/3] bg-slate-900 rounded-2xl overflow-hidden flex items-center justify-center border">
                  <img 
                    src={scanResult.processed_urls[activeImageIndex]} 
                    alt="Processed" 
                    className="max-w-full max-h-full object-contain"
                  />
                  {/* Absolute Highlight Bounding Box overlay */}
                  {selectedField && selectedField.image_id.includes(`_${activeImageIndex}.png`) && (
                    <div style={getBboxStyle(
                      selectedField.bbox, 
                      [
                        parseInt(scanResult.quality.metrics[activeImageIndex].resolution.split('x')[0]),
                        parseInt(scanResult.quality.metrics[activeImageIndex].resolution.split('x')[1])
                      ]
                    )} />
                  )}
                </div>
              </div>

            </div>
          ) : (
            <div className="p-10 text-center bg-slate-50 border border-dashed rounded-3xl space-y-2">
              <ImageIcon className="w-12 h-12 text-slate-300 mx-auto" />
              <p className="text-sm text-slate-600 font-extrabold">No scan results to display yet</p>
              <p className="text-xs text-slate-400 font-semibold">Upload product label images and run the scanner.</p>
            </div>
          )}

          {/* Scanned side navigation controls if multiple images */}
          {scanResult && scanResult.original_urls.length > 1 && (
            <div className="flex justify-center space-x-2">
              {scanResult.original_urls.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveImageIndex(idx)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-black border transition ${
                    activeImageIndex === idx
                      ? 'bg-red-600 text-white border-red-600'
                      : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  Label Image {idx + 1}
                </button>
              ))}
            </div>
          )}

          {/* Detected Declarations Data Grid */}
          {scanResult && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Extraction Data Table */}
              <div className="md:col-span-2 p-6 bg-white border border-[#E2E8F0] rounded-3xl shadow-sm space-y-4">
                <h3 className="text-base font-black text-slate-800 uppercase tracking-wider flex items-center gap-2">
                  <Scale className="w-5 h-5 text-[#DC2626]" />
                  <span>Important Declarations Extracted</span>
                </h3>
                
                <div className="overflow-x-auto">
                  <table className="min-w-full text-xs font-semibold">
                    <thead>
                      <tr className="border-b text-slate-400 uppercase text-[10px]">
                        <th className="py-2 text-left">Label Field</th>
                        <th className="py-2 text-left">Extracted Value</th>
                        <th className="py-2 text-left">Confidence</th>
                        <th className="py-2 text-right">View Link</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y text-slate-700">
                      {Object.entries(scanResult.extracted_declarations).map(([field, data]) => {
                        const isSelected = selectedField && selectedField.field === field;
                        return (
                          <tr 
                            key={field} 
                            onClick={() => data && setSelectedField({ ...data, field })}
                            className={`cursor-pointer transition hover:bg-slate-50 ${
                              isSelected ? 'bg-red-50/55' : ''
                            } ${!data ? 'opacity-55' : ''}`}
                          >
                            <td className="py-3 font-extrabold capitalize text-slate-900">
                              {field.replace('_', ' ')}
                            </td>
                            <td className="py-3 font-bold text-slate-600">
                              {data ? data.value : 'Not Detected'}
                            </td>
                            <td className="py-3">
                              {data ? `${Math.round(data.confidence)}%` : '-'}
                            </td>
                            <td className="py-3 text-right">
                              {data && (
                                <button className="inline-flex items-center space-x-1 text-red-600 hover:text-red-700 font-extrabold">
                                  <span>Highlight</span>
                                  <ChevronRight className="w-3.5 h-3.5" />
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Full Raw OCR Text Box */}
              <div className="p-6 bg-white border border-[#E2E8F0] rounded-3xl shadow-sm space-y-4">
                <h3 className="text-base font-black text-slate-800 uppercase tracking-wider flex items-center gap-2">
                  <FileText className="w-5 h-5 text-slate-600" />
                  <span>Raw OCR Output</span>
                </h3>
                <textarea
                  readOnly
                  value={scanResult.raw_text}
                  className="w-full h-72 p-3 text-xs bg-slate-50 border rounded-2xl resize-none focus:outline-none font-semibold text-slate-600 leading-relaxed"
                />
              </div>

            </div>
          )}

        </div>

      </div>

    </div>
  );
}

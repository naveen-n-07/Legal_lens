import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  CheckCircle2, 
  ArrowRight, 
  ShieldCheck, 
  AlertCircle, 
  Zap, 
  Gavel, 
  Camera,
  RefreshCw,
  Eye,
  FileText,
  RotateCw,
  Plus,
  Trash2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { runInspectionAnalysis } from '../services/inspectionService';
import StatutoryInspectionReport from '../components/StatutoryInspectionReport';
import MobileInspectionUpload from '../components/MobileInspectionUpload';

export default function InspectionUpload({ user }) {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);

  // Form Parameters
  const [productName, setProductName] = useState('');
  const [category, setCategory] = useState('Food & Beverages');
  const [pdpShape, setPdpShape] = useState('rectangular');
  const [location, setLocation] = useState('Central Ministry Enforcement Wing');
  const [inspectorName, setInspectorName] = useState('Field Enforcement Inspector');

  // Input & Multi-Side Management
  const [inputMode, setInputMode] = useState('upload'); // 'upload' | 'camera'
  const [selectedFiles, setSelectedFiles] = useState([]); // [{file, preview, side: 'Side 1 (Front)'}]
  const [activeSideIndex, setActiveSideIndex] = useState(0);

  // Camera Snapshot State
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraStream, setCameraStream] = useState(null);

  // Processing & Results State
  const [processing, setProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [inspectionResult, setInspectionResult] = useState(null);

  // Handle File Selection
  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      const newItems = files.map((f, i) => ({
        file: f,
        preview: URL.createObjectURL(f),
        side: `Side ${selectedFiles.length + i + 1}`
      }));
      setSelectedFiles(prev => [...prev, ...newItems]);
      setErrorMessage('');
    }
  };

  const handleRemoveFile = (idx) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== idx));
  };

  // Camera Controls
  const startInlineCamera = async () => {
    setErrorMessage('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false
      });
      setCameraStream(stream);
      setCameraActive(true);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.warn('Camera error:', err);
      setErrorMessage('Could not initialize camera stream. Please use file upload.');
      setCameraActive(false);
    }
  };

  const stopInlineCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(t => t.stop());
      setCameraStream(null);
    }
    setCameraActive(false);
  };

  const captureCameraSnapshot = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], `camera_snapshot_${Date.now()}.jpg`, { type: 'image/jpeg' });
      const item = {
        file,
        preview: canvas.toDataURL('image/jpeg', 0.9),
        side: `Side ${selectedFiles.length + 1}`
      };
      setSelectedFiles(prev => [...prev, item]);
      stopInlineCamera();
    }, 'image/jpeg', 0.92);
  };

  // Execute Inspection Submission
  const handleExecuteInspection = async (e) => {
    e.preventDefault();
    if (selectedFiles.length === 0) {
      setErrorMessage('Please select or capture at least one packaging image before initiating inspection.');
      return;
    }

    setProcessing(true);
    setErrorMessage('');
    setInspectionResult(null);

    const primaryFile = selectedFiles[0].file;
    const cleanTitle = productName.trim() || primaryFile.name.replace(/\.[^/.]+$/, "");
    const formattedTitle = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);

    try {
      const rawFiles = selectedFiles.map(s => s.file);
      const resData = await runInspectionAnalysis(rawFiles, {
        product_name: formattedTitle,
        category: category,
        pdp_shape: pdpShape,
        location: location
      });
      
      if (!resData.original_image_url) {
        resData.original_image_url = selectedFiles[0].preview;
      }
      resData.previewUrl = resData.annotated_image_b64 || resData.evidence_image_url || resData.annotated_image_url || selectedFiles[0].preview;
      setInspectionResult(resData);
    } catch (err) {
      console.error('Inspection upload failed:', err);
      setErrorMessage(err.message || 'Statutory inspection failed. Please verify that the label image is well-lit and legible.');
    } finally {
      setProcessing(false);
    }
  };

  const formattedSides = selectedFiles.map((s, idx) => ({
    side: idx + 1,
    snapshotUrl: s.preview,
    timestamp: new Date().toLocaleTimeString(),
    status: inspectionResult?.overall_status || '7A COMPLIANT'
  }));

  return (
    <>
      {/* Mobile-First Camera & Fast Inspection Shell (< 768px) */}
      <div className="md:hidden">
        <MobileInspectionUpload user={user} />
      </div>

      {/* Desktop Widescreen Studio (>= 768px) */}
      <div className="hidden md:block p-8 max-w-7xl mx-auto space-y-8 font-sans">
        
        {/* Header Banner */}
        <div className="bg-white border border-[#E2E8F0] p-6 rounded-3xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 bg-red-50 text-red-700 text-xs font-black rounded-lg border border-red-200 mb-2">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>New Statutory Packaging Inspection Registration</span>
            </div>
            <h1 className="text-2xl font-black text-[#1E293B]">Create New Statutory Commodity Inspection</h1>
            <p className="text-xs text-[#64748B] font-semibold mt-0.5">
              Register packaging audit details, upload multi-side label photos or capture live, and execute automated OCR and Legal Metrology rule verification.
            </p>
          </div>
        </div>

        {errorMessage && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 text-xs font-black rounded-2xl flex items-center space-x-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Main Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Form & Image Inputs (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          <form onSubmit={handleExecuteInspection} className="bg-white border border-[#E2E8F0] p-6 rounded-3xl shadow-sm space-y-5 text-xs">
            <h3 className="text-xs font-black text-slate-800 uppercase tracking-wider flex items-center space-x-2 border-b border-slate-100 pb-3">
              <Gavel className="w-4 h-4 text-red-600" />
              <span>Inspection Parameters</span>
            </h3>

            {/* Product Title */}
            <div>
              <label className="block font-black text-slate-800 uppercase tracking-wider mb-1.5">
                Product Title / Commodity Name
              </label>
              <input
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="e.g. Premium Basmati Rice / Packaged Drinking Water"
                className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-medium focus:outline-none focus:border-red-600"
              />
            </div>

            {/* Category & PDP Shape */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-black text-slate-800 uppercase tracking-wider mb-1.5">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-bold focus:outline-none focus:border-red-600"
                >
                  <option>Food & Beverages</option>
                  <option>Cosmetics & Personal Care</option>
                  <option>Pharmaceuticals</option>
                  <option>Electronics & Hardware</option>
                  <option>Textiles & Apparels</option>
                  <option>General Packaged Commodity</option>
                </select>
              </div>

              <div>
                <label className="block font-black text-slate-800 uppercase tracking-wider mb-1.5">PDP Shape</label>
                <select
                  value={pdpShape}
                  onChange={(e) => setPdpShape(e.target.value)}
                  className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-bold focus:outline-none focus:border-red-600"
                >
                  <option value="rectangular">Rectangular Area</option>
                  <option value="cylindrical">Cylindrical / Bottle</option>
                  <option value="special">Special / Pouch</option>
                </select>
              </div>
            </div>

            {/* Location & Enforcement Unit */}
            <div>
              <label className="block font-black text-slate-800 uppercase tracking-wider mb-1.5">Inspection Location / Market</label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Central Wholesale Market, New Delhi"
                className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 font-medium focus:outline-none focus:border-red-600"
              />
            </div>

            {/* Image Input Section */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <span className="font-black text-slate-800 uppercase tracking-wider">
                  Packaging Label Images ({selectedFiles.length})
                </span>
                <div className="flex items-center space-x-1">
                  <button
                    type="button"
                    onClick={() => {
                      if (cameraActive) stopInlineCamera();
                      else startInlineCamera();
                    }}
                    className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-lg transition flex items-center space-x-1"
                  >
                    <Camera className="w-3.5 h-3.5 text-red-600" />
                    <span>{cameraActive ? 'Close Camera' : 'Snap Live'}</span>
                  </button>
                </div>
              </div>

              {/* Inline Camera View if active */}
              {cameraActive && (
                <div className="relative aspect-video bg-slate-950 rounded-2xl overflow-hidden border-2 border-red-500 flex flex-col items-center justify-center">
                  <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                  <div className="absolute bottom-3 inset-x-0 flex justify-center">
                    <button
                      type="button"
                      onClick={captureCameraSnapshot}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-black rounded-xl shadow-lg flex items-center space-x-1.5"
                    >
                      <Camera className="w-4 h-4" />
                      <span>Capture Side Image</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Dropzone */}
              {!cameraActive && (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-300 hover:border-red-500 bg-slate-50 hover:bg-red-50/10 rounded-2xl p-5 text-center cursor-pointer transition space-y-2"
                >
                  <UploadCloud className="w-8 h-8 text-slate-400 mx-auto" />
                  <span className="text-xs text-slate-700 font-bold block">Click to upload packaging photo</span>
                  <span className="text-[10px] text-slate-400 block">PNG, JPG, WEBP up to 25MB</span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </div>
              )}

              {/* Selected Files Preview List */}
              {selectedFiles.length > 0 && (
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {selectedFiles.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2.5 bg-slate-50 rounded-xl border border-slate-200 gap-2">
                      <img src={item.preview} alt="preview" className="w-10 h-10 object-cover rounded-lg border bg-white" />
                      <div className="flex-1 min-w-0">
                        <span className="text-xs font-bold text-slate-800 block truncate">{item.file.name}</span>
                        <span className="text-[10px] text-red-700 font-mono font-bold">{item.side}</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(idx)}
                        className="p-1.5 text-slate-400 hover:text-red-600 transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Submit Action */}
            <button
              type="submit"
              disabled={processing || selectedFiles.length === 0}
              className={`w-full py-3.5 rounded-xl text-white font-extrabold text-xs tracking-wider transition uppercase shadow-md flex items-center justify-center space-x-2 ${
                processing || selectedFiles.length === 0
                  ? 'bg-slate-300 cursor-not-allowed text-slate-500'
                  : 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800'
              }`}
            >
              {processing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>RUNNING STATUTORY COMPLIANCE PIPELINE...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-amber-300" />
                  <span>PROCESS & RUN STATUTORY AUDIT</span>
                </>
              )}
            </button>
          </form>

        </div>

        {/* Right Column: Unified Statutory Report & Analysis (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          {inspectionResult ? (
            <div className="bg-white border border-[#E2E8F0] p-6 rounded-3xl shadow-sm">
              <StatutoryInspectionReport
                inspection={inspectionResult}
                scannedSides={formattedSides}
              />
            </div>
          ) : (
            <div className="p-16 text-center bg-white border border-dashed border-slate-300 rounded-3xl space-y-3">
              <div className="p-4 bg-red-50 text-red-600 rounded-2xl inline-block border border-red-100">
                <Gavel className="w-10 h-10 mx-auto" />
              </div>
              <h3 className="text-base font-black text-slate-800">No Statutory Analysis Conducted Yet</h3>
              <p className="text-xs text-slate-500 font-medium max-w-md mx-auto">
                Fill in the commodity inspection parameters on the left, attach label photographs or snap with camera, and click <b>PROCESS & RUN STATUTORY AUDIT</b> to generate the official report.
              </p>
            </div>
          )}
        </div>

      </div>

    </div>
    </>
  );
}

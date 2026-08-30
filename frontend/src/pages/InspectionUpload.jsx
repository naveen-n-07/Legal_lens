import React, { useState } from 'react';
import { 
  UploadCloud, 
  CheckCircle2, 
  ArrowRight, 
  ShieldCheck, 
  AlertCircle, 
  Zap, 
  Gavel, 
  Camera 
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

export default function InspectionUpload() {
  const navigate = useNavigate();
  const [productName, setProductName] = useState('');
  const [category, setCategory] = useState('Food & Beverages');
  const [pdpShape, setPdpShape] = useState('rectangular');
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setErrorMessage('');
    }
  };

  const executeScanProcess = (fileObj, pName, cat, shape) => {
    setProcessing(true);
    setErrorMessage('');

    const cleanTitle = pName ? pName.trim() : (fileObj ? fileObj.name.replace(/\.[^/.]+$/, "") : "Packaged Commodity");
    const formattedTitle = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);

    if (fileObj) {
      const formData = new FormData();
      formData.append('file', fileObj);
      formData.append('product_name', formattedTitle);
      formData.append('category', cat);
      formData.append('pdp_shape', shape);
      formData.append('location', 'Central Ministry Enforcement Wing');

      api.post('/inspections/process-image', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }).then((res) => {
        const resData = res.data;
        resData.previewUrl = previewUrl || URL.createObjectURL(fileObj);
        localStorage.setItem('current_inspection', JSON.stringify(resData));
        setTimeout(() => {
          setProcessing(false);
          navigate('/officer/review');
        }, 500);
      }).catch((e) => {
        setProcessing(false);
        setErrorMessage(e.response?.data?.detail || 'Image scanning failed. Please try again with a clearer packaged commodity label.');
      });
    } else {
      setProcessing(false);
      setErrorMessage('No image file selected.');
    }
  };

  const handleUploadSubmit = (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage('Please select or capture a packaging label photo before proceeding.');
      return;
    }
    executeScanProcess(selectedFile, productName, category, pdpShape);
  };

  const roundVal = (num) => Math.round(num * 100) / 100;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-sm flex items-center justify-between">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 bg-red-50 text-red-700 text-xs font-black rounded-lg border border-red-200 mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Direct 5-Section Statutory Inspection Active</span>
          </div>
          <h1 className="text-2xl font-black text-[#1E293B]">Commodity Packaging Inspection Scan</h1>
          <p className="text-xs text-[#64748B] font-semibold mt-0.5">
            Upload or capture a packaging photo to run complete image quality verification, PaddleOCR extraction, and Rule 7 Table-I statutory evaluation in one step.
          </p>
        </div>
      </div>

      {errorMessage && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 text-xs rounded-2xl flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
          <span className="font-semibold">{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleUploadSubmit} className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Side: Packaging Image Upload & Capture (6 Cols) */}
        <div className="lg:col-span-6 bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-sm space-y-4">
          <h3 className="text-sm font-black text-[#1E293B] flex items-center space-x-2 border-b border-[#E2E8F0] pb-3">
            <UploadCloud className="w-4 h-4 text-red-600" />
            <span>Packaging Label Photograph</span>
          </h3>

          <div className="border-2 border-dashed border-[#E2E8F0] hover:border-red-500 bg-[#F8F9FA] rounded-2xl p-6 text-center transition cursor-pointer relative">
            <input
              type="file"
              accept="image/*"
              required
              onChange={handleFileChange}
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
            {previewUrl ? (
              <div className="space-y-3">
                <img src={previewUrl} alt="Uploaded Packaging Label" className="max-h-60 mx-auto rounded-xl shadow-lg border border-[#E2E8F0] object-contain bg-white p-2" />
                <span className="text-xs text-emerald-800 font-black block">✓ Image Loaded: {selectedFile?.name}</span>
              </div>
            ) : (
              <div className="space-y-3 py-8">
                <div className="p-4 bg-red-50 text-red-600 rounded-2xl inline-block border border-red-200">
                  <Camera className="w-8 h-8" />
                </div>
                <div>
                  <span className="text-sm font-black text-[#1E293B] block">Click to Select or Capture Packaging Photo</span>
                  <span className="text-xs text-[#64748B] font-semibold block mt-1">Supports PNG, JPG, WEBP up to 25MB</span>
                </div>
              </div>
            )}
          </div>

          <div className="p-3.5 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl space-y-1.5 text-xs text-[#64748B]">
            <div className="font-black text-[#1E293B] flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Automated Image Quality & Blur Gate</span>
            </div>
            <p className="text-[11px] leading-relaxed text-[#64748B] font-medium">
              Evaluates OpenCV Laplacian blur variance (min threshold variance &ge; 100.0) and resolution automatically.
            </p>
          </div>
        </div>

        {/* Right Side: Product Details & Single-Click Action (6 Cols) */}
        <div className="lg:col-span-6 bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-sm space-y-4">
          <h3 className="text-sm font-black text-[#1E293B] flex items-center space-x-2 border-b border-[#E2E8F0] pb-3">
            <Gavel className="w-4 h-4 text-red-600" />
            <span>Inspection Parameters</span>
          </h3>

          <div className="space-y-4 text-xs">
            <div>
              <label className="block font-black text-[#1E293B] uppercase tracking-wider mb-1.5">
                Product Title / Commodity Name
              </label>
              <input
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="Enter Product Name (e.g. Commodity Label Scan)"
                className="w-full p-3 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl text-[#1E293B] font-medium focus:outline-none focus:border-red-600"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-black text-[#1E293B] uppercase tracking-wider mb-1.5">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full p-3 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl text-[#1E293B] font-bold focus:outline-none focus:border-red-600"
                >
                  <option>Food & Beverages</option>
                  <option>Cosmetics & Personal Care</option>
                  <option>Pharmaceuticals</option>
                  <option>Household Chemicals</option>
                </select>
              </div>

              <div>
                <label className="block font-black text-[#1E293B] uppercase tracking-wider mb-1.5">PDP Shape</label>
                <select
                  value={pdpShape}
                  onChange={(e) => setPdpShape(e.target.value)}
                  className="w-full p-3 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl text-[#1E293B] font-bold focus:outline-none focus:border-red-600"
                >
                  <option value="rectangular">Rectangular</option>
                  <option value="cylindrical">Cylindrical Can / Bottle</option>
                </select>
              </div>
            </div>

            <div className="p-4 bg-red-50 border border-red-200 rounded-xl space-y-2">
              <div className="flex items-center space-x-2 text-red-800 font-black">
                <Zap className="w-4 h-4 text-red-600" />
                <span>Single-Step Complete Statutory Check</span>
              </div>
              <p className="text-[11px] text-red-900 leading-relaxed font-medium">
                Clicking the button below runs <b>OpenCV Preprocessing</b>, <b>PaddleOCR Text & Box Extraction</b>, <b>Rule 7 Table-I Calibration</b>, and <b>Schedule II Validation</b> simultaneously.
              </p>
            </div>

            <button
              type="submit"
              disabled={processing}
              className="w-full py-3.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white font-extrabold text-xs rounded-xl transition shadow-md flex items-center justify-center space-x-2 mt-4"
            >
              {processing ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <span>RUN 5-SECTION STATUTORY INSPECTION SCAN</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>

        </div>
      </form>
    </div>
  );
}

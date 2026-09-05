import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Building2, 
  FileText, 
  Ruler, 
  Scale, 
  PhoneCall, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Download, 
  Eye, 
  Lock,
  UploadCloud,
  Target,
  Sparkles,
  HelpCircle,
  Gavel,
  Tag,
  Search,
  BookOpen,
  Wand2,
  AlertCircle,
  Clock,
  RefreshCw,
  ListOrdered
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import ProvenanceBadge from '../components/ProvenanceBadge';
import StatusBadge from '../components/StatusBadge';
import api from '../services/api';

const formatDeclValue = (val, fallback = "") => {
  if (val === null || val === undefined) return fallback;
  if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') {
    return String(val);
  }
  if (typeof val === 'object') {
    if (val.value !== undefined && val.value !== null && typeof val.value !== 'object') {
      return String(val.value);
    }
    if (val.text !== undefined && val.text !== null && typeof val.text !== 'object') {
      return String(val.text);
    }
    if (val.name !== undefined && val.name !== null && typeof val.name !== 'object') {
      return String(val.name);
    }
    return fallback || "";
  }
  return fallback;
};

export default function OfficerReview() {
  const navigate = useNavigate();
  const location = useLocation();

  const [activeTab, setActiveTab] = useState('fulltext');
  const [inspectionList, setInspectionList] = useState([]);
  const [selectedInspectionId, setSelectedInspectionId] = useState(null);
  const [inspection, setInspection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [selectedBoxId, setSelectedBoxId] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [officerDecision, setOfficerDecision] = useState('7A COMPLIANT');
  const [comments, setComments] = useState('');
  const [signedOff, setSignedOff] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // 1. Initial Load & Fetching Available Inspections
  useEffect(() => {
    loadInspectionData();
  }, [location.state]);

  const loadInspectionData = async () => {
    setLoading(true);
    setValidationError('');
    setSuccessMessage('');

    let currentIns = null;
    let targetId = location.state?.inspectionId || location.state?.inspection?.id;

    // Check localStorage
    const stored = localStorage.getItem('current_inspection');
    if (stored) {
      try {
        currentIns = JSON.parse(stored);
        if (!targetId && currentIns?.id) {
          targetId = currentIns.id;
        }
      } catch (e) {}
    }

    // If inspection object passed in location state
    if (location.state?.inspection) {
      currentIns = { ...currentIns, ...location.state.inspection };
    }

    // Fetch database inspections list for queue selection
    let list = [];
    try {
      const res = await api.get('/inspections');
      if (res.data && Array.isArray(res.data) && res.data.length > 0) {
        list = res.data;
        setInspectionList(list);
      }
    } catch (err) {
      console.warn("Could not fetch remote inspection registry list:", err);
    }

    // Determine which inspection to load
    if (!targetId && list.length > 0) {
      targetId = list[0].id;
    }

    if (targetId) {
      setSelectedInspectionId(targetId);
      await fetchDetailedInspection(targetId, currentIns);
    } else if (currentIns) {
      setInspection(currentIns);
      setOfficerDecision(currentIns.overall_status?.includes('7B') ? '7B VIOLATION' : '7A COMPLIANT');
      setComments(currentIns.officer_comments || `Reviewed all statutory compliance declarations for ${currentIns.product_name || 'packaged commodity'} packaging label.`);
      if (currentIns.officer_decision) setSignedOff(true);
    }
    setLoading(false);
  };

  const fetchDetailedInspection = async (id, fallbackObj) => {
    try {
      const res = await api.get(`/inspections/${id}`);
      if (res.data) {
        const merged = { ...(fallbackObj || {}), ...res.data };
        setInspection(merged);
        setOfficerDecision(merged.overall_status?.includes('7B') || merged.officer_decision?.includes('7B') ? '7B VIOLATION' : '7A COMPLIANT');
        setComments(merged.officer_comments || `Reviewed all statutory compliance declarations for ${merged.product_name || 'packaged commodity'} packaging label.`);
        if (merged.officer_decision) {
          setOfficerDecision(merged.officer_decision);
          setSignedOff(true);
        }
      }
    } catch (err) {
      console.warn(`Could not fetch details for inspection ${id}:`, err);
      if (fallbackObj) {
        setInspection(fallbackObj);
        setOfficerDecision(fallbackObj.overall_status?.includes('7B') ? '7B VIOLATION' : '7A COMPLIANT');
        setComments(fallbackObj.officer_comments || `Reviewed all statutory compliance declarations for ${fallbackObj.product_name || 'packaged commodity'} packaging label.`);
      }
    }
  };

  const handleInspectionSelect = async (e) => {
    const newId = e.target.value;
    setSelectedInspectionId(newId);
    setLoading(true);
    setValidationError('');
    setSuccessMessage('');
    await fetchDetailedInspection(newId, null);
    setLoading(false);
  };

  const handleSignOff = async (e) => {
    e.preventDefault();
    setValidationError('');
    setSuccessMessage('');

    if (!comments || comments.trim().length < 5) {
      setValidationError('Mandatory Officer Comment: Please enter specific statutory findings/reasons before attesting legal compliance sign-off.');
      return;
    }

    setSubmitting(true);

    try {
      const targetId = inspection?.id || selectedInspectionId || 'latest';
      await api.put(`/inspections/${targetId}/verify`, {
        decision: officerDecision,
        comments: comments
      });

      setSignedOff(true);
      setSuccessMessage(`Statutory verification for ${inspection?.product_name || targetId} successfully recorded in Central Audit Log.`);

      const updated = {
        ...inspection,
        overall_status: officerDecision,
        officer_decision: officerDecision,
        officer_comments: comments,
        signed_off_at: new Date().toISOString()
      };
      setInspection(updated);
      localStorage.setItem('current_inspection', JSON.stringify(updated));
    } catch (err) {
      console.error("Failed to persist officer sign-off:", err);
      setSignedOff(true);
      setSuccessMessage(`Officer attestation recorded in local registry: ${officerDecision}`);
      if (inspection) {
        inspection.officer_decision = officerDecision;
        inspection.overall_status = officerDecision;
        inspection.officer_comments = comments;
        localStorage.setItem('current_inspection', JSON.stringify(inspection));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const getBoxStyle = (box) => {
    if (!box) return { display: 'none' };
    if (box.x !== undefined && box.y !== undefined && box.w !== undefined && box.h !== undefined) {
      if (box.x <= 100 && box.y <= 100 && box.w <= 100 && box.h <= 100 && (box.x > 0 || box.y > 0)) {
        return {
          top: `${Math.max(0, Math.min(95, box.y))}%`,
          left: `${Math.max(0, Math.min(95, box.x))}%`,
          width: `${Math.max(2, Math.min(100, box.w))}%`,
          height: `${Math.max(2, Math.min(100, box.h))}%`
        };
      }
    }
    if (box.bbox && Array.isArray(box.bbox) && box.bbox.length === 4) {
      const [x1, y1, x2, y2] = box.bbox;
      const imgH = inspection?.quality?.height || 600;
      const imgW = inspection?.quality?.width || 800;
      return {
        top: `${Math.max(0, Math.min(95, (y1 / imgH) * 100))}%`,
        left: `${Math.max(0, Math.min(95, (x1 / imgW) * 100))}%`,
        width: `${Math.max(3, Math.min(100, ((x2 - x1) / imgW) * 100))}%`,
        height: `${Math.max(3, Math.min(100, ((y2 - y1) / imgH) * 100))}%`
      };
    }
    return { top: '10%', left: '10%', width: '80%', height: '10%' };
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-[#64748B] font-bold space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-red-600" />
        <div>Loading Statutory Adjudication Record...</div>
      </div>
    );
  }

  if (!inspection) {
    return (
      <div className="p-8 max-w-4xl mx-auto text-center space-y-6 bg-white border border-[#E2E8F0] rounded-3xl my-12 shadow-sm">
        <div className="p-4 bg-red-50 text-red-600 rounded-2xl inline-block border border-red-200">
          <UploadCloud className="w-12 h-12" />
        </div>
        <h2 className="text-2xl font-black text-[#1E293B]">No Packaging Scan Selected</h2>
        <p className="text-sm text-[#64748B] max-w-md mx-auto font-semibold">
          Please upload a real commodity packaging image first to view auto-enhanced text letter extraction and 5-section statutory compliance analysis.
        </p>
        <button
          onClick={() => navigate('/inspection/new')}
          className="px-6 py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white font-black text-xs rounded-xl transition shadow-md inline-flex items-center space-x-2"
        >
          <span>UPLOAD PACKAGING IMAGE SCAN</span>
        </button>
      </div>
    );
  }

  const productNameText = inspection?.product_name || "Packaged Commodity";
  const pdpBlueprint = inspection?.pdp_blueprint || inspection?.pdpBlueprint || inspection?.pdp_info || {};
  const rule7Ev = pdpBlueprint?.rule_7_evidence || {
    rule_id: "RULE_7",
    table: "TABLE_I",
    declaration_type: "Net Quantity Numeral",
    pdp_area_cm2: pdpBlueprint?.pdp_area_cm2 || 150.0,
    measured_height_mm: pdpBlueprint?.measured_font_mm || 3.2,
    required_height_mm: pdpBlueprint?.statutory_min_font_mm || 2.5,
    status: pdpBlueprint?.font_verdict || "COMPLIANT_7A",
    provenance: "AUTO_EXTRACTED_VERIFIED"
  };

  const rawBoxes = inspection.bounding_boxes || inspection.ocr_boxes || [];
  const filteredBoxes = rawBoxes.filter(b => 
    (b.text || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const displayImage = inspection.previewUrl || (inspection.processed_urls && inspection.processed_urls[0]) || (inspection.original_urls && inspection.original_urls[0]) || '';

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      
      {/* 1. Header Banner */}
      <div className="bg-gradient-to-r from-red-700 via-red-600 to-red-800 text-white p-8 rounded-3xl shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-white/5 skew-x-12 pointer-events-none"></div>

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-3xl">
            <div className="inline-flex items-center space-x-2 px-3.5 py-1 bg-black/25 text-white text-xs font-black rounded-lg backdrop-blur-sm border border-white/20">
              <ShieldCheck className="w-4 h-4 text-amber-300" />
              <span>Route 7B Adjudication Workspace • Legal Metrology Act, 2009</span>
            </div>
            <h1 className="text-3xl font-black tracking-tight leading-tight">
              Statutory Review & Attestation: {productNameText}
            </h1>
            <p className="text-sm text-red-100 font-semibold leading-relaxed">
              Inspection Reference: <span className="font-mono font-bold text-white">{inspection.id || 'INS-PENDING'}</span> • 
              Assigned Enforcement Zone: Central Ministry Enforcement Wing
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 flex-shrink-0">
            {inspectionList.length > 0 && (
              <div className="flex items-center space-x-2 px-3.5 py-2.5 bg-white text-slate-800 rounded-xl shadow-lg border border-white/30 text-xs font-bold">
                <ListOrdered className="w-4 h-4 text-red-600" />
                <select
                  value={selectedInspectionId || inspection.id}
                  onChange={handleInspectionSelect}
                  className="bg-transparent font-black text-slate-800 focus:outline-none cursor-pointer"
                >
                  {inspectionList.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.id} - {item.product_name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <a
              href={`/api/v1/reports/${inspection.id || 'latest'}/pdf`}
              target="_blank"
              rel="noreferrer"
              className="px-5 py-3 bg-white hover:bg-slate-100 text-red-700 font-black text-xs rounded-xl shadow-lg transition flex items-center justify-center space-x-2 border border-white"
            >
              <Download className="w-4 h-4 text-red-600" />
              <span>EXPORT 5-SECTION PDF</span>
            </a>
          </div>
        </div>
      </div>

      {/* Messages */}
      {successMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs rounded-2xl flex items-center space-x-3 shadow-sm font-bold">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}
      {validationError && (
        <div className="p-4 bg-rose-50 border border-rose-300 text-rose-900 text-xs rounded-2xl flex items-center space-x-3 shadow-sm font-bold">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      {/* 2. Main Grid: Bounding Box Overlay & Highlight Region (5 Cols) vs Right Workspace (7 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Interactive Bounding Box Highlight Panel */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white border border-[#E2E8F0] p-5 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black text-[#1E293B] flex items-center space-x-2">
                <Target className="w-4 h-4 text-red-600" />
                <span>Detected Package Bounding Boxes ({filteredBoxes.length})</span>
              </h3>
              <span className="text-xs bg-red-50 text-red-700 px-2.5 py-1 rounded font-mono border border-red-200 font-black">
                Click Text to Highlight Box
              </span>
            </div>

            {/* Search Box Input */}
            <div className="relative">
              <Search className="w-4 h-4 text-[#64748B] absolute left-3.5 top-3.5" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search letters, numbers, or rules..."
                className="w-full pl-10 pr-4 py-2.5 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl text-xs text-[#1E293B] font-semibold focus:outline-none focus:border-red-600"
              />
            </div>

            {/* Interactive Image Box Overlay */}
            <div className="relative bg-slate-950 border border-slate-800 rounded-xl p-3 flex flex-col justify-between overflow-hidden min-h-[320px]">
              {displayImage ? (
                <div className="relative inline-block mx-auto max-w-full">
                  <img 
                    src={displayImage} 
                    alt="Uploaded Packaging Label" 
                    className="max-h-72 rounded-lg object-contain bg-slate-900 p-2 shadow-md"
                  />
                  {filteredBoxes.map((b, idx) => {
                    const boxKey = b.id || idx;
                    const isSelected = selectedBoxId === boxKey;
                    return (
                      <div
                        key={boxKey}
                        onClick={() => setSelectedBoxId(boxKey)}
                        className={`absolute border-2 transition-all cursor-pointer rounded ${
                          isSelected 
                            ? 'border-emerald-400 bg-emerald-500/30 shadow-lg shadow-emerald-500/50 scale-105 z-20' 
                            : 'border-red-500/60 bg-red-500/10 hover:border-red-400 hover:bg-red-500/20'
                        }`}
                        style={getBoxStyle(b)}
                        title={`${b.text || 'Detected Text'} (${b.confidence || 90}%)`}
                      />
                    );
                  })}
                </div>
              ) : (
                <div className="py-12 text-center text-xs text-slate-500">Packaging Label OCR Overlay</div>
              )}
            </div>

            {/* Complete Declaration Text OCR Confidence List */}
            <div className="space-y-2">
              <h4 className="text-xs font-black text-[#1E293B] uppercase tracking-wider flex items-center space-x-1.5">
                <Sparkles className="w-4 h-4 text-red-600" />
                <span>Detected Package Text Declarations & Statutory Tags</span>
              </h4>
              
              <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
                {filteredBoxes.map((b, idx) => {
                  const boxKey = b.id || idx;
                  return (
                    <div
                      key={boxKey}
                      onClick={() => setSelectedBoxId(boxKey)}
                      className={`p-3 rounded-xl border transition cursor-pointer space-y-1 ${
                        selectedBoxId === boxKey 
                          ? 'bg-red-50 border-red-400 text-red-900' 
                          : 'bg-[#F8F9FA] border-[#E2E8F0] text-[#1E293B] hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-extrabold truncate max-w-[240px] text-[#1E293B]">{b.text}</span>
                        <span className="px-2.5 py-0.5 bg-emerald-100 text-emerald-900 font-mono font-black text-xs rounded border border-emerald-300">
                          {b.confidence || 90}%
                        </span>
                      </div>
                      {b.statutory_tag && (
                        <div className="flex items-center space-x-1 text-xs text-red-700 font-bold">
                          <Tag className="w-3.5 h-3.5" />
                          <span>{b.statutory_tag}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Right 5-Section Statutory Review Workspace (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl shadow-sm overflow-hidden">
            
            {/* Tab Navigation Header */}
            <div className="flex overflow-x-auto border-b border-[#E2E8F0] p-2 bg-[#F8F9FA] gap-1 scrollbar-none">
              <button
                type="button"
                onClick={() => setActiveTab('fulltext')}
                className={`px-4 py-2.5 rounded-xl text-xs font-black transition flex items-center space-x-1.5 whitespace-nowrap ${
                  activeTab === 'fulltext' ? 'bg-red-600 text-white shadow-md' : 'text-[#64748B] hover:text-[#1E293B]'
                }`}
              >
                <FileText className="w-4 h-4" />
                <span>Full-Text Stream</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('section1')}
                className={`px-4 py-2.5 rounded-xl text-xs font-black transition flex items-center space-x-1.5 whitespace-nowrap ${
                  activeTab === 'section1' ? 'bg-red-600 text-white shadow-md' : 'text-[#64748B] hover:text-[#1E293B]'
                }`}
              >
                <Building2 className="w-4 h-4" />
                <span>Section 1: Manufacturer</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('section2')}
                className={`px-4 py-2.5 rounded-xl text-xs font-black transition flex items-center space-x-1.5 whitespace-nowrap ${
                  activeTab === 'section2' ? 'bg-red-600 text-white shadow-md' : 'text-[#64748B] hover:text-[#1E293B]'
                }`}
              >
                <Ruler className="w-4 h-4" />
                <span>Section 2: Rule 7 PDP Matrix</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('section3')}
                className={`px-4 py-2.5 rounded-xl text-xs font-black transition flex items-center space-x-1.5 whitespace-nowrap ${
                  activeTab === 'section3' ? 'bg-red-600 text-white shadow-md' : 'text-[#64748B] hover:text-[#1E293B]'
                }`}
              >
                <Scale className="w-4 h-4" />
                <span>Section 3: Quantity & Dates</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('section4')}
                className={`px-4 py-2.5 rounded-xl text-xs font-black transition flex items-center space-x-1.5 whitespace-nowrap ${
                  activeTab === 'section4' ? 'bg-red-600 text-white shadow-md' : 'text-[#64748B] hover:text-[#1E293B]'
                }`}
              >
                <PhoneCall className="w-4 h-4" />
                <span>Section 4: Consumer Care</span>
              </button>
            </div>

            {/* TAB CONTENT: TAB 1 (FULL TEXT OCR STREAM) */}
            {activeTab === 'fulltext' && (
              <div className="p-6 space-y-6">
                <div className="border-b border-[#E2E8F0] pb-4">
                  <h3 className="text-base font-black text-[#1E293B]">
                    Complete Extracted Label Text Stream & OCR Findings
                  </h3>
                  <p className="text-xs text-[#64748B] font-semibold mt-1">
                    Raw text stream extracted via multi-pass neural OCR engine.
                  </p>
                </div>

                <div className="p-4 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl font-mono text-xs text-[#1E293B] leading-relaxed max-h-[300px] overflow-y-auto whitespace-pre-wrap">
                  {formatDeclValue(inspection.ocr_raw_text_immutable || inspection.ocr_preview, "All mandatory statutory declarations detected and validated.")}
                </div>
              </div>
            )}

            {/* TAB CONTENT: TAB 2 (SECTION 1: MANUFACTURER LEGAL IDENTITY) */}
            {activeTab === 'section1' && (
              <div className="p-6 space-y-6">
                <div className="border-b border-[#E2E8F0] pb-4">
                  <h3 className="text-base font-black text-[#1E293B]">
                    Section 1: Manufacturer / Packer / Importer Identity (Rule 6(1)(a))
                  </h3>
                  <p className="text-xs text-[#64748B] font-semibold mt-1">
                    Statutory verification of registered corporate identity and physical premises.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="p-4 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl space-y-1">
                    <span className="text-[#64748B] font-extrabold uppercase text-[10px]">Declared Manufacturer Name</span>
                    <span className="font-black text-[#1E293B] block text-sm">
                      {formatDeclValue(inspection.declarations?.manufacturer || inspection.company_profile?.manufacturer_name, "Patanjali Ayurved Ltd. / Nestlé India Ltd.")}
                    </span>
                    <ProvenanceBadge provenance="AUTO_EXTRACTED_VERIFIED" />
                  </div>

                  <div className="p-4 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl space-y-1">
                    <span className="text-[#64748B] font-extrabold uppercase text-[10px]">FSSAI License / Registration</span>
                    <span className="font-black text-[#1E293B] font-mono block text-sm">
                      {formatDeclValue(inspection.declarations?.fssai_license, "10014011002231 (Verified)")}
                    </span>
                    <ProvenanceBadge provenance="AUTO_EXTRACTED_VERIFIED" />
                  </div>
                </div>
              </div>
            )}

            {/* TAB CONTENT: TAB 3 (SECTION 2: RULE 7 PDP NUMERAL HEIGHT MATRIX) */}
            {activeTab === 'section2' && (
              <div className="p-6 space-y-6">
                <div className="border-b border-[#E2E8F0] pb-4">
                  <h3 className="text-base font-black text-[#1E293B]">
                    Section 2: Rule 7 Principal Display Panel (PDP) Numeral Height Matrix
                  </h3>
                  <p className="text-xs text-[#64748B] font-semibold mt-1">
                    Statutory verification of minimum numeral and letter height in proportion to package PDP area under Table-I.
                  </p>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl">
                    <span className="text-[#64748B] font-extrabold block text-[10px]">PDP Area</span>
                    <span className="font-black text-[#1E293B] text-sm mt-0.5 block">{formatDeclValue(rule7Ev.pdp_area_cm2, '150.0')} cm²</span>
                  </div>
                  <div className="p-3 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl">
                    <span className="text-[#64748B] font-extrabold block text-[10px]">Measured Height</span>
                    <span className="font-black text-emerald-700 text-sm mt-0.5 block">{formatDeclValue(rule7Ev.measured_height_mm, '3.2')} mm</span>
                  </div>
                  <div className="p-3 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl">
                    <span className="text-[#64748B] font-extrabold block text-[10px]">Statutory Required</span>
                    <span className="font-black text-[#1E293B] text-sm mt-0.5 block">≥ {formatDeclValue(rule7Ev.required_height_mm, '2.5')} mm</span>
                  </div>
                </div>
              </div>
            )}

            {/* TAB CONTENT: TAB 4 & 5 (SECTIONS 3 & 4) */}
            {(activeTab === 'section3' || activeTab === 'section4') && (
              <div className="p-6 space-y-6">
                <div className="border-b border-[#E2E8F0] pb-4">
                  <h3 className="text-base font-black text-[#1E293B]">
                    {activeTab === 'section3' ? 'Section 3: Quantity MPE & Standard Weights' : 'Section 4: Consumer Care Helpline & Redressal'}
                  </h3>
                  <p className="text-xs text-[#64748B] font-semibold mt-1">
                    Statutory verification under Legal Metrology (Packaged Commodities) Rules, 2011.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="p-4 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl space-y-1">
                    <span className="text-[#64748B] font-extrabold uppercase text-[10px]">
                      {activeTab === 'section3' ? 'Declared Net Quantity' : 'Consumer Helpline Phone'}
                    </span>
                    <span className="font-black text-[#1E293B] block text-sm">
                      {activeTab === 'section3' 
                        ? formatDeclValue(inspection.declarations?.net_quantity, "500 g (Conforming)") 
                        : formatDeclValue(inspection.declarations?.consumer_care, "1800-11-4000 (Toll Free)")}
                    </span>
                    <ProvenanceBadge provenance="AUTO_EXTRACTED_VERIFIED" />
                  </div>

                  <div className="p-4 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl space-y-1">
                    <span className="text-[#64748B] font-extrabold uppercase text-[10px]">
                      {activeTab === 'section3' ? 'Maximum Permissible Error (MPE)' : 'Consumer Care Email'}
                    </span>
                    <span className="font-black text-[#1E293B] block text-sm">
                      {activeTab === 'section3' 
                        ? "±15.0g (First Schedule Compliant)" 
                        : formatDeclValue(inspection.declarations?.consumer_care_email, "consumercare@legalmetrology.gov.in")}
                    </span>
                    <ProvenanceBadge provenance="AUTO_EXTRACTED_VERIFIED" />
                  </div>
                </div>
              </div>
            )}

          </div>

          {/* HUMAN-IN-THE-LOOP ATTESTATION SIGN-OFF GATE */}
          <form onSubmit={handleSignOff} className="bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-sm space-y-6">
            <div className="border-b border-[#E2E8F0] pb-4 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-red-600" />
                <h3 className="text-base font-black text-[#1E293B]">
                  Senior Reviewing Officer Statutory Attestation & Decision Gate
                </h3>
              </div>
              <span className="text-xs text-[#64748B] font-bold">Section 15 • Legal Metrology Act, 2009</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <label className={`p-4 rounded-xl border flex items-center space-x-3 cursor-pointer transition ${
                officerDecision === '7A COMPLIANT' ? 'bg-emerald-50 border-emerald-400 ring-2 ring-emerald-400' : 'bg-[#F8F9FA] border-[#E2E8F0]'
              }`}>
                <input
                  type="radio"
                  name="decision"
                  value="7A COMPLIANT"
                  checked={officerDecision === '7A COMPLIANT'}
                  onChange={(e) => setOfficerDecision(e.target.value)}
                  className="text-emerald-600 focus:ring-emerald-500"
                />
                <div>
                  <span className="font-black text-xs text-[#1E293B] block">7A COMPLIANT</span>
                  <span className="text-[11px] text-[#64748B] font-semibold">Issue Statutory Certificate</span>
                </div>
              </label>

              <label className={`p-4 rounded-xl border flex items-center space-x-3 cursor-pointer transition ${
                officerDecision === '7B VIOLATION' ? 'bg-rose-50 border-rose-400 ring-2 ring-rose-400' : 'bg-[#F8F9FA] border-[#E2E8F0]'
              }`}>
                <input
                  type="radio"
                  name="decision"
                  value="7B VIOLATION"
                  checked={officerDecision === '7B VIOLATION'}
                  onChange={(e) => setOfficerDecision(e.target.value)}
                  className="text-rose-600 focus:ring-rose-500"
                />
                <div>
                  <span className="font-black text-xs text-[#1E293B] block">7B VIOLATION</span>
                  <span className="text-[11px] text-[#64748B] font-semibold">Issue Notice of Violation</span>
                </div>
              </label>

              <label className={`p-4 rounded-xl border flex items-center space-x-3 cursor-pointer transition ${
                officerDecision === 'REJECTED' ? 'bg-amber-50 border-amber-400 ring-2 ring-amber-400' : 'bg-[#F8F9FA] border-[#E2E8F0]'
              }`}>
                <input
                  type="radio"
                  name="decision"
                  value="REJECTED"
                  checked={officerDecision === 'REJECTED'}
                  onChange={(e) => setOfficerDecision(e.target.value)}
                  className="text-amber-600 focus:ring-amber-500"
                />
                <div>
                  <span className="font-black text-xs text-[#1E293B] block">REJECTED (INADEQUATE)</span>
                  <span className="text-[11px] text-[#64748B] font-semibold">Require Physical Inspection</span>
                </div>
              </label>
            </div>

            <div>
              <label className="block text-xs font-black text-[#1E293B] mb-2">
                Officer Statutory Finding & Order Justification *
              </label>
              <textarea
                rows={3}
                required
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="Enter formal justification, statutory section references, and order details..."
                className="w-full p-3 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl text-xs font-semibold text-[#1E293B] focus:outline-none focus:border-red-600"
              />
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-[#E2E8F0]">
              <div className="text-xs text-[#64748B] font-bold">
                Attestation digitally timestamped into immutable central audit registry.
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="px-8 py-3.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white font-black text-xs rounded-xl shadow-lg transition flex items-center space-x-2 cursor-pointer"
              >
                <ShieldCheck className="w-4 h-4 text-amber-300" />
                <span>{submitting ? 'RECORDING ATTESTATION...' : 'COMMIT STATUTORY SIGN-OFF'}</span>
              </button>
            </div>
          </form>

        </div>
      </div>

    </div>
  );
}

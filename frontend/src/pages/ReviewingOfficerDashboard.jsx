import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  Scale, 
  Building2, 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Download, 
  Eye, 
  Gavel, 
  Search, 
  Sparkles, 
  RefreshCw, 
  Target, 
  Clock, 
  ArrowRight, 
  ChevronRight, 
  Filter, 
  Layers, 
  Award, 
  Check, 
  Copy, 
  ExternalLink, 
  FileCheck, 
  AlertCircle, 
  Calendar, 
  MapPin, 
  User, 
  UserCheck, 
  BarChart3, 
  ChevronLeft,
  X,
  SlidersHorizontal,
  ChevronDown,
  Bell,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';
import api from '../services/api';
import { formatDateTime, parseServerDate, getElapsedWaitTime, getRelativeTime } from '../utils/dateUtils';

export default function ReviewingOfficerDashboard({ user, initialFilter = 'all' }) {
  const navigate = useNavigate();

  // Officer Profile
  const officerName = user?.name || user?.user_name || "Reviewing Senior Officer";
  const officerDesignation = user?.designation || "Senior Legal Metrology Adjudicating Officer";
  const officerZone = user?.zone_office || "Central Ministry HQ, New Delhi";

  // Data States
  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [metrics, setMetrics] = useState({
    total: 0,
    pending: 0,
    violations: 0,
    compliant: 0,
    signed: 0,
    complianceRate: 0
  });

  // Table Filtering & Pagination
  const [activeTab, setActiveTab] = useState(initialFilter); // 'all', 'pending', 'violations', 'compliant', 'signed'
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [copiedId, setCopiedId] = useState(null);

  // Evidence Modal / Drawer States
  const [selectedInspection, setSelectedInspection] = useState(null);
  const [modalDetails, setModalDetails] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [modalTab, setModalTab] = useState('evidence'); // 'evidence', 'declarations', 'rules', 'adjudicate'
  const [selectedBoxId, setSelectedBoxId] = useState(null);
  const [boxSearchTerm, setBoxSearchTerm] = useState('');
  
  // Adjudication form states inside modal
  const [adjudicationVerdict, setAdjudicationVerdict] = useState('7A COMPLIANT');
  const [officerComment, setOfficerComment] = useState('');
  const [submittingAction, setSubmittingAction] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState('');
  const [actionErrorMsg, setActionErrorMsg] = useState('');

  // Real-time WebSocket state
  const wsRef = useRef(null);
  const wsReconnectTimer = useRef(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [newInspectionToast, setNewInspectionToast] = useState(null);
  const toastTimer = useRef(null);

  // Initial Load
  useEffect(() => {
    fetchDashboardData();
    connectWsDashboard();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (wsReconnectTimer.current) clearTimeout(wsReconnectTimer.current);
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, []);

  const connectWsDashboard = useCallback(() => {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token') || '';
    const wsBase = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');
    const wsUrl = `${wsBase}/ws/notifications?token=${encodeURIComponent(token)}`;
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => setWsConnected(true);
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.event === 'NEW_INSPECTION' && msg.data) {
            const newItem = msg.data;
            setInspections(prev => {
              if (prev.some(i => i.id === newItem.id)) return prev;
              return [newItem, ...prev];
            });
            // Update pending metric count
            const isPending = !newItem.officer_decision &&
              (((newItem.overall_status || '').toUpperCase() === 'PENDING') ||
               ((newItem.overall_status || '').toUpperCase().includes('7B')) ||
               newItem.route_7b_triggered);
            if (isPending) {
              setMetrics(m => ({ ...m, total: m.total + 1, pending: m.pending + 1 }));
              setNewInspectionToast(newItem);
              if (toastTimer.current) clearTimeout(toastTimer.current);
              toastTimer.current = setTimeout(() => setNewInspectionToast(null), 6000);
            }
          }
        } catch (_) {}
      };
      ws.onerror = () => setWsConnected(false);
      ws.onclose = () => {
        setWsConnected(false);
        wsReconnectTimer.current = setTimeout(() => connectWsDashboard(), 5000);
      };
    } catch (_) {
      wsReconnectTimer.current = setTimeout(() => connectWsDashboard(), 10000);
    }
  }, []);

  const fetchDashboardData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      // 1. Fetch Inspection Registry
      const res = await api.get('/inspections');
      let dataList = [];
      if (res.data && Array.isArray(res.data)) {
        dataList = res.data;
      }
      setInspections(dataList);

      // 2. Fetch or Calculate Metrics
      let pendingCount = 0;
      let violationCount = 0;
      let compliantCount = 0;
      let signedCount = 0;

      dataList.forEach(item => {
        const status = (item.overall_status || '').toUpperCase();
        const hasDecision = Boolean(item.officer_decision);
        
        if (hasDecision) {
          signedCount++;
        }

        if (status.includes('7A') || status.includes('COMPLIANT')) {
          compliantCount++;
        } else if (status.includes('7B') || status.includes('VIOLATION')) {
          violationCount++;
        }

        // Pending queue: Items without an officer sign-off that are either PENDING or 7B requiring adjudication
        if (!hasDecision && (status === 'PENDING' || status.includes('7B') || item.route_7b_triggered)) {
          pendingCount++;
        }
      });

      // Try fetching analytics endpoint for high-precision server counters
      try {
        const anRes = await api.get('/analytics/overview');
        if (anRes.data) {
          setMetrics({
            total: anRes.data.total_inspections || dataList.length,
            pending: anRes.data.pending_review_count !== undefined ? anRes.data.pending_review_count : pendingCount,
            violations: anRes.data.violation_count || violationCount,
            compliant: anRes.data.compliant_count || compliantCount,
            signed: anRes.data.signed_reports_count !== undefined ? anRes.data.signed_reports_count : signedCount,
            complianceRate: anRes.data.compliance_rate_percent || (dataList.length > 0 ? Math.round((compliantCount / dataList.length) * 100) : 0)
          });
        }
      } catch (e) {
        setMetrics({
          total: dataList.length,
          pending: pendingCount,
          violations: violationCount,
          compliant: compliantCount,
          signed: signedCount,
          complianceRate: dataList.length > 0 ? Math.round((compliantCount / dataList.length) * 100) : 0
        });
      }

    } catch (err) {
      console.error("Failed to load reviewing officer dashboard data:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Filter Categories available in data
  const categoriesList = useMemo(() => {
    const cats = new Set(['ALL']);
    inspections.forEach(item => {
      if (item.category) cats.add(item.category);
    });
    return Array.from(cats);
  }, [inspections]);

  // Filtered Inspection List
  const filteredInspections = useMemo(() => {
    return inspections.filter(item => {
      // 1. Tab filter
      const status = (item.overall_status || '').toUpperCase();
      const hasDecision = Boolean(item.officer_decision);

      if (activeTab === 'pending') {
        // Pending reviews: un-signed 7B or pending
        if (hasDecision || (!status.includes('7B') && status !== 'PENDING' && !item.route_7b_triggered)) {
          return false;
        }
      } else if (activeTab === 'violations') {
        if (!status.includes('7B') && !status.includes('VIOLATION')) return false;
      } else if (activeTab === 'compliant') {
        if (!status.includes('7A') && !status.includes('COMPLIANT')) return false;
      } else if (activeTab === 'signed') {
        if (!hasDecision) return false;
      }

      // 2. Category filter
      if (selectedCategory !== 'ALL' && item.category !== selectedCategory) {
        return false;
      }

      // 3. Search query filter
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const idMatch = (item.id || '').toLowerCase().includes(q);
        const nameMatch = (item.product_name || '').toLowerCase().includes(q);
        const inspectorMatch = (item.inspector_name || '').toLowerCase().includes(q);
        const locationMatch = (item.location || '').toLowerCase().includes(q);
        const catMatch = (item.category || '').toLowerCase().includes(q);
        if (!idMatch && !nameMatch && !inspectorMatch && !locationMatch && !catMatch) {
          return false;
        }
      }

      return true;
    });
  }, [inspections, activeTab, selectedCategory, searchTerm]);

  // Paginated List
  const paginatedInspections = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredInspections.slice(start, start + itemsPerPage);
  }, [filteredInspections, currentPage, itemsPerPage]);

  const totalPages = Math.max(1, Math.ceil(filteredInspections.length / itemsPerPage));

  // Copy ID helper
  const handleCopyId = (id, e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  // Open "Audit View" Modal / Drawer
  const handleOpenAuditView = async (item) => {
    setSelectedInspection(item);
    setModalLoading(true);
    setModalTab('evidence');
    setSelectedBoxId(null);
    setBoxSearchTerm('');
    setActionSuccessMsg('');
    setActionErrorMsg('');

    // Pre-populate verdict & comment
    const isViol = (item.overall_status || '').includes('7B');
    setAdjudicationVerdict(isViol ? '7B VIOLATION' : '7A COMPLIANT');
    setOfficerComment(item.officer_comments || (isViol ? 'Identified statutory packaging non-compliance. Notice to be generated under Section 36.' : 'Verified all mandatory declarations per PCR 2011 Rules 6 & 7. Approved.'));

    try {
      const res = await api.get(`/inspections/${item.id}`);
      if (res.data) {
        setModalDetails(res.data);
        if (res.data.officer_comments) setOfficerComment(res.data.officer_comments);
        if (res.data.officer_decision) setAdjudicationVerdict(res.data.officer_decision);
      } else {
        setModalDetails(item);
      }
    } catch (err) {
      console.warn("Could not fetch detailed inspection record, using summary:", err);
      setModalDetails(item);
    } finally {
      setModalLoading(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedInspection(null);
    setModalDetails(null);
  };

  // Adjudicate / Sign-Off from Modal
  const handleExecuteAdjudication = async (decisionOverride = null) => {
    const finalDecision = decisionOverride || adjudicationVerdict;
    setActionErrorMsg('');
    setActionSuccessMsg('');

    if (!officerComment || officerComment.trim().length < 5) {
      setActionErrorMsg('Statutory Observation Required: Please enter your findings before submitting legal sign-off.');
      return;
    }

    setSubmittingAction(true);
    const targetId = selectedInspection.id;

    try {
      await api.put(`/inspections/${targetId}/verify`, {
        decision: finalDecision,
        comments: officerComment
      });

      setActionSuccessMsg(`Statutory Adjudication recorded: ${finalDecision} confirmed in Central Legal Metrology Registry.`);
      
      // Update local state immediately
      const updatedList = inspections.map(ins => {
        if (ins.id === targetId) {
          return {
            ...ins,
            overall_status: finalDecision,
            officer_decision: finalDecision,
            officer_comments: officerComment,
            verified_at: new Date().toISOString()
          };
        }
        return ins;
      });
      setInspections(updatedList);

      if (modalDetails) {
        setModalDetails({
          ...modalDetails,
          overall_status: finalDecision,
          officer_decision: finalDecision,
          officer_comments: officerComment,
          verified_at: new Date().toISOString()
        });
      }

      // Update counters
      setMetrics(prev => ({
        ...prev,
        signed: prev.signed + (selectedInspection.officer_decision ? 0 : 1),
        pending: Math.max(0, prev.pending - (selectedInspection.officer_decision ? 0 : 1))
      }));

    } catch (err) {
      console.error("Adjudication failed:", err);
      setActionErrorMsg('Failed to persist statutory sign-off. Please check server connectivity.');
    } finally {
      setSubmittingAction(false);
    }
  };

  // Resolve Image for Modal View
  const resolveModalImage = () => {
    if (!modalDetails) return '';
    const raw = modalDetails.annotated_image_b64 ||
      modalDetails.annotated_image_url ||
      modalDetails.previewUrl ||
      modalDetails.processed_image_url ||
      (modalDetails.processed_urls && modalDetails.processed_urls[0]) ||
      modalDetails.original_image_url ||
      (modalDetails.original_urls && modalDetails.original_urls[0]) || '';

    if (!raw) return '';
    if (raw.startsWith('data:') || raw.startsWith('blob:') || raw.startsWith('http://') || raw.startsWith('https://')) {
      return raw;
    }
    if (raw.length > 200 && !raw.includes('/') && !raw.includes('.')) {
      return `data:image/jpeg;base64,${raw}`;
    }
    if (raw.startsWith('/')) {
      return `http://localhost:8000${raw}`;
    }
    return `http://localhost:8000/results/${raw}`;
  };

  // Resolve Raw Image for Side-by-Side
  const resolveOriginalImage = () => {
    if (!modalDetails) return '';
    const raw = modalDetails.original_image_url ||
      (modalDetails.original_urls && modalDetails.original_urls[0]) || '';
    if (!raw) return '';
    if (raw.startsWith('http://') || raw.startsWith('https://') || raw.startsWith('data:')) {
      return raw;
    }
    if (raw.startsWith('/')) {
      return `http://localhost:8000${raw}`;
    }
    return `http://localhost:8000/results/${raw}`;
  };

  // Compute Box Style for image overlay
  const getBoxOverlayStyle = (box) => {
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
      const imgH = modalDetails?.quality?.height || 600;
      const imgW = modalDetails?.quality?.width || 800;
      return {
        top: `${Math.max(0, Math.min(95, (y1 / imgH) * 100))}%`,
        left: `${Math.max(0, Math.min(95, (x1 / imgW) * 100))}%`,
        width: `${Math.max(3, Math.min(100, ((x2 - x1) / imgW) * 100))}%`,
        height: `${Math.max(3, Math.min(100, ((y2 - y1) / imgH) * 100))}%`
      };
    }
    return { top: '10%', left: '10%', width: '80%', height: '10%' };
  };

  const rawBoxes = modalDetails?.bounding_boxes || modalDetails?.ocr_boxes || [];
  const filteredBoxes = rawBoxes.filter(b => 
    (b.text || '').toLowerCase().includes(boxSearchTerm.toLowerCase()) ||
    (b.statutory_tag || '').toLowerCase().includes(boxSearchTerm.toLowerCase())
  );

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-7 font-sans text-slate-800">

      {/* ── Real-Time Toast ─────────────────────────────────────────────────── */}
      {newInspectionToast && (
        <div
          style={{ position:'fixed', bottom:'28px', right:'28px', zIndex:9999,
            animation:'slideInRight 0.35s cubic-bezier(0.16,1,0.3,1)' }}
          className="flex items-start gap-3 bg-slate-900 border border-emerald-500/60 text-white px-5 py-4 rounded-2xl shadow-2xl max-w-sm"
        >
          <span className="flex-shrink-0 flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500/20 border border-emerald-400/40 mt-0.5">
            <Bell className="w-4 h-4 text-emerald-400" />
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-black uppercase tracking-widest text-emerald-400 mb-0.5">NEW INSPECTION RECEIVED</p>
            <p className="text-sm font-bold text-white truncate">{newInspectionToast.product_name || 'Packaged Commodity'}</p>
            <p className="text-xs text-slate-400 font-medium mt-0.5">
              By {newInspectionToast.inspector_name || 'Inspector'} · Audit registry updated
            </p>
          </div>
          <button onClick={() => setNewInspectionToast(null)} className="flex-shrink-0 text-slate-500 hover:text-white transition mt-0.5">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      <style>{`
        @keyframes slideInRight { from{opacity:0;transform:translateX(60px)} to{opacity:1;transform:translateX(0)} }
      `}</style>
      
      {/* 1. Header & Privilege Badge (Indian Government Portal Theme) */}
      <div className="bg-gradient-to-r from-[#7a1c1c] via-[#8B1E1E] to-[#601212] text-white p-7 md:p-8 rounded-3xl shadow-xl relative overflow-hidden border border-red-900/50">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-white/5 skew-x-12 pointer-events-none"></div>
        <div className="absolute -left-10 -bottom-10 w-48 h-48 bg-black/10 rounded-full blur-xl pointer-events-none"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-3xl">
            
            {/* Tricolor Accent Pill & Privilege Badges */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center space-x-2 px-3 py-1 bg-black/30 text-white text-xs font-black rounded-lg backdrop-blur-sm border border-white/20">
                <div className="h-2 w-5 rounded flex overflow-hidden">
                  <div className="w-1/3 bg-[#FF9933]"></div>
                  <div className="w-1/3 bg-white"></div>
                  <div className="w-1/3 bg-[#138808]"></div>
                </div>
                <span>DEPARTMENT OF CONSUMER AFFAIRS • LEGAL METROLOGY</span>
              </div>

              <span className="inline-flex items-center space-x-1.5 px-3 py-1 bg-amber-400 text-slate-950 text-xs font-black rounded-lg shadow-sm">
                <Gavel className="w-3.5 h-3.5 text-slate-950" />
                <span>SENIOR ADJUDICATION PRIVILEGES ACTIVE</span>
              </span>

              <span className="inline-flex items-center space-x-1.5 px-3 py-1 bg-white/15 text-white text-xs font-extrabold rounded-lg border border-white/20">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-300" />
                <span>SECTION 36 STATUTORY AUTHORITY</span>
              </span>

              {/* WS Live Indicator */}
              <span className={`inline-flex items-center space-x-1.5 px-3 py-1 text-xs font-extrabold rounded-lg border ${
                wsConnected ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' : 'bg-red-900/30 text-red-300 border-red-600/30'
              }`}>
                {wsConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
                <span>{wsConnected ? 'LIVE' : 'OFFLINE'}</span>
              </span>
            </div>

            {/* Main Header Title */}
            <div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight leading-tight flex items-center gap-3">
                <span>Reviewing Senior Officer Command Center</span>
              </h1>
              <p className="text-sm sm:text-base text-red-100 font-semibold mt-1">
                Adjudicate field package scans, inspect spatial OCR bounding boxes, and execute Section 36 statutory sign-offs under the Legal Metrology Act, 2009.
              </p>
            </div>

            {/* Officer Meta Info Strip */}
            <div className="flex flex-wrap items-center gap-4 text-xs font-bold text-red-100/90 pt-1">
              <div className="flex items-center space-x-1.5 bg-black/20 px-3 py-1 rounded-md">
                <UserCheck className="w-4 h-4 text-amber-300" />
                <span>Officer: <strong className="text-white font-black">{officerName}</strong></span>
              </div>
              <div className="flex items-center space-x-1.5 bg-black/20 px-3 py-1 rounded-md">
                <MapPin className="w-4 h-4 text-red-200" />
                <span>Zone: <span className="text-white font-semibold">{officerZone}</span></span>
              </div>
              <div className="flex items-center space-x-1.5 bg-black/20 px-3 py-1 rounded-md">
                <Layers className="w-4 h-4 text-emerald-300" />
                <span>Rule Engine: <span className="text-white font-mono font-bold">v2.1 (Calibrated)</span></span>
              </div>
            </div>
          </div>

          {/* Quick Action Refresh Button */}
          <div className="flex flex-row lg:flex-col items-center lg:items-end gap-3 flex-shrink-0">
            <button
              onClick={() => fetchDashboardData(true)}
              disabled={refreshing}
              className="px-5 py-3 bg-white hover:bg-slate-100 text-[#7a1c1c] font-black text-xs rounded-xl shadow-lg transition flex items-center space-x-2 border border-white/80 active:scale-95 disabled:opacity-70"
            >
              <RefreshCw className={`w-4 h-4 text-[#7a1c1c] ${refreshing ? 'animate-spin' : ''}`} />
              <span>{refreshing ? 'REFRESHING REGISTRY...' : 'REFRESH AUDIT REGISTRY'}</span>
            </button>

            <a
              href="/api/v1/inspections/latest/report/pdf"
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2.5 bg-black/25 hover:bg-black/40 text-white font-extrabold text-xs rounded-xl transition flex items-center space-x-2 border border-white/20"
            >
              <Download className="w-3.5 h-3.5 text-amber-300" />
              <span>SAMPLE STATUTORY NOTICE</span>
            </a>
          </div>
        </div>
      </div>

      {/* 2. Tri-Role Interconnection Architecture Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
          <div className="flex items-center space-x-2 text-xs font-black text-slate-800 uppercase tracking-wider">
            <Layers className="w-4 h-4 text-[#7a1c1c]" />
            <span>Tri-Role Unified Enforcement Pipeline</span>
          </div>
          <span className="text-xs text-slate-600 font-extrabold bg-slate-100 px-2.5 py-0.5 rounded-full border border-slate-200">
            Operational Workflow Architecture
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          {/* Step 1: Inspector */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 relative group hover:bg-white hover:border-red-200 transition">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-black text-slate-600 uppercase tracking-wide">1. Field Inspector</span>
              <span className="text-[10px] bg-sky-100 text-sky-800 font-extrabold px-2 py-0.5 rounded">Scans & Submits</span>
            </div>
            <p className="text-xs text-slate-600 font-medium leading-snug">
              Captures package imagery, runs OCR/YOLO, and logs raw declarations into central database.
            </p>
            <div className="mt-2 text-xs font-bold text-slate-800 flex items-center justify-between">
              <span>Total Ingested: <strong className="font-mono text-slate-900">{metrics.total}</strong></span>
              <span className="text-[11px] text-slate-600">ID: INS-2026</span>
            </div>
          </div>

          {/* Step 2: Reviewing Officer (Active) */}
          <div className="p-3.5 rounded-xl bg-red-50/70 border-2 border-red-300 relative shadow-sm">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-black text-[#7a1c1c] uppercase tracking-wide flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-600 animate-ping"></span>
                2. Reviewing Officer (You)
              </span>
              <span className="text-[10px] bg-red-600 text-white font-extrabold px-2 py-0.5 rounded">Active Adjudication</span>
            </div>
            <p className="text-xs text-slate-700 font-medium leading-snug">
              Inspects spatial bounding cards, validates Rule 7 font calibration, approves or flags Section 36 orders.
            </p>
            <div className="mt-2 text-xs font-bold text-[#7a1c1c] flex items-center justify-between">
              <span>Pending Review: <strong className="font-mono text-amber-700">{metrics.pending}</strong></span>
              <span>Signed: <strong className="font-mono text-emerald-700">{metrics.signed}</strong></span>
            </div>
          </div>

          {/* Step 3: Admin */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 relative group hover:bg-white hover:border-purple-200 transition">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-black text-slate-600 uppercase tracking-wide">3. Central Admin</span>
              <span className="text-[10px] bg-purple-100 text-purple-800 font-extrabold px-2 py-0.5 rounded">Governance & Rules</span>
            </div>
            <p className="text-xs text-slate-600 font-medium leading-snug">
              Manages RBAC permission matrices and maintains system-wide Rule Engine v2.1 calibration.
            </p>
            <div className="mt-2 text-xs font-bold text-slate-800 flex items-center justify-between">
              <span>Engine Status: <strong className="font-mono text-purple-700">v2.1 ONLINE</strong></span>
              <span className="text-[11px] text-slate-600">ID: ADM-2026</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Key Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        
        {/* Metric 1: Pending Reviews */}
        <div
          onClick={() => { setActiveTab('pending'); setCurrentPage(1); }}
          className={`cursor-pointer p-5 rounded-2xl border transition shadow-sm relative overflow-hidden ${
            activeTab === 'pending'
              ? 'bg-amber-50/80 border-amber-400 ring-2 ring-amber-400/30'
              : 'bg-white border-slate-200 hover:border-amber-300 hover:shadow-md'
          }`}
        >
          <div className="flex items-center justify-between text-xs font-black uppercase tracking-wider text-amber-900">
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-amber-600" />
              Pending Reviews
            </span>
            <span className="text-[10px] px-2 py-0.5 bg-amber-100 text-amber-800 rounded font-black border border-amber-300">
              QUEUE (7B)
            </span>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-3xl sm:text-4xl font-black text-slate-900 font-mono tracking-tight">
              {metrics.pending}
            </div>
            <span className="text-xs font-extrabold text-amber-800 bg-amber-100/80 px-2 py-0.5 rounded">
              Needs Sign-off
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 font-medium">
            Route 7B flagged commodities requiring senior adjudication.
          </p>
        </div>

        {/* Metric 2: Confirmed Violations */}
        <div
          onClick={() => { setActiveTab('violations'); setCurrentPage(1); }}
          className={`cursor-pointer p-5 rounded-2xl border transition shadow-sm relative overflow-hidden ${
            activeTab === 'violations'
              ? 'bg-rose-50/80 border-rose-400 ring-2 ring-rose-400/30'
              : 'bg-white border-slate-200 hover:border-rose-300 hover:shadow-md'
          }`}
        >
          <div className="flex items-center justify-between text-xs font-black uppercase tracking-wider text-rose-900">
            <span className="flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              Confirmed Violations
            </span>
            <span className="text-[10px] px-2 py-0.5 bg-rose-100 text-rose-800 rounded font-black border border-rose-300">
              7B BREACH
            </span>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-3xl sm:text-4xl font-black text-slate-900 font-mono tracking-tight">
              {metrics.violations}
            </div>
            <span className="text-xs font-extrabold text-rose-800 bg-rose-100/80 px-2 py-0.5 rounded">
              Section 36
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 font-medium">
            Non-compliant label declarations flagged under PCR 2011.
          </p>
        </div>

        {/* Metric 3: Compliant Audits */}
        <div
          onClick={() => { setActiveTab('compliant'); setCurrentPage(1); }}
          className={`cursor-pointer p-5 rounded-2xl border transition shadow-sm relative overflow-hidden ${
            activeTab === 'compliant'
              ? 'bg-emerald-50/80 border-emerald-400 ring-2 ring-emerald-400/30'
              : 'bg-white border-slate-200 hover:border-emerald-300 hover:shadow-md'
          }`}
        >
          <div className="flex items-center justify-between text-xs font-black uppercase tracking-wider text-emerald-900">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Compliant Audits
            </span>
            <span className="text-[10px] px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-black border border-emerald-300">
              7A PASSED
            </span>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-3xl sm:text-4xl font-black text-slate-900 font-mono tracking-tight">
              {metrics.compliant}
            </div>
            <span className="text-xs font-extrabold text-emerald-800 bg-emerald-100/80 px-2 py-0.5 rounded">
              Full Clearance
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 font-medium">
            Commodities meeting all mandatory statutory declarations.
          </p>
        </div>

        {/* Metric 4: Signed Section 36 Reports */}
        <div
          onClick={() => { setActiveTab('signed'); setCurrentPage(1); }}
          className={`cursor-pointer p-5 rounded-2xl border transition shadow-sm relative overflow-hidden ${
            activeTab === 'signed'
              ? 'bg-purple-50/80 border-purple-400 ring-2 ring-purple-400/30'
              : 'bg-white border-slate-200 hover:border-purple-300 hover:shadow-md'
          }`}
        >
          <div className="flex items-center justify-between text-xs font-black uppercase tracking-wider text-purple-900">
            <span className="flex items-center gap-1.5">
              <FileCheck className="w-4 h-4 text-purple-600" />
              Signed Sec 36 Reports
            </span>
            <span className="text-[10px] px-2 py-0.5 bg-purple-100 text-purple-800 rounded font-black border border-purple-300">
              OFFICIAL ATTESTED
            </span>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-3xl sm:text-4xl font-black text-slate-900 font-mono tracking-tight">
              {metrics.signed}
            </div>
            <span className="text-xs font-extrabold text-purple-800 bg-purple-100/80 px-2 py-0.5 rounded">
              Legal Notices
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-600 font-medium">
            Statutory certificates and legal orders signed by senior officer.
          </p>
        </div>
      </div>

      {/* 4. Interactive Audit Registry Table Section */}
      <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
        
        {/* Table Top Bar: Title, Search, and Category Dropdown */}
        <div className="p-5 sm:p-6 border-b border-slate-200 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-[#7a1c1c]" />
                <span>Central Packaging Audit Registry</span>
                <span className="text-xs font-bold text-slate-600 bg-slate-100 px-2.5 py-0.5 rounded-full border border-slate-200">
                  {filteredInspections.length} Registered Records
                </span>
              </h2>
              <p className="text-xs text-slate-600 font-semibold mt-0.5">
                Audit entries submitted by field inspectors for statutory review and Section 36 legal order attestation.
              </p>
            </div>

            {/* Filter Tabs */}
            <div className="flex flex-wrap items-center gap-1.5 bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-black">
              {[
                { id: 'all', label: `All (${metrics.total})` },
                { id: 'pending', label: `Pending Review (${metrics.pending})` },
                { id: 'violations', label: `Violations (${metrics.violations})` },
                { id: 'compliant', label: `Compliant (${metrics.compliant})` },
                { id: 'signed', label: `Signed Off (${metrics.signed})` },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => { setActiveTab(tab.id); setCurrentPage(1); }}
                  className={`px-3 py-1.5 rounded-lg transition ${
                    activeTab === tab.id 
                      ? 'bg-[#7a1c1c] text-white shadow-sm' 
                      : 'text-slate-700 hover:text-slate-900 hover:bg-white'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Search & Category Filter Row */}
          <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 text-slate-600 absolute left-3.5 top-3" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                placeholder="Search by Inspection ID, Product Commodity, Inspector, or Location..."
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 placeholder-slate-600 focus:outline-none focus:border-[#7a1c1c] focus:bg-white transition"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-3 top-3 text-slate-600 hover:text-slate-600"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Category Dropdown */}
            <div className="flex items-center space-x-2 w-full sm:w-auto">
              <span className="text-xs font-bold text-slate-600 whitespace-nowrap">Category:</span>
              <select
                value={selectedCategory}
                onChange={(e) => { setSelectedCategory(e.target.value); setCurrentPage(1); }}
                className="bg-slate-50 border border-slate-200 text-xs font-black text-slate-800 rounded-xl px-3 py-2.5 focus:outline-none focus:border-[#7a1c1c] cursor-pointer"
              >
                {categoriesList.map(cat => (
                  <option key={cat} value={cat}>
                    {cat === 'ALL' ? 'All Commodities' : cat}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Audit Registry Table */}
        <div className="overflow-x-auto">
          {loading ? (
            <div className="py-20 text-center text-slate-600 space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-[#7a1c1c]" />
              <p className="text-sm font-black text-slate-700">Loading Central Inspection Registry...</p>
            </div>
          ) : filteredInspections.length === 0 ? (
            <div className="py-16 text-center text-slate-600 space-y-3">
              <div className="w-12 h-12 rounded-full bg-red-50 text-[#7a1c1c] flex items-center justify-center mx-auto border border-red-200">
                <Search className="w-6 h-6" />
              </div>
              <p className="text-sm font-black text-slate-800">No Inspection Records Found</p>
              <p className="text-xs text-slate-600 max-w-sm mx-auto font-medium">
                No entries match the selected tab or search query. Adjust your filter parameters or refresh the registry.
              </p>
              <button
                onClick={() => { setActiveTab('all'); setSearchTerm(''); setSelectedCategory('ALL'); }}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl transition"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-100/80 border-b border-slate-200 text-[11px] font-black uppercase text-slate-600 tracking-wider">
                  <th className="py-3.5 px-4 sm:px-6">Inspection ID</th>
                  <th className="py-3.5 px-4">Product Commodity</th>
                  <th className="py-3.5 px-4">Category</th>
                  <th className="py-3.5 px-4">Field Location</th>
                  <th className="py-3.5 px-4">Submitting Inspector</th>
                  <th className="py-3.5 px-4">Statutory Status</th>
                  <th className="py-3.5 px-4 sm:px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-xs">
                {paginatedInspections.map((item) => {
                  const status = (item.overall_status || '').toUpperCase();
                  const isCompliant = status.includes('7A') || status.includes('COMPLIANT');
                  const isViolation = status.includes('7B') || status.includes('VIOLATION');
                  const hasDecision = Boolean(item.officer_decision);

                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-red-50/40 transition duration-150 group"
                    >
                      {/* 1. Inspection ID */}
                      <td className="py-3.5 px-4 sm:px-6 font-mono font-bold text-slate-900 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          <span className="text-[#7a1c1c] font-black">{item.id}</span>
                          <button
                            onClick={(e) => handleCopyId(item.id, e)}
                            title="Copy Inspection ID"
                            className="text-slate-600 hover:text-slate-600 transition"
                          >
                            {copiedId === item.id ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                        <div className="text-[10px] text-slate-600 font-sans font-medium">
                          {formatDateTime(item.created_at)}
                        </div>
                      </td>

                      {/* 2. Product Commodity */}
                      <td className="py-3.5 px-4 font-bold text-slate-900">
                        <div className="flex items-center space-x-2.5">
                          <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center flex-shrink-0 text-slate-600 overflow-hidden">
                            {item.processed_image_url || item.original_image_url ? (
                              <img
                                src={`http://localhost:8000${item.processed_image_url || item.original_image_url}`}
                                alt="thumb"
                                className="w-full h-full object-cover"
                                onError={(e) => { e.target.style.display = 'none'; }}
                              />
                            ) : (
                              <Scale className="w-4 h-4 text-slate-600" />
                            )}
                          </div>
                          <div>
                            <div className="font-black text-slate-900 max-w-[200px] truncate" title={item.product_name}>
                              {item.product_name || "Packaged Commodity"}
                            </div>
                            <span className="text-[10px] text-slate-600 font-normal">
                              Shape: {item.pdp_shape || 'Rectangular'}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* 3. Category */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="px-2.5 py-1 bg-slate-100 text-slate-700 font-extrabold rounded-md text-[11px] border border-slate-200">
                          {item.category || "Commodity"}
                        </span>
                      </td>

                      {/* 4. Field Location */}
                      <td className="py-3.5 px-4 text-slate-600 font-medium whitespace-nowrap">
                        <div className="flex items-center space-x-1.5 text-xs text-slate-700">
                          <MapPin className="w-3.5 h-3.5 text-slate-600 flex-shrink-0" />
                          <span className="max-w-[170px] truncate" title={item.location}>
                            {item.location || "Central Ministry Enforcement"}
                          </span>
                        </div>
                      </td>

                      {/* 5. Submitting Inspector */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex items-center space-x-1.5">
                          <User className="w-3.5 h-3.5 text-[#7a1c1c]" />
                          <div>
                            <span className="font-bold text-slate-900 block">{item.inspector_name || "Field Inspector"}</span>
                            <span className="text-[10px] text-slate-600 font-mono">ID: {item.inspector_id || "INS-2026"}</span>
                          </div>
                        </div>
                      </td>

                      {/* 6. Dynamic Statutory Status Badge */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="space-y-1">
                          <StatusBadge status={item.overall_status} />
                          {hasDecision && (
                            <div className="text-[10px] font-black text-purple-800 flex items-center space-x-1">
                              <FileCheck className="w-3 h-3 text-purple-600" />
                              <span>Attested: {item.officer_decision}</span>
                            </div>
                          )}
                        </div>
                      </td>

                      {/* 7. Actions */}
                      <td className="py-3.5 px-4 sm:px-6 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => handleOpenAuditView(item)}
                            className="px-3.5 py-1.5 bg-[#7a1c1c] hover:bg-[#8B1E1E] text-white font-black text-xs rounded-xl shadow-sm transition flex items-center space-x-1.5 active:scale-95"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>Audit View</span>
                          </button>

                          <a
                            href={`/api/v1/inspections/${item.id}/report/pdf`}
                            target="_blank"
                            rel="noreferrer"
                            title="Download Official Statutory Notice / Certificate (Section 36 PDF)"
                            className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-[#7a1c1c] rounded-xl border border-slate-200 transition"
                          >
                            <Download className="w-4 h-4" />
                          </a>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Table Footer: Pagination */}
        <div className="p-4 sm:p-5 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 font-semibold">
          <div className="flex items-center space-x-2">
            <span>Showing {Math.min(filteredInspections.length, (currentPage - 1) * itemsPerPage + 1)} to {Math.min(filteredInspections.length, currentPage * itemsPerPage)} of {filteredInspections.length} entries</span>
            <span>•</span>
            <div className="flex items-center space-x-1">
              <span>Show:</span>
              <select
                value={itemsPerPage}
                onChange={(e) => { setItemsPerPage(Number(e.target.value)); setCurrentPage(1); }}
                className="bg-white border border-slate-200 rounded px-2 py-0.5 text-xs font-bold text-slate-800"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-1.5">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-2 rounded-lg border border-slate-200 hover:bg-white disabled:opacity-40 disabled:hover:bg-transparent transition text-slate-700 font-bold"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            
            <span className="px-3 py-1 font-black text-slate-900 bg-white border border-slate-200 rounded-lg">
              Page {currentPage} of {totalPages}
            </span>

            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-2 rounded-lg border border-slate-200 hover:bg-white disabled:opacity-40 disabled:hover:bg-transparent transition text-slate-700 font-bold"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 5. ACTION MODALS / DRAWER: Detailed Inspection Evidence & Adjudication View */}
      {selectedInspection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-6xl max-h-[92vh] flex flex-col overflow-hidden">
            
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-[#7a1c1c] via-[#8B1E1E] to-[#601212] text-white p-5 sm:p-6 flex items-center justify-between border-b border-red-900 flex-shrink-0">
              <div className="space-y-1">
                <div className="flex items-center space-x-2 text-xs font-bold text-red-200">
                  <span className="px-2 py-0.5 bg-black/30 rounded font-mono text-white">
                    {selectedInspection.id}
                  </span>
                  <span>•</span>
                  <span>Submitted by {selectedInspection.inspector_name || "Field Inspector"}</span>
                  <span>•</span>
                  <span>{selectedInspection.category || "Commodity"}</span>
                </div>
                <h3 className="text-xl sm:text-2xl font-black tracking-tight text-white flex items-center gap-2">
                  <span>{selectedInspection.product_name || "Packaged Commodity"}</span>
                </h3>
              </div>

              <div className="flex items-center space-x-2">
                <a
                  href={`/api/v1/inspections/${selectedInspection.id}/report/pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3.5 py-2 bg-white text-[#7a1c1c] hover:bg-slate-100 rounded-xl font-black text-xs transition flex items-center space-x-1.5 shadow"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Export Section 36 PDF</span>
                </a>
                <button
                  onClick={handleCloseModal}
                  className="p-2 bg-black/20 hover:bg-black/40 text-white rounded-xl transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Navigation Tabs inside Modal */}
            <div className="flex items-center space-x-2 px-6 pt-3 bg-slate-100 border-b border-slate-200 flex-shrink-0 overflow-x-auto text-xs font-black">
              <button
                onClick={() => setModalTab('evidence')}
                className={`pb-3 px-4 flex items-center space-x-1.5 border-b-2 transition ${
                  modalTab === 'evidence'
                    ? 'border-[#7a1c1c] text-[#7a1c1c]'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                <Target className="w-4 h-4" />
                <span>Side-by-Side Spatial Evidence & OCR</span>
              </button>

              <button
                onClick={() => setModalTab('declarations')}
                className={`pb-3 px-4 flex items-center space-x-1.5 border-b-2 transition ${
                  modalTab === 'declarations'
                    ? 'border-[#7a1c1c] text-[#7a1c1c]'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                <FileText className="w-4 h-4" />
                <span>5-Section Statutory Matrix</span>
              </button>

              <button
                onClick={() => setModalTab('rules')}
                className={`pb-3 px-4 flex items-center space-x-1.5 border-b-2 transition ${
                  modalTab === 'rules'
                    ? 'border-[#7a1c1c] text-[#7a1c1c]'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Rule Engine (v2.1) & Font Height</span>
              </button>

              <button
                onClick={() => setModalTab('adjudicate')}
                className={`pb-3 px-4 flex items-center space-x-1.5 border-b-2 transition ${
                  modalTab === 'adjudicate'
                    ? 'border-[#7a1c1c] text-[#7a1c1c]'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                <Gavel className="w-4 h-4" />
                <span>Senior Adjudication & Verdict Sign-Off</span>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-5 sm:p-6">
              {modalLoading ? (
                <div className="py-24 text-center text-slate-600 space-y-3">
                  <RefreshCw className="w-8 h-8 animate-spin mx-auto text-[#7a1c1c]" />
                  <p className="font-black text-sm">Loading Full Packaging OCR & Verification Matrix...</p>
                </div>
              ) : (
                <>
                  {/* Action feedback alerts */}
                  {actionSuccessMsg && (
                    <div className="mb-4 p-4 bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs rounded-2xl flex items-center space-x-3 shadow-sm font-bold">
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                      <span>{actionSuccessMsg}</span>
                    </div>
                  )}
                  {actionErrorMsg && (
                    <div className="mb-4 p-4 bg-rose-50 border border-rose-300 text-rose-900 text-xs rounded-2xl flex items-center space-x-3 shadow-sm font-bold">
                      <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
                      <span>{actionErrorMsg}</span>
                    </div>
                  )}

                  {/* TAB 1: SIDE-BY-SIDE SPATIAL EVIDENCE & OCR */}
                  {modalTab === 'evidence' && (
                    <div className="space-y-6">
                      {/* Side-by-side Images Section */}
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                        
                        {/* Left: Original Inspector Capture */}
                        <div className="bg-slate-900 rounded-2xl p-4 text-white flex flex-col justify-between border border-slate-800">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2">
                            <span className="text-xs font-black uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                              <Building2 className="w-4 h-4 text-sky-400" />
                              Inspector Field Capture (Raw)
                            </span>
                            <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                              ORIGINAL
                            </span>
                          </div>
                          <div className="relative flex-1 min-h-[280px] max-h-[340px] flex items-center justify-center bg-slate-950 rounded-xl overflow-hidden p-2">
                            {resolveOriginalImage() ? (
                              <img
                                src={resolveOriginalImage()}
                                alt="Raw Capture"
                                className="max-h-[320px] max-w-full object-contain rounded"
                              />
                            ) : (
                              <div className="text-xs text-slate-600 font-semibold">No raw image uploaded</div>
                            )}
                          </div>
                        </div>

                        {/* Right: Processed / Enhanced with Bounding Boxes */}
                        <div className="bg-slate-900 rounded-2xl p-4 text-white flex flex-col justify-between border border-slate-800">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2">
                            <span className="text-xs font-black uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                              <Target className="w-4 h-4 text-emerald-400" />
                              PaddleOCR / YOLO Spatial Overlay
                            </span>
                            <span className="text-[10px] bg-emerald-950 text-emerald-300 px-2 py-0.5 rounded font-mono border border-emerald-800">
                              {rawBoxes.length} DETECTIONS
                            </span>
                          </div>
                          
                          <div className="relative flex-1 min-h-[280px] max-h-[340px] flex items-center justify-center bg-slate-950 rounded-xl overflow-hidden p-2">
                            {resolveModalImage() ? (
                              <div className="relative inline-block max-h-full max-w-full">
                                <img
                                  src={resolveModalImage()}
                                  alt="Annotated"
                                  className="max-h-[320px] max-w-full object-contain rounded"
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
                                      style={getBoxOverlayStyle(b)}
                                      title={`${b.text || 'Detected text'} (${b.confidence || 90}%)`}
                                    />
                                  );
                                })}
                              </div>
                            ) : (
                              <div className="text-xs text-slate-600 font-semibold">No annotated visual preview</div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Detected Text & Confidence Scores List */}
                      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 sm:p-5 space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <h4 className="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-[#7a1c1c]" />
                            <span>Spatial Declaration Detections & OCR Confidence Scores ({filteredBoxes.length})</span>
                          </h4>
                          
                          <div className="relative w-full sm:w-64">
                            <Search className="w-3.5 h-3.5 text-slate-600 absolute left-2.5 top-2.5" />
                            <input
                              type="text"
                              value={boxSearchTerm}
                              onChange={(e) => setBoxSearchTerm(e.target.value)}
                              placeholder="Filter detected text words..."
                              className="w-full pl-8 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:border-[#7a1c1c]"
                            />
                          </div>
                        </div>

                        {filteredBoxes.length === 0 ? (
                          <p className="text-xs text-slate-600 py-3 font-medium">No spatial bounding box data found for this inspection.</p>
                        ) : (
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-56 overflow-y-auto pr-1">
                            {filteredBoxes.map((b, idx) => {
                              const boxKey = b.id || idx;
                              const isSelected = selectedBoxId === boxKey;
                              const conf = typeof b.confidence === 'number' ? (b.confidence > 1 ? b.confidence : b.confidence * 100) : 90;
                              
                              return (
                                <div
                                  key={boxKey}
                                  onClick={() => setSelectedBoxId(boxKey)}
                                  className={`p-2.5 rounded-xl border transition cursor-pointer text-xs space-y-1 ${
                                    isSelected
                                      ? 'bg-red-50 border-[#7a1c1c] text-[#7a1c1c] shadow-sm'
                                      : 'bg-white border-slate-200 text-slate-800 hover:border-slate-300'
                                  }`}
                                >
                                  <div className="flex items-center justify-between text-[10px]">
                                    <span className="font-mono font-bold text-slate-600">
                                      {b.statutory_tag || `DETECTION #${idx + 1}`}
                                    </span>
                                    <span className={`px-2 py-0.5 rounded font-mono font-black ${
                                      conf >= 90
                                        ? 'bg-emerald-100 text-emerald-800'
                                        : conf >= 75
                                          ? 'bg-amber-100 text-amber-800'
                                          : 'bg-rose-100 text-rose-800'
                                    }`}>
                                      {conf.toFixed(1)}% CONF
                                    </span>
                                  </div>
                                  <div className="font-black text-slate-900 truncate" title={b.text}>
                                    "{b.text || 'N/A'}"
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* TAB 2: 5-SECTION STATUTORY DECLARATIONS MATRIX */}
                  {modalTab === 'declarations' && (
                    <div className="space-y-5">
                      <div className="bg-slate-50 border border-slate-200 p-4 rounded-2xl">
                        <h4 className="text-xs font-black text-slate-900 uppercase tracking-wider mb-2">
                          Rule 6 Mandatory Declarations Evaluation
                        </h4>
                        <p className="text-xs text-slate-600 font-medium leading-relaxed">
                          Under Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011, every pre-packaged commodity must contain the following statutory declarations on the Principal Display Panel (PDP) or package surface.
                        </p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        {/* 1. Name and Address */}
                        <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-black text-slate-900">1. Manufacturer / Packer / Importer</span>
                            <span className="text-[10px] bg-sky-100 text-sky-800 font-extrabold px-2 py-0.5 rounded">Rule 6(1)(a)</span>
                          </div>
                          <div className="text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-100 font-semibold">
                            {modalDetails?.company_profile?.name || modalDetails?.declarations?.manufacturer?.value || "Detected / Verified on packaging"}
                          </div>
                        </div>

                        {/* 2. Generic Name & Net Qty */}
                        <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-black text-slate-900">2. Net Quantity & Common Name</span>
                            <span className="text-[10px] bg-emerald-100 text-emerald-800 font-extrabold px-2 py-0.5 rounded">Rule 6(1)(b)/(c)</span>
                          </div>
                          <div className="text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-100 font-semibold">
                            Quantity: <strong className="text-slate-900 font-black">{modalDetails?.declarations?.net_quantity?.value || modalDetails?.quantity_mpe?.declared_quantity || "Detected"}</strong> • Commodity: {modalDetails?.product_name || "Packaged Food"}
                          </div>
                        </div>

                        {/* 3. MRP Inclusive of all taxes */}
                        <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-black text-slate-900">3. Retail Sale Price (MRP Incl. Taxes)</span>
                            <span className="text-[10px] bg-amber-100 text-amber-800 font-extrabold px-2 py-0.5 rounded">Rule 6(1)(e)</span>
                          </div>
                          <div className="text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-100 font-semibold">
                            {modalDetails?.declarations?.mrp?.value || "₹ Verified on label"} (Inclusive of all taxes clause checked)
                          </div>
                        </div>

                        {/* 4. Dates */}
                        <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-black text-slate-900">4. Month & Year of Manufacture / Expiry</span>
                            <span className="text-[10px] bg-purple-100 text-purple-800 font-extrabold px-2 py-0.5 rounded">Rule 6(1)(d)</span>
                          </div>
                          <div className="text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-100 font-semibold">
                            Mfg: {modalDetails?.declarations?.manufacturing_date?.value || "Detected"} | Expiry: {modalDetails?.declarations?.expiry_date?.value || "Verified"}
                          </div>
                        </div>

                        {/* 5. Consumer Care */}
                        <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2 md:col-span-2">
                          <div className="flex items-center justify-between">
                            <span className="font-black text-slate-900">5. Consumer Care Helpline & Grievance Redressal</span>
                            <span className="text-[10px] bg-rose-100 text-rose-800 font-extrabold px-2 py-0.5 rounded">Rule 6(1)(n)</span>
                          </div>
                          <div className="text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-100 font-semibold">
                            Email: {modalDetails?.customer_care?.email || modalDetails?.declarations?.consumer_care_email?.value || "customer@metrix.gov.in"} • Phone: {modalDetails?.customer_care?.phone || modalDetails?.declarations?.consumer_care_phone?.value || "1800-11-4000"}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 3: RULE ENGINE & FONT HEIGHT CALIBRATION */}
                  {modalTab === 'rules' && (
                    <div className="space-y-5">
                      {/* Rule 7 PDP Font Blueprint */}
                      <div className="p-5 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-2">
                            <Scale className="w-4 h-4 text-[#7a1c1c]" />
                            <span>Rule 7: Principal Display Panel (PDP) Font Height Calibration</span>
                          </h4>
                          <span className="px-2.5 py-0.5 bg-emerald-100 text-emerald-800 rounded font-black text-[10px]">
                            TABLE I & II VALIDATION
                          </span>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                            <span className="text-slate-600 block text-[11px] font-bold">Calculated PDP Area:</span>
                            <strong className="text-slate-900 text-base font-black font-mono">
                              {modalDetails?.pdp_blueprint?.pdp_area_cm2 || 150.0} cm²
                            </strong>
                          </div>
                          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                            <span className="text-slate-600 block text-[11px] font-bold">Measured Numeral Height:</span>
                            <strong className="text-slate-900 text-base font-black font-mono">
                              {modalDetails?.pdp_blueprint?.measured_font_mm || 3.2} mm
                            </strong>
                          </div>
                          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                            <span className="text-slate-600 block text-[11px] font-bold">Statutory Min Height:</span>
                            <strong className="text-emerald-700 text-base font-black font-mono">
                              {modalDetails?.pdp_blueprint?.statutory_min_font_mm || 2.5} mm
                            </strong>
                          </div>
                        </div>
                      </div>

                      {/* Violations / Checks List */}
                      <div className="space-y-3">
                        <h4 className="text-xs font-black text-slate-900 uppercase tracking-wider">
                          Statutory Violations & Automated Rule Engine Diagnostics
                        </h4>

                        {(!modalDetails?.violations || modalDetails.violations.length === 0) ? (
                          <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-xl text-xs font-bold flex items-center space-x-2">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            <span>No critical statutory violations detected by Rule Engine v2.1. All Rule 6 mandatory tags identified.</span>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {modalDetails.violations.map((v, i) => (
                              <div key={i} className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs flex items-start space-x-3 text-rose-950">
                                <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                                <div className="space-y-0.5">
                                  <div className="font-black text-rose-900">
                                    {v.rule_id || 'RULE_VIOLATION'}: {v.target_parameter || v.detected_issue}
                                  </div>
                                  <div className="text-rose-800/90 font-medium">
                                    {v.statutory_reference || "Legal Metrology (Packaged Commodities) Rules, 2011"}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* TAB 4: SENIOR ADJUDICATION & VERDICT SIGN-OFF */}
                  {modalTab === 'adjudicate' && (
                    <div className="space-y-5">
                      <div className="bg-slate-50 border border-slate-200 p-4 rounded-2xl">
                        <h4 className="text-xs font-black text-slate-900 uppercase tracking-wider mb-1 flex items-center gap-2">
                          <Gavel className="w-4 h-4 text-[#7a1c1c]" />
                          <span>Official Legal Adjudication under Section 36</span>
                        </h4>
                        <p className="text-xs text-slate-600 font-medium leading-relaxed">
                          As the Reviewing Senior Officer, your decision here constitutes statutory legal adjudication. Attesting compliance clears the packaging for retail trade; flagging non-compliance issues an actionable notice.
                        </p>
                      </div>

                      {/* Verdict Radio Selector */}
                      <div className="space-y-2">
                        <label className="block text-xs font-black text-slate-900 uppercase">
                          Select Statutory Compliance Verdict:
                        </label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div
                            onClick={() => setAdjudicationVerdict('7A COMPLIANT')}
                            className={`p-4 rounded-xl border-2 cursor-pointer transition flex items-center justify-between ${
                              adjudicationVerdict === '7A COMPLIANT'
                                ? 'border-emerald-500 bg-emerald-50 text-emerald-950 shadow-sm'
                                : 'border-slate-200 hover:border-slate-300 text-slate-700'
                            }`}
                          >
                            <div className="flex items-center space-x-2.5">
                              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                              <div>
                                <strong className="font-black block text-xs">7A: COMPLIANT (Approve)</strong>
                                <span className="text-[11px] text-slate-600">Commodity packaging meets all statutory provisions.</span>
                              </div>
                            </div>
                            <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                              adjudicationVerdict === '7A COMPLIANT' ? 'border-emerald-600 bg-emerald-600' : 'border-slate-400'
                            }`}>
                              {adjudicationVerdict === '7A COMPLIANT' && <div className="w-1.5 h-1.5 rounded-full bg-white"></div>}
                            </div>
                          </div>

                          <div
                            onClick={() => setAdjudicationVerdict('7B VIOLATION')}
                            className={`p-4 rounded-xl border-2 cursor-pointer transition flex items-center justify-between ${
                              adjudicationVerdict === '7B VIOLATION'
                                ? 'border-rose-500 bg-rose-50 text-rose-950 shadow-sm'
                                : 'border-slate-200 hover:border-slate-300 text-slate-700'
                            }`}
                          >
                            <div className="flex items-center space-x-2.5">
                              <AlertTriangle className="w-5 h-5 text-rose-600" />
                              <div>
                                <strong className="font-black block text-xs">7B: VIOLATION (Flag Non-Compliance)</strong>
                                <span className="text-[11px] text-slate-600">Issue statutory notice under Section 36 of 2009 Act.</span>
                              </div>
                            </div>
                            <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                              adjudicationVerdict === '7B VIOLATION' ? 'border-rose-600 bg-rose-600' : 'border-slate-400'
                            }`}>
                              {adjudicationVerdict === '7B VIOLATION' && <div className="w-1.5 h-1.5 rounded-full bg-white"></div>}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Officer Findings Comments */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="block text-xs font-black text-slate-900 uppercase">
                            Official Findings & Reason for Attestation (Mandatory):
                          </label>
                          <span className="text-[10px] text-slate-600 font-bold">Stored in Central Audit Log</span>
                        </div>
                        <textarea
                          rows={4}
                          value={officerComment}
                          onChange={(e) => setOfficerComment(e.target.value)}
                          placeholder="Enter specific statutory findings, observed font height measurements, or legal grounds for adjudication..."
                          className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:border-[#7a1c1c] focus:bg-white transition"
                        />

                        {/* Quick Comment Templates */}
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          <span className="text-[10px] font-bold text-slate-600 uppercase">Quick templates:</span>
                          <button
                            type="button"
                            onClick={() => setOfficerComment("Verified full compliance with PCR 2011 Rules 6 & 7. Label declarations accurate.")}
                            className="text-[10px] font-bold bg-slate-100 hover:bg-slate-200 px-2.5 py-1 rounded text-slate-700"
                          >
                            + Fully Compliant
                          </button>
                          <button
                            type="button"
                            onClick={() => setOfficerComment("Violation under Rule 7 Table I: Font height does not satisfy minimum required area.")}
                            className="text-[10px] font-bold bg-slate-100 hover:bg-slate-200 px-2.5 py-1 rounded text-slate-700"
                          >
                            + Font Height Breach
                          </button>
                          <button
                            type="button"
                            onClick={() => setOfficerComment("Violation under Rule 6(1)(e): MRP missing mandatory 'inclusive of all taxes' declaration.")}
                            className="text-[10px] font-bold bg-slate-100 hover:bg-slate-200 px-2.5 py-1 rounded text-slate-700"
                          >
                            + MRP Tax Missing
                          </button>
                        </div>
                      </div>

                      {/* Action Submission Buttons */}
                      <div className="pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
                        <div className="text-xs text-slate-600 font-bold">
                          Officer: <span className="text-slate-900 font-black">{officerName}</span> ({officerZone})
                        </div>

                        <div className="flex items-center space-x-3">
                          <button
                            type="button"
                            disabled={submittingAction}
                            onClick={() => handleExecuteAdjudication('7B VIOLATION')}
                            className="px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-black text-xs rounded-xl shadow transition flex items-center space-x-1.5 disabled:opacity-50"
                          >
                            <AlertTriangle className="w-4 h-4" />
                            <span>FLAG VIOLATION (7B)</span>
                          </button>

                          <button
                            type="button"
                            disabled={submittingAction}
                            onClick={() => handleExecuteAdjudication('7A COMPLIANT')}
                            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs rounded-xl shadow transition flex items-center space-x-1.5 disabled:opacity-50"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                            <span>APPROVE AS COMPLIANT (7A)</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 sm:p-5 bg-slate-100 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600 font-bold flex-shrink-0">
              <div>
                Statutory Reference: <span className="text-slate-900 font-mono">Sec. 36 Legal Metrology Act, 2009</span>
              </div>
              <button
                onClick={handleCloseModal}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-xl font-black text-xs transition"
              >
                Close Audit View
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

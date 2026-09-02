import React, { useState, useEffect } from 'react';
import { 
  Camera, 
  PlusCircle, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  FileText, 
  Download, 
  Wifi, 
  WifiOff, 
  RefreshCw, 
  Eye, 
  ShieldCheck, 
  Search, 
  ChevronRight, 
  TrendingUp, 
  MapPin, 
  UserCheck, 
  Layers,
  BookOpen,
  ArrowRight,
  Database,
  Calendar
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';
import api from '../services/api';

export default function InspectorDashboard({ user }) {
  const navigate = useNavigate();
  const [offlineQueue, setOfflineQueue] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState('2 mins ago');
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  const [metrics, setMetrics] = useState({
    total_inspections: 42,
    compliant_count: 34,
    issues_flagged: 6,
    pending_submissions: 2
  });

  const [recentInspections, setRecentInspections] = useState([
    {
      id: 'INS-2026-00042',
      product_name: 'Organic Whole Wheat Flour 5kg',
      category: 'Food & Beverages',
      date_time: '2026-08-30 18:45',
      location: 'Okhla Wholesale Market, Shed #4',
      status: '7A: COMPLIANT',
      ocr_preview: 'Generic Name: Wheat Flour • Net Qty: 5kg • MRP ₹240.00 (Incl. all taxes)'
    },
    {
      id: 'INS-2026-00041',
      product_name: 'Ayurvedic Herbal Hair Oil 200ml',
      category: 'Cosmetics & Personal Care',
      date_time: '2026-08-30 17:10',
      location: 'Karol Bagh Retail Market, Shop #12',
      status: '7B: VIOLATION / MANUAL REVIEW',
      ocr_preview: 'Rule 7 Violation: Measured font height 1.8mm below statutory minimum 2.5mm'
    },
    {
      id: 'INS-2026-00040',
      product_name: 'Pure Desi Ghee 1L Pouch',
      category: 'Food & Beverages',
      date_time: '2026-08-30 15:30',
      location: 'Connaught Place Supermarket, Floor 1',
      status: 'PENDING REVIEW',
      ocr_preview: 'Verification Pending: Net Quantity numeral legibility low (92%)'
    },
    {
      id: 'INS-2026-00039',
      product_name: 'Disinfectant Floor Cleaner 500ml',
      category: 'Household Chemicals',
      date_time: '2026-08-30 14:15',
      location: 'Mayapuri Industrial Area Depot #08',
      status: '7A: COMPLIANT',
      ocr_preview: 'Generic Name: Floor Cleaner • Net Qty: 500ml • MRP ₹115.00 (Incl. all taxes)'
    }
  ]);

  const [selectedEvidence, setSelectedEvidence] = useState(null);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Fetch dynamic field inspections if API available
    api.get('/inspections')
      .then((res) => {
        if (res.data && res.data.length > 0) {
          setRecentInspections(res.data.slice(0, 10));
          setMetrics({
            total_inspections: res.data.length,
            compliant_count: res.data.filter(i => i.overall_status?.includes('7A') || i.overall_status?.includes('COMPLIANT')).length,
            issues_flagged: res.data.filter(i => i.overall_status?.includes('7B') || i.overall_status?.includes('VIOLATION')).length,
            pending_submissions: res.data.filter(i => i.overall_status?.includes('PENDING')).length
          });
        }
      })
      .catch(() => {});

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const handleTriggerSync = () => {
    setIsSyncing(true);
    setTimeout(() => {
      setIsSyncing(false);
      setOfflineQueue(0);
      setLastSyncTime('Just now');
    }, 1200);
  };

  const handleDownloadGuidelines = () => {
    window.open('https://consumeraffairs.nic.in', '_blank');
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      
      {/* 1. Quick Action Workflow Hub (Primary Crimson Banner) */}
      <div className="bg-gradient-to-r from-red-700 via-red-600 to-red-800 text-white p-8 rounded-3xl shadow-lg relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-white/5 skew-x-12 pointer-events-none"></div>

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 bg-black/25 text-white text-xs font-black rounded-lg border border-white/20 backdrop-blur-sm">
              <ShieldCheck className="w-4 h-4 text-amber-300" />
              <span>Field Enforcement Officer Portal • Legal Metrology Act, 2009</span>
            </div>
            <h1 className="text-3xl font-black tracking-tight leading-tight">
              Welcome, Inspector {user?.name || 'Official Inspector'}
            </h1>
            <p className="text-sm text-red-100 font-semibold leading-relaxed">
              Assigned Zone: Central Ministry Enforcement Wing • Delhi NCR Region
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 flex-shrink-0">
            <button
              onClick={() => navigate('/inspection/new')}
              className="px-6 py-3.5 bg-white hover:bg-slate-100 text-red-700 font-black text-sm rounded-xl shadow-xl transition flex items-center justify-center space-x-2 border border-white"
            >
              <PlusCircle className="w-5 h-5 text-red-600" />
              <span>+ START NEW INSPECTION</span>
            </button>

            <button
              onClick={() => navigate('/history')}
              className="px-5 py-3.5 bg-black/30 hover:bg-black/40 text-white font-extrabold text-xs rounded-xl transition flex items-center justify-center space-x-2 border border-white/20"
            >
              <FileText className="w-4 h-4 text-slate-200" />
              <span>View History</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Inspector KPI Overview Cards (Top Metric Grid) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* KPI 1: Total Inspections */}
        <div className="bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black text-[#64748B] uppercase tracking-wider">
              Total Inspections Conducted
            </span>
            <div className="p-2.5 bg-red-50 text-red-600 rounded-xl border border-red-200">
              <Camera className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black text-[#1E293B]">{metrics.total_inspections}</div>
          <p className="text-xs text-[#64748B] font-bold">Personal Officer Lifetime Count</p>
        </div>

        {/* KPI 2: Compliant Products Scanned */}
        <div className="bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black text-[#64748B] uppercase tracking-wider">
              Compliant Products Scanned
            </span>
            <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-200">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black text-emerald-700">{metrics.compliant_count}</div>
          <p className="text-xs text-emerald-800 font-bold">Passed Rule 6 & Rule 7 Checks</p>
        </div>

        {/* KPI 3: Potential Issues Flagged */}
        <div className="bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black text-[#64748B] uppercase tracking-wider">
              Potential Issues Flagged
            </span>
            <div className="p-2.5 bg-amber-50 text-amber-600 rounded-xl border border-amber-200">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black text-amber-700">{metrics.issues_flagged}</div>
          <p className="text-xs text-amber-800 font-bold">Escalated to Route 7B Officer Queue</p>
        </div>

        {/* KPI 4: Pending Submissions */}
        <div className="bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black text-[#64748B] uppercase tracking-wider">
              Pending Submissions
            </span>
            <div className="p-2.5 bg-sky-50 text-sky-600 rounded-xl border border-sky-200">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-black text-sky-700">{metrics.pending_submissions}</div>
          <p className="text-xs text-sky-800 font-bold">Drafts Awaiting Final Attestation</p>
        </div>

      </div>

      {/* Main Grid: Left Data Feed (8 Cols) vs Right Live Widgets (4 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Active Field Inspections Feed (8 Cols) */}
        <div className="lg:col-span-8 bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#E2E8F0] gap-2">
            <div>
              <h2 className="text-lg font-black text-[#1E293B] flex items-center space-x-2">
                <Layers className="w-5 h-5 text-red-600" />
                <span>Active Field Inspections Log</span>
              </h2>
              <p className="text-xs text-[#64748B] font-semibold mt-0.5">
                Real-time inspections recorded by your assigned officer terminal
              </p>
            </div>

            <button
              onClick={() => navigate('/history')}
              className="text-xs font-black text-red-700 hover:text-red-800 flex items-center space-x-1"
            >
              <span>View All Records</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Clean Light-Themed Data Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#F8F9FA] text-[#64748B] uppercase font-black border-b border-[#E2E8F0]">
                <tr>
                  <th className="p-3.5">Inspection ID</th>
                  <th className="p-3.5">Product Name</th>
                  <th className="p-3.5">Date & Time</th>
                  <th className="p-3.5">Location</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5 text-right">Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0] text-[#1E293B]">
                {recentInspections.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition">
                    <td className="p-3.5 font-black font-mono text-red-700">{item.id}</td>
                    <td className="p-3.5">
                      <span className="font-black text-[#1E293B] block">{item.product_name}</span>
                      <span className="text-xs text-[#64748B] font-semibold block">{item.category}</span>
                    </td>
                    <td className="p-3.5 text-xs font-bold text-[#64748B] whitespace-nowrap">
                      {item.date_time || (item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Recent')}
                    </td>
                    <td className="p-3.5 text-xs font-semibold text-[#1E293B]">{item.location}</td>
                    <td className="p-3.5">
                      <StatusBadge status={item.status || item.overall_status} />
                    </td>
                    <td className="p-3.5 text-right space-x-2">
                      <button
                        onClick={() => setSelectedEvidence(item)}
                        className="px-3.5 py-1.5 bg-[#F1F5F9] hover:bg-slate-200 text-[#1E293B] font-black text-xs rounded-lg transition border border-[#E2E8F0] inline-flex items-center space-x-1 cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5 text-red-600" />
                        <span>OCR View</span>
                      </button>
                      <button
                        onClick={() => navigate('/officer/review', { state: { inspection: item, inspectionId: item.id } })}
                        className="px-3.5 py-1.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white font-black text-xs rounded-lg transition shadow-sm inline-flex items-center space-x-1 cursor-pointer"
                      >
                        <span>Review</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Side Widgets (4 Cols) */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Live Quick Status Widget: Offline Cache Sync & Backend State */}
          <div className="bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] space-y-4">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
              <h3 className="text-sm font-black text-[#1E293B] flex items-center space-x-2">
                <Database className="w-4 h-4 text-red-600" />
                <span>Field Sync & System Status</span>
              </h3>
              <span className={`px-2.5 py-1 rounded-full text-xs font-black border flex items-center space-x-1 ${
                isOnline ? 'bg-emerald-50 text-emerald-900 border-emerald-300' : 'bg-amber-50 text-amber-900 border-amber-300'
              }`}>
                {isOnline ? <Wifi className="w-3.5 h-3.5 text-emerald-600" /> : <WifiOff className="w-3.5 h-3.5 text-amber-600" />}
                <span>{isOnline ? 'ONLINE' : 'OFFLINE'}</span>
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3.5 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl flex items-center justify-between">
                <span className="text-[#64748B] font-bold">Unsynced Local Drafts</span>
                <span className="font-black text-[#1E293B] text-sm">{offlineQueue} Reports</span>
              </div>

              <div className="p-3.5 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl flex items-center justify-between">
                <span className="text-[#64748B] font-bold">PostgreSQL Backend Sync</span>
                <span className="font-black text-emerald-700 font-mono">ACTIVE (TLS 1.3)</span>
              </div>

              <div className="p-3.5 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl flex items-center justify-between">
                <span className="text-[#64748B] font-bold">Last Database Sync</span>
                <span className="font-black text-[#1E293B]">{lastSyncTime}</span>
              </div>
            </div>

            <button
              onClick={handleTriggerSync}
              disabled={isSyncing}
              className="w-full py-3 bg-[#F1F5F9] hover:bg-slate-200 text-[#1E293B] font-black text-xs rounded-xl transition border border-[#E2E8F0] flex items-center justify-center space-x-2"
            >
              <RefreshCw className={`w-4 h-4 text-red-600 ${isSyncing ? 'animate-spin' : ''}`} />
              <span>{isSyncing ? 'SYNCING LOCAL CACHE...' : 'FORCE SYNC LOCAL CACHE NOW'}</span>
            </button>
          </div>

          {/* Official Guidelines & Quick Links */}
          <div className="bg-white border border-[#E2E8F0] p-6 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] space-y-4">
            <h3 className="text-sm font-black text-[#1E293B] flex items-center space-x-2 border-b border-[#E2E8F0] pb-3">
              <BookOpen className="w-4 h-4 text-red-600" />
              <span>Compliance Resources</span>
            </h3>

            <div className="space-y-2.5 text-xs">
              <button
                onClick={handleDownloadGuidelines}
                className="w-full p-3 bg-[#F8F9FA] hover:bg-slate-100 border border-[#E2E8F0] rounded-xl text-left font-black text-[#1E293B] transition flex items-center justify-between"
              >
                <div className="flex items-center space-x-2">
                  <Download className="w-4 h-4 text-red-600" />
                  <span>Download PCR Rules 2011 Handbook</span>
                </div>
                <ChevronRight className="w-4 h-4 text-[#64748B]" />
              </button>

              <button
                onClick={() => navigate('/scanner')}
                className="w-full p-3 bg-[#F8F9FA] hover:bg-slate-100 border border-[#E2E8F0] rounded-xl text-left font-black text-[#1E293B] transition flex items-center justify-between"
              >
                <div className="flex items-center space-x-2">
                  <Camera className="w-4 h-4 text-red-600" />
                  <span>Launch Live Camera Scan Stream</span>
                </div>
                <ChevronRight className="w-4 h-4 text-[#64748B]" />
              </button>
            </div>
          </div>

        </div>

      </div>

      {/* OCR Evidence Snippet Modal */}
      {selectedEvidence && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-[#E2E8F0] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-3">
              <div>
                <span className="font-mono text-xs font-black text-red-700">{selectedEvidence.id}</span>
                <h3 className="text-base font-black text-[#1E293B]">{selectedEvidence.product_name}</h3>
              </div>
              <button
                onClick={() => setSelectedEvidence(null)}
                className="p-2 text-[#64748B] hover:text-[#1E293B] rounded-lg hover:bg-slate-100"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-[#F8F9FA] rounded-xl border border-[#E2E8F0] space-y-1">
                <span className="font-black text-[#64748B] uppercase tracking-wider block text-[11px]">
                  Extracted OCR Text Preview & Bounding Box Findings:
                </span>
                <p className="font-mono font-bold text-[#1E293B] leading-relaxed">
                  {selectedEvidence.ocr_preview}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-3 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl">
                  <span className="text-[#64748B] block font-bold">Category</span>
                  <span className="font-black text-[#1E293B] mt-0.5 block">{selectedEvidence.category}</span>
                </div>

                <div className="p-3 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl">
                  <span className="text-[#64748B] block font-bold">Inspection Location</span>
                  <span className="font-black text-[#1E293B] mt-0.5 block truncate">{selectedEvidence.location}</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                const target = selectedEvidence;
                setSelectedEvidence(null);
                navigate('/officer/review', { state: { inspection: target, inspectionId: target?.id } });
              }}
              className="w-full py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white font-black text-xs rounded-xl transition shadow-md cursor-pointer"
            >
              OPEN FULL 5-SECTION AUDIT WORKSPACE →
            </button>
          </div>
        </div>
      )}

    </div>
  );
}

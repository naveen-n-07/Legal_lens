import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  FileText, 
  ExternalLink, 
  Download, 
  Clock, 
  ShieldCheck, 
  ShieldAlert, 
  Layers, 
  RefreshCw,
  Building2,
  Calendar,
  Eye,
  CheckCircle2,
  AlertTriangle,
  ArrowUpDown
} from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';
import AuditMobileCard from '../components/AuditMobileCard';
import api from '../services/api';
import { formatDateTime, getRelativeTime } from '../utils/dateUtils';

export default function AuditHistory({ user }) {
  const role = user?.role || 'inspector';
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const [search, setSearch] = useState(searchParams.get('q') || '');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchInspections();
  }, []);

  const fetchInspections = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    
    try {
      const res = await api.get('/inspections');
      if (res.data && res.data.length > 0) {
        setInspections(res.data);
      } else {
        const current = localStorage.getItem('current_inspection');
        if (current) {
          try {
            setInspections([JSON.parse(current)]);
          } catch (e) {
            setInspections([]);
          }
        }
      }
    } catch (e) {
      const current = localStorage.getItem('current_inspection');
      if (current) {
        try {
          setInspections([JSON.parse(current)]);
        } catch (err) {
          setInspections([]);
        }
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const filteredInspections = inspections.filter((item) => {
    const q = search.toLowerCase();
    const matchesSearch = !q ||
      item.product_name?.toLowerCase().includes(q) ||
      item.id?.toLowerCase().includes(q) ||
      item.location?.toLowerCase().includes(q) ||
      item.inspector_name?.toLowerCase().includes(q) ||
      item.category?.toLowerCase().includes(q);

    const matchesStatus = statusFilter === 'ALL' || (item.overall_status || '').includes(statusFilter);
    const matchesCategory = categoryFilter === 'ALL' || item.category === categoryFilter;

    return matchesSearch && matchesStatus && matchesCategory;
  });

  const handleViewInspection = (item) => {
    if (role === 'reviewing_officer' || role === 'admin') {
      navigate('/officer/review', { state: { inspection: item, inspectionId: item.id } });
    } else {
      window.open(`/api/v1/inspections/${item.id}/report/pdf`, '_blank');
    }
  };

  const handleDownloadPDF = (id) => {
    window.open(`/api/v1/inspections/${id}/report/pdf`, '_blank');
  };

  // Metrics
  const totalCount = inspections.length;
  const compliantCount = inspections.filter(i => (i.overall_status || '').includes('7A') || (i.overall_status || '').includes('COMPLIANT')).length;
  const violationCount = inspections.filter(i => (i.overall_status || '').includes('7B') || (i.overall_status || '').includes('VIOLATION')).length;
  const pendingCount = totalCount - compliantCount - violationCount;

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto font-sans">
      
      {/* ── Page Header & Stats Banner ───────────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 bg-red-50 text-[#7A1C1C] border border-red-200 rounded text-2xs font-extrabold uppercase font-mono tracking-wider">
              SECTION 36 CENTRAL AUDIT TRAIL
            </span>
            <span className="text-slate-400">•</span>
            <span className="text-2xs font-bold text-slate-500">Legal Metrology (PC) Rules 2011</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight font-display">
            National Inspection Audit Registry
          </h1>
          <p className="text-xs text-slate-600 font-semibold max-w-2xl leading-relaxed">
            Immutable, centralized statutory inspection evidence ledger recording AI extractions, font calibrations, and reviewing officer adjudications.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start lg:self-center">
          <button
            onClick={() => fetchInspections(true)}
            disabled={refreshing}
            className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs rounded-xl border border-slate-200 shadow-xs transition flex items-center gap-2 active:scale-95 disabled:opacity-70 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-[#7A1C1C]' : ''}`} />
            <span>{refreshing ? 'Refreshing...' : 'Refresh Registry'}</span>
          </button>
        </div>
      </div>

      {/* ── Metric Cards Strip ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-card space-y-1">
          <span className="text-2xs font-black text-slate-400 uppercase tracking-wider block">Total Scans Logged</span>
          <span className="text-2xl font-black font-mono text-slate-900">{totalCount}</span>
          <span className="text-[11px] text-slate-500 block font-medium">All field captures</span>
        </div>

        <div className="bg-white border border-emerald-200/80 p-4 rounded-xl shadow-card space-y-1">
          <span className="text-2xs font-black text-emerald-700 uppercase tracking-wider block">7A Conforming</span>
          <span className="text-2xl font-black font-mono text-emerald-800">{compliantCount}</span>
          <span className="text-[11px] text-emerald-600 block font-medium">Passed statutory checks</span>
        </div>

        <div className="bg-white border border-rose-200/80 p-4 rounded-xl shadow-card space-y-1">
          <span className="text-2xs font-black text-rose-700 uppercase tracking-wider block">7B Violations</span>
          <span className="text-2xl font-black font-mono text-rose-800">{violationCount}</span>
          <span className="text-[11px] text-rose-600 block font-medium">Enforcement action flagged</span>
        </div>

        <div className="bg-white border border-amber-200/80 p-4 rounded-xl shadow-card space-y-1">
          <span className="text-2xs font-black text-amber-700 uppercase tracking-wider block">Pending Review</span>
          <span className="text-2xl font-black font-mono text-amber-800">{pendingCount}</span>
          <span className="text-[11px] text-amber-600 block font-medium">Awaiting senior officer</span>
        </div>
      </div>

      {/* ── Search & Filter Controls Toolbar ─────────────────────────────────── */}
      <div className="p-3.5 bg-white border border-slate-200 rounded-xl shadow-card flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Inspection ID, commodity, location, inspector..."
            className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 font-semibold placeholder:text-slate-400 focus:outline-none focus:border-[#7A1C1C] focus:bg-white transition"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 font-bold focus:outline-none focus:border-[#7A1C1C] cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="7A">7A Compliant</option>
              <option value="7B">7B Violation</option>
              <option value="PENDING">Pending Review</option>
            </select>
          </div>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 font-bold focus:outline-none focus:border-[#7A1C1C] cursor-pointer"
          >
            <option value="ALL">All Categories</option>
            <option value="Packaged Food">Packaged Food</option>
            <option value="Beverages">Beverages</option>
            <option value="Personal Care">Personal Care</option>
            <option value="General Commodity">General Commodity</option>
          </select>
        </div>
      </div>

      {/* ── Mobile Audit Card Feed (Screens < 768px) ────────────────────── */}
      <div className="md:hidden space-y-3">
        {loading ? (
          <div className="p-8 text-center text-slate-500 font-bold space-y-2 bg-white rounded-2xl border border-slate-200 shadow-sm">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-[#7A1C1C]" />
            <p className="text-xs">Loading national inspection records...</p>
          </div>
        ) : filteredInspections.length > 0 ? (
          filteredInspections.map((item) => (
            <AuditMobileCard
              key={item.id}
              item={item}
              role={role}
              onView={handleViewInspection}
              onDownload={handleDownloadPDF}
            />
          ))
        ) : (
          <div className="p-8 text-center text-slate-400 font-semibold space-y-2 bg-white rounded-2xl border border-slate-200">
            <Clock className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="font-bold text-slate-700 text-sm">No inspection records match your query.</p>
            <p className="text-2xs text-slate-400">Try adjusting your search keywords or resetting filters.</p>
          </div>
        )}
      </div>

      {/* ── Data-Dense Widescreen Table (Screens >= 768px) ──────────────────── */}
      <div className="hidden md:block bg-white border border-slate-200 rounded-xl overflow-hidden shadow-card">
        <div className="overflow-x-auto max-h-[620px] overflow-y-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/90 text-slate-600 uppercase font-black tracking-wider border-b border-slate-200 sticky top-0 z-10 backdrop-blur-md">
              <tr>
                <th className="p-3.5 pl-4 w-44">Inspection ID</th>
                <th className="p-3.5">Commodity Name</th>
                <th className="p-3.5">Category</th>
                <th className="p-3.5">Timestamp & Location</th>
                <th className="p-3.5">Inspector / Officer</th>
                <th className="p-3.5">Statutory Verdict</th>
                <th className="p-3.5 pr-4 text-right">Official Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={7} className="p-16 text-center text-slate-500 font-bold space-y-2">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-[#7A1C1C]" />
                    <p className="text-xs">Loading national inspection records from SQLite database...</p>
                  </td>
                </tr>
              ) : filteredInspections.length > 0 ? (
                filteredInspections.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 transition-colors duration-150 align-middle">
                    
                    {/* 1. ID */}
                    <td className="p-3.5 pl-4 font-mono font-black text-slate-900 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span className="px-2 py-0.5 bg-slate-100 text-[#7A1C1C] border border-slate-200 rounded font-mono text-2xs">
                          {item.id}
                        </span>
                      </div>
                    </td>

                    {/* 2. Product Name */}
                    <td className="p-3.5 font-bold text-slate-900 max-w-[200px]">
                      <div className="truncate font-black text-slate-900" title={item.product_name}>
                        {item.product_name || "Packaged Commodity"}
                      </div>
                      {item.brand_name && (
                        <div className="text-[11px] text-slate-500 font-semibold truncate">
                          Brand: {item.brand_name}
                        </div>
                      )}
                    </td>

                    {/* 3. Category */}
                    <td className="p-3.5 text-slate-600 font-bold whitespace-nowrap">
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md border border-slate-200 text-2xs">
                        {item.category || "General"}
                      </span>
                    </td>

                    {/* 4. Timestamp & Location */}
                    <td className="p-3.5 text-slate-600 font-semibold whitespace-nowrap">
                      <div className="font-mono text-2xs text-slate-700">
                        {item.created_at ? formatDateTime(item.created_at) : "Verified in Field"}
                      </div>
                      <div className="text-[11px] text-slate-400 font-medium truncate max-w-[160px]">
                        {item.location || "Northern Zonal Office"}
                      </div>
                    </td>

                    {/* 5. Inspector */}
                    <td className="p-3.5 whitespace-nowrap">
                      <div className="font-black text-slate-800 text-xs">
                        {item.inspector_name || "Field Enforcement Inspector"}
                      </div>
                      {item.officer_decision && (
                        <div className="text-[11px] text-emerald-700 font-bold flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Adjudicated: {item.officer_decision}</span>
                        </div>
                      )}
                    </td>

                    {/* 6. Status Chip */}
                    <td className="p-3.5 whitespace-nowrap">
                      <StatusBadge status={item.overall_status} />
                    </td>

                    {/* 7. Action Buttons */}
                    <td className="p-3.5 pr-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleViewInspection(item)}
                          className="px-3 py-1.5 bg-[#7A1C1C] hover:bg-[#631515] text-white rounded-lg font-black text-2xs transition-all shadow-xs flex items-center gap-1 cursor-pointer hover:-translate-y-0.5"
                          title="Open full inspection and spatial evidence"
                        >
                          <Eye className="w-3 h-3" />
                          <span>{role === 'inspector' ? 'View PDF' : 'Audit Case'}</span>
                        </button>
                        
                        <button
                          onClick={() => handleDownloadPDF(item.id)}
                          title="Export Section 36 Adjudication PDF"
                          className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition border border-slate-200 cursor-pointer"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>

                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="p-16 text-center text-slate-400 font-semibold space-y-2">
                    <Clock className="w-8 h-8 text-slate-300 mx-auto" />
                    <p className="font-bold text-slate-700 text-sm">No statutory inspection records match your query.</p>
                    <p className="text-2xs text-slate-400">Try adjusting your search keywords or resetting filters.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer Summary */}
        <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between text-2xs text-slate-500 font-bold gap-2">
          <span>
            Showing <strong className="text-slate-800">{filteredInspections.length}</strong> of <strong className="text-slate-800">{totalCount}</strong> inspection records
          </span>
          <span className="font-mono text-slate-400">
            METRIX-LM Section 36 Record Registry • High Availability
          </span>
        </div>
      </div>

    </div>
  );
}

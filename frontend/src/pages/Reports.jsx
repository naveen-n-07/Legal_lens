/**
 * Reports.jsx — METRIX-LM Analytics & Report Export Centre
 * ══════════════════════════════════════════════════════════
 * Fully role-aware reporting module:
 *   - Admin    : Full national audit PDF + CSV of all inspections
 *   - Inspector: PDF of their own scans only + CSV of own records
 *   - Officer  : PDF of reviewed/pending cases + adjudication CSV
 *
 * PDF downloads proxy through /api/v1/reports/{id}/pdf (backend).
 * CSV is generated client-side from the inspections list.
 */

import React, { useState, useEffect } from 'react';
import {
  FileText, Download, RefreshCw, Search, Filter,
  CheckCircle2, AlertTriangle, Clock, BarChart3,
  FileSpreadsheet, ShieldCheck, Package, TrendingUp,
  AlertCircle, ChevronDown, X
} from 'lucide-react';
import api from '../services/api';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmtDate = (ts) => {
  if (!ts) return '—';
  try { return new Date(ts).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }); }
  catch { return ts; }
};

const StatusChip = ({ status = '' }) => {
  const s = status.toUpperCase();
  if (s.includes('7A') || s.includes('COMPLIANT'))
    return <span className="px-2 py-0.5 text-[10px] font-black bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md">7A COMPLIANT</span>;
  if (s.includes('7B') || s.includes('VIOLATION'))
    return <span className="px-2 py-0.5 text-[10px] font-black bg-rose-50 text-rose-700 border border-rose-200 rounded-md">7B VIOLATION</span>;
  return <span className="px-2 py-0.5 text-[10px] font-black bg-amber-50 text-amber-700 border border-amber-200 rounded-md">PENDING</span>;
};

// ─── CSV Export ───────────────────────────────────────────────────────────────

const exportCSV = (rows, filename) => {
  const headers = [
    'Inspection ID', 'Product Name', 'Category', 'Location',
    'Inspector Name', 'Status', 'Compliance %', 'Route 7B',
    'Officer Decision', 'Officer Name', 'Scan Date'
  ];
  const csvRows = [
    headers.join(','),
    ...rows.map(r => [
      `"${r.id || ''}"`,
      `"${r.product_name || ''}"`,
      `"${r.category || ''}"`,
      `"${r.location || ''}"`,
      `"${r.inspector_name || ''}"`,
      `"${r.overall_status || ''}"`,
      `"${r.overall_confidence || ''}"`,
      r.route_7b_triggered ? 'YES' : 'NO',
      `"${r.officer_decision || ''}"`,
      `"${r.officer_name || ''}"`,
      `"${fmtDate(r.created_at)}"`,
    ].join(','))
  ];
  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = filename;
  a.click(); URL.revokeObjectURL(url);
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export default function Reports({ user }) {
  const role = user?.role || 'inspector';
  const userId = user?.id || '';

  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [downloading, setDownloading] = useState('');
  const [toast, setToast] = useState('');

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(''), 4000); };

  // ─── Fetch inspections ──────────────────────────────────────────────────────
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await api.get('/inspections');
        setInspections(Array.isArray(res.data) ? res.data : []);
      } catch {
        setInspections([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // ─── Role-scoped data ───────────────────────────────────────────────────────
  const myInspections = inspections.filter(i => {
    if (role === 'admin') return true;
    if (role === 'inspector') return i.inspector_id === userId || i.inspector_name === user?.name;
    if (role === 'reviewing_officer') return true; // officers see all
    return true;
  });

  // ─── Filtered list for the table ───────────────────────────────────────────
  const filtered = myInspections.filter(i => {
    const q = search.toLowerCase();
    const matchSearch = !q ||
      (i.id || '').toLowerCase().includes(q) ||
      (i.product_name || '').toLowerCase().includes(q) ||
      (i.location || '').toLowerCase().includes(q) ||
      (i.inspector_name || '').toLowerCase().includes(q);
    const s = (i.overall_status || '').toUpperCase();
    const matchStatus = statusFilter === 'ALL' ? true
      : statusFilter === '7A' ? (s.includes('7A') || s.includes('COMPLIANT'))
      : statusFilter === '7B' ? (s.includes('7B') || s.includes('VIOLATION'))
      : statusFilter === 'PENDING' ? (!i.officer_decision && s === 'PENDING')
      : true;
    return matchSearch && matchStatus;
  });

  // ─── Stats ──────────────────────────────────────────────────────────────────
  const total = myInspections.length;
  const compliant = myInspections.filter(i => {
    const s = (i.overall_status || '').toUpperCase();
    return s.includes('7A') || s.includes('COMPLIANT');
  }).length;
  const violations = myInspections.filter(i => {
    const s = (i.overall_status || '').toUpperCase();
    return s.includes('7B') || s.includes('VIOLATION');
  }).length;
  const pending = myInspections.filter(i => !i.officer_decision && (i.overall_status || '').toUpperCase() === 'PENDING').length;
  const complianceRate = total ? ((compliant / total) * 100).toFixed(1) : '0.0';

  // ─── PDF Download ────────────────────────────────────────────────────────────
  const handleDownloadPDF = async (inspId, label = '') => {
    const id = inspId || (myInspections[0]?.id) || 'INS-2026-SUMMARY';
    setDownloading(id);
    try {
      const token = localStorage.getItem('metrix_token') || '';
      const url = `/api/v1/reports/${id}/pdf`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `METRIX_LM_Audit_${id}_${new Date().toISOString().slice(0,10)}.pdf`;
      link.click();
      showToast(`PDF exported: ${label || id}`);
    } catch (err) {
      showToast('PDF generation failed. Please try again.');
    } finally {
      setDownloading('');
    }
  };

  // ─── CSV Download ────────────────────────────────────────────────────────────
  const handleExportCSV = (scope = 'all') => {
    const rows = scope === 'violations'
      ? myInspections.filter(i => (i.overall_status || '').toUpperCase().includes('7B'))
      : scope === 'pending'
      ? myInspections.filter(i => !i.officer_decision)
      : myInspections;

    if (rows.length === 0) { showToast('No records available for this export.'); return; }

    const roleLabel = role === 'admin' ? 'National' : role === 'reviewing_officer' ? 'Officer' : 'Inspector';
    const filename = `METRIX_LM_${roleLabel}_${scope}_${new Date().toISOString().slice(0,10)}.csv`;
    exportCSV(rows, filename);
    showToast(`CSV exported: ${rows.length} records`);
  };

  // ─── Role-aware header label ─────────────────────────────────────────────────
  const roleConfig = {
    admin: {
      title: 'National Enforcement Analytics & Export',
      subtitle: 'Complete national audit data across all field inspectors and reviewing officers.',
      badge: 'ADMIN · FULL ACCESS',
      badgeColor: 'bg-purple-100 text-purple-800 border-purple-300',
    },
    reviewing_officer: {
      title: 'Adjudication Analytics & Report Export',
      subtitle: 'Export Section 36 adjudication records, violation certificates and officer sign-off audit trail.',
      badge: 'REVIEWING OFFICER',
      badgeColor: 'bg-amber-100 text-amber-800 border-amber-300',
    },
    inspector: {
      title: 'Field Inspection Reports & Analytics',
      subtitle: 'Download PDF certificates and CSV data for your submitted field inspection records.',
      badge: 'FIELD INSPECTOR',
      badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    },
  };
  const cfg = roleConfig[role] || roleConfig.inspector;

  return (
    <div className="min-h-screen bg-slate-50 font-sans">

      {/* Toast */}
      {toast && (
        <div style={{ position:'fixed', bottom:24, right:24, zIndex:9999 }}
          className="flex items-center gap-3 bg-slate-900 border border-emerald-500/50 text-white px-5 py-3.5 rounded-2xl shadow-2xl max-w-sm text-sm font-semibold">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{toast}</span>
          <button onClick={() => setToast('')} className="ml-2 text-white/50 hover:text-white"><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      {/* ── Page Header ─────────────────────────────────────────────────────── */}
      <div className="bg-gradient-to-r from-[#7a1c1c] via-[#8B1E1E] to-[#601212] text-white px-6 md:px-8 py-6 shadow-xl">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-black/30 text-white text-xs font-black rounded-lg border border-white/20">
                <div className="h-2 w-5 rounded flex overflow-hidden">
                  <div className="w-1/3 bg-[#FF9933]" /><div className="w-1/3 bg-white" /><div className="w-1/3 bg-[#138808]" />
                </div>
                DEPT. OF CONSUMER AFFAIRS · LEGAL METROLOGY
              </div>
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-black rounded-lg border ${cfg.badgeColor}`}>
                <ShieldCheck className="w-3.5 h-3.5" /> {cfg.badge}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight">{cfg.title}</h1>
            <p className="text-sm text-red-100 font-semibold">{cfg.subtitle}</p>
          </div>

          <div className="flex items-center gap-2 text-xs font-bold text-red-100/80 bg-black/20 px-4 py-2 rounded-xl border border-white/10 self-start">
            <BarChart3 className="w-4 h-4 text-amber-300" />
            <span>{total} total records · {complianceRate}% compliance rate</span>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-7 space-y-6">

        {/* ── KPI Strip ───────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Total Inspections', value: total, icon: Package, color: 'bg-slate-50 border-slate-200 text-slate-800' },
            { label: '7A Compliant', value: compliant, icon: CheckCircle2, color: 'bg-emerald-50 border-emerald-200 text-emerald-800' },
            { label: '7B Violations', value: violations, icon: AlertTriangle, color: 'bg-rose-50 border-rose-200 text-rose-800' },
            { label: 'Pending Review', value: pending, icon: Clock, color: 'bg-amber-50 border-amber-200 text-amber-800' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className={`border p-4 rounded-2xl shadow-sm ${color}`}>
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-wider mb-2 opacity-70">
                <span>{label}</span><Icon className="w-3.5 h-3.5" />
              </div>
              <div className="text-3xl font-black font-mono">{loading ? '…' : value}</div>
            </div>
          ))}
        </div>

        {/* ── Export Action Cards ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">

          {/* PDF — Latest / Summary */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-sm hover:shadow-md transition-shadow">
            <div className="p-3 bg-red-50 text-red-700 rounded-xl border border-red-200 w-fit">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-black text-slate-900 text-base">
                {role === 'admin' ? 'National Audit Certificate (PDF)' : 'My Latest Inspection PDF'}
              </h3>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                {role === 'admin'
                  ? 'Generates the latest official statutory audit certificate with government headings, rule matrices and officer signatures.'
                  : role === 'reviewing_officer'
                  ? 'Downloads the PDF certificate for the latest inspection case in the adjudication registry.'
                  : 'Downloads the official PDF certificate for your most recent field inspection scan.'}
              </p>
            </div>
            <button
              onClick={() => handleDownloadPDF(myInspections[0]?.id, 'Latest Inspection')}
              disabled={!!downloading || loading || myInspections.length === 0}
              className="w-full py-3 bg-gradient-to-r from-[#7a1c1c] to-red-700 hover:from-red-700 hover:to-red-800 disabled:opacity-50 text-white font-black text-xs rounded-xl transition shadow flex items-center justify-center gap-2 active:scale-95">
              {downloading === myInspections[0]?.id
                ? <><RefreshCw className="w-4 h-4 animate-spin" /> GENERATING...</>
                : <><Download className="w-4 h-4" /> EXPORT LATEST PDF</>}
            </button>
          </div>

          {/* CSV — All records */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-sm hover:shadow-md transition-shadow">
            <div className="p-3 bg-emerald-50 text-emerald-700 rounded-xl border border-emerald-200 w-fit">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-black text-slate-900 text-base">Full Audit CSV Dataset</h3>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                {role === 'admin'
                  ? 'Exports all inspection records across every inspector — ID, product, status, compliance %, officer decision, and timestamps.'
                  : role === 'reviewing_officer'
                  ? 'Exports all inspection records with officer adjudication decisions and sign-off timestamps.'
                  : 'Exports all your submitted inspection records with compliance status and extracted declarations.'}
              </p>
            </div>
            <button
              onClick={() => handleExportCSV('all')}
              disabled={loading || myInspections.length === 0}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-black text-xs rounded-xl transition shadow flex items-center justify-center gap-2 active:scale-95">
              <Download className="w-4 h-4" /> EXPORT CSV ({myInspections.length} records)
            </button>
          </div>

          {/* CSV — Violations only */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-sm hover:shadow-md transition-shadow">
            <div className="p-3 bg-rose-50 text-rose-700 rounded-xl border border-rose-200 w-fit">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-black text-slate-900 text-base">Violations-Only CSV Export</h3>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                Exports only the 7B violation records requiring enforcement action — ideal for generating statutory notices under the Legal Metrology Act, 2009.
              </p>
            </div>
            <button
              onClick={() => handleExportCSV('violations')}
              disabled={loading || violations === 0}
              className="w-full py-3 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white font-black text-xs rounded-xl transition shadow flex items-center justify-center gap-2 active:scale-95">
              <Download className="w-4 h-4" /> EXPORT VIOLATIONS ({violations})
            </button>
          </div>

        </div>

        {/* ── Per-Inspection PDF Download Table ──────────────────────────────── */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 px-5 py-4 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#7a1c1c]" />
              <span className="text-xs font-black text-slate-800 uppercase tracking-wider">
                Inspection Records — Select to Download PDF
              </span>
              <span className="ml-2 px-2 py-0.5 text-[10px] bg-slate-100 text-slate-600 border border-slate-200 rounded font-black">
                {filtered.length} shown
              </span>
            </div>
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input value={search} onChange={e => setSearch(e.target.value)}
                  placeholder="Search ID, product, location..."
                  className="pl-7 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-200 w-52" />
              </div>
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                className="px-2 py-1.5 text-xs border border-slate-200 rounded-lg font-bold text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-200">
                <option value="ALL">All Statuses</option>
                <option value="7A">7A Compliant</option>
                <option value="7B">7B Violation</option>
                <option value="PENDING">Pending</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10">
                <tr className="bg-slate-100 text-slate-600 font-black uppercase tracking-wider border-b border-slate-200">
                  <th className="p-3 text-left">Inspection ID</th>
                  <th className="p-3 text-left">Product</th>
                  <th className="p-3 text-left">Inspector</th>
                  <th className="p-3 text-left">Location</th>
                  <th className="p-3 text-center">Status</th>
                  <th className="p-3 text-center">Scan Date</th>
                  <th className="p-3 text-right">PDF</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading && (
                  <tr><td colSpan={7} className="p-10 text-center text-slate-400">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2" />
                    Loading inspection records…
                  </td></tr>
                )}
                {!loading && filtered.length === 0 && (
                  <tr><td colSpan={7} className="p-10 text-center text-slate-400 font-medium">
                    <Clock className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    {myInspections.length === 0
                      ? 'No inspection records found. Perform a field scan to generate your first report.'
                      : 'No records match the current filter.'}
                  </td></tr>
                )}
                {!loading && filtered.map(item => (
                  <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-3 font-mono font-black text-[10px] text-[#7a1c1c] max-w-[130px] truncate" title={item.id}>{item.id}</td>
                    <td className="p-3 font-bold text-slate-900 max-w-[130px] truncate" title={item.product_name}>{item.product_name || '—'}</td>
                    <td className="p-3 text-slate-600 max-w-[110px] truncate">{item.inspector_name || '—'}</td>
                    <td className="p-3 text-slate-500 max-w-[110px] truncate">{item.location || '—'}</td>
                    <td className="p-3 text-center"><StatusChip status={item.overall_status} /></td>
                    <td className="p-3 text-center text-slate-400 font-mono text-[10px]">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString('en-IN') : '—'}
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleDownloadPDF(item.id, item.product_name)}
                        disabled={downloading === item.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#7a1c1c] hover:bg-[#601212] disabled:opacity-60 text-white font-black text-[10px] rounded-lg transition shadow active:scale-95">
                        {downloading === item.id
                          ? <RefreshCw className="w-3 h-3 animate-spin" />
                          : <Download className="w-3 h-3" />}
                        PDF
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}

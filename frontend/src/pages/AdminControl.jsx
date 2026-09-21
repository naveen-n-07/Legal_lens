/**
 * AdminControl.jsx — METRIX-LM Admin Command & Control Dashboard
 * ═══════════════════════════════════════════════════════════════
 * Three-panel tabbed dashboard:
 *   Tab 1 – Command Center (KPI telemetry + live stats)
 *   Tab 2 – Rule Engine Studio (versioning, parameter editing, sync)
 *   Tab 3 – Inspector Work Assignment & Dispatch
 *   Tab 4 – User Accounts & RBAC Matrix
 *   Tab 5 – Global Audit Log Stream
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  ShieldCheck, Users, Gavel, History, UserPlus, CheckCircle2,
  AlertCircle, Search, RefreshCw, Lock, BarChart3, Activity,
  Zap, Database, GitBranch, AlertTriangle, FileText, MapPin,
  UserCheck, Clock, ChevronDown, ChevronRight, X, Eye,
  ArrowUpRight, Settings, Layers, Target, Cpu, Globe,
  BookOpen, Award, Bell, TrendingUp, Package, CheckSquare,
  XCircle, Wifi, Edit3, Save, RotateCcw, Send, Filter,
  Download, Copy, Check, Info, Trash2
} from 'lucide-react';
import {
  fetchAllUsers, createUser, updateUserRole,
  fetchAllRules, toggleRuleStatus, updateRuleParam, syncRuleVersion,
  fetchInspectionsSummary, fetchAuditLogs, fetchInspections, assignWork, clearSystemLogs
} from '../services/adminService';
import { formatDateTime, getRelativeTime, parseServerDate } from '../utils/dateUtils';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmtDate = (ts) => {
  if (!ts) return '—';
  return formatDateTime(ts);
};

const relTime = (ts) => {
  if (!ts) return '';
  return getRelativeTime(ts);
};

const RoleBadge = ({ role }) => {
  const map = {
    admin: 'bg-purple-100 text-purple-800 border-purple-300',
    reviewing_officer: 'bg-amber-100 text-amber-800 border-amber-300',
    inspector: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  };
  const labels = { admin: 'Admin', reviewing_officer: 'Rev. Officer', inspector: 'Inspector' };
  return (
    <span className={`px-2.5 py-0.5 text-[11px] font-black rounded-md uppercase tracking-wider border ${map[role] || 'bg-slate-100 text-slate-700 border-slate-300'}`}>
      {labels[role] || role}
    </span>
  );
};

const StatusChip = ({ status }) => {
  const s = (status || '').toUpperCase();
  if (s.includes('7A') || s.includes('COMPLIANT'))
    return <span className="px-2 py-0.5 text-[10px] font-black bg-emerald-50 text-emerald-700 border border-emerald-200 rounded">7A COMPLIANT</span>;
  if (s.includes('7B') || s.includes('VIOLATION'))
    return <span className="px-2 py-0.5 text-[10px] font-black bg-rose-50 text-rose-700 border border-rose-200 rounded">7B VIOLATION</span>;
  return <span className="px-2 py-0.5 text-[10px] font-black bg-amber-50 text-amber-700 border border-amber-200 rounded">PENDING</span>;
};

const Toast = ({ msg, type = 'success', onClose }) => {
  if (!msg) return null;
  const styles = {
    success: 'bg-emerald-900 border-emerald-500/60 text-emerald-300',
    error:   'bg-rose-900 border-rose-500/60 text-rose-300',
    info:    'bg-slate-800 border-slate-500/60 text-slate-300',
  };
  const Icon = type === 'success' ? CheckCircle2 : type === 'error' ? AlertCircle : Info;
  return (
    <div style={{ position:'fixed', bottom:28, right:28, zIndex:9999,
      animation:'slideInRight 0.3s cubic-bezier(0.16,1,0.3,1)' }}
      className={`flex items-start gap-3 border px-5 py-4 rounded-2xl shadow-2xl max-w-sm ${styles[type]}`}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <p className="text-sm font-semibold text-white flex-1">{msg}</p>
      <button onClick={onClose} className="flex-shrink-0 text-white/50 hover:text-white"><X className="w-4 h-4" /></button>
      <style>{`@keyframes slideInRight{from{opacity:0;transform:translateX(60px)}to{opacity:1;transform:translateX(0)}}`}</style>
    </div>
  );
};

const ConfirmModal = ({ title, body, onConfirm, onCancel, confirmLabel = 'Confirm', danger = false }) => (
  <div className="fixed inset-0 z-[9998] flex items-center justify-center bg-black/60 backdrop-blur-sm">
    <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full mx-4 p-6 space-y-5">
      <div className="flex items-start gap-3">
        <AlertTriangle className={`w-6 h-6 flex-shrink-0 mt-0.5 ${danger ? 'text-rose-600' : 'text-amber-500'}`} />
        <div>
          <h3 className="font-black text-slate-900 text-base">{title}</h3>
          <p className="text-sm text-slate-600 mt-1">{body}</p>
        </div>
      </div>
      <div className="flex justify-end gap-3">
        <button onClick={onCancel}
          className="px-4 py-2 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-300 transition">
          Cancel
        </button>
        <button onClick={onConfirm}
          className={`px-5 py-2 text-xs font-black text-white rounded-lg transition shadow ${danger ? 'bg-rose-600 hover:bg-rose-700' : 'bg-[#7a1c1c] hover:bg-[#601212]'}`}>
          {confirmLabel}
        </button>
      </div>
    </div>
  </div>
);

// ─── KPI Metric Card ──────────────────────────────────────────────────────────

const KpiCard = ({ icon: Icon, label, value, sub, color = 'red', trend }) => {
  const colors = {
    red:    { bg: 'bg-red-50',     text: 'text-[#7a1c1c]',  border: 'border-red-200',    icon: 'text-[#7a1c1c]' },
    green:  { bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200', icon: 'text-emerald-600' },
    amber:  { bg: 'bg-amber-50',   text: 'text-amber-800',   border: 'border-amber-200',   icon: 'text-amber-600' },
    purple: { bg: 'bg-purple-50',  text: 'text-purple-800',  border: 'border-purple-200',  icon: 'text-purple-600' },
    slate:  { bg: 'bg-slate-50',   text: 'text-slate-800',   border: 'border-slate-200',   icon: 'text-slate-600' },
  };
  const c = colors[color] || colors.red;
  return (
    <div className={`${c.bg} border ${c.border} p-5 rounded-2xl space-y-2 hover:shadow-md transition-shadow`}>
      <div className="flex items-center justify-between">
        <span className={`text-[10px] font-black uppercase tracking-widest ${c.text}`}>{label}</span>
        <Icon className={`w-4 h-4 ${c.icon}`} />
      </div>
      <div className={`text-3xl font-black font-mono tracking-tight ${c.text}`}>{value ?? '—'}</div>
      {sub && <p className="text-[11px] text-slate-500 font-medium">{sub}</p>}
      {trend !== undefined && (
        <div className="flex items-center gap-1 text-[10px] font-bold text-emerald-600">
          <TrendingUp className="w-3 h-3" /><span>{trend}</span>
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export default function AdminControl({ user }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [toast, setToast] = useState({ msg: '', type: 'success' });
  const [confirm, setConfirm] = useState(null);

  // Data state
  const [users, setUsers] = useState([]);
  const [rules, setRules] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [summary, setSummary] = useState(null);
  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState({});
  const [refreshing, setRefreshing] = useState(false);

  // Toast helper
  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast({ msg: '', type: 'success' }), 5000);
  };

  // ─ Load data on tab switch ─────────────────────────────────────────────────
  const loadData = useCallback(async (tab, isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    const t = tab || activeTab;
    try {
      if (t === 'overview' || t === 'dispatch') {
        const [sumRes, usrRes] = await Promise.all([fetchInspectionsSummary(), fetchAllUsers()]);
        setSummary(sumRes.data);
        setUsers(usrRes.data);
      }
      if (t === 'rules') {
        const res = await fetchAllRules();
        setRules(res.data);
      }
      if (t === 'users') {
        const res = await fetchAllUsers();
        setUsers(res.data);
      }
      if (t === 'logs') {
        const res = await fetchAuditLogs(300);
        setAuditLogs(res.data);
      }
      if (t === 'dispatch') {
        const res = await fetchInspections();
        setInspections(Array.isArray(res.data) ? res.data : []);
      }
    } catch (err) {
      console.warn('Admin load error:', err);
      // Provide graceful fallback data
      if (t === 'users' && users.length === 0) {
        setUsers([
          { id:'ADM-2026', name:'System Administrator',    email:'admin@legalmetrology.gov.in',    designation:'System & Rule Administrator', zone_office:'Central Ministry HQ, New Delhi', role:'admin' },
          { id:'INS-2026', name:'Field Inspector',         email:'inspector@legalmetrology.gov.in', designation:'Field Enforcement Inspector',  zone_office:'Northern Zonal Enforcement Office', role:'inspector' },
          { id:'OFF-2026', name:'Reviewing Senior Officer',email:'officer.test@legalmetrology.gov.in',designation:'Senior Legal Metrology Officer', zone_office:'Central Ministry HQ, New Delhi', role:'reviewing_officer' },
          { id:'OFF-2026-ALIAS', name:'Reviewing Officer Lead',email:'officer@legalmetrology.gov.in',designation:'Adjudication Lead Officer', zone_office:'Central Ministry HQ, New Delhi', role:'reviewing_officer' },
        ]);
      }
    } finally {
      setRefreshing(false);
    }
  }, [activeTab, users.length]);

  useEffect(() => { loadData(activeTab); }, [activeTab]);

  const handleClearSystemLogs = async () => {
    try {
      const res = await clearSystemLogs();
      showToast(res.data?.message || 'System reset to zero-base. All old logs purged.');
      loadData(activeTab, true);
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to reset system data.', 'error');
    } finally {
      setConfirm(null);
    }
  };

  // ─── TAB DEFINITIONS ──────────────────────────────────────────────────────────
  const TABS = [
    { id: 'overview', label: 'Command Center',      icon: BarChart3 },
    { id: 'rules',    label: 'Rule Engine Studio',  icon: Gavel },
    { id: 'dispatch', label: 'Work Assignment',     icon: Send },
    { id: 'users',    label: 'User & RBAC Matrix',  icon: Users },
    { id: 'logs',     label: 'Audit Log Stream',    icon: History },
  ];

  // ══════════════════════════════════════════════════════════════════════════════
  // TAB 1 — COMMAND CENTER
  // ══════════════════════════════════════════════════════════════════════════════
  const OverviewTab = () => (
    <div className="space-y-6">
      {/* National KPI Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard icon={Package}    label="Total Scans"         value={summary?.total_scans ?? 0}       color="red"    sub="All-time field inspections" />
        <KpiCard icon={AlertTriangle} label="Pending Review"  value={summary?.pending_review ?? 0}    color="amber"  sub="Awaiting officer sign-off" />
        <KpiCard icon={CheckCircle2} label="7A Compliant"     value={summary?.compliant ?? 0}          color="green"  sub="Passed all statutory checks" />
        <KpiCard icon={XCircle}    label="7B Violations"      value={summary?.violations ?? 0}         color="red"    sub="Enforcement action required" />
        <KpiCard icon={CheckSquare} label="Officer Signed Off" value={summary?.signed_off ?? 0}        color="purple" sub="Section 36 adjudication done" />
        <KpiCard icon={TrendingUp} label="Compliance Rate"    value={`${summary?.compliance_rate ?? 0}%`} color="green" sub="National field average" />
      </div>

      {/* Engine + Rule Count */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-[#7a1c1c] to-[#4a1010] text-white p-5 rounded-2xl shadow-lg col-span-1">
          <div className="flex items-center gap-2 mb-3">
            <Cpu className="w-5 h-5 text-amber-300" />
            <span className="text-xs font-black uppercase tracking-widest text-amber-300">Rule Engine</span>
          </div>
          <div className="text-4xl font-black font-mono">{summary?.engine_version ?? 'v2.1'}</div>
          <p className="text-xs text-red-200 mt-1">Active Semantic Version</p>
          <div className="mt-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-bold text-emerald-300">ONLINE · HOT-SYNC READY</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1 flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5" /> Active Compliance Rules
          </div>
          <div className="text-3xl font-black text-slate-900 font-mono">{summary?.active_rule_count ?? 0}</div>
          <p className="text-xs text-slate-500 mt-1">Legal Metrology (PC) Rules 2011 + FSSAI</p>
          <button onClick={() => setActiveTab('rules')}
            className="mt-3 text-xs font-black text-[#7a1c1c] hover:text-red-900 flex items-center gap-1 transition">
            Manage Rules <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>

        <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5" /> Platform Users
          </div>
          <div className="text-3xl font-black text-slate-900 font-mono">{users.length || '—'}</div>
          <div className="mt-2 space-y-1">
            {['admin','inspector','reviewing_officer'].map(r => (
              <div key={r} className="flex items-center justify-between text-[10px]">
                <span className="text-slate-500 font-medium capitalize">{r.replace('_',' ')}</span>
                <span className="font-black text-slate-800">{users.filter(u=>u.role===r).length}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Inspector Workload Table */}
      {summary?.inspector_workload?.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
            <Target className="w-4 h-4 text-[#7a1c1c]" />
            <span className="text-xs font-black text-slate-800 uppercase tracking-wider">Inspector Workload Telemetry</span>
          </div>
          <table className="w-full text-xs">
            <thead><tr className="bg-slate-50 text-slate-600 font-black uppercase tracking-wider border-b border-slate-100">
              <th className="p-3 text-left">Inspector</th>
              <th className="p-3 text-center">Total Scans</th>
              <th className="p-3 text-center">Pending Review</th>
              <th className="p-3 text-center">Workload Bar</th>
            </tr></thead>
            <tbody className="divide-y divide-slate-100">
              {summary.inspector_workload.map((w, i) => {
                const pct = w.total ? Math.round((w.pending_officer_review / w.total) * 100) : 0;
                return (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="p-3 font-bold text-slate-900">{w.name}</td>
                    <td className="p-3 text-center font-mono font-bold">{w.total}</td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-0.5 rounded font-black text-[10px] ${w.pending_officer_review > 0 ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-slate-100 text-slate-500'}`}>
                        {w.pending_officer_review}
                      </span>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-[#7a1c1c] rounded-full" style={{ width: `${Math.min(100, pct)}%` }} />
                        </div>
                        <span className="text-[10px] font-bold text-slate-500 w-8 text-right">{pct}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  // ══════════════════════════════════════════════════════════════════════════════
  // TAB 2 — RULE ENGINE STUDIO
  // ══════════════════════════════════════════════════════════════════════════════
  const RuleEngineTab = () => {
    const [newVersion, setNewVersion] = useState('');
    const [gsrn, setGsrn] = useState('');
    const [changelog, setChangelog] = useState('');
    const [syncing, setSyncing] = useState(false);
    const [ruleSearch, setRuleSearch] = useState('');
    const [editingRule, setEditingRule] = useState(null);
    const [editDraft, setEditDraft] = useState({});

    const currentVersion = rules[0]?.version || summary?.engine_version || 'v2.1';
    const filtered = rules.filter(r =>
      (r.rule_id || '').toLowerCase().includes(ruleSearch.toLowerCase()) ||
      (r.target_parameter || r.field_name || '').toLowerCase().includes(ruleSearch.toLowerCase()) ||
      (r.statutory_reference || r.regulation_section || '').toLowerCase().includes(ruleSearch.toLowerCase())
    );

    const handleSyncVersion = async () => {
      if (!newVersion.trim()) return showToast('Please enter a new version string.', 'error');
      setConfirm({
        title: 'Sync Rule Engine Version',
        body: `This will update ALL ${rules.length} active rules to version "${newVersion}" and write a version change audit record. This action cannot be undone without re-seeding. Proceed?`,
        danger: true,
        confirmLabel: 'Apply & Sync',
        onConfirm: async () => {
          setConfirm(null);
          setSyncing(true);
          try {
            const res = await syncRuleVersion(newVersion, gsrn, changelog);
            showToast(`Rule engine synced to ${newVersion}. ${res.data.rules_updated} rules updated.`, 'success');
            setNewVersion(''); setGsrn(''); setChangelog('');
            await loadData('rules');
          } catch (err) {
            showToast(err.response?.data?.detail || 'Sync failed.', 'error');
          } finally { setSyncing(false); }
        },
        onCancel: () => setConfirm(null),
      });
    };

    const handleToggle = async (rule) => {
      try {
        await toggleRuleStatus(rule.rule_id, rule.is_active, rule);
        showToast(`Rule ${rule.rule_id} ${rule.is_active ? 'deactivated' : 'activated'}.`);
        await loadData('rules');
      } catch { showToast('Failed to toggle rule status.', 'error'); }
    };

    const handleSaveEdit = async () => {
      try {
        await updateRuleParam(editingRule.rule_id, { ...editingRule, ...editDraft });
        showToast(`Rule ${editingRule.rule_id} updated successfully.`);
        setEditingRule(null); setEditDraft({});
        await loadData('rules');
      } catch { showToast('Failed to save rule changes.', 'error'); }
    };

    return (
      <div className="space-y-6">
        {/* Version Control Panel */}
        <div className="bg-gradient-to-r from-slate-900 to-[#1a0808] text-white p-6 rounded-2xl border border-slate-700 shadow-xl">
          <div className="flex flex-col lg:flex-row lg:items-center gap-6">
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-2 text-amber-300 text-xs font-black uppercase tracking-widest mb-2">
                <GitBranch className="w-4 h-4" />
                Rule Engine Version Control Studio
              </div>
              <div className="flex items-center gap-3">
                <span className="text-slate-400 text-sm font-medium">Current Version:</span>
                <span className="text-2xl font-black font-mono text-amber-300">{currentVersion}</span>
                <span className="px-2 py-0.5 text-[10px] bg-emerald-500/20 text-emerald-300 rounded-md font-black border border-emerald-500/40">ACTIVE</span>
              </div>
              <p className="text-xs text-slate-400">{rules.length} statutory rules in the active compliance registry.</p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 flex-shrink-0 lg:min-w-[520px]">
              <div className="flex-1 min-w-0">
                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">New Version Tag</label>
                <input value={newVersion} onChange={e => setNewVersion(e.target.value)}
                  placeholder="e.g. v2.2"
                  className="w-full px-3 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-amber-400" />
              </div>
              <div className="flex-1 min-w-0">
                <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">GSR/N Reference</label>
                <input value={gsrn} onChange={e => setGsrn(e.target.value)}
                  placeholder="e.g. G.S.R. 488(E)"
                  className="w-full px-3 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-amber-400" />
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <label className="block text-[10px] font-black text-slate-400 uppercase mb-1">Statutory Changelog Summary</label>
              <textarea value={changelog} onChange={e => setChangelog(e.target.value)} rows={2}
                placeholder="Describe the statutory amendment or notification change..."
                className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-xs focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none" />
            </div>
            <div className="flex items-end">
              <button onClick={handleSyncVersion} disabled={syncing || !newVersion.trim()}
                className="px-6 py-3 bg-amber-400 hover:bg-amber-300 disabled:opacity-50 text-slate-950 font-black text-xs rounded-xl transition flex items-center gap-2 shadow-lg active:scale-95">
                {syncing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                <span>{syncing ? 'SYNCING...' : 'APPLY & SYNC TO ENGINE'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Rule Registry Table */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 px-5 py-4 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-[#7a1c1c]" />
              <span className="text-xs font-black text-slate-800 uppercase tracking-wider">
                Statutory Compliance Rules Registry ({filtered.length} / {rules.length})
              </span>
            </div>
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input value={ruleSearch} onChange={e => setRuleSearch(e.target.value)}
                placeholder="Search rule ID, parameter, section..."
                className="pl-8 pr-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-200 w-64" />
            </div>
          </div>

          <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10">
                <tr className="bg-slate-100 text-slate-600 font-black uppercase tracking-wider border-b border-slate-200">
                  <th className="p-3 text-left">Rule ID</th>
                  <th className="p-3 text-left">Target Parameter</th>
                  <th className="p-3 text-left">Statutory Reference</th>
                  <th className="p-3 text-left">Severity</th>
                  <th className="p-3 text-center">Version</th>
                  <th className="p-3 text-center">Status</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {filtered.map(r => (
                  <tr key={r.rule_id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-3 font-mono font-black text-[#7a1c1c] text-[11px]">{r.rule_id}</td>
                    <td className="p-3 font-bold max-w-[150px] truncate" title={r.target_parameter || r.field_name}>
                      {r.target_parameter || r.field_name || '—'}
                    </td>
                    <td className="p-3 text-slate-500 max-w-[180px] truncate" title={r.statutory_reference || r.regulation_section}>
                      {r.statutory_reference || r.regulation_section || '—'}
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 text-[10px] font-black rounded border ${
                        r.severity === 'HIGH' || r.severity === 'CRITICAL'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : r.severity === 'MEDIUM'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-slate-50 text-slate-600 border-slate-200'
                      }`}>{r.severity || 'HIGH'}</span>
                    </td>
                    <td className="p-3 text-center font-mono text-[10px] text-slate-500 font-bold">{r.version || '—'}</td>
                    <td className="p-3 text-center">
                      <button onClick={() => handleToggle(r)}
                        className={`px-2.5 py-0.5 text-[10px] font-black rounded border transition ${r.is_active
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                          : 'bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-200'
                        }`}>
                        {r.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </button>
                    </td>
                    <td className="p-3 text-right">
                      <button onClick={() => { setEditingRule(r); setEditDraft({}); }}
                        className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded text-[11px] border border-slate-200 transition flex items-center gap-1 ml-auto">
                        <Edit3 className="w-3 h-3" /> Edit
                      </button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={7} className="p-8 text-center text-slate-400 font-medium">No rules match your search.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Inline Edit Drawer */}
        {editingRule && (
          <div className="fixed inset-0 z-[9990] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl max-h-[85vh] overflow-y-auto">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Editing Rule</p>
                  <h3 className="font-black text-slate-900 text-base font-mono">{editingRule.rule_id}</h3>
                </div>
                <button onClick={() => { setEditingRule(null); setEditDraft({}); }} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 space-y-4">
                {[
                  ['target_parameter', 'Target Parameter', 'text'],
                  ['statutory_reference', 'Statutory Reference', 'text'],
                  ['error_message', 'Error / Violation Message', 'text'],
                  ['explanation', 'Explanation', 'textarea'],
                  ['severity', 'Severity', 'select:HIGH,MEDIUM,LOW,CRITICAL'],
                  ['version', 'Rule Version', 'text'],
                ].map(([key, label, type]) => {
                  const val = key in editDraft ? editDraft[key] : (editingRule[key] || '');
                  const set = (v) => setEditDraft(d => ({ ...d, [key]: v }));
                  return (
                    <div key={key}>
                      <label className="block text-[10px] font-black uppercase text-slate-500 mb-1">{label}</label>
                      {type === 'textarea'
                        ? <textarea rows={3} value={val} onChange={e => set(e.target.value)}
                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-200 resize-none" />
                        : type.startsWith('select:')
                        ? <select value={val} onChange={e => set(e.target.value)}
                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-200">
                            {type.replace('select:', '').split(',').map(o => <option key={o} value={o}>{o}</option>)}
                          </select>
                        : <input type="text" value={val} onChange={e => set(e.target.value)}
                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-200" />
                      }
                    </div>
                  );
                })}
              </div>
              <div className="px-6 pb-5 flex justify-end gap-3">
                <button onClick={() => { setEditingRule(null); setEditDraft({}); }}
                  className="px-4 py-2 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-200 transition">
                  Cancel
                </button>
                <button onClick={handleSaveEdit}
                  className="px-5 py-2 text-xs font-black text-white bg-[#7a1c1c] hover:bg-[#601212] rounded-lg shadow transition flex items-center gap-2">
                  <Save className="w-3.5 h-3.5" /> Save Changes
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  // ══════════════════════════════════════════════════════════════════════════════
  // TAB 3 — WORK ASSIGNMENT & DISPATCH ENGINE
  // ══════════════════════════════════════════════════════════════════════════════
  const DispatchTab = () => {
    const [inspSearch, setInspSearch] = useState('');
    const [filterStatus, setFilterStatus] = useState('pending');
    const [assignModal, setAssignModal] = useState(null); // { inspection }
    const [assignType, setAssignType] = useState('officer_review');
    const [assignUserId, setAssignUserId] = useState('');
    const [assignNotes, setAssignNotes] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const officers = users.filter(u => u.role === 'reviewing_officer');
    const fieldInspectors = users.filter(u => u.role === 'inspector');

    const filteredInspections = inspections.filter(i => {
      const s = (i.overall_status || '').toUpperCase();
      const matchStatus = filterStatus === 'all' ? true
        : filterStatus === 'pending' ? (!i.officer_decision && (s === 'PENDING' || s.includes('7B') || i.route_7b_triggered))
        : filterStatus === 'compliant' ? (s.includes('7A') || s.includes('COMPLIANT'))
        : filterStatus === 'violations' ? (s.includes('7B') || s.includes('VIOLATION'))
        : true;
      const q = inspSearch.toLowerCase();
      const matchSearch = !q || (i.id || '').toLowerCase().includes(q) ||
        (i.product_name || '').toLowerCase().includes(q) ||
        (i.inspector_name || '').toLowerCase().includes(q);
      return matchStatus && matchSearch;
    });

    const handleAssign = async () => {
      if (!assignUserId) return showToast('Please select a user to assign.', 'error');
      setSubmitting(true);
      try {
        await assignWork(assignModal.id, assignUserId, assignType, assignNotes);
        showToast(`Inspection ${assignModal.id} assigned successfully.`);
        setAssignModal(null); setAssignNotes(''); setAssignUserId('');
        await loadData('dispatch');
      } catch (err) {
        showToast(err.response?.data?.detail || 'Assignment failed.', 'error');
      } finally { setSubmitting(false); }
    };

    return (
      <div className="space-y-5">
        {/* Workload Summary Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Unassigned (Pending)', count: inspections.filter(i => !i.officer_decision && ((i.overall_status||'').toUpperCase()==='PENDING'||i.route_7b_triggered)).length, color: 'amber' },
            { label: 'Officers Available', count: officers.length, color: 'purple' },
            { label: 'Field Inspectors', count: fieldInspectors.length, color: 'green' },
            { label: 'Total Inspections', count: inspections.length, color: 'red' },
          ].map(({ label, count, color }) => (
            <KpiCard key={label} icon={Activity} label={label} value={count} color={color} />
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={inspSearch} onChange={e => setInspSearch(e.target.value)}
              placeholder="Search inspection ID, product, inspector..."
              className="pl-8 pr-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-200 w-72" />
          </div>
          {['all','pending','violations','compliant'].map(f => (
            <button key={f} onClick={() => setFilterStatus(f)}
              className={`px-3 py-1.5 text-xs font-black rounded-lg border transition ${filterStatus === f
                ? 'bg-[#7a1c1c] text-white border-[#7a1c1c]'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'}`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Inspections Dispatch Table */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
            <Send className="w-4 h-4 text-[#7a1c1c]" />
            <span className="text-xs font-black text-slate-800 uppercase tracking-wider">
              Inspection Dispatch Queue ({filteredInspections.length} records)
            </span>
          </div>
          <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10">
                <tr className="bg-slate-100 text-slate-600 font-black uppercase tracking-wider border-b border-slate-200">
                  <th className="p-3 text-left">Inspection ID</th>
                  <th className="p-3 text-left">Product</th>
                  <th className="p-3 text-left">Inspector</th>
                  <th className="p-3 text-left">Status</th>
                  <th className="p-3 text-left">Assigned Officer</th>
                  <th className="p-3 text-center">Date</th>
                  <th className="p-3 text-right">Dispatch</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {filteredInspections.length === 0 && (
                  <tr><td colSpan={7} className="p-8 text-center text-slate-400">No inspections match current filters.</td></tr>
                )}
                {filteredInspections.map(i => (
                  <tr key={i.id} className="hover:bg-slate-50">
                    <td className="p-3 font-mono font-black text-[10px] text-[#7a1c1c] max-w-[120px] truncate" title={i.id}>{i.id}</td>
                    <td className="p-3 font-bold max-w-[120px] truncate" title={i.product_name}>{i.product_name || '—'}</td>
                    <td className="p-3 text-slate-600 max-w-[100px] truncate">{i.inspector_name || '—'}</td>
                    <td className="p-3"><StatusChip status={i.overall_status} /></td>
                    <td className="p-3">
                      {i.officer_name
                        ? <span className="text-emerald-700 font-bold">{i.officer_name}</span>
                        : <span className="text-amber-500 font-bold italic">Unassigned</span>}
                    </td>
                    <td className="p-3 text-center text-slate-400 font-mono text-[10px]">
                      {i.created_at ? new Date(i.created_at).toLocaleDateString('en-IN') : '—'}
                    </td>
                    <td className="p-3 text-right">
                      <button onClick={() => { setAssignModal(i); setAssignType('officer_review'); setAssignUserId(officers[0]?.id || ''); }}
                        className="px-2.5 py-1.5 bg-[#7a1c1c] hover:bg-[#601212] text-white font-black text-[10px] rounded-lg transition flex items-center gap-1 ml-auto shadow">
                        <Send className="w-3 h-3" /> Dispatch
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Assignment Modal */}
        {assignModal && (
          <div className="fixed inset-0 z-[9990] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-black text-slate-400 uppercase">Dispatch Inspection</p>
                  <h3 className="font-black text-slate-900 font-mono text-sm">{assignModal.id}</h3>
                  <p className="text-xs text-slate-500">{assignModal.product_name}</p>
                </div>
                <button onClick={() => setAssignModal(null)} className="text-slate-400 hover:text-slate-700"><X className="w-5 h-5" /></button>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-[10px] font-black uppercase text-slate-500 mb-1.5">Assignment Type</label>
                  <div className="flex gap-3">
                    {[
                      { val: 'officer_review', label: 'Route to Reviewing Officer' },
                      { val: 'inspector_dispatch', label: 'Re-assign to Inspector' },
                    ].map(({ val, label }) => (
                      <label key={val} className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-xs font-bold transition ${assignType === val ? 'bg-red-50 border-red-300 text-[#7a1c1c]' : 'border-slate-200 text-slate-600 hover:border-slate-400'}`}>
                        <input type="radio" value={val} checked={assignType === val} onChange={() => { setAssignType(val); setAssignUserId(''); }} className="hidden" />
                        {label}
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase text-slate-500 mb-1.5">
                    {assignType === 'officer_review' ? 'Select Reviewing Officer' : 'Select Inspector'}
                  </label>
                  <select value={assignUserId} onChange={e => setAssignUserId(e.target.value)}
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-200">
                    <option value="">— Select —</option>
                    {(assignType === 'officer_review' ? officers : fieldInspectors).map(u => (
                      <option key={u.id} value={u.id}>{u.name} ({u.zone_office})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase text-slate-500 mb-1.5">Dispatch Notes (Optional)</label>
                  <textarea value={assignNotes} onChange={e => setAssignNotes(e.target.value)} rows={2}
                    placeholder="Add instructions or context for the assigned officer..."
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-red-200 resize-none" />
                </div>
              </div>
              <div className="px-6 pb-5 flex justify-end gap-3">
                <button onClick={() => setAssignModal(null)}
                  className="px-4 py-2 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-200 transition">
                  Cancel
                </button>
                <button onClick={handleAssign} disabled={submitting || !assignUserId}
                  className="px-5 py-2 text-xs font-black text-white bg-[#7a1c1c] hover:bg-[#601212] disabled:opacity-50 rounded-lg shadow transition flex items-center gap-2">
                  {submitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  Confirm Dispatch
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  // ══════════════════════════════════════════════════════════════════════════════
  // TAB 4 — USER ACCOUNTS & RBAC MATRIX
  // ══════════════════════════════════════════════════════════════════════════════
  const UsersTab = () => {
    const [userSearch, setUserSearch] = useState('');
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [form, setForm] = useState({ name:'', email:'', password:'', designation:'Enforcement Officer', zone_office:'Northern Zonal Office', role:'inspector' });
    const [creating, setCreating] = useState(false);

    const filteredUsers = users.filter(u =>
      !userSearch || (u.name||'').toLowerCase().includes(userSearch.toLowerCase()) ||
      (u.email||'').toLowerCase().includes(userSearch.toLowerCase()) ||
      (u.role||'').toLowerCase().includes(userSearch.toLowerCase())
    );

    const handleCreate = async (e) => {
      e.preventDefault();
      setCreating(true);
      try {
        await createUser(form);
        showToast(`User ${form.email} created as ${form.role}.`);
        setShowCreateForm(false);
        setForm({ name:'', email:'', password:'', designation:'Enforcement Officer', zone_office:'Northern Zonal Office', role:'inspector' });
        await loadData('users');
      } catch (err) {
        showToast(err.response?.data?.detail || 'Failed to create user.', 'error');
      } finally { setCreating(false); }
    };

    const handleRoleChange = async (userId, newRole, userName) => {
      setConfirm({
        title: 'Change User Role',
        body: `Change ${userName}'s role to "${newRole}"? This immediately changes their system access permissions.`,
        danger: false,
        confirmLabel: 'Change Role',
        onConfirm: async () => {
          setConfirm(null);
          try {
            await updateUserRole(userId, newRole);
            showToast(`${userName} role updated to ${newRole}.`);
            await loadData('users');
          } catch { showToast('Role update failed.', 'error'); }
        },
        onCancel: () => setConfirm(null),
      });
    };

    const f = (k) => e => setForm(prev => ({ ...prev, [k]: e.target.value }));

    return (
      <div className="space-y-5">
        {/* Header + Create Button */}
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={userSearch} onChange={e => setUserSearch(e.target.value)}
              placeholder="Search by name, email or role..."
              className="pl-8 pr-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-200 w-72" />
          </div>
          <button onClick={() => setShowCreateForm(v => !v)}
            className={`px-4 py-2 text-xs font-black rounded-xl border transition flex items-center gap-2 ${showCreateForm ? 'bg-slate-100 text-slate-700 border-slate-300' : 'bg-[#7a1c1c] text-white border-[#7a1c1c] shadow hover:bg-[#601212]'}`}>
            <UserPlus className="w-3.5 h-3.5" />
            {showCreateForm ? 'Hide Form' : 'Create New User'}
          </button>
        </div>

        {/* Create User Form */}
        {showCreateForm && (
          <form onSubmit={handleCreate} className="bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-5">
            <h3 className="text-xs font-black text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <UserPlus className="w-4 h-4 text-[#7a1c1c]" /> Register New System User
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
              {[
                ['name', 'Full Official Name', 'text', 'e.g. Rajesh Kumar Sharma'],
                ['email', 'Government Email', 'email', 'official@legalmetrology.gov.in'],
                ['password', 'Password', 'password', 'Min 8 characters'],
                ['designation', 'Designation', 'text', 'e.g. Field Enforcement Inspector'],
                ['zone_office', 'Zone Office', 'text', 'e.g. Northern Zonal Office'],
              ].map(([key, label, type, placeholder]) => (
                <div key={key}>
                  <label className="block font-black text-slate-600 mb-1 uppercase text-[10px]">{label}</label>
                  <input type={type} required={['name','email','password'].includes(key)}
                    value={form[key]} onChange={f(key)} placeholder={placeholder}
                    className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-red-200" />
                </div>
              ))}
              <div>
                <label className="block font-black text-slate-600 mb-1 uppercase text-[10px]">RBAC Role</label>
                <select value={form.role} onChange={f('role')}
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-900 font-bold focus:outline-none focus:ring-2 focus:ring-red-200">
                  <option value="inspector">inspector — Field Enforcement Inspector</option>
                  <option value="reviewing_officer">reviewing_officer — Reviewing & Adjudication Officer</option>
                  <option value="admin">admin — System & Rule Administrator</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={creating}
                className="px-5 py-2.5 bg-[#7a1c1c] hover:bg-[#601212] disabled:opacity-60 text-white font-black text-xs rounded-xl shadow transition flex items-center gap-2">
                {creating ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <UserPlus className="w-3.5 h-3.5" />}
                CREATE USER ACCOUNT
              </button>
              <button type="button" onClick={() => setShowCreateForm(false)}
                className="px-4 py-2.5 bg-slate-100 text-slate-700 font-bold text-xs rounded-xl border border-slate-200 hover:bg-slate-200 transition">
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Users Table */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
            <Users className="w-4 h-4 text-[#7a1c1c]" />
            <span className="text-xs font-black text-slate-800 uppercase tracking-wider">
              System User Directory ({filteredUsers.length} accounts)
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-100 text-slate-600 font-black uppercase tracking-wider border-b border-slate-200">
                  <th className="p-3 text-left">User</th>
                  <th className="p-3 text-left">Email</th>
                  <th className="p-3 text-left">Designation & Zone</th>
                  <th className="p-3 text-center">Current Role</th>
                  <th className="p-3 text-right">Change Role</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {filteredUsers.map(u => (
                  <tr key={u.id} className="hover:bg-slate-50">
                    <td className="p-3">
                      <div className="flex items-center gap-2.5">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-black text-xs flex-shrink-0 ${
                          u.role === 'admin' ? 'bg-purple-600' : u.role === 'reviewing_officer' ? 'bg-amber-500' : 'bg-emerald-600'
                        }`}>
                          {(u.name || 'U').charAt(0)}
                        </div>
                        <div>
                          <p className="font-black text-slate-900">{u.name}</p>
                          <p className="text-[10px] font-mono text-slate-400">{u.id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-3 font-mono text-[#7a1c1c] font-bold text-[11px]">{u.email}</td>
                    <td className="p-3">
                      <p className="font-semibold text-slate-800">{u.designation}</p>
                      <p className="text-[10px] text-slate-400 flex items-center gap-1"><MapPin className="w-2.5 h-2.5" />{u.zone_office}</p>
                    </td>
                    <td className="p-3 text-center"><RoleBadge role={u.role} /></td>
                    <td className="p-3 text-right">
                      <select value={u.role} onChange={e => handleRoleChange(u.id, e.target.value, u.name)}
                        className="px-2 py-1.5 bg-white border border-slate-200 rounded-lg text-[11px] font-bold text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-200 cursor-pointer hover:border-red-400 transition">
                        <option value="admin">admin</option>
                        <option value="inspector">inspector</option>
                        <option value="reviewing_officer">reviewing_officer</option>
                      </select>
                    </td>
                  </tr>
                ))}
                {filteredUsers.length === 0 && (
                  <tr><td colSpan={5} className="p-8 text-center text-slate-400">No users found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // ══════════════════════════════════════════════════════════════════════════════
  // TAB 5 — GLOBAL AUDIT LOG STREAM
  // ══════════════════════════════════════════════════════════════════════════════
  const AuditLogsTab = () => {
    const [logSearch, setLogSearch] = useState('');
    const [logFilter, setLogFilter] = useState('ALL');

    const actionGroups = {
      ALL: null,
      INSPECTIONS: ['INSPECTION_SCAN_PROCESSED','VERIFY_INSPECTION'],
      RULES: ['UPDATE_RULE','CREATE_RULE','DELETE_RULE','RULE_VERSION_UPDATE'],
      USERS: ['CREATE_USER','UPDATE_USER_ROLE'],
      DISPATCH: ['WORK_ASSIGNED'],
    };

    const filtered = auditLogs.filter(log => {
      const matchGroup = !actionGroups[logFilter] || actionGroups[logFilter].includes(log.action);
      const q = logSearch.toLowerCase();
      const matchSearch = !q || (log.user_name||'').toLowerCase().includes(q) ||
        (log.action||'').toLowerCase().includes(q) || (log.details||'').toLowerCase().includes(q);
      return matchGroup && matchSearch;
    });

    const actionColor = (action = '') => {
      if (action.includes('RULE_VERSION')) return 'bg-purple-50 text-purple-700 border-purple-200';
      if (action.includes('RULE')) return 'bg-blue-50 text-blue-700 border-blue-200';
      if (action.includes('USER')) return 'bg-amber-50 text-amber-700 border-amber-200';
      if (action.includes('INSPECTION')) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      if (action.includes('ASSIGNED')) return 'bg-sky-50 text-sky-700 border-sky-200';
      return 'bg-slate-50 text-slate-700 border-slate-200';
    };

    return (
      <div className="space-y-4">
        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={logSearch} onChange={e => setLogSearch(e.target.value)}
              placeholder="Search by user, action, details..."
              className="pl-8 pr-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-200 w-72" />
          </div>
          {Object.keys(actionGroups).map(g => (
            <button key={g} onClick={() => setLogFilter(g)}
              className={`px-3 py-1.5 text-[10px] font-black rounded-lg border uppercase transition ${logFilter === g
                ? 'bg-[#7a1c1c] text-white border-[#7a1c1c]'
                : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'}`}>
              {g}
            </button>
          ))}
          <span className="text-xs text-slate-500 font-medium">{filtered.length} records</span>
          <button
            onClick={() => setConfirm({
              title: 'Reset System to Zero Base?',
              body: 'This will purge all previous inspection records, scan sessions, and audit logs so you can start completely fresh from 0. User accounts, RBAC roles, and compliance rules will be preserved.',
              danger: true,
              confirmLabel: 'Clear All & Reset to 0',
              onConfirm: handleClearSystemLogs
            })}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 rounded-lg text-[11px] font-black transition cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear Logs & Reset System
          </button>
        </div>

        {/* Log Stream */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#7a1c1c]" />
            <span className="text-xs font-black text-slate-800 uppercase tracking-wider">System Audit Log Stream</span>
            <span className="ml-auto px-2 py-0.5 text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 rounded font-black">
              IMMUTABLE
            </span>
          </div>
          <div className="overflow-x-auto max-h-[520px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10">
                <tr className="bg-slate-100 text-slate-600 font-black uppercase tracking-wider border-b border-slate-200">
                  <th className="p-3 text-left w-32">Timestamp</th>
                  <th className="p-3 text-left">Officer / User</th>
                  <th className="p-3 text-left">Action</th>
                  <th className="p-3 text-left">Resource ID</th>
                  <th className="p-3 text-left">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.length === 0 && (
                  <tr><td colSpan={5} className="p-10 text-center text-slate-400">No audit logs available. Actions performed in the system will appear here.</td></tr>
                )}
                {filtered.map((log, idx) => (
                  <tr key={log.id || idx} className="hover:bg-slate-50 align-top">
                    <td className="p-3 font-mono text-[10px] text-slate-400 whitespace-nowrap">
                      <div>{fmtDate(log.timestamp)}</div>
                      <div className="text-slate-300">{relTime(log.timestamp)}</div>
                    </td>
                    <td className="p-3">
                      <p className="font-black text-slate-900">{log.user_name || '—'}</p>
                      <p className="font-mono text-[10px] text-[#7a1c1c]">{log.user_id}</p>
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 text-[10px] font-black rounded border font-mono whitespace-nowrap ${actionColor(log.action)}`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="p-3 font-mono text-[10px] text-slate-500 max-w-[120px] truncate" title={log.resource_id}>
                      {log.resource_id || '—'}
                    </td>
                    <td className="p-3 text-slate-600 max-w-[300px] text-[11px]">{log.details || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // ══════════════════════════════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════════════════════════════
  return (
    <div className="min-h-screen bg-slate-50 font-sans">

      {/* Toast */}
      <Toast msg={toast.msg} type={toast.type} onClose={() => setToast({ msg:'' })} />

      {/* Confirm Modal */}
      {confirm && <ConfirmModal {...confirm} />}

      {/* ── Page Header ─────────────────────────────────────────────────────── */}
      <div className="bg-gradient-to-r from-[#7a1c1c] via-[#8B1E1E] to-[#601212] text-white px-6 md:px-8 py-6 shadow-xl border-b border-red-900/40">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-5">

          <div className="space-y-2">
            {/* Badge Strip */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center space-x-2 px-3 py-1 bg-black/30 text-white text-xs font-black rounded-lg border border-white/20 backdrop-blur-sm">
                <div className="h-2 w-5 rounded flex overflow-hidden">
                  <div className="w-1/3 bg-[#FF9933]" /><div className="w-1/3 bg-white" /><div className="w-1/3 bg-[#138808]" />
                </div>
                <span>DEPT. OF CONSUMER AFFAIRS · LEGAL METROLOGY</span>
              </div>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-400 text-slate-950 text-xs font-black rounded-lg">
                <ShieldCheck className="w-3.5 h-3.5" /> ADMIN COMMAND & CONTROL
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/15 text-white text-xs font-bold rounded-lg border border-white/20">
                <Cpu className="w-3.5 h-3.5 text-amber-300" />
                <span>Engine: <strong className="font-black">{summary?.engine_version || 'v2.1'}</strong></span>
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/20 text-emerald-300 text-xs font-extrabold rounded-lg border border-emerald-500/40">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                SYSTEM ONLINE
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight leading-tight">
              Admin Command & Control Dashboard
            </h1>
            <p className="text-sm text-red-100 font-semibold">
              Govern platform users, dynamically manage statutory rules, dispatch inspections and monitor system-wide compliance telemetry.
            </p>

            <div className="flex flex-wrap gap-3 text-xs font-bold text-red-100/80 pt-1">
              <div className="flex items-center gap-1.5 bg-black/20 px-3 py-1 rounded-md">
                <UserCheck className="w-3.5 h-3.5 text-amber-300" />
                Admin: <strong className="text-white">{user?.name || 'System Administrator'}</strong>
              </div>
              <div className="flex items-center gap-1.5 bg-black/20 px-3 py-1 rounded-md">
                <Database className="w-3.5 h-3.5 text-red-200" />
                Rules: <strong className="text-white font-mono">{summary?.active_rule_count ?? '—'}</strong> active
              </div>
              <div className="flex items-center gap-1.5 bg-black/20 px-3 py-1 rounded-md">
                <Globe className="w-3.5 h-3.5 text-emerald-300" />
                Total Scans: <strong className="text-white font-mono">{summary?.total_scans ?? '—'}</strong>
              </div>
            </div>
          </div>

          <button onClick={() => loadData(activeTab, true)} disabled={refreshing}
            className="flex-shrink-0 px-5 py-3 bg-white/20 hover:bg-white/30 text-white font-black text-xs rounded-xl border border-white/30 transition flex items-center gap-2 active:scale-95 disabled:opacity-70 self-start lg:self-center">
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'REFRESHING...' : 'REFRESH'}
          </button>
        </div>
      </div>

      {/* ── Tab Navigation ───────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex overflow-x-auto">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-5 py-4 text-xs font-black uppercase tracking-wider whitespace-nowrap border-b-2 transition ${
                activeTab === id
                  ? 'border-[#7a1c1c] text-[#7a1c1c] bg-red-50/50'
                  : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
              }`}>
              <Icon className="w-3.5 h-3.5" />
              {label}
              {id === 'dispatch' && summary?.pending_review > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-[9px] bg-amber-400 text-slate-900 rounded-full font-black">
                  {summary.pending_review}
                </span>
              )}
              {id === 'logs' && auditLogs.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-[9px] bg-slate-200 text-slate-700 rounded-full font-black">
                  {auditLogs.length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ── Tab Content ─────────────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-7">
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'rules'    && <RuleEngineTab />}
        {activeTab === 'dispatch' && <DispatchTab />}
        {activeTab === 'users'    && <UsersTab />}
        {activeTab === 'logs'     && <AuditLogsTab />}
      </div>
    </div>
  );
}

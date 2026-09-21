import React, { useState, useEffect } from 'react';
import { 
  Camera, 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  FileText, 
  TrendingUp, 
  AlertTriangle, 
  ArrowRight,
  Gavel,
  Scale,
  Sparkles,
  Search,
  ExternalLink,
  Layers
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    total_inspections: 0,
    compliant_count: 0,
    violation_count: 0,
    pending_review_count: 0,
    compliance_rate_percent: 0,
    route_7b_trigger_count: 0,
    top_violations: []
  });

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const res = await api.get('/analytics/overview');
      if (res.data) {
        setStats(res.data);
      }
    } catch (err) {
      console.warn("Analytics API offline, using cached metrics.");
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      
      {/* 1. Hero Red Banner — "Online Services & Inspection Gateway" */}
      <div className="bg-gradient-to-r from-red-700 via-red-600 to-red-800 text-white p-10 rounded-3xl shadow-xl relative overflow-hidden">
        <div className="absolute -right-10 -bottom-10 w-72 h-72 bg-white/5 rounded-full blur-2xl pointer-events-none"></div>

        <div className="relative z-10 space-y-5 max-w-4xl">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 bg-black/25 text-white text-xs font-black rounded-xl backdrop-blur-sm border border-white/20">
            <Scale className="w-4 h-4 text-amber-300" />
            <span>National Metrology Portal • Legal Metrology (Packaged Commodities) Rules, 2011</span>
          </div>

          <h1 className="text-4xl font-black tracking-tight leading-tight">
            Avail Online Metrology Services & Statutory Enforcement Verification
          </h1>

          <p className="text-base text-red-100 font-semibold leading-relaxed">
            Real-time automated scanning, PaddleOCR declaration extraction, Rule 7 font height calibration, and senior officer adjudication workspace.
          </p>

          <div className="pt-2 flex flex-wrap gap-4">
            <button
              onClick={() => navigate('/scanner')}
              className="px-7 py-3.5 bg-white hover:bg-slate-100 text-red-700 font-black text-sm rounded-xl shadow-lg transition flex items-center space-x-2"
            >
              <Camera className="w-5 h-5 text-red-600" />
              <span>LAUNCH LIVE CAMERA SCANNER →</span>
            </button>

            <button
              onClick={() => navigate('/officer/review')}
              className="px-7 py-3.5 bg-black/30 hover:bg-black/40 text-white border border-white/30 font-black text-sm rounded-xl transition flex items-center space-x-2"
            >
              <ShieldAlert className="w-5 h-5 text-amber-300" />
              <span>REVIEW ADJUDICATION QUEUE (7B)</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Quick Action Services Cards Grid */}
      <div className="space-y-4">
        <div className="border-b-2 border-red-600 pb-2 flex items-center justify-between">
          <h2 className="text-base font-black text-slate-900 uppercase tracking-wider flex items-center space-x-2">
            <Layers className="w-5 h-5 text-red-600" />
            <span>Featured Statutory Services</span>
          </h2>
          <span className="text-xs text-slate-600 font-extrabold">Legal Metrology Act, 2009 Services</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          
          <div 
            onClick={() => navigate('/scanner')}
            className="bg-white border border-slate-200 hover:border-red-500 p-6 rounded-2xl shadow-sm hover:shadow-md transition cursor-pointer group space-y-3"
          >
            <div className="w-12 h-12 bg-red-50 text-red-600 rounded-xl flex items-center justify-center font-black group-hover:bg-red-600 group-hover:text-white transition">
              <Camera className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-black text-slate-900 group-hover:text-red-600 transition">
                Live Camera Scanner
              </h3>
              <p className="text-xs text-slate-600 mt-1 font-bold leading-relaxed">
                Point camera at packaged commodity to scan statutory declarations.
              </p>
            </div>
          </div>

          <div 
            onClick={() => navigate('/officer/review')}
            className="bg-white border border-slate-200 hover:border-red-500 p-6 rounded-2xl shadow-sm hover:shadow-md transition cursor-pointer group space-y-3"
          >
            <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-xl flex items-center justify-center font-black group-hover:bg-amber-600 group-hover:text-white transition">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-black text-slate-900 group-hover:text-red-600 transition">
                Officer Review Queue
              </h3>
              <p className="text-xs text-slate-600 mt-1 font-bold leading-relaxed">
                Adjudicate Route 7B flagged non-compliant evidence files.
              </p>
            </div>
          </div>

          <div 
            onClick={() => navigate('/history')}
            className="bg-white border border-slate-200 hover:border-red-500 p-6 rounded-2xl shadow-sm hover:shadow-md transition cursor-pointer group space-y-3"
          >
            <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center font-black group-hover:bg-blue-600 group-hover:text-white transition">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-black text-slate-900 group-hover:text-red-600 transition">
                Inspection Audit History
              </h3>
              <p className="text-xs text-slate-600 mt-1 font-bold leading-relaxed">
                Search and export full national enforcement audit log registry.
              </p>
            </div>
          </div>

          <div 
            onClick={() => navigate('/reports')}
            className="bg-white border border-slate-200 hover:border-red-500 p-6 rounded-2xl shadow-sm hover:shadow-md transition cursor-pointer group space-y-3"
          >
            <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center font-black group-hover:bg-emerald-600 group-hover:text-white transition">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-black text-slate-900 group-hover:text-red-600 transition">
                Analytics & PDF Reports
              </h3>
              <p className="text-xs text-slate-600 mt-1 font-bold leading-relaxed">
                Generate statutory inspection certificates and PDF compliance reports.
              </p>
            </div>
          </div>

        </div>
      </div>

      {/* 3. National Compliance Metrics & Key Performance Indicators */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-1.5">
          <span className="text-xs font-black text-slate-500 uppercase tracking-wider">Total Scanned Packages</span>
          <div className="text-3xl font-black text-slate-900">{stats?.total_inspections || 0}</div>
          <span className="text-xs text-emerald-700 font-extrabold">100% Audited Stream</span>
        </div>

        <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-1.5">
          <span className="text-xs font-black text-slate-500 uppercase tracking-wider">7A: Compliant Packages</span>
          <div className="text-3xl font-black text-emerald-600">{stats?.compliant_count || 0}</div>
          <span className="text-xs text-slate-700 font-bold">{stats?.compliance_rate_percent || 0}% Compliance Rate</span>
        </div>

        <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-1.5">
          <span className="text-xs font-black text-slate-500 uppercase tracking-wider">7B: Flagged Violations</span>
          <div className="text-3xl font-black text-red-600">{stats?.violation_count || 0}</div>
          <span className="text-xs text-red-600 font-bold">Route 7B Action Required</span>
        </div>

        <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-1.5">
          <span className="text-xs font-black text-slate-500 uppercase tracking-wider">Pending Senior Sign-off</span>
          <div className="text-3xl font-black text-amber-600">{stats?.pending_review_count || 0}</div>
          <span className="text-xs text-amber-700 font-extrabold">Awaiting Adjudication</span>
        </div>
      </div>

      {/* 4. Information Categories & Recent Inspections */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Top Statutory Violations (7 Cols) */}
        <div className="lg:col-span-7 bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-4">
          <div className="border-b-2 border-red-600 pb-2.5 flex items-center justify-between">
            <h3 className="text-base font-black text-slate-900 uppercase tracking-wider flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <span>Top Statutory Non-Compliance Categories</span>
            </h3>
          </div>

          <div className="space-y-3">
            {(stats?.top_violations || []).map((v, idx) => (
              <div key={idx} className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
                <div>
                  <span className="text-xs font-mono font-black text-red-700 px-2.5 py-1 bg-red-100 rounded border border-red-300 mr-2.5">
                    {v.rule_id}
                  </span>
                  <span className="text-sm font-black text-slate-900">{v.title}</span>
                </div>
                <span className="px-3.5 py-1 bg-red-600 text-white font-black text-xs rounded-full shadow-sm">
                  {v.count} Cases
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Portal Information & Rules Reference (5 Cols) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 p-6 rounded-2xl shadow-sm space-y-4">
          <div className="border-b-2 border-red-600 pb-2.5">
            <h3 className="text-base font-black text-slate-900 uppercase tracking-wider flex items-center space-x-2">
              <Gavel className="w-5 h-5 text-red-600" />
              <span>Statutory Reference Matrix</span>
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
              <span className="font-black text-slate-900 text-sm block">Rule 6(1): Principal Display Panel Declarations</span>
              <p className="text-xs text-slate-700 font-medium">
                Mandated declarations: Generic Commodity Name, Manufacturer Address, Net Qty, Mfg Date, MRP Tax Clause, Consumer Care Details.
              </p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
              <span className="font-black text-slate-900 text-sm block">Rule 7: Table-I Numeral & Letter Height Matrix</span>
              <p className="text-xs text-slate-700 font-medium">
                Statutory minimum heights evaluated against PDP surface area (50, 100, 500, 2500 cm²).
              </p>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
              <span className="font-black text-slate-900 text-sm block">Schedule II: Standardized Package Sizes</span>
              <p className="text-xs text-slate-700 font-medium">
                Enforces standard package weights/volumes for prescribed food and consumer commodities.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

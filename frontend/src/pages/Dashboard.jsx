import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  Clock, 
  FileCheck2, 
  TrendingUp, 
  BarChart2, 
  PieChart as PieIcon, 
  ArrowUpRight,
  Sparkles
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, LineChart, Line 
} from 'recharts';
import api from '../services/api';

export default function Dashboard() {
  const [analytics, setAnalytics] = useState({
    total_inspections: 148,
    compliant_count: 104,
    violation_count: 28,
    pending_review_count: 16,
    compliance_rate_percent: 70.2,
    route_7b_trigger_count: 24,
    category_breakdown: {
      'Food & Beverages': 52,
      'Personal Care': 34,
      'Pharmaceuticals': 28,
      'Electronics': 18,
      'Household & Chemicals': 16
    },
    top_violations: [
      { name: 'Missing MRP / Inclusive of Taxes', count: 14 },
      { name: 'Missing Country of Origin (Imported)', count: 9 },
      { name: 'Typography Font Height Non-compliance', count: 5 }
    ]
  });

  useEffect(() => {
    api.get('/dashboard/analytics')
      .then((res) => setAnalytics(res.data))
      .catch(() => {});
  }, []);

  const pieData = [
    { name: '7A Compliant', value: analytics.compliant_count, color: '#16A34A' },
    { name: '7B Violation / Review', value: analytics.violation_count, color: '#D97706' },
    { name: 'Pending Review', value: analytics.pending_review_count, color: '#0284C7' },
  ];

  const categoryBarData = Object.entries(analytics.category_breakdown).map(([name, value]) => ({
    name,
    inspections: value
  }));

  const monthlyTrendData = [
    { month: 'Jan', compliant: 80, violations: 18 },
    { month: 'Feb', compliant: 92, violations: 22 },
    { month: 'Mar', compliant: 110, violations: 25 },
    { month: 'Apr', compliant: 104, violations: 28 },
  ];

  return (
    <div className="p-8 space-y-8">
      {/* Top Header Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-wide">
            Analytics Command Center
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time Legal Metrology Statutory Compliance Telemetry & Regional Audit Overview
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <span className="px-3 py-1.5 bg-emerald-950/70 text-emerald-400 border border-emerald-500/40 text-xs font-bold rounded-lg flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Rule Engine v2.4 Active</span>
          </span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="p-6 bg-navy-800 border border-slate-700 rounded-xl shadow-lg flex items-center space-x-4">
          <div className="p-3 bg-gov-blue/20 text-gov-blue rounded-xl border border-gov-blue/30">
            <FileCheck2 className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Inspections</div>
            <div className="text-3xl font-extrabold text-white mt-1">{analytics.total_inspections}</div>
            <div className="text-xs text-emerald-400 flex items-center mt-1">
              <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
              <span>+14% this month</span>
            </div>
          </div>
        </div>

        <div className="p-6 bg-navy-800 border border-slate-700 rounded-xl shadow-lg flex items-center space-x-4">
          <div className="p-3 bg-emerald-950/80 text-emerald-400 rounded-xl border border-emerald-500/40">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">7A Compliant Goods</div>
            <div className="text-3xl font-extrabold text-emerald-400 mt-1">{analytics.compliant_count}</div>
            <div className="text-xs text-slate-400 mt-1">
              <span>{analytics.compliance_rate_percent}% overall rate</span>
            </div>
          </div>
        </div>

        <div className="p-6 bg-navy-800 border border-slate-700 rounded-xl shadow-lg flex items-center space-x-4">
          <div className="p-3 bg-amber-950/80 text-amber-300 rounded-xl border border-amber-500/40">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">7B Flagged Violations</div>
            <div className="text-3xl font-extrabold text-amber-400 mt-1">{analytics.violation_count}</div>
            <div className="text-xs text-amber-300/80 mt-1">
              <span>{analytics.route_7b_trigger_count} Route 7B escalations</span>
            </div>
          </div>
        </div>

        <div className="p-6 bg-navy-800 border border-slate-700 rounded-xl shadow-lg flex items-center space-x-4">
          <div className="p-3 bg-sky-950/80 text-sky-400 rounded-xl border border-sky-500/40">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Pending Officer Review</div>
            <div className="text-3xl font-extrabold text-sky-400 mt-1">{analytics.pending_review_count}</div>
            <div className="text-xs text-slate-400 mt-1">
              <span>Requires sign-off</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recharts Graphical Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Compliance Breakdown Pie Chart */}
        <div className="p-6 bg-navy-800 border border-slate-700 rounded-xl shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <PieIcon className="w-4 h-4 text-gov-blue" />
              <span>Compliance Distribution</span>
            </h3>
          </div>
          <div className="h-64 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', borderRadius: '8px', color: '#FFF' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center space-x-4 text-xs font-bold text-slate-300 mt-2">
            <div className="flex items-center space-x-1.5">
              <span className="w-3 h-3 rounded-full bg-emerald-500"></span>
              <span>7A Compliant</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-3 h-3 rounded-full bg-amber-500"></span>
              <span>7B Violation</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-3 h-3 rounded-full bg-sky-500"></span>
              <span>Pending</span>
            </div>
          </div>
        </div>

        {/* Commodity Category Breakdown Bar Chart */}
        <div className="p-6 bg-navy-800 border border-slate-700 rounded-xl shadow-lg lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <BarChart2 className="w-4 h-4 text-gov-blue" />
              <span>Inspection Volume by Commodity Category</span>
            </h3>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryBarData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} />
                <YAxis stroke="#94A3B8" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', borderRadius: '8px', color: '#FFF' }} />
                <Bar dataKey="inspections" fill="#2563EB" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

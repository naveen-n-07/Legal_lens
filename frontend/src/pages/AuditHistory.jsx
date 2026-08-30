import React, { useState, useEffect } from 'react';
import { Search, Filter, FileText, ExternalLink, Download } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';
import api from '../services/api';

export default function AuditHistory() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [inspections, setInspections] = useState([
    {
      id: 'INS-2026-08913',
      product_name: 'Organic Multifloreal Honey 500g',
      category: 'Food & Beverages',
      location: 'Connaught Place Supermarket, Store #14',
      inspector_name: 'Inspector Rajesh Kumar',
      overall_status: '7B: VIOLATION / MANUAL REVIEW',
      overall_confidence: 88.62,
      created_at: '2026-08-29 22:30'
    },
    {
      id: 'INS-2026-08912',
      product_name: 'Amul Salted Butter 500g',
      category: 'Food & Beverages',
      location: 'Chandni Chowk Godown #12',
      inspector_name: 'Inspector Rajesh Kumar',
      overall_status: '7A: COMPLIANT',
      overall_confidence: 97.40,
      created_at: '2026-08-29 21:15'
    },
    {
      id: 'INS-2026-08911',
      product_name: 'Imported Almond Oil 200ml',
      category: 'Personal Care',
      location: 'Karol Bagh Store #04',
      inspector_name: 'Inspector Rajesh Kumar',
      overall_status: '7B: VIOLATION / MANUAL REVIEW',
      overall_confidence: 79.10,
      created_at: '2026-08-29 19:40'
    }
  ]);

  useEffect(() => {
    api.get('/inspections')
      .then((res) => {
        if (res.data && res.data.length > 0) setInspections(res.data);
      })
      .catch(() => {});
  }, []);

  const filteredInspections = inspections.filter((item) => {
    const matchesSearch = item.product_name.toLowerCase().includes(search.toLowerCase()) ||
                          item.id.toLowerCase().includes(search.toLowerCase()) ||
                          item.location.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || item.overall_status.includes(statusFilter);
    return matchesSearch && matchesStatus;
  });

  const handleDownloadPDF = (id) => {
    window.open(`/api/v1/reports/${id}/pdf`, '_blank');
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-wide">
            Inspection Audit History
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Data-dense table view of statutory audits under the Legal Metrology Act, 2009
          </p>
        </div>
      </div>

      {/* Filter & Search Controls */}
      <div className="p-4 bg-navy-800 border border-slate-700 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4 shadow">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by ID, product, location..."
            className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-gov-blue"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-gov-blue"
          >
            <option value="ALL">All Statuses</option>
            <option value="7A">7A Compliant</option>
            <option value="7B">7B Violation</option>
            <option value="PENDING">Pending Review</option>
          </select>
        </div>
      </div>

      {/* Widescreen Data Table */}
      <div className="bg-navy-800 border border-slate-700 rounded-xl overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 text-slate-400 uppercase font-bold border-b border-slate-700">
              <tr>
                <th className="p-4">Inspection ID</th>
                <th className="p-4">Product Commodity</th>
                <th className="p-4">Category</th>
                <th className="p-4">Field Location</th>
                <th className="p-4">Inspector</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/60 text-slate-200">
              {filteredInspections.map((item) => (
                <tr key={item.id} className="hover:bg-slate-700/40 transition">
                  <td className="p-4 font-extrabold text-gov-blue">{item.id}</td>
                  <td className="p-4 font-bold text-white">{item.product_name}</td>
                  <td className="p-4 text-slate-300">{item.category}</td>
                  <td className="p-4 text-slate-400">{item.location}</td>
                  <td className="p-4 text-slate-300">{item.inspector_name}</td>
                  <td className="p-4">
                    <StatusBadge status={item.overall_status} />
                  </td>
                  <td className="p-4 text-right space-x-2">
                    <button
                      onClick={() => navigate('/officer/review', { state: { inspection: item } })}
                      className="px-3 py-1.5 bg-gov-blue hover:bg-blue-600 text-white rounded font-bold text-xs transition"
                    >
                      Audit View
                    </button>
                    <button
                      onClick={() => handleDownloadPDF(item.id)}
                      title="Download PDF"
                      className="p-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

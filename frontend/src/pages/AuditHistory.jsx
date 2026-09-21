import React, { useState, useEffect } from 'react';
import { Search, Filter, FileText, ExternalLink, Download, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import StatusBadge from '../components/StatusBadge';
import api from '../services/api';

export default function AuditHistory({ user }) {
  const role = user?.role || 'inspector';
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInspections();
  }, []);

  const fetchInspections = async () => {
    setLoading(true);
    try {
      const res = await api.get('/inspections');
      if (res.data && res.data.length > 0) {
        setInspections(res.data);
      } else {
        // Retrieve current active user inspection from local storage if available
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
    }
  };

  const filteredInspections = inspections.filter((item) => {
    const matchesSearch = item.product_name?.toLowerCase().includes(search.toLowerCase()) ||
                          item.id?.toLowerCase().includes(search.toLowerCase()) ||
                          item.location?.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || item.overall_status?.includes(statusFilter);
    return matchesSearch && matchesStatus;
  });

  const handleViewInspection = (item) => {
    // Admins and officers → adjudication view; inspectors → PDF download
    if (role === 'reviewing_officer' || role === 'admin') {
      navigate('/officer/review', { state: { inspection: item, inspectionId: item.id } });
    } else {
      // Inspector: open the PDF directly
      window.open(`/api/v1/reports/${item.id}/pdf`, '_blank');
    }
  };

  const handleDownloadPDF = (id) => {
    window.open(`/api/v1/reports/${id}/pdf`, '_blank');
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-[#1E293B] tracking-tight">
            National Inspection Audit Registry
          </h1>
          <p className="text-sm text-[#64748B] font-bold mt-1">
            Data-dense enforcement audit log under the Legal Metrology (Packaged Commodities) Rules, 2011
          </p>
        </div>
      </div>

      {/* Filter & Search Controls */}
      <div className="p-4 bg-white border border-[#E2E8F0] rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4 shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)]">
        <div className="relative w-full sm:w-96">
          <Search className="w-5 h-5 text-[#64748B] absolute left-3.5 top-3.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by ID, commodity, location..."
            className="w-full pl-10 pr-4 py-2.5 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl text-sm text-[#1E293B] font-semibold focus:outline-none focus:border-red-600"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <Filter className="w-5 h-5 text-[#64748B]" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2.5 bg-[#F8F9FA] border border-[#E2E8F0] rounded-xl text-sm text-[#1E293B] font-extrabold focus:outline-none focus:border-red-600"
          >
            <option value="ALL">All Statutory Statuses</option>
            <option value="7A">7A Compliant</option>
            <option value="7B">7B Violation</option>
            <option value="PENDING">Pending Review</option>
          </select>
        </div>
      </div>

      {/* Widescreen Data Table */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl overflow-hidden shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)]">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-[#F8F9FA] text-[#64748B] uppercase font-black border-b border-[#E2E8F0]">
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
            <tbody className="divide-y divide-[#E2E8F0] text-[#1E293B]">
              {filteredInspections.length > 0 ? (
                filteredInspections.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition">
                    <td className="p-4 font-black font-mono text-red-700">{item.id}</td>
                    <td className="p-4 font-black text-[#1E293B]">{item.product_name}</td>
                    <td className="p-4 text-[#64748B] font-bold">{item.category}</td>
                    <td className="p-4 text-[#64748B] font-semibold">{item.location}</td>
                    <td className="p-4 text-[#1E293B] font-bold">{item.inspector_name || 'Official Inspector'}</td>
                    <td className="p-4">
                      <StatusBadge status={item.overall_status} />
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => handleViewInspection(item)}
                        className="px-4 py-2 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white rounded-lg font-black text-xs transition shadow-sm cursor-pointer"
                      >
                        {role === 'inspector' ? 'View PDF' : 'Audit View'}
                      </button>
                      <button
                        onClick={() => handleDownloadPDF(item.id)}
                        title="Download PDF"
                        className="p-2 bg-[#F1F5F9] hover:bg-slate-200 text-[#334155] rounded-lg transition border border-[#E2E8F0]"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="p-12 text-center text-[#64748B] font-semibold">
                    <Clock className="w-8 h-8 text-[#64748B] mx-auto mb-2" />
                    <span>No statutory inspection records found. Use Live Camera Scanner to perform a scan.</span>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

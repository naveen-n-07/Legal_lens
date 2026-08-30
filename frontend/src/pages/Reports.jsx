import React from 'react';
import { FileText, Download, ShieldCheck, Printer, FileSpreadsheet } from 'lucide-react';

export default function Reports() {
  const handleDownloadPDF = () => {
    window.open('/api/v1/reports/INS-2026-SUMMARY/pdf', '_blank');
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-[#1E293B] tracking-tight">
          Analytics & Official PDF Report Export
        </h1>
        <p className="text-xs text-[#64748B] font-semibold mt-1">
          Generate timestamped statutory violation certificates, regional summary reports, and legal notices under the Legal Metrology Act, 2009.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* PDF Certificate Generator Card */}
        <div className="p-6 bg-white border border-[#E2E8F0] rounded-2xl space-y-4 shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)]">
          <div className="p-3 bg-red-50 text-red-600 rounded-xl border border-red-200 w-fit">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-black text-[#1E293B]">Monthly Statutory Audit Certificate</h3>
            <p className="text-xs text-[#64748B] mt-1 leading-relaxed font-medium">
              Generates a publication-quality ReportLab PDF document containing government headings, metadata tables, itemized rule evaluation matrices, OCR bounding boxes, and senior officer signatures.
            </p>
          </div>
          <button
            onClick={handleDownloadPDF}
            className="w-full py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white font-extrabold text-xs rounded-xl transition shadow-md flex items-center justify-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>EXPORT OFFICIAL MONTHLY PDF CERTIFICATE</span>
          </button>
        </div>

        {/* CSV Data Export Card */}
        <div className="p-6 bg-white border border-[#E2E8F0] rounded-2xl space-y-4 shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)]">
          <div className="p-3 bg-emerald-50 text-emerald-700 rounded-xl border border-emerald-200 w-fit">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-black text-[#1E293B]">Raw Audit CSV Dataset Export</h3>
            <p className="text-xs text-[#64748B] mt-1 leading-relaxed font-medium">
              Exports raw relational database records, violation counts, and officer sign-off timestamps for integration with Ministry legal databases.
            </p>
          </div>
          <button
            onClick={() => alert('Raw CSV Dataset Exported.')}
            className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-black text-xs rounded-xl transition shadow-md flex items-center justify-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>EXPORT CSV DATASET</span>
          </button>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import {
  Gavel,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  X,
  Save,
  RotateCcw,
  FileText,
  HelpCircle,
  Clock,
  Sparkles,
  Info,
  Layers,
  Scale,
  Send
} from 'lucide-react';
import { overrideInspectionVerdict } from '../services/adminService';

export default function ReviewerEditModal({ inspection, isOpen, onClose, onSuccess }) {
  if (!isOpen || !inspection) return null;

  const currentStatus = (inspection.officer_decision || inspection.overall_status || 'PENDING').toUpperCase();
  const initialVerdict = currentStatus.includes('7A') || currentStatus.includes('COMPLIANT')
    ? '7A COMPLIANT'
    : '7B VIOLATION';

  const [verdict, setVerdict] = useState(initialVerdict);
  const [justification, setJustification] = useState(inspection.officer_comments || '');
  
  // Extract initial declarations
  const technicalMatrix = inspection.technical_matrix || inspection.declarations || {};
  const [declarations, setDeclarations] = useState({
    mrp: technicalMatrix.mrp?.value || technicalMatrix.mrp || '',
    net_quantity: technicalMatrix.net_quantity?.value || technicalMatrix.net_quantity || '',
    manufacturing_date: technicalMatrix.manufacturing_date?.value || technicalMatrix.manufacturing_date || '',
    expiry_date: technicalMatrix.expiry_date?.value || technicalMatrix.expiry_date || technicalMatrix.best_before?.value || technicalMatrix.best_before || '',
    manufacturer_details: technicalMatrix.manufacturer_details?.value || technicalMatrix.manufacturer_details || technicalMatrix.manufacturer_name?.value || technicalMatrix.manufacturer_name || '',
    customer_care: technicalMatrix.customer_care?.value || technicalMatrix.customer_care || technicalMatrix.consumer_care?.value || technicalMatrix.consumer_care || ''
  });

  // Extract rule checks
  const checksList = inspection.checks || inspection.compliance_results || [];
  const [ruleStatuses, setRuleStatuses] = useState({});

  useEffect(() => {
    const initialRuleMap = {};
    checksList.forEach(chk => {
      const key = chk.rule_id || chk.field_name;
      if (key) {
        initialRuleMap[key] = chk.is_compliant ? 'COMPLIANT' : 'VIOLATION';
      }
    });
    setRuleStatuses(initialRuleMap);
  }, [inspection]);

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleDeclarationChange = (field, value) => {
    setDeclarations(prev => ({ ...prev, [field]: value }));
  };

  const handleRuleToggle = (ruleKey, currentVal) => {
    setRuleStatuses(prev => ({
      ...prev,
      [ruleKey]: currentVal === 'COMPLIANT' ? 'VIOLATION' : 'COMPLIANT'
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!justification.trim() || justification.trim().length < 8) {
      setErrorMsg('Mandatory Statutory Justification is required (minimum 8 characters explaining the reason for amendment).');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        verdict,
        justification_note: justification.trim(),
        declarations: {
          mrp: { value: declarations.mrp, source: 'MANUAL_REVIEWER_OVERRIDE' },
          net_quantity: { value: declarations.net_quantity, source: 'MANUAL_REVIEWER_OVERRIDE' },
          manufacturing_date: { value: declarations.manufacturing_date, source: 'MANUAL_REVIEWER_OVERRIDE' },
          expiry_date: { value: declarations.expiry_date, source: 'MANUAL_REVIEWER_OVERRIDE' },
          manufacturer_details: { value: declarations.manufacturer_details, source: 'MANUAL_REVIEWER_OVERRIDE' },
          customer_care: { value: declarations.customer_care, source: 'MANUAL_REVIEWER_OVERRIDE' }
        },
        rule_statuses: ruleStatuses,
        officer_comments: justification.trim()
      };

      const res = await overrideInspectionVerdict(inspection.id, payload);
      if (res.data?.status === 'SUCCESS' || res.status === 200) {
        if (onSuccess) onSuccess(res.data);
        onClose();
      } else {
        setErrorMsg(res.data?.detail || 'Failed to submit adjudication override.');
      }
    } catch (err) {
      console.error('Adjudication override error:', err);
      setErrorMsg(err.response?.data?.detail || err.message || 'An error occurred while saving the amendment.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto animate-fadeIn">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-3xl w-full my-8 flex flex-col max-h-[92vh] overflow-hidden">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-[#4a0f0f] px-6 py-4 flex items-center justify-between text-white flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-400/40 flex items-center justify-center text-amber-300">
              <Gavel className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-black text-sm tracking-wide">Reviewer Adjudication Override & Amendment</h3>
                <span className="px-2 py-0.5 bg-amber-500/30 text-amber-200 text-[10px] font-black rounded border border-amber-400/30 uppercase">
                  Route 7B Gate
                </span>
              </div>
              <p className="text-xs text-slate-300 font-mono">
                Case ID: <span className="text-amber-300 font-bold">{inspection.id}</span> • {inspection.product_name}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6 overflow-y-auto flex-1 text-xs">
          
          {errorMsg && (
            <div className="bg-rose-50 border border-rose-200 p-3.5 rounded-xl flex items-start gap-2.5 text-rose-800">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-600" />
              <div className="flex-1 font-semibold">{errorMsg}</div>
            </div>
          )}

          {/* Section 1: Final Statutory Compliance Verdict */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-black uppercase tracking-wider text-slate-700 text-[11px] flex items-center gap-1.5">
                <Scale className="w-4 h-4 text-[#7a1c1c]" />
                1. Statutory Adjudication Verdict Override
              </span>
              <span className="text-[10px] font-bold text-slate-500">
                Original AI Status: <span className="font-black font-mono text-slate-800">{currentStatus}</span>
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <label className={`flex items-start gap-3 p-3 rounded-xl border-2 cursor-pointer transition ${
                verdict === '7A COMPLIANT'
                  ? 'bg-emerald-50/80 border-emerald-500 text-emerald-900 shadow-sm'
                  : 'bg-white border-slate-200 hover:border-slate-300 text-slate-700'
              }`}>
                <input
                  type="radio"
                  name="verdict"
                  value="7A COMPLIANT"
                  checked={verdict === '7A COMPLIANT'}
                  onChange={() => setVerdict('7A COMPLIANT')}
                  className="mt-0.5 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                />
                <div>
                  <div className="font-black text-xs flex items-center gap-1.5 text-emerald-800">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    Rule 7A Compliant (Pass / Clearance)
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Affirms all statutory packaging declarations satisfy Legal Metrology PCR 2011 requirements.
                  </p>
                </div>
              </label>

              <label className={`flex items-start gap-3 p-3 rounded-xl border-2 cursor-pointer transition ${
                verdict === '7B VIOLATION'
                  ? 'bg-rose-50/80 border-rose-500 text-rose-900 shadow-sm'
                  : 'bg-white border-slate-200 hover:border-slate-300 text-slate-700'
              }`}>
                <input
                  type="radio"
                  name="verdict"
                  value="7B VIOLATION"
                  checked={verdict === '7B VIOLATION'}
                  onChange={() => setVerdict('7B VIOLATION')}
                  className="mt-0.5 text-rose-600 focus:ring-rose-500 cursor-pointer"
                />
                <div>
                  <div className="font-black text-xs flex items-center gap-1.5 text-rose-800">
                    <ShieldAlert className="w-4 h-4 text-rose-600" />
                    Rule 7B Statutory Violation (Notice Under Section 36)
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Issues non-compliance finding requiring legal adjudication under Section 36 of 2009 Act.
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Section 2: Extracted Statutory Declarations Amendment */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-black uppercase tracking-wider text-slate-700 text-[11px] flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-[#7a1c1c]" />
                2. Amend Extracted Packaging Declarations (OCR Correction)
              </span>
              <span className="text-[10px] text-slate-500">Correct any misrecognized characters or values</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-[10px] font-black uppercase text-slate-600 mb-1">
                  Maximum Retail Price (MRP) & Tax Clause
                </label>
                <input
                  type="text"
                  value={declarations.mrp}
                  onChange={(e) => handleDeclarationChange('mrp', e.target.value)}
                  placeholder="e.g. ₹ 150.00 (Incl. of all taxes)"
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:border-[#7a1c1c]"
                />
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase text-slate-600 mb-1">
                  Net Quantity (Rule 6(1)(b))
                </label>
                <input
                  type="text"
                  value={declarations.net_quantity}
                  onChange={(e) => handleDeclarationChange('net_quantity', e.target.value)}
                  placeholder="e.g. 500 g / 1 L"
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:border-[#7a1c1c]"
                />
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase text-slate-600 mb-1">
                  Date of Manufacture / Import (Rule 6(1)(d))
                </label>
                <input
                  type="text"
                  value={declarations.manufacturing_date}
                  onChange={(e) => handleDeclarationChange('manufacturing_date', e.target.value)}
                  placeholder="e.g. 09/2026 or 15/09/2026"
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:border-[#7a1c1c]"
                />
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase text-slate-600 mb-1">
                  Best Before / Use By Period
                </label>
                <input
                  type="text"
                  value={declarations.expiry_date}
                  onChange={(e) => handleDeclarationChange('expiry_date', e.target.value)}
                  placeholder="e.g. 12 Months from packing"
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:border-[#7a1c1c]"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-[10px] font-black uppercase text-slate-600 mb-1">
                  Manufacturer / Packer / Importer Name & Full Address
                </label>
                <input
                  type="text"
                  value={declarations.manufacturer_details}
                  onChange={(e) => handleDeclarationChange('manufacturer_details', e.target.value)}
                  placeholder="e.g. M/s XYZ Foods Pvt. Ltd., Industrial Area, New Delhi - 110020"
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:border-[#7a1c1c]"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-[10px] font-black uppercase text-slate-600 mb-1">
                  Consumer Care Details (Phone / Email / Address)
                </label>
                <input
                  type="text"
                  value={declarations.customer_care}
                  onChange={(e) => handleDeclarationChange('customer_care', e.target.value)}
                  placeholder="e.g. Tel: 1800-11-4000, care@company.com"
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:border-[#7a1c1c]"
                />
              </div>
            </div>
          </div>

          {/* Section 3: Rule Evaluation Status Toggles */}
          {checksList.length > 0 && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
              <span className="font-black uppercase tracking-wider text-slate-700 text-[11px] flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-[#7a1c1c]" />
                3. PCR 2011 Rule Evaluation Status Overrides
              </span>

              <div className="divide-y divide-slate-200 border border-slate-200 rounded-lg bg-white overflow-hidden max-h-48 overflow-y-auto">
                {checksList.map((chk, idx) => {
                  const key = chk.rule_id || chk.field_name || `rule_${idx}`;
                  const currentRuleVal = ruleStatuses[key] || (chk.is_compliant ? 'COMPLIANT' : 'VIOLATION');
                  const isPass = currentRuleVal === 'COMPLIANT';

                  return (
                    <div key={key} className="p-2.5 flex items-center justify-between hover:bg-slate-50 transition">
                      <div className="pr-3">
                        <div className="font-black text-slate-800 flex items-center gap-1.5">
                          <span className="font-mono text-[#7a1c1c]">{chk.rule_id || chk.field_name}</span>
                          <span className="text-[10px] text-slate-500 font-normal">({chk.expected_rule || chk.regulation || 'Legal Metrology'})</span>
                        </div>
                        <p className="text-[10px] text-slate-500 truncate max-w-md">{chk.warning_message || chk.explanation || 'Statutory declaration check'}</p>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleRuleToggle(key, currentRuleVal)}
                        className={`px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-wider transition border flex items-center gap-1 cursor-pointer ${
                          isPass
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-300 hover:bg-emerald-100'
                            : 'bg-rose-50 text-rose-700 border-rose-300 hover:bg-rose-100'
                        }`}
                      >
                        {isPass ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : <ShieldAlert className="w-3 h-3 text-rose-600" />}
                        {isPass ? 'COMPLIANT' : 'VIOLATION'}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Section 4: Mandatory Statutory Justification */}
          <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-4 space-y-2">
            <div className="flex items-center justify-between">
              <label className="font-black uppercase tracking-wider text-amber-950 text-[11px] flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                4. Statutory Justification & Legal Reason for Amendment (MANDATORY) *
              </label>
              <span className="text-[10px] font-bold text-amber-800">Immutable Audit Trail Logged</span>
            </div>
            <p className="text-[11px] text-amber-900/80 font-medium">
              State the statutory reasoning for modifying this inspection verdict (e.g. secondary packaging panel verification, manufacturer clarification, or OCR noise correction).
            </p>
            <textarea
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              rows={3}
              required
              placeholder="e.g., Legitimate tax declaration detected in adjacent packaging panel under physical inspection; overriding initial false negative for Rule 6(1)(a)."
              className="w-full px-3 py-2.5 bg-white border border-amber-300 rounded-xl text-xs font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400/50 resize-none"
            />
          </div>

        </form>

        {/* Footer Actions */}
        <div className="bg-slate-100 px-6 py-4 border-t border-slate-200 flex items-center justify-between flex-shrink-0">
          <p className="text-[10px] text-slate-500 font-medium">
            * Submitting automatically logs an audit diff and broadcasts real-time alert to Administrators.
          </p>
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 rounded-xl border border-slate-300 transition"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting || !justification.trim()}
              className="px-5 py-2 text-xs font-black text-white bg-[#7a1c1c] hover:bg-[#601212] disabled:opacity-50 rounded-xl shadow-md transition flex items-center gap-2 cursor-pointer"
            >
              {submitting ? (
                <>
                  <Clock className="w-3.5 h-3.5 animate-spin" />
                  <span>Committing Override...</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>Commit Statutory Override</span>
                </>
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

import React from 'react';
import { CheckCircle2, UserCheck, AlertTriangle, HelpCircle } from 'lucide-react';

export default function ProvenanceBadge({ provenance }) {
  const prov = (provenance || 'AUTO_EXTRACTED_VERIFIED').toUpperCase();

  if (prov === 'AUTO_EXTRACTED_VERIFIED') {
    return (
      <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-black bg-emerald-50 text-emerald-900 border border-emerald-300">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
        <span>Auto-Extracted (Verified)</span>
      </span>
    );
  }

  if (prov === 'MANUALLY_ENTERED') {
    return (
      <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-black bg-blue-50 text-blue-900 border border-blue-300">
        <UserCheck className="w-3.5 h-3.5 text-blue-700" />
        <span>Manually Entered</span>
      </span>
    );
  }

  if (prov === 'NOT_PROVIDED_FLAGGED') {
    return (
      <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-black bg-red-50 text-red-900 border border-red-300">
        <AlertTriangle className="w-3.5 h-3.5 text-red-700" />
        <span>Not Provided (Flagged)</span>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-black bg-amber-50 text-amber-900 border border-amber-300">
      <HelpCircle className="w-3.5 h-3.5 text-amber-700" />
      <span>Unverified (Requires Sign-off)</span>
    </span>
  );
}

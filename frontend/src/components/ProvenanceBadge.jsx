import React from 'react';
import { CheckCircle2, UserCheck, AlertTriangle, HelpCircle } from 'lucide-react';

export default function ProvenanceBadge({ provenance }) {
  const prov = (provenance || 'AUTO_EXTRACTED_VERIFIED').toUpperCase();

  if (prov === 'AUTO_EXTRACTED_VERIFIED') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-500/30">
        <CheckCircle2 className="w-3 h-3" />
        <span>Auto-Extracted (Verified)</span>
      </span>
    );
  }

  if (prov === 'MANUALLY_ENTERED') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-950/80 text-blue-400 border border-blue-500/30">
        <UserCheck className="w-3 h-3" />
        <span>Manually Entered</span>
      </span>
    );
  }

  if (prov === 'NOT_PROVIDED_FLAGGED') {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-950/80 text-rose-400 border border-rose-500/30">
        <AlertTriangle className="w-3 h-3" />
        <span>Not Provided (Flagged)</span>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-950/80 text-amber-400 border border-amber-500/30">
      <HelpCircle className="w-3 h-3" />
      <span>Unverified (Requires Sign-off)</span>
    </span>
  );
}

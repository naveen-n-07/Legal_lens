import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, XCircle } from 'lucide-react';

export default function StatusBadge({ status }) {
  const s = status ? status.toUpperCase() : 'PENDING';

  if (s.includes('7A') || s.includes('COMPLIANT') || s === 'VERIFIED') {
    return (
      <span className="inline-flex items-center space-x-1.5 px-3 py-1 bg-emerald-50 text-emerald-900 border border-emerald-300 text-xs font-black rounded-full shadow-sm">
        <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
        <span>7A: COMPLIANT</span>
      </span>
    );
  } else if (s.includes('7B') || s.includes('VIOLATION') || s.includes('ISSUE')) {
    return (
      <span className="inline-flex items-center space-x-1.5 px-3 py-1 bg-red-50 text-red-900 border border-red-300 text-xs font-black rounded-full shadow-sm">
        <AlertTriangle className="w-4 h-4 text-red-700 flex-shrink-0" />
        <span>7B: VIOLATION / MANUAL REVIEW</span>
      </span>
    );
  } else if (s === 'REJECTED') {
    return (
      <span className="inline-flex items-center space-x-1.5 px-3 py-1 bg-rose-50 text-rose-900 border border-rose-300 text-xs font-black rounded-full shadow-sm">
        <XCircle className="w-4 h-4 text-rose-700 flex-shrink-0" />
        <span>REJECTED</span>
      </span>
    );
  } else {
    return (
      <span className="inline-flex items-center space-x-1.5 px-3 py-1 bg-sky-50 text-sky-900 border border-sky-300 text-xs font-black rounded-full shadow-sm">
        <Clock className="w-4 h-4 text-sky-700 flex-shrink-0" />
        <span>PENDING REVIEW</span>
      </span>
    );
  }
}

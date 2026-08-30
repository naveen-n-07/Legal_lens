import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, XCircle } from 'lucide-react';

export default function StatusBadge({ status }) {
  const s = status ? status.toUpperCase() : 'PENDING';

  if (s.includes('7A') || s.includes('COMPLIANT') || s === 'VERIFIED') {
    return (
      <span className="inline-flex items-center space-x-1.5 px-3 py-1 bg-emerald-950/70 text-emerald-400 border border-emerald-500/40 text-xs font-bold rounded-full shadow-sm">
        <CheckCircle2 className="w-3.5 h-3.5" />
        <span>7A: COMPLIANT</span>
      </span>
    );
  } else if (s.includes('7B') || s.includes('VIOLATION') || s.includes('ISSUE')) {
    return (
      <span className="inline-flex items-center space-x-1.5 px-3 py-1 bg-amber-950/70 text-amber-300 border border-amber-500/40 text-xs font-bold rounded-full shadow-sm">
        <AlertTriangle className="w-3.5 h-3.5" />
        <span>7B: VIOLATION / MANUAL REVIEW</span>
      </span>
    );
  } else if (s === 'REJECTED') {
    return (
      <span className="inline-flex items-center space-x-1.5 px-3 py-1 bg-rose-950/70 text-rose-400 border border-rose-500/40 text-xs font-bold rounded-full shadow-sm">
        <XCircle className="w-3.5 h-3.5" />
        <span>REJECTED</span>
      </span>
    );
  } else {
    return (
      <span className="inline-flex items-center space-x-1.5 px-3 py-1 bg-sky-950/70 text-sky-400 border border-sky-500/40 text-xs font-bold rounded-full shadow-sm">
        <Clock className="w-3.5 h-3.5" />
        <span>PENDING REVIEW</span>
      </span>
    );
  }
}

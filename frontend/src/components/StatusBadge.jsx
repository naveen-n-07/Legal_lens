import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, XCircle, ShieldCheck, ShieldAlert } from 'lucide-react';

export default function StatusBadge({ status, size = 'default' }) {
  const s = status ? status.toUpperCase() : 'PENDING';

  const isSmall = size === 'sm';

  if (s.includes('7A') || s.includes('COMPLIANT') || s === 'VERIFIED') {
    return (
      <span className={`inline-flex items-center gap-1.5 ${isSmall ? 'px-2 py-0.5 text-2xs' : 'px-2.5 py-1 text-xs'} font-black rounded-md bg-emerald-50 text-emerald-800 border border-emerald-300/80 shadow-sm font-sans tracking-wide`}>
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse-subtle flex-shrink-0" />
        <CheckCircle2 className={`${isSmall ? 'w-3 h-3' : 'w-3.5 h-3.5'} text-emerald-700 flex-shrink-0`} />
        <span>7A: COMPLIANT</span>
      </span>
    );
  } else if (s.includes('7B') || s.includes('VIOLATION') || s.includes('ISSUE')) {
    return (
      <span className={`inline-flex items-center gap-1.5 ${isSmall ? 'px-2 py-0.5 text-2xs' : 'px-2.5 py-1 text-xs'} font-black rounded-md bg-rose-50 text-rose-800 border border-rose-300/80 shadow-sm font-sans tracking-wide`}>
        <span className="w-1.5 h-1.5 rounded-full bg-rose-600 animate-pulse-subtle flex-shrink-0" />
        <AlertTriangle className={`${isSmall ? 'w-3 h-3' : 'w-3.5 h-3.5'} text-rose-700 flex-shrink-0`} />
        <span>7B: VIOLATION</span>
      </span>
    );
  } else if (s === 'REJECTED') {
    return (
      <span className={`inline-flex items-center gap-1.5 ${isSmall ? 'px-2 py-0.5 text-2xs' : 'px-2.5 py-1 text-xs'} font-black rounded-md bg-slate-100 text-slate-800 border border-slate-300 shadow-sm font-sans tracking-wide`}>
        <XCircle className={`${isSmall ? 'w-3 h-3' : 'w-3.5 h-3.5'} text-slate-600 flex-shrink-0`} />
        <span>REJECTED</span>
      </span>
    );
  } else {
    return (
      <span className={`inline-flex items-center gap-1.5 ${isSmall ? 'px-2 py-0.5 text-2xs' : 'px-2.5 py-1 text-xs'} font-black rounded-md bg-amber-50 text-amber-900 border border-amber-300/80 shadow-sm font-sans tracking-wide`}>
        <span className="w-1.5 h-1.5 rounded-full bg-amber-600 animate-pulse-subtle flex-shrink-0" />
        <Clock className={`${isSmall ? 'w-3 h-3' : 'w-3.5 h-3.5'} text-amber-700 flex-shrink-0`} />
        <span>PENDING REVIEW</span>
      </span>
    );
  }
}

import React from 'react';
import { 
  Building2, 
  Calendar, 
  MapPin, 
  User, 
  Eye, 
  Download, 
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Sparkles
} from 'lucide-react';
import StatusBadge from './StatusBadge';
import { formatDateTime, getRelativeTime } from '../utils/dateUtils';

export default function AuditMobileCard({ 
  item, 
  role = 'inspector', 
  onView, 
  onDownload, 
  rank, 
  waitTime,
  isFifoQueue = false
}) {
  if (!item) return null;

  return (
    <div className={`bg-white border rounded-2xl p-4 shadow-card hover:shadow-card-hover transition-all duration-200 space-y-3.5 touch-manipulation ${
      rank === 1 ? 'border-amber-300 ring-2 ring-amber-100 bg-amber-50/20' : 'border-slate-200/90'
    }`}>
      
      {/* 1. Header: Inspection ID & Rank / Submission Time */}
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
        <div className="flex items-center gap-2">
          {rank && (
            <span className={`inline-flex items-center justify-center px-2 py-0.5 rounded-md text-2xs font-mono font-black ${
              rank === 1 
                ? 'bg-[#7a1c1c] text-white shadow-xs' 
                : rank <= 3 
                  ? 'bg-amber-500 text-slate-950' 
                  : 'bg-slate-200 text-slate-800'
            }`}>
              #{rank}
            </span>
          )}
          <span className="px-2 py-0.5 bg-red-50 text-[#7A1C1C] border border-red-200 rounded-md font-mono text-2xs font-extrabold tracking-wide">
            {item.id}
          </span>
          {item.category && (
            <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-2xs font-bold truncate max-w-[110px]">
              {item.category}
            </span>
          )}
        </div>

        <div className="text-[11px] font-mono text-slate-500 font-semibold flex items-center gap-1">
          <Clock className={`w-3 h-3 ${waitTime?.isUrgent ? 'text-rose-600' : 'text-slate-400'}`} />
          <span className={waitTime?.isUrgent ? 'text-rose-700 font-black' : ''}>
            {waitTime ? waitTime.text : (item.created_at ? getRelativeTime(item.created_at) : 'Active')}
          </span>
        </div>
      </div>

      {/* 2. Commodity Info & Brand */}
      <div className="space-y-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-base font-black text-slate-900 leading-snug tracking-tight font-display">
            {item.product_name || "Packaged Commodity"}
          </h3>
        </div>

        {item.brand_name && (
          <p className="text-xs text-slate-500 font-semibold">
            Brand / Manufacturer: <span className="text-slate-800 font-bold">{item.brand_name}</span>
          </p>
        )}

        <div className="flex items-center gap-3 text-2xs text-slate-600 font-medium pt-0.5">
          <div className="flex items-center gap-1 truncate">
            <User className="w-3 h-3 text-slate-400 flex-shrink-0" />
            <span className="truncate">{item.inspector_name || 'Field Inspector'}</span>
          </div>
          {item.location && (
            <div className="flex items-center gap-1 truncate text-slate-500">
              <MapPin className="w-3 h-3 text-slate-400 flex-shrink-0" />
              <span className="truncate">{item.location}</span>
            </div>
          )}
        </div>
      </div>

      {/* 3. Statutory Compliance Verdict Banner */}
      <div className="pt-1 flex items-center justify-between bg-slate-50 p-2.5 rounded-xl border border-slate-100">
        <span className="text-2xs font-black uppercase text-slate-600 tracking-wider">
          Statutory Status:
        </span>
        <StatusBadge status={item.overall_status} size="default" />
      </div>

      {/* 4. Officer Findings Note (If Adjudicated) */}
      {item.officer_decision && (
        <div className="p-2.5 bg-emerald-50/70 border border-emerald-200/80 rounded-xl text-2xs space-y-0.5">
          <div className="font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-emerald-700" />
            <span>Adjudication Signed: {item.officer_decision}</span>
          </div>
          {item.officer_comments && (
            <p className="text-slate-700 italic font-medium truncate">
              "{item.officer_comments}"
            </p>
          )}
        </div>
      )}

      {/* 5. Mobile Action Row (Minimum 44px Touch Targets) */}
      <div className="grid grid-cols-2 gap-2 pt-1">
        <button
          onClick={() => onView ? onView(item) : null}
          className="min-h-[44px] px-3 py-2.5 bg-[#7A1C1C] hover:bg-[#631515] active:bg-[#4A1010] text-white font-black text-xs rounded-xl shadow-xs transition-all flex items-center justify-center gap-1.5 touch-manipulation cursor-pointer"
        >
          <Eye className="w-4 h-4" />
          <span>{isFifoQueue ? `Adjudicate ${rank ? `#${rank}` : ''}` : (role === 'inspector' ? 'View PDF' : 'Audit Case')}</span>
        </button>

        <button
          onClick={() => onDownload ? onDownload(item.id) : null}
          className="min-h-[44px] px-3 py-2.5 bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-800 font-bold text-xs rounded-xl border border-slate-200 transition-all flex items-center justify-center gap-1.5 touch-manipulation cursor-pointer"
        >
          <Download className="w-4 h-4 text-slate-600" />
          <span>Export PDF</span>
        </button>
      </div>

    </div>
  );
}

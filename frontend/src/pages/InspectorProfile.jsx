import React from 'react';
import { User, ShieldCheck, MapPin, Award, Building, Mail, Phone, Lock, Calendar } from 'lucide-react';
import ProvenanceBadge from '../components/ProvenanceBadge';

export default function InspectorProfile({ user }) {
  const name = user?.name || user?.user_name || 'Official Field Inspector';
  const role = user?.role || 'inspector';

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="bg-white border border-[#E2E8F0] p-8 rounded-3xl shadow-[0_4px_20px_rgba(0,0,0,0.05)] space-y-6">
        
        {/* Header Profile Badge */}
        <div className="flex flex-col sm:flex-row items-center space-y-4 sm:space-y-0 sm:space-x-6 pb-6 border-b border-[#E2E8F0]">
          <div className="w-20 h-20 bg-slate-900 text-white rounded-full flex items-center justify-center text-2xl font-black shadow-lg border-2 border-red-600 uppercase">
            {name.split(' ').map(n => n[0]).join('').slice(0, 2)}
          </div>

          <div className="text-center sm:text-left space-y-1">
            <div className="flex items-center space-x-2 justify-center sm:justify-start">
              <h1 className="text-2xl font-black text-[#1E293B]">{name}</h1>
              <span className="px-3 py-1 bg-red-100 text-red-800 text-xs font-black rounded-full border border-red-300 uppercase">
                {role.replace('_', ' ')}
              </span>
            </div>
            <p className="text-sm text-[#64748B] font-extrabold">
              Legal Metrology Enforcement Officer • Badge ID: LMPC-INSP-2026-DEL
            </p>
          </div>
        </div>

        {/* Credentials Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-4 bg-[#F8F9FA] border border-[#E2E8F0] rounded-2xl space-y-1">
            <span className="text-[#64748B] font-extrabold block flex items-center space-x-1.5">
              <Building className="w-4 h-4 text-red-600" />
              <span>Department Ministry</span>
            </span>
            <span className="text-sm font-black text-[#1E293B] block">
              Ministry of Consumer Affairs, Food & Public Distribution
            </span>
          </div>

          <div className="p-4 bg-[#F8F9FA] border border-[#E2E8F0] rounded-2xl space-y-1">
            <span className="text-[#64748B] font-extrabold block flex items-center space-x-1.5">
              <MapPin className="w-4 h-4 text-red-600" />
              <span>Assigned Enforcement Zone</span>
            </span>
            <span className="text-sm font-black text-[#1E293B] block">
              Central Enforcement Wing • Delhi NCR Region
            </span>
          </div>

          <div className="p-4 bg-[#F8F9FA] border border-[#E2E8F0] rounded-2xl space-y-1">
            <span className="text-[#64748B] font-extrabold block flex items-center space-x-1.5">
              <Mail className="w-4 h-4 text-red-600" />
              <span>Official Email Address</span>
            </span>
            <span className="text-sm font-black text-red-700 font-mono block">
              {user?.email || 'inspector@legalmetrology.gov.in'}
            </span>
          </div>

          <div className="p-4 bg-[#F8F9FA] border border-[#E2E8F0] rounded-2xl space-y-1">
            <span className="text-[#64748B] font-extrabold block flex items-center space-x-1.5">
              <ShieldCheck className="w-4 h-4 text-red-600" />
              <span>Security Access Level</span>
            </span>
            <span className="text-sm font-black text-emerald-700 block">
              Level 2 Field Inspector Clearance (Active)
            </span>
          </div>
        </div>

      </div>
    </div>
  );
}

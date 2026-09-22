import React, { useState } from 'react';
import { 
  Scale, 
  Search, 
  Bell, 
  User, 
  LogOut, 
  Globe, 
  ShieldCheck,
  ChevronDown
} from 'lucide-react';
import AdminNotificationBell from './AdminNotificationBell';

export default function Navbar({ user, onLogout }) {
  const userName = user?.name || user?.user_name || 'Official User';
  const role = user?.role || 'inspector';

  const [searchCategory, setSearchCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    console.log("Portal Search:", searchCategory, searchQuery);
  };

  return (
    <header className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-50">
      
      {/* 1. Top Flag Tricolor Accent Strip & National Portal Utility Bar */}
      <div className="bg-slate-900 text-white text-xs py-2 px-6 flex items-center justify-between border-b border-slate-800">
        {/* Tricolor Accent Bar */}
        <div className="flex items-center space-x-2.5">
          <div className="h-2.5 w-9 rounded flex overflow-hidden">
            <div className="w-1/3 bg-[#FF9933]"></div>
            <div className="w-1/3 bg-white"></div>
            <div className="w-1/3 bg-[#138808]"></div>
          </div>
          <span className="font-extrabold text-slate-200 tracking-wide">
            भारत सरकार | GOVERNMENT OF INDIA
          </span>
          <span className="text-slate-600">|</span>
          <span className="hidden lg:inline text-slate-300 font-semibold">
            उपभोक्ता मामले, खाद्य और सार्वजनिक वितरण मंत्रालय | Ministry of Consumer Affairs
          </span>
        </div>

        {/* Accessibility & Language Tools */}
        <div className="flex items-center space-x-4 font-bold text-slate-200 text-xs">
          <button className="hover:text-white transition">Skip to main content</button>
          <span className="text-slate-700">|</span>
          <div className="flex items-center space-x-1">
            <button className="px-2 py-0.5 text-xs font-black bg-slate-800 hover:bg-slate-700 rounded border border-slate-700">A-</button>
            <button className="px-2 py-0.5 text-xs font-black bg-slate-800 hover:bg-slate-700 rounded border border-slate-700">A</button>
            <button className="px-2 py-0.5 text-xs font-black bg-slate-800 hover:bg-slate-700 rounded border border-slate-700">A+</button>
          </div>
          <span className="text-slate-700">|</span>
          <div className="flex items-center space-x-1 hover:text-white cursor-pointer font-extrabold">
            <Globe className="w-4 h-4 text-blue-400" />
            <span>English / हिन्दी</span>
          </div>
        </div>
      </div>

      {/* 2. Main Portal Header (White Surface with National Portal Styling) */}
      <div className="px-6 py-3.5 flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Left Branding Logo & Title */}
        <div className="flex items-center space-x-4 flex-shrink-0">
          <div className="w-12 h-12 bg-gradient-to-br from-red-600 to-red-800 text-white rounded-xl flex items-center justify-center shadow-md border border-red-700">
            <Scale className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-black text-slate-900 tracking-tight leading-none">
                Legal Metrology Portal
              </h1>
              <span className="px-2.5 py-0.5 bg-red-100 text-red-700 text-xs font-black rounded border border-red-200">
                INDIA.GOV.IN INSP
              </span>
            </div>
            <p className="text-sm text-slate-600 font-bold mt-1">
              Packaged Commodities Rules (PCR), 2011 Compliance System
            </p>
          </div>
        </div>

        {/* Center Prominent Global Search Bar */}
        <form onSubmit={handleSearchSubmit} className="flex-1 max-w-2xl w-full flex items-center bg-slate-100 p-1.5 rounded-xl border border-slate-300 focus-within:border-red-600 focus-within:ring-2 focus-within:ring-red-600/30 transition shadow-inner">
          <select 
            value={searchCategory}
            onChange={(e) => setSearchCategory(e.target.value)}
            className="bg-white text-slate-800 text-sm font-extrabold px-3.5 py-2.5 rounded-lg border border-slate-200 focus:outline-none cursor-pointer"
          >
            <option value="all">All Categories</option>
            <option value="rules">Statutory Rules (1-34)</option>
            <option value="inspections">Inspection Scans</option>
            <option value="schedule2">Schedule II Sizes</option>
          </select>

          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search Rules, Violations, MRP Tax Clauses, LMPC Certificates..."
            className="flex-1 bg-transparent px-3.5 text-sm text-slate-900 font-semibold placeholder-slate-400 focus:outline-none"
          />

          <button
            type="submit"
            className="px-5 py-2.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white font-black text-sm rounded-lg transition shadow-md flex items-center space-x-1.5 flex-shrink-0"
          >
            <Search className="w-4 h-4" />
            <span>SEARCH</span>
          </button>
        </form>

        {/* Right User & Role Indicator Badge + Admin Notification Bell */}
        <div className="flex items-center space-x-4 flex-shrink-0">
          {role === 'admin' && (
            <div className="flex items-center">
              <AdminNotificationBell user={user} />
            </div>
          )}

          <div className="flex items-center space-x-3 pl-4 border-l border-slate-200">
            <div className="w-10 h-10 bg-slate-800 text-white rounded-full flex items-center justify-center font-black text-sm shadow border border-slate-700 uppercase">
              {userName.split(' ').map(n => n[0]).join('').slice(0, 2)}
            </div>

            <div className="text-left">
              <div className="text-sm font-black text-slate-900 leading-none">{userName}</div>
              <span className={`inline-block text-xs font-black px-2 py-0.5 rounded mt-1 uppercase border ${
                role === 'admin' 
                  ? 'bg-purple-100 text-purple-800 border-purple-300' 
                  : role === 'reviewing_officer' 
                    ? 'bg-amber-100 text-amber-900 border-amber-300' 
                    : 'bg-emerald-100 text-emerald-900 border-emerald-300'
              }`}>
                {role?.replace('_', ' ')}
              </span>
            </div>

            <button 
              onClick={onLogout}
              title="Logout"
              className="p-2.5 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>

      </div>
    </header>
  );
}

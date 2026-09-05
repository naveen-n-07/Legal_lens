import React, { useState } from 'react';
import { ShieldCheck, Lock, ExternalLink, Cookie, ChevronDown, ChevronUp } from 'lucide-react';

export default function Footer() {
  const [showCookieBanner, setShowCookieBanner] = useState(true);
  const [collapsed, setCollapsed] = useState(true);

  if (collapsed) {
    return (
      <footer className="bg-slate-900 text-white text-xs border-t-2 border-red-600 px-6 py-2 flex items-center justify-between shadow-inner">
        <div className="flex items-center space-x-2 text-[11px] text-slate-400 truncate">
          <span className="font-semibold text-slate-300">
            SIH 2026 Problem Statement 26034
          </span>
          <span>•</span>
          <span className="hidden md:inline">Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution</span>
        </div>
        <button 
          onClick={() => setCollapsed(false)}
          className="flex items-center space-x-1 text-[11px] text-red-400 hover:text-red-300 font-bold underline cursor-pointer flex-shrink-0"
        >
          <span>Expand Portal Footer</span>
          <ChevronUp className="w-3.5 h-3.5" />
        </button>
      </footer>
    );
  }

  return (
    <footer className="bg-slate-900 text-white text-xs border-t-4 border-red-600 relative">
      
      {/* Footer Collapse Control Bar */}
      <div className="bg-slate-950 border-b border-slate-800 px-6 py-1.5 flex items-center justify-between">
        <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">
          Statutory Government Directory & Information Guidelines
        </span>
        <button 
          onClick={() => setCollapsed(true)}
          className="flex items-center space-x-1 text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold px-2.5 py-0.5 rounded border border-slate-700 transition cursor-pointer"
        >
          <span>Minimize Footer</span>
          <ChevronDown className="w-3 h-3" />
        </button>
      </div>

      {/* 1. Cookie Consent & Data Privacy Banner (India.gov.in Style) */}
      {showCookieBanner && (
        <div className="bg-slate-950 border-b border-slate-800 p-4">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center space-x-3 text-slate-300 text-xs">
              <Cookie className="w-5 h-5 text-amber-400 flex-shrink-0" />
              <span>
                <b>Cookie Notice:</b> We use essential cookies to maintain secure sessions and compliance audit logs under statutory IT rules.
              </span>
            </div>

            <div className="flex items-center space-x-2 flex-shrink-0">
              <button 
                onClick={() => setShowCookieBanner(false)}
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded border border-slate-700 transition"
              >
                CUSTOMIZE COOKIES
              </button>
              <button 
                onClick={() => setShowCookieBanner(false)}
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded border border-slate-700 transition"
              >
                DECLINE
              </button>
              <button 
                onClick={() => setShowCookieBanner(false)}
                className="px-4 py-1.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white font-extrabold text-xs rounded transition shadow-md"
              >
                ACCEPT ALL COOKIES
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Main Government Footer Section */}
      <div className="max-w-7xl mx-auto p-8 space-y-6">
        
        {/* Navigation Link Directory */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 border-b border-slate-800 pb-6 text-slate-400">
          <div>
            <h4 className="text-white font-extrabold mb-2 uppercase text-[11px] tracking-wider text-red-500">
              Information & Guidelines
            </h4>
            <ul className="space-y-1.5 text-[11px]">
              <li><a href="#" className="hover:text-white transition">Legal Metrology Act, 2009</a></li>
              <li><a href="#" className="hover:text-white transition">Packaged Commodities Rules, 2011</a></li>
              <li><a href="#" className="hover:text-white transition">Rule 7 Table-I Font Matrix</a></li>
              <li><a href="#" className="hover:text-white transition">Schedule II Standard Package Sizes</a></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-extrabold mb-2 uppercase text-[11px] tracking-wider text-red-500">
              Portal Services
            </h4>
            <ul className="space-y-1.5 text-[11px]">
              <li><a href="#" className="hover:text-white transition">Live Camera Commodity Scanner</a></li>
              <li><a href="#" className="hover:text-white transition">Senior Officer Adjudication Queue</a></li>
              <li><a href="#" className="hover:text-white transition">LMPC Certificate Generator</a></li>
              <li><a href="#" className="hover:text-white transition">National Inspection Audit Registry</a></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-extrabold mb-2 uppercase text-[11px] tracking-wider text-red-500">
              Policies & Help
            </h4>
            <ul className="space-y-1.5 text-[11px]">
              <li><a href="#" className="hover:text-white transition">Terms & Conditions</a></li>
              <li><a href="#" className="hover:text-white transition">Privacy Policy & IT Act Security</a></li>
              <li><a href="#" className="hover:text-white transition">Hyperlinking Policy</a></li>
              <li><a href="#" className="hover:text-white transition">Copyright & Attribution Policy</a></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white font-extrabold mb-2 uppercase text-[11px] tracking-wider text-red-500">
              Government Portals
            </h4>
            <ul className="space-y-1.5 text-[11px]">
              <li><a href="https://india.gov.in" target="_blank" rel="noreferrer" className="hover:text-white flex items-center space-x-1"><span>National Portal of India</span> <ExternalLink className="w-3 h-3" /></a></li>
              <li><a href="https://consumeraffairs.nic.in" target="_blank" rel="noreferrer" className="hover:text-white flex items-center space-x-1"><span>Ministry of Consumer Affairs</span> <ExternalLink className="w-3 h-3" /></a></li>
              <li><a href="#" className="hover:text-white transition">Digital India Programme</a></li>
            </ul>
          </div>
        </div>

        {/* Bottom Statutory Disclaimer & Copyright */}
        <div className="flex flex-col md:flex-row items-center justify-between text-[11px] text-slate-400 gap-4">
          <div>
            <p className="font-semibold text-slate-300">
              Designed and Developed for SIH 2026 Problem Statement 26034. Hosted by Government Data Centre.
            </p>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Content Owned, Maintained and Updated by Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution.
            </p>
          </div>

          <div className="flex items-center space-x-3 text-[10px] font-mono text-slate-400 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 flex-shrink-0">
            <span>Last Updated: 30 Aug 2026</span>
            <span>|</span>
            <span className="text-emerald-400 font-bold">System Status: ONLINE</span>
          </div>
        </div>

      </div>
    </footer>
  );
}

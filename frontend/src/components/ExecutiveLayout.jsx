import React, { useState, useEffect } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  Scale,
  LayoutDashboard,
  Camera,
  ShieldAlert,
  History,
  FileText,
  Gavel,
  Lock,
  User,
  LogOut,
  Search,
  ChevronLeft,
  ChevronRight,
  PlusCircle,
  Globe,
  Bell,
  Cpu,
  CheckCircle2,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  Command
} from 'lucide-react';
import AdminNotificationBell from './AdminNotificationBell';
import MobileNavigation from './MobileNavigation';

export default function ExecutiveLayout({ user, onLogout, children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchCategory, setSearchCategory] = useState('all');
  const [searchFocused, setSearchFocused] = useState(false);

  const userName = user?.name || user?.user_name || 'Official User';
  const role = user?.role || 'inspector';
  const userDesignation = user?.designation || (role === 'admin' ? 'System Administrator' : role === 'reviewing_officer' ? 'Senior Legal Metrology Officer' : 'Field Enforcement Inspector');
  const userZone = user?.zone_office || 'Central Ministry HQ, New Delhi';

  // Keyboard shortcut for search (Ctrl + K / Cmd + K)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('executive-global-search');
        if (searchInput) searchInput.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    navigate(`/history?q=${encodeURIComponent(searchQuery)}`);
  };

  // Navigation Items by Role
  let navItems = [];
  if (role === 'admin') {
    navItems = [
      { path: '/admin/control', label: 'Command & Control', icon: LayoutDashboard, badge: 'CORE' },
      { path: '/history', label: 'National Audit Registry', icon: History },
      { path: '/officer/review', label: 'FIFO Review Queue', icon: ShieldAlert, badge: 'FIFO' },
      { path: '/reports', label: 'Analytics & Compliance Reports', icon: FileText },
    ];
  } else if (role === 'reviewing_officer') {
    navItems = [
      { path: '/dashboard', label: 'Reviewer Dashboard', icon: LayoutDashboard },
      { path: '/officer/review', label: 'FIFO Review Queue', icon: ShieldAlert, badge: 'FIFO' },
      { path: '/history', label: 'National Audit Registry', icon: History },
      { path: '/reports', label: 'Analytics & Section 36 Reports', icon: FileText },
    ];
  } else {
    // Field Inspector
    navItems = [
      { path: '/dashboard', label: 'Field Dashboard', icon: LayoutDashboard },
      { path: '/inspection/new', label: 'New Field Scan', icon: PlusCircle, badge: 'NEW' },
      { path: '/scanner', label: 'Live Camera Scanner', icon: Camera, badge: 'LIVE' },
      { path: '/history', label: 'Inspection Audit History', icon: History },
      { path: '/profile', label: 'Inspector Profile', icon: User },
    ];
  }

  const roleMeta = {
    admin: {
      label: 'SYSTEM ADMINISTRATOR',
      badgeClass: 'bg-purple-50 text-purple-800 border-purple-300',
      description: 'System Governance & Rule Matrix Control'
    },
    reviewing_officer: {
      label: 'REVIEWING SENIOR OFFICER',
      badgeClass: 'bg-amber-50 text-amber-900 border-amber-300',
      description: 'Statutory Adjudication & Certificate Sign-Off'
    },
    inspector: {
      label: 'FIELD ENFORCEMENT INSPECTOR',
      badgeClass: 'bg-emerald-50 text-emerald-900 border-emerald-300',
      description: 'Field Evidence Capture & OCR Verification'
    }
  }[role] || { label: role, badgeClass: 'bg-slate-100 text-slate-800 border-slate-300', description: 'Metrology Portal Access' };

  return (
    <div className="h-screen bg-[#F8FAFC] flex flex-col font-sans text-slate-900 overflow-hidden select-text">
      
      {/* ══════════════════════════════════════════════════════════════════════════
          1. MOBILE APP SHELL (Top Header + Slide-Over Drawer + Bottom Action Bar)
          ══════════════════════════════════════════════════════════════════════════ */}
      <MobileNavigation user={user} onLogout={onLogout} />

      {/* ══════════════════════════════════════════════════════════════════════════
          2. DESKTOP TOP NATIONAL UTILITY & TRICOLOR RIBBON (hidden on mobile)
          ══════════════════════════════════════════════════════════════════════════ */}
      <header className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-30 hidden md:block flex-shrink-0">
        
        {/* Tricolor Accent Strip */}
        <div className="bg-[#0F2744] text-white text-xs py-1.5 px-4 sm:px-6 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="h-2 w-8 rounded-sm flex overflow-hidden shadow-sm flex-shrink-0">
              <div className="w-1/3 bg-[#FF9933]" />
              <div className="w-1/3 bg-white" />
              <div className="w-1/3 bg-[#138808]" />
            </div>
            <div className="flex items-center space-x-2 text-2xs font-extrabold tracking-wider text-slate-200 uppercase">
              <span>भारत सरकार</span>
              <span className="text-slate-500">|</span>
              <span>GOVERNMENT OF INDIA</span>
              <span className="hidden md:inline text-slate-500">•</span>
              <span className="hidden md:inline text-slate-300 font-semibold lowercase">
                Ministry of Consumer Affairs, Food & Public Distribution
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3 text-2xs font-bold text-slate-300">
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="font-mono text-emerald-300 font-bold">METRIX-LM v2.1</span>
            </div>
            <span className="text-slate-600">|</span>
            <div className="flex items-center space-x-1 hover:text-white cursor-pointer transition">
              <Globe className="w-3.5 h-3.5 text-sky-400" />
              <span>ENG / हिन्दी</span>
            </div>
          </div>
        </div>

        {/* Main Executive Brand & Action Bar */}
        <div className="px-4 sm:px-6 py-2.5 flex items-center justify-between gap-4">
          
          {/* Left Brand Identity Lockup */}
          <div className="flex items-center space-x-3.5 flex-shrink-0">
            <div className="w-10 h-10 bg-gradient-to-br from-[#7A1C1C] via-[#631515] to-[#4A1010] text-white rounded-xl flex items-center justify-center shadow-md border border-[#8B2323]">
              <Scale className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-base font-black tracking-tight text-slate-900 font-display">
                  LegalLens <span className="text-[#7A1C1C]">METRIX-LM</span>
                </span>
                <span className="px-2 py-0.5 bg-red-50 text-[#7A1C1C] text-[10px] font-black rounded border border-red-200 uppercase font-mono">
                  PCR 2011
                </span>
              </div>
              <p className="text-2xs text-slate-500 font-bold leading-tight">
                Statutory Compliance & Legal Metrology Adjudication Engine
              </p>
            </div>
          </div>

          {/* Center Global Search (Prominent & Accessible with Ctrl+K) */}
          <form onSubmit={handleSearchSubmit} className="flex-1 max-w-xl flex items-center">
            <div className={`w-full flex items-center bg-slate-50 border ${searchFocused ? 'border-[#7A1C1C] ring-2 ring-[#7A1C1C]/20 bg-white' : 'border-slate-200 hover:border-slate-300'} px-3 py-1.5 rounded-xl transition duration-150`}>
              <Search className="w-4 h-4 text-slate-400 mr-2 flex-shrink-0" />
              <input
                id="executive-global-search"
                type="text"
                value={searchQuery}
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setSearchFocused(false)}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search inspections, rules (Rule 6/7), MRP tax clauses, companies..."
                className="w-full bg-transparent text-xs font-semibold text-slate-900 placeholder:text-slate-400 focus:outline-none"
              />
              <div className="flex items-center gap-1 pl-2 border-l border-slate-200 flex-shrink-0">
                <kbd className="px-1.5 py-0.5 text-[10px] font-mono font-bold bg-white text-slate-500 border border-slate-200 rounded shadow-2xs">
                  Ctrl K
                </kbd>
              </div>
            </div>
          </form>

          {/* Right Header Badges + Notification + Profile */}
          <div className="flex items-center space-x-3 flex-shrink-0">
            
            {/* Real-time Notification Bell for Admins / Officers */}
            <AdminNotificationBell user={user} />

            {/* User Profile Pill */}
            <div className="flex items-center space-x-3 pl-3 border-l border-slate-200">
              <div className="w-9 h-9 bg-gradient-to-br from-[#0F2744] to-[#1E3A5F] text-white rounded-xl flex items-center justify-center font-black text-xs shadow-sm border border-slate-700 uppercase font-mono">
                {userName.split(' ').map(n => n[0]).join('').slice(0, 2)}
              </div>

              <div className="text-left hidden lg:block">
                <div className="text-xs font-black text-slate-900 leading-tight truncate max-w-[140px]">
                  {userName}
                </div>
                <div className={`inline-block text-[10px] font-black px-1.5 py-0.2 rounded mt-0.5 uppercase border ${roleMeta.badgeClass}`}>
                  {roleMeta.label.split(' ')[0]}
                </div>
              </div>

              <button
                onClick={onLogout}
                title="Log out of Government Portal"
                className="p-2 text-slate-500 hover:text-red-700 hover:bg-red-50 rounded-xl transition cursor-pointer border border-transparent hover:border-red-200"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>

        </div>
      </header>

      {/* ══════════════════════════════════════════════════════════════════════════
          3. MAIN WORKSPACE: DESKTOP SIDEBAR + RESPONSIVE CONTENT CANVAS
          ══════════════════════════════════════════════════════════════════════════ */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        
        {/* Executive Unified Desktop Sidebar (hidden on mobile) */}
        <aside className={`bg-white border-r border-slate-200 shadow-sm transition-all duration-300 hidden md:flex flex-col flex-shrink-0 ${collapsed ? 'w-20' : 'w-72'}`}>
          
          {/* Navigation Links */}
          <div className="p-3.5 flex-1 space-y-1.5 overflow-y-auto">
            
            {/* Role Header (When Expanded) */}
            {!collapsed && (
              <div className="px-3 py-2 mb-2 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                    ACTIVE WORKSPACE
                  </span>
                  <span className="text-xs font-black text-slate-800">
                    {roleMeta.label}
                  </span>
                </div>
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              </div>
            )}

            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-black transition-all duration-150 border ${
                      isActive
                        ? 'bg-[#FDF2F2] text-[#7A1C1C] border-red-200 shadow-xs'
                        : 'text-slate-700 border-transparent hover:bg-slate-50 hover:text-[#7A1C1C] hover:border-slate-200'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {!collapsed && <span className="truncate flex-1">{item.label}</span>}
                  {!collapsed && item.badge && (
                    <span className={`text-[10px] px-2 py-0.5 rounded font-black border font-mono ${
                      item.badge === 'LIVE'
                        ? 'bg-emerald-100 text-emerald-900 border-emerald-300 animate-pulse'
                        : item.badge === 'CORE'
                          ? 'bg-purple-100 text-purple-900 border-purple-300'
                          : item.badge === 'FIFO'
                            ? 'bg-amber-100 text-amber-900 border-amber-300'
                            : 'bg-rose-100 text-rose-900 border-rose-300'
                    }`}>
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}

            {/* Official Authority Card */}
            {!collapsed && (
              <div className="mt-6 p-4 bg-gradient-to-br from-slate-50 to-slate-100/70 rounded-2xl border border-slate-200 text-2xs space-y-2">
                <div className="flex items-center space-x-1.5 font-black text-[#7A1C1C]">
                  <Gavel className="w-3.5 h-3.5" />
                  <span className="uppercase tracking-wider">Statutory Authority</span>
                </div>
                <p className="text-slate-600 font-medium leading-relaxed">
                  {roleMeta.description}
                </p>
                <div className="pt-2 border-t border-slate-200/80 font-mono text-slate-500 flex items-center justify-between text-[10px]">
                  <span>Zone: Central HQ</span>
                  <span className="text-emerald-700 font-black font-sans">SEC 36 VERIFIED</span>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar Collapse Toggle */}
          <div className="p-3 border-t border-slate-200 flex items-center justify-between bg-slate-50/50">
            {!collapsed && (
              <span className="text-[11px] font-bold text-slate-500 font-mono">
                LegalLens 2026
              </span>
            )}
            <button
              onClick={() => setCollapsed(!collapsed)}
              title={collapsed ? "Expand navigation sidebar" : "Collapse sidebar"}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-white rounded-xl transition border border-transparent hover:border-slate-200 cursor-pointer mx-auto"
            >
              {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>
        </aside>

        {/* Main Content Area (with bottom padding on mobile for the persistent action bar) */}
        <main className="flex-1 overflow-y-auto bg-[#F8FAFC] flex flex-col justify-between pb-20 md:pb-0">
          <div className="flex-1">
            {children}
          </div>

          {/* Clean Portal Sub-Footer (hidden on mobile to save vertical space) */}
          <footer className="hidden md:flex p-4 border-t border-slate-200/80 bg-white text-2xs text-slate-500 font-medium flex-col sm:flex-row items-center justify-between gap-2 flex-shrink-0">
            <div className="flex items-center space-x-2">
              <span className="font-black text-slate-700">Legal Metrology Compliance Portal (METRIX-LM)</span>
              <span>•</span>
              <span>Government of India</span>
            </div>
            <div className="flex items-center space-x-4 font-mono text-[11px] text-slate-400">
              <span>Under PCR, 2011 & Sec 36 Legal Metrology Act</span>
              <span>•</span>
              <span className="text-emerald-700 font-bold">STATUS: AUDIT READY</span>
            </div>
          </footer>
        </main>

      </div>
    </div>
  );
}

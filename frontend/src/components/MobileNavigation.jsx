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
  User,
  LogOut,
  Menu,
  X,
  PlusCircle,
  Globe,
  Bell,
  Sparkles,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';
import AdminNotificationBell from './AdminNotificationBell';

export default function MobileNavigation({ user, onLogout }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const userName = user?.name || user?.user_name || 'Official User';
  const role = user?.role || 'inspector';
  const userDesignation = user?.designation || (role === 'admin' ? 'System Administrator' : role === 'reviewing_officer' ? 'Senior Legal Metrology Officer' : 'Field Enforcement Inspector');
  const userZone = user?.zone_office || 'Central Ministry HQ, New Delhi';

  // Close drawer on route change
  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  // Lock body scroll when drawer is open
  useEffect(() => {
    if (drawerOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [drawerOpen]);

  // Role Navigation Items
  let navItems = [];
  let bottomNavItems = [];

  if (role === 'admin') {
    navItems = [
      { path: '/admin/control', label: 'Command & Control', icon: LayoutDashboard, badge: 'CORE' },
      { path: '/history', label: 'National Audit Registry', icon: History },
      { path: '/officer/review', label: 'FIFO Review Queue', icon: ShieldAlert, badge: 'FIFO' },
      { path: '/reports', label: 'Compliance Reports', icon: FileText },
    ];
    bottomNavItems = [
      { path: '/admin/control', label: 'Control', icon: LayoutDashboard },
      { path: '/history', label: 'Registry', icon: History },
      { path: '/officer/review', label: 'Overrides', icon: ShieldAlert, isCenter: true },
      { path: '/reports', label: 'Reports', icon: FileText },
      { path: '/profile', label: 'Profile', icon: User },
    ];
  } else if (role === 'reviewing_officer') {
    navItems = [
      { path: '/dashboard', label: 'Reviewer Dashboard', icon: LayoutDashboard },
      { path: '/officer/review', label: 'FIFO Review Queue', icon: ShieldAlert, badge: 'FIFO' },
      { path: '/history', label: 'National Audit Registry', icon: History },
      { path: '/reports', label: 'Section 36 Reports', icon: FileText },
    ];
    bottomNavItems = [
      { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { path: '/history', label: 'Registry', icon: History },
      { path: '/officer/review', label: 'Review Queue', icon: ShieldAlert, isCenter: true },
      { path: '/reports', label: 'Reports', icon: FileText },
      { path: '/profile', label: 'Profile', icon: User },
    ];
  } else {
    // Field Inspector
    navItems = [
      { path: '/dashboard', label: 'Field Dashboard', icon: LayoutDashboard },
      { path: '/inspection/new', label: 'New Field Scan', icon: PlusCircle, badge: 'NEW' },
      { path: '/scanner', label: 'Live Camera Scanner', icon: Camera, badge: 'LIVE' },
      { path: '/history', label: 'Inspection History', icon: History },
      { path: '/profile', label: 'Inspector Profile', icon: User },
    ];
    bottomNavItems = [
      { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { path: '/history', label: 'History', icon: History },
      { path: '/inspection/new', label: 'Scan Package', icon: Camera, isCenter: true },
      { path: '/reports', label: 'Reports', icon: FileText },
      { path: '/profile', label: 'Profile', icon: User },
    ];
  }

  const roleBadgeClass = {
    admin: 'bg-purple-50 text-purple-800 border-purple-300',
    reviewing_officer: 'bg-amber-50 text-amber-900 border-amber-300',
    inspector: 'bg-emerald-50 text-emerald-900 border-emerald-300',
  }[role] || 'bg-slate-100 text-slate-800 border-slate-300';

  return (
    <>
      {/* ══════════════════════════════════════════════════════════════════════════
          1. STICKY MOBILE TOP HEADER (md:hidden)
          ══════════════════════════════════════════════════════════════════════════ */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-40 flex md:hidden items-center justify-between px-3.5 py-2.5 shadow-xs">
        
        {/* Left: Brand logo & Title */}
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 bg-gradient-to-br from-[#7A1C1C] via-[#631515] to-[#4A1010] text-white rounded-lg flex items-center justify-center shadow-sm border border-[#8B2323]">
            <Scale className="w-4 h-4 text-amber-300" />
          </div>
          <div>
            <span className="text-sm font-black tracking-tight text-slate-900 font-display">
              LegalLens <span className="text-[#7A1C1C]">METRIX</span>
            </span>
            <div className="flex items-center space-x-1 text-[10px] text-slate-500 font-bold leading-none">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-mono">PCR 2011</span>
            </div>
          </div>
        </div>

        {/* Right: Role Indicator, Bell & Hamburger Toggle */}
        <div className="flex items-center space-x-2">
          {/* Unread Alert Bell for Admins & Reviewers */}
          <AdminNotificationBell user={user} />

          <button
            onClick={() => setDrawerOpen(true)}
            aria-label="Open portal navigation drawer"
            className="p-2 text-slate-700 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition cursor-pointer border border-slate-200 touch-manipulation min-h-[40px] min-w-[40px] flex items-center justify-center"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════════
          2. SLIDE-OVER MOBILE DRAWER WITH BACKDROP BLUR
          ══════════════════════════════════════════════════════════════════════════ */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden animate-fadeIn">
          
          {/* Backdrop Overlay */}
          <div
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs transition-opacity"
            onClick={() => setDrawerOpen(false)}
          />

          {/* Drawer Surface */}
          <div className="relative ml-auto w-full max-w-xs bg-white h-full shadow-2xl flex flex-col justify-between overflow-y-auto border-l border-slate-200 z-10 animate-slideLeft">
            
            {/* Drawer Top Header */}
            <div>
              {/* Tricolor National Ribbon */}
              <div className="bg-[#0F2744] text-white p-3 flex items-center justify-between border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <div className="h-2 w-6 rounded-xs flex overflow-hidden flex-shrink-0">
                    <div className="w-1/3 bg-[#FF9933]" />
                    <div className="w-1/3 bg-white" />
                    <div className="w-1/3 bg-[#138808]" />
                  </div>
                  <span className="text-[11px] font-extrabold tracking-wide text-slate-200 uppercase">
                    GOVERNMENT OF INDIA
                  </span>
                </div>
                <button
                  onClick={() => setDrawerOpen(false)}
                  className="p-1 text-slate-300 hover:text-white rounded-lg transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* User Officer Card */}
              <div className="p-4 bg-slate-50 border-b border-slate-200 space-y-2">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-[#0F2744] to-[#1E3A5F] text-white rounded-xl flex items-center justify-center font-black text-sm uppercase font-mono shadow-sm">
                    {userName.split(' ').map(n => n[0]).join('').slice(0, 2)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-black text-slate-900 truncate leading-tight font-display">
                      {userName}
                    </h4>
                    <span className={`inline-block text-[10px] font-black px-2 py-0.5 rounded mt-1 uppercase border ${roleBadgeClass}`}>
                      {role?.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                <p className="text-2xs text-slate-500 font-medium">
                  {userDesignation} • {userZone}
                </p>
              </div>

              {/* Navigation Links */}
              <div className="p-3 space-y-1.5">
                <span className="px-3 text-[10px] font-black uppercase text-slate-400 tracking-wider block mb-1">
                  MAIN NAVIGATION
                </span>

                {navItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => setDrawerOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center space-x-3 px-3.5 py-3 rounded-xl text-xs font-black transition-all border touch-manipulation min-h-[44px] ${
                          isActive
                            ? 'bg-red-50 text-[#7A1C1C] border-red-200 shadow-xs'
                            : 'text-slate-700 border-transparent hover:bg-slate-50 hover:text-[#7A1C1C]'
                        }`
                      }
                    >
                      <Icon className="w-4 h-4 flex-shrink-0" />
                      <span className="flex-1 font-sans">{item.label}</span>
                      {item.badge && (
                        <span className="text-[10px] px-2 py-0.5 rounded font-black border font-mono bg-slate-100 text-slate-700">
                          {item.badge}
                        </span>
                      )}
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                    </NavLink>
                  );
                })}
              </div>
            </div>

            {/* Drawer Bottom Actions */}
            <div className="p-4 border-t border-slate-200 bg-slate-50/70 space-y-2">
              <div className="flex items-center justify-between text-2xs text-slate-500 font-mono">
                <span>Legal Metrology Act, 2009</span>
                <span className="text-emerald-700 font-bold">SEC 36 LIVE</span>
              </div>

              <button
                onClick={onLogout}
                className="w-full min-h-[44px] px-4 py-2.5 bg-white hover:bg-red-50 text-rose-700 border border-slate-200 hover:border-red-300 font-black text-xs rounded-xl transition flex items-center justify-center gap-2 shadow-xs cursor-pointer touch-manipulation"
              >
                <LogOut className="w-4 h-4" />
                <span>Log Out of Portal</span>
              </button>
            </div>

          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          3. PERSISTENT BOTTOM NAVIGATION BAR (md:hidden)
          ══════════════════════════════════════════════════════════════════════════ */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200/90 flex md:hidden items-center justify-around px-2 py-1 shadow-lg pb-[env(safe-area-inset-bottom,4px)]">
        {bottomNavItems.map((item) => {
          const Icon = item.icon;
          const isCenter = item.isCenter;

          if (isCenter) {
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex flex-col items-center justify-center -mt-5 relative touch-manipulation transition-transform active:scale-95`
                }
              >
                {({ isActive }) => (
                  <div className="flex flex-col items-center">
                    <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg transition-all ${
                      isActive
                        ? 'bg-gradient-to-tr from-[#7A1C1C] to-[#B71C1C] text-amber-300 ring-4 ring-red-100'
                        : 'bg-gradient-to-tr from-[#7A1C1C] to-[#5E1212] text-white'
                    }`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className="text-[10px] font-black text-[#7A1C1C] mt-0.5 tracking-tight font-sans">
                      {item.label}
                    </span>
                  </div>
                )}
              </NavLink>
            );
          }

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex-1 flex flex-col items-center justify-center py-1.5 px-1 min-h-[48px] rounded-xl touch-manipulation transition-colors ${
                  isActive ? 'text-[#7A1C1C]' : 'text-slate-500 hover:text-slate-800'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={`w-5 h-5 ${isActive ? 'text-[#7A1C1C]' : 'text-slate-500'}`} />
                  <span className={`text-[10px] mt-0.5 tracking-tight font-sans ${
                    isActive ? 'font-black text-[#7A1C1C]' : 'font-bold text-slate-500'
                  }`}>
                    {item.label}
                  </span>
                </>
              )}
            </NavLink>
          );
        })}
      </nav>
    </>
  );
}

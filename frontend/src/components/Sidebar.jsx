import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Camera,
  ShieldAlert, 
  History, 
  FileText, 
  Gavel,
  QrCode,
  Lock,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

export default function Sidebar({ user, collapsed, setCollapsed }) {
  const role = user?.role || 'inspector';

  let navItems = [];

  if (role === 'admin') {
    navItems = [
      { path: '/dashboard', label: 'Dashboard Command Center', icon: LayoutDashboard },
      { path: '/admin/control', label: 'User & RBAC Admin Matrix', icon: Lock, badge: 'ADMIN' },
      { path: '/history', label: 'Global Audit History', icon: History },
      { path: '/reports', label: 'Analytics & Compliance Reports', icon: FileText },
    ];
  } else if (role === 'reviewing_officer') {
    navItems = [
      { path: '/dashboard', label: 'Dashboard Command Center', icon: LayoutDashboard },
      { path: '/officer/review', label: 'Officer Review Queue (7B)', icon: ShieldAlert, badge: '2' },
      { path: '/history', label: 'Inspection Audit History', icon: History },
      { path: '/reports', label: 'Analytics & PDF Reports', icon: FileText },
    ];
  } else {
    // Default: inspector
    navItems = [
      { path: '/scanner', label: 'Live Camera Scanner', icon: Camera, badge: 'LIVE' },
      { path: '/inspection/new', label: 'New Inspection Scan', icon: QrCode },
      { path: '/history', label: 'My Inspection History', icon: History },
    ];
  }

  return (
    <aside className={`bg-white border-r border-slate-200 shadow-sm transition-all duration-300 flex flex-col ${collapsed ? 'w-20' : 'w-64'}`}>
      
      {/* Navigation Links */}
      <div className="p-4 flex-1 space-y-1.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3.5 py-3 rounded-xl text-xs font-black transition ${
                  isActive
                    ? 'bg-gradient-to-r from-red-600 to-red-700 text-white shadow-md'
                    : 'text-slate-700 hover:bg-slate-100 hover:text-red-700'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
              {!collapsed && item.badge && (
                <span className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-bold border ${
                  item.badge === 'LIVE' 
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-300 animate-pulse' 
                    : item.badge === 'ADMIN'
                      ? 'bg-purple-100 text-purple-800 border-purple-300'
                      : 'bg-amber-100 text-amber-800 border-amber-300'
                }`}>
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </div>

      {/* Official Role Indicator Card */}
      {!collapsed && (
        <div className="p-4 m-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1 shadow-inner">
          <div className="flex items-center space-x-2 font-black text-red-700">
            <Gavel className="w-4 h-4 text-red-600" />
            <span className="uppercase">{role?.replace('_', ' ')} PRIVILEGES</span>
          </div>
          <p className="text-slate-600 text-[11px] font-medium leading-relaxed">
            {role === 'admin' 
              ? 'Full system access & RBAC user administration active.' 
              : role === 'reviewing_officer' 
                ? 'Senior adjudication & PDF certificate sign-off privileges active.' 
                : 'Field scanner & inspection evidence submission active.'}
          </p>
        </div>
      )}

      {/* Sidebar Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="p-3 border-t border-slate-200 text-slate-500 hover:text-slate-900 flex items-center justify-center hover:bg-slate-100 transition"
      >
        {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
      </button>
    </aside>
  );
}

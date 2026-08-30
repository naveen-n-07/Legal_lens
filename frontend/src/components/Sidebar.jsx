import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Camera,
  ShieldAlert, 
  History, 
  FileText, 
  Gavel,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

export default function Sidebar({ user, collapsed, setCollapsed }) {
  const isAdmin = user?.role === 'admin' || user?.role === 'officer';

  const navItems = [
    { path: '/dashboard', label: 'Dashboard Command Center', icon: LayoutDashboard },
    { path: '/scanner', label: 'Live Camera Scanner', icon: Camera, badge: 'LIVE' },
    { path: '/officer/review', label: 'Officer Review Queue (7B)', icon: ShieldAlert, badge: '2' },
    { path: '/history', label: 'Inspection Audit History', icon: History },
    { path: '/reports', label: 'Analytics & PDF Reports', icon: FileText },
  ];

  return (
    <aside className={`bg-navy-800 border-r border-slate-700 transition-all duration-300 flex flex-col ${collapsed ? 'w-20' : 'w-64'}`}>
      <div className="p-4 flex-1 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3.5 py-3 rounded-lg text-sm font-semibold transition ${
                  isActive
                    ? 'bg-gov-blue text-white shadow-md'
                    : 'text-slate-300 hover:bg-slate-700/60 hover:text-white'
                }`
              }
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
              {!collapsed && item.badge && (
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-bold border ${
                  item.badge === 'LIVE' 
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 animate-pulse' 
                    : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                }`}>
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </div>

      {/* Role Indicator Card */}
      {!collapsed && (
        <div className="p-4 m-3 bg-slate-900/80 rounded-xl border border-slate-700 text-xs">
          <div className="flex items-center space-x-2 text-indigo-300 font-bold mb-1">
            <Gavel className="w-4 h-4 text-indigo-400" />
            <span>{isAdmin ? 'SENIOR OFFICER MODE' : 'INSPECTOR MODE'}</span>
          </div>
          <p className="text-slate-400">
            {isAdmin ? 'Full override & sign-off privileges active.' : 'Field scan & evidence submission active.'}
          </p>
        </div>
      )}

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="p-3 border-t border-slate-700 text-slate-400 hover:text-white flex items-center justify-center hover:bg-slate-700/40"
      >
        {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
      </button>
    </aside>
  );
}

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
  User,
  ChevronLeft,
  ChevronRight,
  PlusCircle
} from 'lucide-react';

export default function Sidebar({ user, collapsed, setCollapsed }) {
  const role = user?.role || 'inspector';

  let navItems = [];

  if (role === 'admin') {
    navItems = [
      { path: '/dashboard', label: 'Dashboard Command Center', icon: LayoutDashboard },
      { path: '/scan', label: 'Product Label Scanner', icon: Camera, badge: 'SCAN' },
      { path: '/admin/control', label: 'User & RBAC Admin Matrix', icon: Lock, badge: 'ADMIN' },
      { path: '/history', label: 'Global Audit History', icon: History },
      { path: '/reports', label: 'Analytics & Compliance Reports', icon: FileText },
    ];
  } else if (role === 'reviewing_officer') {
    navItems = [
      { path: '/dashboard', label: 'Dashboard Command Center', icon: LayoutDashboard },
      { path: '/scan', label: 'Product Label Scanner', icon: Camera, badge: 'SCAN' },
      { path: '/officer/review', label: 'Officer Review Queue (7B)', icon: ShieldAlert, badge: '2' },
      { path: '/history', label: 'Inspection Audit History', icon: History },
      { path: '/reports', label: 'Analytics & PDF Reports', icon: FileText },
    ];
  } else {
    // Role: Field Inspector
    navItems = [
      { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { path: '/scan', label: 'Product Label Scanner', icon: Camera, badge: 'NEW' },
      { path: '/inspection/new', label: 'New Inspection', icon: PlusCircle },
      { path: '/scanner', label: 'Live Camera Scanner', icon: Camera, badge: 'LIVE' },
      { path: '/history', label: 'Inspection History', icon: History },
      { path: '/profile', label: 'Profile', icon: User },
    ];
  }

  return (
    <aside className={`bg-[#F1F5F9] border-r border-[#E2E8F0] shadow-sm transition-all duration-300 flex flex-col ${collapsed ? 'w-20' : 'w-72'}`}>
      
      {/* Navigation Links */}
      <div className="p-4 flex-1 space-y-2 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3.5 px-4 py-3.5 rounded-xl text-sm font-black transition border ${
                  isActive
                    ? 'bg-[#FEF2F2] text-[#DC2626] border-[#FCA5A5]/50 shadow-sm'
                    : 'text-[#1E293B] border-transparent hover:bg-white hover:text-[#DC2626] hover:border-[#E2E8F0]'
                }`
              }
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
              {!collapsed && item.badge && (
                <span className={`ml-auto text-xs px-2.5 py-0.5 rounded-full font-black border ${
                  item.badge === 'LIVE' 
                    ? 'bg-emerald-100 text-emerald-900 border-emerald-300 animate-pulse' 
                    : item.badge === 'ADMIN'
                      ? 'bg-purple-100 text-purple-900 border-purple-300'
                      : 'bg-amber-100 text-amber-900 border-amber-300'
                }`}>
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}

        {/* Official Role Indicator Card */}
        {!collapsed && (
          <div className="mt-6 p-4 bg-white rounded-xl border border-[#E2E8F0] text-xs space-y-1.5 shadow-sm">
            <div className="flex items-center space-x-2 font-black text-[#DC2626] text-xs">
              <Gavel className="w-4 h-4 text-[#DC2626]" />
              <span className="uppercase">{role?.replace('_', ' ')} PRIVILEGES</span>
            </div>
            <p className="text-[#64748B] text-xs font-semibold leading-relaxed">
              {role === 'admin' 
                ? 'Full system access & RBAC user administration active.' 
                : role === 'reviewing_officer' 
                  ? 'Senior adjudication & PDF certificate sign-off privileges active.' 
                  : 'Field scanner & inspection evidence submission active.'}
            </p>
          </div>
        )}
      </div>

      {/* Sidebar Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="p-3 border-t border-[#E2E8F0] text-[#64748B] hover:text-[#1E293B] flex items-center justify-center hover:bg-white transition"
      >
        {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
      </button>
    </aside>
  );
}

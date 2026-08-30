import React from 'react';
import { Scale, Shield, Bell, Wifi, User, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Navbar({ user, onLogout }) {
  const navigate = useNavigate();

  return (
    <header className="h-16 bg-navy-800 border-b border-slate-700 px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Left Branding */}
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-gov-blue/20 rounded-lg text-gov-blue border border-gov-blue/30">
          <Scale className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-extrabold text-white text-lg tracking-wide">METRIX-LM</span>
            <span className="bg-gov-indigo text-indigo-200 text-xs px-2 py-0.5 rounded font-bold uppercase tracking-wider border border-indigo-400/30">
              SIH 2026 Enterprise
            </span>
          </div>
          <p className="text-xs text-slate-400">AI Legal Metrology Statutory Inspection System</p>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-4">
        {/* System Online Status */}
        <div className="hidden md:flex items-center space-x-2 px-3 py-1 bg-emerald-950/60 text-emerald-400 rounded-full border border-emerald-500/30 text-xs font-semibold">
          <Wifi className="w-3.5 h-3.5 animate-pulse" />
          <span>Edge DB & FastAPI Online</span>
        </div>

        {/* Notifications */}
        <button className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700/50 transition">
          <Bell className="w-5 h-5" />
        </button>

        {/* User Profile */}
        <div className="flex items-center space-x-3 pl-3 border-l border-slate-700">
          <div className="w-9 h-9 bg-gov-blue text-white rounded-full flex items-center justify-center font-bold text-sm shadow">
            {user ? user.user_name.split(' ').map(n => n[0]).join('').slice(0, 2) : 'RK'}
          </div>
          <div className="hidden sm:block text-left">
            <div className="text-sm font-bold text-white leading-none">{user ? user.user_name : 'Rajesh Kumar'}</div>
            <div className="text-xs text-slate-400 mt-1 uppercase font-semibold tracking-wider">
              {user ? user.role : 'Inspector'}
            </div>
          </div>
          <button 
            onClick={onLogout}
            title="Logout"
            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 rounded-lg transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}

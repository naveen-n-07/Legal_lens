import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bell,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  X,
  Clock,
  ChevronRight,
  ExternalLink,
  Check,
  RotateCcw,
  Sparkles,
  Gavel
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { fetchAdminNotifications, markNotificationRead, markAllNotificationsRead } from '../services/adminService';
import { formatDateTime, getRelativeTime } from '../utils/dateUtils';

export default function AdminNotificationBell({ user }) {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [toastNotif, setToastNotif] = useState(null);
  
  const dropdownRef = useRef(null);
  const wsRef = useRef(null);
  const toastTimer = useRef(null);

  // Load initial notifications
  const loadNotifications = useCallback(async () => {
    try {
      const res = await fetchAdminNotifications(false, 30);
      if (res.data) {
        setNotifications(res.data.notifications || []);
        setUnreadCount(res.data.unread_count || 0);
      }
    } catch (err) {
      console.warn('Failed to load admin notifications:', err);
    }
  }, []);

  // Listen to WebSocket for real-time alerts
  useEffect(() => {
    loadNotifications();

    const token = localStorage.getItem('metrix_token') || localStorage.getItem('token') || sessionStorage.getItem('token') || '';
    const wsBase = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');
    const wsUrl = `${wsBase}/ws/notifications?token=${encodeURIComponent(token)}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.event === 'ADMIN_NOTIFICATION' && msg.data) {
            const newNotif = msg.data;
            setNotifications(prev => [newNotif, ...prev]);
            setUnreadCount(prev => prev + 1);

            // Pop toast alert
            setToastNotif(newNotif);
            if (toastTimer.current) clearTimeout(toastTimer.current);
            toastTimer.current = setTimeout(() => setToastNotif(null), 7000);
          }
        } catch (e) {
          // ignore non-JSON
        }
      };

      ws.onerror = (e) => {
        console.warn('[WS] Notification bell websocket error:', e);
      };
    } catch (wsErr) {
      console.warn('[WS] Could not connect notification websocket:', wsErr);
    }

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, [loadNotifications]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkRead = async (notifId, e) => {
    if (e) e.stopPropagation();
    try {
      await markNotificationRead(notifId);
      setNotifications(prev => prev.map(n => n.id === notifId ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.warn('Failed to mark read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.warn('Failed to mark all read:', err);
    }
  };

  const handleNotificationClick = (notif) => {
    handleMarkRead(notif.id);
    setIsOpen(false);
    if (notif.inspection_id) {
      navigate(`/officer/review?id=${notif.inspection_id}`);
    } else {
      navigate('/admin?tab=overrides');
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition cursor-pointer"
        title="Admin Notifications & Adjudication Overrides"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-4 w-4 bg-rose-600 text-[10px] font-black text-white items-center justify-center">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          </span>
        )}
      </button>

      {/* Floating Real-Time Toast Alert */}
      {toastNotif && (
        <div className="fixed top-20 right-6 z-[9999] max-w-sm bg-slate-900 text-white p-4 rounded-2xl shadow-2xl border border-amber-500/50 flex items-start gap-3 animate-slideInRight">
          <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Gavel className="w-4 h-4" />
          </div>
          <div className="flex-1 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-black text-amber-400 uppercase tracking-wider text-[10px]">
                Adjudication Override Alert
              </span>
              <button onClick={() => setToastNotif(null)} className="text-slate-400 hover:text-white">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="font-bold text-slate-100 mt-1">{toastNotif.title}</p>
            <p className="text-slate-300 text-[11px] mt-0.5 leading-snug line-clamp-2">{toastNotif.message}</p>
            <button
              onClick={() => { setToastNotif(null); handleNotificationClick(toastNotif); }}
              className="mt-2 text-[10px] font-black text-amber-300 hover:text-amber-200 inline-flex items-center gap-1"
            >
              <span>Inspect Audit Trail</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-white rounded-2xl shadow-2xl border border-slate-200 z-[9990] overflow-hidden text-xs animate-fadeIn">
          
          {/* Header */}
          <div className="px-4 py-3 bg-slate-900 text-white flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-amber-400" />
              <span className="font-black text-xs uppercase tracking-wider">Adjudication Alerts & Overrides</span>
            </div>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-[10px] font-bold text-amber-300 hover:text-amber-100 transition cursor-pointer"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
            {notifications.length === 0 ? (
              <div className="py-10 text-center text-slate-400 space-y-1">
                <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto" />
                <p className="font-bold text-slate-700">No Notifications</p>
                <p className="text-[10px]">All statutory reports and verdicts are up to date.</p>
              </div>
            ) : (
              notifications.map((n) => {
                const isAlert = n.severity === 'ALERT' || n.severity === 'CRITICAL';
                const meta = n.metadata || {};

                return (
                  <div
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`p-3.5 hover:bg-slate-50 transition cursor-pointer flex items-start gap-3 ${
                      !n.is_read ? 'bg-amber-50/40' : ''
                    }`}
                  >
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
                      isAlert ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {isAlert ? <ShieldAlert className="w-3.5 h-3.5" /> : <Gavel className="w-3.5 h-3.5" />}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="font-black text-slate-900 truncate">{n.title}</span>
                        {!n.is_read && (
                          <span className="w-2 h-2 rounded-full bg-rose-500 flex-shrink-0" title="Unread" />
                        )}
                      </div>
                      
                      <p className="text-slate-600 text-[11px] mt-0.5 leading-snug line-clamp-2">{n.message}</p>

                      {meta.justification && (
                        <div className="mt-1.5 p-1.5 bg-slate-100 rounded-md text-[10px] text-slate-700 italic truncate" title={meta.justification}>
                          "{meta.justification}"
                        </div>
                      )}

                      <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                        <span className="flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          {getRelativeTime(n.created_at)}
                        </span>
                        {n.reviewer_name && (
                          <span className="font-bold text-[#7a1c1c]">By {n.reviewer_name}</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="p-2.5 bg-slate-50 border-t border-slate-100 text-center">
            <button
              onClick={() => { setIsOpen(false); navigate('/admin?tab=overrides'); }}
              className="text-[11px] font-black text-[#7a1c1c] hover:underline inline-flex items-center gap-1"
            >
              <span>View Full Audit Ledger in Admin Command Center</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>

        </div>
      )}

    </div>
  );
}

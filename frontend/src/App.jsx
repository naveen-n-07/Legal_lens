import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';

import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import LiveScanner from './pages/LiveScanner';
import InspectionUpload from './pages/InspectionUpload';
import OfficerReview from './pages/OfficerReview';
import AuditHistory from './pages/AuditHistory';
import Reports from './pages/Reports';

export default function App() {
  const [user, setUser] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    // Check if user was previously logged in
    const storedUser = localStorage.getItem('metrix_user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        setUser(null);
      }
    }
  }, []);

  const handleLoginSuccess = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('metrix_token');
    localStorage.removeItem('metrix_user');
    setUser(null);
  };

  if (!user) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      <Navbar user={user} onLogout={handleLogout} />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar user={user} collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />

        <main className="flex-1 overflow-y-auto bg-slate-900">
          <Routes>
            <Route path="/" element={<Navigate to="/scanner" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/scanner" element={<LiveScanner />} />
            <Route path="/inspection/new" element={<InspectionUpload />} />
            <Route path="/officer/review" element={<OfficerReview />} />
            <Route path="/history" element={<AuditHistory />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="*" element={<Navigate to="/scanner" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

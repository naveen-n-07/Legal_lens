import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ExecutiveLayout from './components/ExecutiveLayout';

import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import InspectorDashboard from './pages/InspectorDashboard';
import InspectorProfile from './pages/InspectorProfile';
import LiveScanner from './pages/LiveScanner';
import ScanPortal from './pages/ScanPortal';
import InspectionUpload from './pages/InspectionUpload';
import OfficerReview from './pages/OfficerReview';
import OfficerReviewQueue from './pages/OfficerReviewQueue';
import ReviewingOfficerDashboard from './pages/ReviewingOfficerDashboard';
import AuditHistory from './pages/AuditHistory';
import Reports from './pages/Reports';
import AdminControl from './pages/AdminControl';

export default function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
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
    localStorage.removeItem('token');
    localStorage.removeItem('metrix_user');
    setUser(null);
  };

  if (!user) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  const role = user.role || 'inspector';

  // Role-Based Default Landing Route
  const getDefaultLandingRoute = () => {
    if (role === 'admin') return '/admin/control';
    if (role === 'reviewing_officer') return '/dashboard';
    return '/dashboard';
  };

  return (
    <ExecutiveLayout user={user} onLogout={handleLogout}>
      <Routes>
        <Route path="/" element={<Navigate to={getDefaultLandingRoute()} replace />} />
        
        {/* Role-Sensitive Dashboard */}
        <Route 
          path="/dashboard" 
          element={
            role === 'admin' 
              ? <AdminControl user={user} /> 
              : role === 'reviewing_officer' 
                ? <ReviewingOfficerDashboard user={user} /> 
                : <InspectorDashboard user={user} />
          } 
        />
        
        {/* Field Inspector Core Routes */}
        <Route path="/scanner" element={<LiveScanner />} />
        <Route path="/scan" element={<ScanPortal />} />
        <Route path="/inspection/new" element={<InspectionUpload user={user} />} />
        <Route path="/profile" element={<InspectorProfile user={user} />} />
        
        {/* Common Inspection History & Reports */}
        <Route path="/history" element={<AuditHistory user={user} />} />
        <Route path="/reports" element={<Reports user={user} />} />

        {/* Dedicated FIFO Officer Review Queue (Route 7B) */}
        <Route 
          path="/officer/review" 
          element={
            (role === 'reviewing_officer' || role === 'admin') 
              ? <OfficerReviewQueue user={user} /> 
              : <Navigate to={getDefaultLandingRoute()} replace />
          } 
        />

        <Route 
          path="/officer/adjudicate" 
          element={
            (role === 'reviewing_officer' || role === 'admin') 
              ? <OfficerReview user={user} /> 
              : <Navigate to={getDefaultLandingRoute()} replace />
          } 
        />

        {/* Controller / Admin Only Routes */}
        <Route 
          path="/admin/control" 
          element={
            role === 'admin' ? <AdminControl user={user} /> : <Navigate to={getDefaultLandingRoute()} replace />
          } 
        />

        <Route path="*" element={<Navigate to={getDefaultLandingRoute()} replace />} />
      </Routes>
    </ExecutiveLayout>
  );
}

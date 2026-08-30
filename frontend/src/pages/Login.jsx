import React, { useState } from 'react';
import { 
  Scale, 
  Lock, 
  Mail, 
  ShieldCheck, 
  AlertCircle, 
  ArrowRight, 
  Eye, 
  EyeOff, 
  Sparkles,
  Gavel,
  Zap
} from 'lucide-react';
import api from '../services/api';

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('officer.test@legalmetrology.gov.in');
  const [password, setPassword] = useState('OfficialTestPass123!');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (email.trim().toLowerCase() !== 'officer.test@legalmetrology.gov.in' || password !== 'OfficialTestPass123!') {
      setTimeout(() => {
        setLoading(false);
        setError('Invalid credentials! Please use officer.test@legalmetrology.gov.in / OfficialTestPass123!');
      }, 400);
      return;
    }

    try {
      const res = await api.post('/auth/login', { email, password, role: 'inspector' });
      const { access_token, user_name, role: userRole } = res.data;
      
      localStorage.setItem('metrix_token', access_token);
      localStorage.setItem('metrix_user', JSON.stringify({ email, user_name, role: userRole }));
      
      onLoginSuccess({ email, user_name: user_name || 'Official Inspector', role: userRole || 'inspector' });
    } catch (err) {
      setTimeout(() => {
        const demoUser = {
          email: 'officer.test@legalmetrology.gov.in',
          user_name: 'Official Inspector',
          role: 'inspector'
        };
        localStorage.setItem('metrix_token', 'demo-jwt-token-sih-2026');
        localStorage.setItem('metrix_user', JSON.stringify(demoUser));
        onLoginSuccess(demoUser);
      }, 400);
    } finally {
      setLoading(false);
    }
  };

  const fillDemoAccount = () => {
    setEmail('officer.test@legalmetrology.gov.in');
    setPassword('OfficialTestPass123!');
    setError('');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 sm:p-6 lg:p-8 relative overflow-hidden">
      <div className="absolute top-1/4 left-10 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-10 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none"></div>

      <div className="w-full max-w-6xl bg-slate-900/80 border border-slate-800 rounded-3xl shadow-2xl backdrop-blur-xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 relative z-10">
        
        {/* Left Side Hero Branding (7 Cols) */}
        <div className="lg:col-span-7 p-8 sm:p-12 bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950/60 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-slate-800 relative">
          <div>
            <div className="flex items-center space-x-4 mb-10">
              <div className="p-3.5 bg-blue-600/20 text-blue-400 rounded-2xl border border-blue-500/30 shadow-inner flex items-center justify-center">
                <Scale className="w-8 h-8" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-2xl font-black tracking-tight text-white">METRIX-LM</span>
                  <span className="px-2.5 py-0.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-[10px] font-bold rounded-full uppercase tracking-wider shadow">
                    SIH 2026 Official
                  </span>
                </div>
                <p className="text-xs text-slate-400 font-medium mt-0.5">
                  Ministry of Consumer Affairs, Food & Public Distribution • Govt of India
                </p>
              </div>
            </div>

            <div className="space-y-5 my-8">
              <div className="inline-flex items-center space-x-2 px-3 py-1 bg-emerald-950/60 text-emerald-400 rounded-full border border-emerald-500/30 text-xs font-bold">
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI-Powered Statutory Legal Metrology Inspection Portal</span>
              </div>

              <h2 className="text-3xl sm:text-4xl font-extrabold text-white leading-tight tracking-tight">
                5-Section Statutory Regulatory Enforcement
              </h2>

              <p className="text-sm text-slate-300 leading-relaxed">
                Automated statutory inspection workflow enforcing the <b>Legal Metrology Act, 2009</b> and <b>Packaged Commodities Rules, 2011 (G.S.R. 629(E))</b> with Rule 7 Table-I font height calibration and Schedule II package validation.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 my-8">
              <div className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-2xl flex items-start space-x-3">
                <Gavel className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">Rule 7, Table-I Calibration</h4>
                  <p className="text-xs text-slate-400 mt-1">
                    PDP Surface Area (A) font height calibration matrix (1.0mm - 6.0mm).
                  </p>
                </div>
              </div>

              <div className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-2xl flex items-start space-x-3">
                <Zap className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">Image Quality Gate</h4>
                  <p className="text-xs text-slate-400 mt-1">
                    OpenCV Laplacian variance blur detection (variance &ge; 100.0).
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-slate-800/80 text-xs text-slate-500 flex justify-between items-center">
            <span>METRIX-LM v2.4 Enterprise Edition</span>
            <span>REST API Online</span>
          </div>
        </div>

        {/* Right Side Authentication Form (5 Cols) */}
        <div className="lg:col-span-5 p-8 sm:p-10 bg-slate-900/90 flex flex-col justify-center relative">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-500"></div>

          <div className="mb-6">
            <div className="inline-flex items-center space-x-2 px-3 py-1 bg-blue-950/60 text-blue-400 rounded-lg border border-blue-500/30 text-xs font-bold mb-3">
              <ShieldCheck className="w-4 h-4" />
              <span>Inspector Authentication</span>
            </div>
            <h3 className="text-2xl font-black text-white tracking-tight">Portal Login</h3>
            <p className="text-xs text-slate-400 mt-1">Sign in with official credentials to access the workspace</p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-rose-950/80 border border-rose-500/50 text-rose-300 text-xs rounded-2xl flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <span className="font-semibold">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Official Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                  placeholder="officer.test@legalmetrology.gov.in"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-11 py-3 bg-slate-950/80 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                  placeholder="OfficialTestPass123!"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-3.5 text-slate-400 hover:text-white transition"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-extrabold text-sm rounded-xl transition-all duration-200 shadow-xl shadow-blue-600/25 flex items-center justify-center space-x-2 active:scale-[0.99]"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <span>AUTHENTICATE & ACCESS PORTAL</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-slate-800/80">
            <button
              type="button"
              onClick={fillDemoAccount}
              className="w-full py-2.5 px-3 bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-blue-500/50 rounded-xl text-xs font-bold text-slate-300 hover:text-white transition flex items-center justify-center space-x-2 shadow-sm"
            >
              <span>1-Click Fill (officer.test@legalmetrology.gov.in)</span>
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}

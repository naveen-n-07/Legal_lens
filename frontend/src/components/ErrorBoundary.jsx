import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("METRIX-LM React Error Boundary Caught Error:", error, errorInfo);
  }

  handleReset = () => {
    localStorage.removeItem('metrix_user');
    localStorage.removeItem('metrix_token');
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-6 text-center text-white">
          <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl space-y-4">
            <div className="p-4 bg-rose-950/80 text-rose-400 rounded-2xl inline-block border border-rose-800">
              <AlertTriangle className="w-10 h-10 mx-auto" />
            </div>

            <h2 className="text-xl font-black">Application State Error</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              An unexpected UI state exception occurred. Resetting session storage will restore operational status.
            </p>

            <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl font-mono text-[11px] text-rose-300 text-left truncate">
              {this.state.error?.toString()}
            </div>

            <button
              onClick={this.handleReset}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-extrabold text-xs rounded-xl transition flex items-center justify-center space-x-2"
            >
              <RefreshCw className="w-4 h-4" />
              <span>RESET SESSION & RELOAD WORKSPACE</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

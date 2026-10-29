import React, { useState } from 'react';
import {
  Layers,
  Lock,
  Mail,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  QrCode,
  AlertCircle,
} from 'lucide-react';
import api from '../services/api';

export default function SignInPage({ onLoginSuccess }) {
  const [usernameOrEmail, setUsernameOrEmail] = useState('priya@campus.edu');
  const [password, setPassword] = useState('Admin@123');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const demoAccounts = [
    {
      role: 'Administrator',
      name: 'Dr. Priya Sharma',
      email: 'priya@campus.edu',
      pass: 'Admin@123',
    },
    {
      role: 'Teacher',
      name: 'Prof. Elena Rostova',
      email: 'elena@campus.edu',
      pass: 'Teacher@123',
    },
    {
      role: 'Technician',
      name: 'Alex Martinez',
      email: 'alex.tech@campus.edu',
      pass: 'Tech@123',
    },
  ];

  const handleSignIn = async e => {
    e.preventDefault();
    if (!usernameOrEmail.trim() || !password.trim() || loading) return;

    setLoading(true);
    setErrorMsg(null);
    try {
      const user = await api.login(usernameOrEmail, password);
      onLoginSuccess(user);
    } catch (err) {
      setErrorMsg(err.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDemo = acc => {
    setUsernameOrEmail(acc.email);
    setPassword(acc.pass);
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center p-4">
      <div className="max-w-4xl w-full grid grid-cols-1 md:grid-cols-2 bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden">
        {/* Left Hero Column matching Figma */}
        <div className="bg-[#090d16] text-white p-8 sm:p-10 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-8">
              <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-base font-extrabold tracking-tight text-white leading-tight">
                  CampusAssist
                </h1>
                <p className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
                  Smart AV Helpdesk
                </p>
              </div>
            </div>

            <div className="space-y-3 mb-8">
              <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-400 bg-indigo-950/60 border border-indigo-800/40 px-2.5 py-1 rounded-full">
                AI-Powered Support
              </span>
              <h2 className="text-2xl font-extrabold text-white leading-snug">
                Smart Classroom AV Incident Operations
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                Connect teachers and technicians with guided Qwen3-8B troubleshooting, ChromaDB semantic SOP retrieval, and zero-auth QR lectern scanning.
              </p>
            </div>

            {/* Feature highlights */}
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center shrink-0 mt-0.5">
                  <Sparkles className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-200">Grounded Diagnostic Copilot</h3>
                  <p className="text-[11px] text-slate-400">Step-by-step action plans synthesized from verified manuals.</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center shrink-0 mt-0.5">
                  <QrCode className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-200">Lectern QR Scanner</h3>
                  <p className="text-[11px] text-slate-400">One-tap classroom identification & duplicate complaint check.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Demo Fill Pills */}
          <div className="pt-6 border-t border-white/10 mt-6">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
              Select Demo Credentials
            </span>
            <div className="grid grid-cols-3 gap-2">
              {demoAccounts.map(acc => (
                <button
                  key={acc.role}
                  type="button"
                  onClick={() => handleSelectDemo(acc)}
                  className="p-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors text-left"
                >
                  <div className="text-[11px] font-bold text-white truncate">{acc.role}</div>
                  <div className="text-[9px] text-slate-400 truncate">{acc.name.split(' ')[0]}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Form Column */}
        <div className="p-8 sm:p-10 flex flex-col justify-between">
          <div>
            <div className="mb-6">
              <h2 className="text-xl font-bold text-slate-900">Sign in to Helpdesk</h2>
              <p className="text-xs text-slate-500 mt-1">
                Enter your campus credentials to access your role workspace
              </p>
            </div>

            {errorMsg && (
              <div className="mb-4 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span className="font-semibold">{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleSignIn} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Username or Campus Email</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="e.g. priya@campus.edu"
                    value={usernameOrEmail}
                    onChange={e => setUsernameOrEmail(e.target.value)}
                    required
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-sm shadow-indigo-600/20 transition-colors mt-2"
              >
                <span>{loading ? 'Authenticating...' : 'Sign In'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

          <div className="pt-6 border-t border-slate-100 text-center text-[11px] text-slate-400">
            Salted SHA-256 Authentication • SQLite Persistent Database
          </div>
        </div>
      </div>
    </div>
  );
}

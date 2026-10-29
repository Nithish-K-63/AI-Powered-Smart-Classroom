import React, { useState, useEffect } from 'react';
import {
  Bell,
  Info,
  Shield,
  UserCheck,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Server,
  Database,
  Layers,
  X,
} from 'lucide-react';

export default function Header({
  pageTitle,
  pageSubtitle,
  currentUser,
  onRoleSwitch,
  connectionStatus = 'checking',
  healthData = null,
  connectionError = null,
  onRetryConnection,
}) {
  const [time, setTime] = useState('');
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const [statusModalOpen, setStatusModalOpen] = useState(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const roles = [
    { label: 'Administrator', roleRaw: 'admin', initials: 'PS', name: 'Dr. Priya Sharma' },
    { label: 'Teacher', roleRaw: 'teacher', initials: 'ER', name: 'Prof. Elena Rostova' },
    { label: 'Technician', roleRaw: 'technician', initials: 'AM', name: 'Alex Martinez' },
  ];

  const isConnected = connectionStatus === 'connected';
  const isDisconnected = connectionStatus === 'disconnected';
  const isChecking = connectionStatus === 'checking';

  return (
    <header className="h-16 border-b border-slate-200 bg-white/90 backdrop-blur-md sticky top-0 z-20 px-6 flex items-center justify-between">
      {/* Page Title & Breadcrumb */}
      <div>
        <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-2">
          <span>Single Campus</span>
          <span className="text-slate-300">•</span>
          <span>Local time {time}</span>
        </div>
        <h1 className="text-lg font-bold text-slate-900 leading-tight">
          {pageTitle}
        </h1>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Backend Connection Status Indicator */}
        <div className="relative">
          <button
            onClick={() => setStatusModalOpen(!statusModalOpen)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
              isConnected
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100/70'
                : isDisconnected
                ? 'bg-rose-50 text-rose-800 border-rose-300 hover:bg-rose-100 animate-pulse'
                : 'bg-amber-50 text-amber-800 border-amber-200'
            }`}
            title="Click for Backend Connection & Health Status"
          >
            {isConnected ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Backend Connected</span>
              </>
            ) : isDisconnected ? (
              <>
                <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                <span className="font-bold">Backend Disconnected</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                <span>Checking Backend...</span>
              </>
            )}
          </button>

          {/* Connection Details Dropdown / Popover */}
          {statusModalOpen && (
            <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-white border border-slate-200 shadow-2xl p-4 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-indigo-600" />
                  <span className="text-xs font-bold text-slate-900">
                    FastAPI Backend Status
                  </span>
                </div>
                <button
                  onClick={() => setStatusModalOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              {isConnected && healthData ? (
                <div className="space-y-2.5 text-xs">
                  <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 flex items-center justify-between">
                    <span className="font-bold flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      Status: Healthy
                    </span>
                    <span className="text-[10px] font-bold uppercase bg-emerald-200/60 px-1.5 py-0.5 rounded text-emerald-800">
                      HTTP 200 OK
                    </span>
                  </div>

                  <div className="space-y-1.5 p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-slate-600">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Database:</span>
                      <span className="font-semibold text-slate-800">
                        {healthData.database || 'SQLite (WAL Mode)'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Vector Store:</span>
                      <span className="font-semibold text-slate-800">
                        {healthData.vector_store_chunks || 20} SOP Chunks
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">AI Inference:</span>
                      <span className="font-semibold text-indigo-600">
                        Qwen3-8B Copilot Ready
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Retriever:</span>
                      <span className="font-semibold text-slate-800">
                        {healthData.retriever?.backend_used || 'ChromaDB'}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      onRetryConnection?.();
                    }}
                    className="w-full py-2 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Ping Health Check</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 space-y-1">
                    <div className="flex items-center gap-1.5 font-bold text-rose-700">
                      <AlertTriangle className="w-4 h-4" />
                      <span>Connection Failed</span>
                    </div>
                    <p className="text-[11px] leading-relaxed text-rose-800">
                      {connectionError || 'Unable to establish connection to FastAPI backend at /api/health.'}
                    </p>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 space-y-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      Troubleshooting Instructions:
                    </span>
                    <ol className="list-decimal pl-4 space-y-1 text-[11px]">
                      <li>Ensure backend server is running:</li>
                      <code className="block bg-white p-1 rounded font-mono text-[10px] border border-slate-200 text-slate-800">
                        python -m uvicorn main:app --reload
                      </code>
                      <li>Backend should be listening on port 8000.</li>
                      <li>Verify Vite proxy configured in vite.config.js.</li>
                    </ol>
                  </div>

                  <button
                    onClick={() => {
                      onRetryConnection?.();
                    }}
                    className="w-full py-2.5 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-colors shadow-sm"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Retry Connection Now</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Bell Icon */}
        <button
          className="p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors relative"
          title="Campus Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-indigo-600"></span>
        </button>

        {/* Quick Role Switcher Dropdown */}
        <div className="relative">
          <button
            onClick={() => setRoleMenuOpen(!roleMenuOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 hover:bg-slate-100 transition-all text-xs font-bold text-slate-800"
          >
            <div className="w-6 h-6 rounded-md bg-indigo-600 text-white flex items-center justify-center text-[10px] font-bold">
              {currentUser?.initials || 'CA'}
            </div>
            <div className="flex flex-col text-left">
              <span className="text-[11px] font-bold text-slate-900 leading-tight">
                {currentUser?.full_name?.split(' ')[0] || 'User'}
              </span>
              <span className="text-[9px] font-semibold text-indigo-600 leading-none">
                {currentUser?.role || 'Administrator'}
              </span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {roleMenuOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl bg-white border border-slate-200 shadow-xl p-1 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100">
                Switch Active Role
              </div>
              {roles.map(r => (
                <button
                  key={r.roleRaw}
                  onClick={() => {
                    onRoleSwitch(r);
                    setRoleMenuOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-lg transition-colors text-left ${
                    currentUser?.role?.toLowerCase() === r.label.toLowerCase()
                      ? 'bg-indigo-50 text-indigo-700 font-bold'
                      : 'text-slate-700 hover:bg-slate-50 font-medium'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded bg-slate-200 text-slate-700 flex items-center justify-center text-[10px] font-bold">
                      {r.initials}
                    </span>
                    <span>{r.label}</span>
                  </div>
                  {currentUser?.role?.toLowerCase() === r.label.toLowerCase() && (
                    <UserCheck className="w-3.5 h-3.5 text-indigo-600" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

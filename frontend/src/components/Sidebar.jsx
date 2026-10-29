import React from 'react';
import {
  LayoutDashboard,
  MessageSquareQuote,
  QrCode,
  Wrench,
  ClipboardList,
  Briefcase,
  FileText,
  BookOpen,
  Settings,
  Sparkles,
  LogOut,
  Layers,
  CheckCircle2,
} from 'lucide-react';

export default function Sidebar({
  currentPage,
  setCurrentPage,
  currentUser,
  onLogout,
  connectionStatus = 'checking',
}) {
  const role = currentUser?.role?.toLowerCase() || 'administrator';
  const isConnected = connectionStatus === 'connected';
  const isDisconnected = connectionStatus === 'disconnected';

  // Role-based visible navigation items
  const navItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: LayoutDashboard,
      roles: ['administrator', 'teacher', 'technician', 'admin'],
    },
    {
      id: 'troubleshoot',
      label: 'Troubleshooting Chat',
      icon: MessageSquareQuote,
      roles: ['administrator', 'teacher', 'admin'],
    },
    {
      id: 'qr',
      label: 'Classroom QR',
      icon: QrCode,
      roles: ['administrator', 'teacher', 'technician', 'admin'],
    },
    {
      id: 'raise_request',
      label: 'Technician Requests',
      icon: Wrench,
      roles: ['administrator', 'teacher', 'technician', 'admin'],
    },
    {
      id: 'my_complaints',
      label: 'My Complaints',
      icon: ClipboardList,
      roles: ['administrator', 'teacher', 'technician', 'admin'],
    },
    {
      id: 'technician_workspace',
      label: 'Technician Workspace',
      icon: Briefcase,
      roles: ['administrator', 'technician', 'admin'],
    },
    {
      id: 'complaint_logs',
      label: 'Complaint Logs',
      icon: FileText,
      roles: ['administrator', 'teacher', 'technician', 'admin'],
    },
    {
      id: 'knowledge_base',
      label: 'Knowledge Base',
      icon: BookOpen,
      roles: ['administrator', 'admin'],
    },
    {
      id: 'admin_settings',
      label: 'Admin Settings',
      icon: Settings,
      roles: ['administrator', 'admin'],
    },
  ];

  const visibleItems = navItems.filter(item =>
    item.roles.some(r => role.includes(r))
  );

  return (
    <aside className="w-64 min-w-[256px] bg-[#090d16] text-white flex flex-col justify-between h-screen sticky top-0 border-r border-white/10 z-30 select-none">
      {/* Brand Header */}
      <div className="p-4 pt-5">
        <div className="flex items-center gap-3 px-1 mb-5">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="text-base font-extrabold tracking-tight text-white leading-tight">
              CampusAssist
            </div>
            <div className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
              Smart AV Helpdesk
            </div>
          </div>
        </div>

        <div className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 flex items-center justify-between text-xs text-slate-300 mb-4">
          <span className="flex items-center gap-1.5 font-medium">
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected
                  ? 'bg-emerald-400 animate-pulse'
                  : isDisconnected
                  ? 'bg-rose-500'
                  : 'bg-amber-400 animate-pulse'
              }`}
            ></span>
            Main Campus
          </span>
          <span
            className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
              isConnected
                ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20'
                : isDisconnected
                ? 'text-rose-400 bg-rose-500/10 border border-rose-500/20'
                : 'text-amber-400 bg-amber-500/10'
            }`}
          >
            {isConnected ? 'Live' : isDisconnected ? 'Offline' : 'Sync'}
          </span>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1">
          {visibleItems.map(item => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentPage(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 text-left ${
                  isActive
                    ? 'bg-indigo-600/20 text-white border border-indigo-500/40 font-semibold shadow-sm shadow-indigo-500/10'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon
                  className={`w-4 h-4 transition-colors ${
                    isActive ? 'text-indigo-400' : 'text-slate-400 group-hover:text-white'
                  }`}
                />
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Model & Status Card */}
      <div className="p-4 border-t border-white/10 space-y-3">
        <div className="rounded-xl p-3 bg-white/5 border border-white/10">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-white">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Qwen3-8B Copilot</span>
            </div>
            <span
              className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                isConnected
                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                  : isDisconnected
                  ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
                  : 'text-amber-400 bg-amber-500/10 border-amber-500/20'
              }`}
            >
              {isConnected ? 'Ready' : isDisconnected ? 'Offline' : 'Sync'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 leading-snug">
            {isConnected
              ? 'ChromaDB RAG evidence retrieval & grounded step synthesis.'
              : isDisconnected
              ? 'FastAPI server offline. Start with python -m uvicorn main:app'
              : 'Verifying backend health and ChromaDB RAG index...'}
          </p>
        </div>

        {/* User Card */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center text-xs font-bold text-white shadow">
              {currentUser?.initials || 'CA'}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-bold text-white truncate">
                {currentUser?.full_name || 'Campus User'}
              </div>
              <div className="text-[10px] text-slate-400 truncate">
                {currentUser?.role || 'Administrator'}
              </div>
            </div>
          </div>
          <button
            onClick={onLogout}
            title="Sign out"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-white/5 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}

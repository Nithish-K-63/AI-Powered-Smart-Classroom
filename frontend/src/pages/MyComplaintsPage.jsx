import React, { useState, useEffect } from 'react';
import {
  ClipboardList,
  Search,
  Filter,
  ChevronRight,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  MessageSquare,
} from 'lucide-react';
import api from '../services/api';

export default function MyComplaintsPage({ currentUser, onNavigateToChat }) {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const loadComplaints = async () => {
    try {
      setLoading(true);
      const data = await api.getComplaints({ limit: 100 });
      // If teacher, can view all or filter by teacher
      setComplaints(data);
    } catch (err) {
      console.error('Failed to load complaints:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadComplaints();
  }, []);

  const filtered = complaints.filter(c => {
    const matchesSearch =
      search === '' ||
      c.id?.toLowerCase().includes(search.toLowerCase()) ||
      c.complaint_code?.toLowerCase().includes(search.toLowerCase()) ||
      c.device_type?.toLowerCase().includes(search.toLowerCase()) ||
      c.classroom_name?.toLowerCase().includes(search.toLowerCase()) ||
      c.problem_description?.toLowerCase().includes(search.toLowerCase());
    const matchesStatus =
      statusFilter === '' || c.status?.toLowerCase() === statusFilter.toLowerCase();
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = status => {
    const s = (status || '').toLowerCase();
    if (s === 'resolved') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          Resolved
        </span>
      );
    }
    if (s === 'escalated') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
          Escalated
        </span>
      );
    }
    if (s === 'in_progress' || s === 'in progress' || s === 'acknowledged') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
          In Progress
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
        <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
        Pending
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Controls */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Classroom Incidents & Complaints</h2>
          <p className="text-xs text-slate-500">Review status, technician dispatches, and resolution notes</p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter complaints..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 w-44 sm:w-56"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="py-1.5 px-2.5 rounded-xl border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="escalated">Escalated</option>
          </select>

          <button
            onClick={loadComplaints}
            className="p-2 rounded-xl border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Complaints Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.length === 0 ? (
          <div className="col-span-2 py-12 text-center text-slate-400 bg-white rounded-2xl border border-slate-200">
            No complaints found for the selected filter.
          </div>
        ) : (
          filtered.map(comp => (
            <div
              key={comp.id}
              className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow transition-all space-y-3 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs font-bold text-indigo-600">
                    {comp.complaint_code || comp.id?.slice(0, 10)}
                  </span>
                  {getStatusBadge(comp.status)}
                </div>

                <div className="text-sm font-bold text-slate-900 mb-1">
                  {comp.classroom_name || comp.room_no || 'Classroom'} •{' '}
                  <span className="capitalize font-semibold text-slate-600">
                    {comp.device_type?.replace('_', ' ')}
                  </span>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed line-clamp-2">
                  "{comp.problem_description}"
                </p>

                {comp.resolution_notes && (
                  <div className="mt-2 p-2 rounded-lg bg-emerald-50 text-[11px] text-emerald-800 border border-emerald-100">
                    <span className="font-bold">Resolution: </span>
                    {comp.resolution_notes}
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                <span>
                  {new Date(comp.created_at).toLocaleDateString([], {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>

                <button
                  onClick={() => onNavigateToChat(comp)}
                  className="px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-indigo-50 hover:text-indigo-600 border border-slate-200 text-slate-700 font-bold text-xs flex items-center gap-1 transition-colors"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Open Session</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

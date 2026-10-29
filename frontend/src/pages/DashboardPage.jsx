import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  CheckCircle,
  Clock,
  AlertTriangle,
  Search,
  Filter,
  X,
  ChevronRight,
  ShieldAlert,
  ArrowUpRight,
  RefreshCw,
  Eye,
} from 'lucide-react';
import api from '../services/api';

export default function DashboardPage({ onNavigateToChat }) {
  const [metrics, setMetrics] = useState(null);
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedComplaint, setSelectedComplaint] = useState(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [metricsData, complaintsData] = await Promise.all([
        api.getDashboardMetrics(),
        api.getComplaints({ limit: 50 }),
      ]);
      setMetrics(metricsData);
      setComplaints(complaintsData);
      if (complaintsData.length > 0 && !selectedComplaint) {
        setSelectedComplaint(complaintsData[0]);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const filteredComplaints = complaints.filter(c => {
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

  const getUrgencyBadge = urgency => {
    const u = (urgency || '').toLowerCase();
    if (u === 'high' || u === 'urgent') {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-100 text-rose-700">
          High
        </span>
      );
    }
    if (u === 'medium') {
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-700">
          Medium
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600">
        Normal
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* 4 Telemetry Metric Cards matching Figma exactly */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Complaints */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hover:shadow transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider">Total Complaints</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {metrics?.total_complaints?.toLocaleString() || '0'}
          </div>
          <div className="mt-2 text-xs text-slate-500 flex items-center gap-1 font-medium">
            <span className="text-emerald-600 font-bold flex items-center">
              <ArrowUpRight className="w-3.5 h-3.5" /> +12.4%
            </span>
            <span>from previous semester</span>
          </div>
        </div>

        {/* Resolved Complaints */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hover:shadow transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider">Resolved</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {metrics?.resolved_complaints?.toLocaleString() || '0'}
          </div>
          <div className="mt-2 text-xs text-slate-500 flex items-center gap-1 font-medium">
            <span className="text-emerald-600 font-bold">
              {metrics?.resolution_rate_percent || 0}%
            </span>
            <span>first-contact fix rate</span>
          </div>
        </div>

        {/* Pending Review */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hover:shadow transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider">Pending Review</span>
            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {metrics?.pending_complaints?.toLocaleString() || '0'}
          </div>
          <div className="mt-2 text-xs text-slate-500 flex items-center gap-1 font-medium">
            <span className="text-amber-600 font-bold">Active</span>
            <span>classroom queue</span>
          </div>
        </div>

        {/* Escalated to Tech */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hover:shadow transition-shadow">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-bold uppercase tracking-wider">Escalated</span>
            <div className="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {metrics?.escalated_complaints?.toLocaleString() || '0'}
          </div>
          <div className="mt-2 text-xs text-slate-500 flex items-center gap-1 font-medium">
            <span className="text-rose-600 font-bold">Field Techs</span>
            <span>dispatched on site</span>
          </div>
        </div>
      </div>

      {/* Analytics Row: Trend Bar Chart & Device Breakdown matching Figma */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weekly Trend Bar Chart */}
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-base font-bold text-slate-900">Weekly Incident Volume</h2>
              <p className="text-xs text-slate-500">Live complaint telemetry across campus teaching days</p>
            </div>
            <button
              onClick={fetchDashboardData}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              title="Refresh Telemetry"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <div className="h-44 flex items-end justify-between gap-4 px-2">
            {(() => {
              const trendList = metrics?.weekly_trend || [
                { day: 'Mon', value: 0 },
                { day: 'Tue', value: 0 },
                { day: 'Wed', value: 0 },
                { day: 'Thu', value: 0 },
                { day: 'Fri', value: 0 },
                { day: 'Sat', value: 0 },
                { day: 'Sun', value: 0 },
              ];
              const maxVal = Math.max(...trendList.map(b => b.value), 1);
              return trendList.map(bar => {
                const heightPct = Math.round((bar.value / maxVal) * 100);
                return (
                  <div key={bar.day} className="flex-1 flex flex-col items-center gap-2 group">
                    <div className="text-[10px] font-bold text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">
                      {bar.value}
                    </div>
                    <div className="w-full max-w-[42px] bg-slate-100 rounded-t-lg h-36 flex items-end overflow-hidden">
                      <div
                        className="w-full bg-indigo-600 group-hover:bg-indigo-700 rounded-t-lg transition-all duration-300"
                        style={{ height: bar.value > 0 ? `${Math.max(15, heightPct)}%` : '4px' }}
                      ></div>
                    </div>
                    <span className="text-xs font-bold text-slate-600">{bar.day}</span>
                  </div>
                );
              });
            })()}
          </div>
        </div>

        {/* Device Distribution Progress */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <h2 className="text-base font-bold text-slate-900 mb-1">Device Distribution</h2>
          <p className="text-xs text-slate-500 mb-5">Incident occurrences by AV hardware class</p>

          <div className="space-y-4">
            {(metrics?.device_distribution || []).map((device, idx) => {
              const totalCount = metrics?.total_complaints || 0;
              const pct = totalCount > 0 ? Math.round((device.count / totalCount) * 100) : 0;
              return (
                <div key={device.name} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold text-slate-700">
                    <span className="capitalize">{device.name}</span>
                    <span className="text-slate-500 font-bold">{device.count.toLocaleString()} ({pct}%)</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        idx === 0
                          ? 'bg-indigo-600'
                          : idx === 1
                          ? 'bg-blue-500'
                          : idx === 2
                          ? 'bg-violet-500'
                          : idx === 3
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.max(pct > 0 ? 6 : 0, pct)}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Live Complaints Table & Floating Quick View Container */}
      <div className="relative grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table Column (2 cols when panel open, 3 cols when closed) */}
        <div className={`${selectedComplaint ? 'lg:col-span-2' : 'lg:col-span-3'} bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden transition-all duration-200`}>
          {/* Table Header & Controls */}
          <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">Classroom Incidents</h2>
              <p className="text-xs text-slate-500">Live complaints synced with SQLite persistent storage</p>
            </div>

            <div className="flex items-center gap-2">
              {/* Search */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search code, room, device..."
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
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Ticket</th>
                  <th className="py-3 px-4">Room</th>
                  <th className="py-3 px-4">Device</th>
                  <th className="py-3 px-4">Issue Summary</th>
                  <th className="py-3 px-4">Urgency</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700 font-medium">
                {filteredComplaints.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="py-8 text-center text-slate-400">
                      No complaints match the current filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredComplaints.map(comp => (
                    <tr
                      key={comp.id}
                      onClick={() => setSelectedComplaint(comp)}
                      className={`hover:bg-indigo-50/40 cursor-pointer transition-colors ${
                        selectedComplaint?.id === comp.id ? 'bg-indigo-50/60' : ''
                      }`}
                    >
                      <td className="py-3 px-4 font-mono font-bold text-indigo-600">
                        {comp.complaint_code || comp.id?.slice(0, 10)}
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-900">
                        {comp.classroom_name || comp.room_no || 'Room'}
                      </td>
                      <td className="py-3 px-4 capitalize font-semibold">
                        {comp.device_type?.replace('_', ' ')}
                      </td>
                      <td className="py-3 px-4 max-w-xs truncate text-slate-600">
                        {comp.problem_description}
                      </td>
                      <td className="py-3 px-4">
                        {getUrgencyBadge(comp.urgency)}
                      </td>
                      <td className="py-3 px-4">
                        {getStatusBadge(comp.status)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={e => {
                            e.stopPropagation();
                            setSelectedComplaint(comp);
                          }}
                          className="p-1 rounded text-slate-400 hover:text-indigo-600 transition-colors"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Floating Quick View Panel matching Figma */}
        {selectedComplaint && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-lg p-5 flex flex-col justify-between animate-in fade-in slide-in-from-right-4 duration-200">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Incident Details
                  </span>
                  <h3 className="text-sm font-bold font-mono text-indigo-600">
                    {selectedComplaint.complaint_code || selectedComplaint.id}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedComplaint(null)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Status and Urgency */}
              <div className="flex items-center gap-2 mb-4">
                {getStatusBadge(selectedComplaint.status)}
                {getUrgencyBadge(selectedComplaint.urgency)}
              </div>

              {/* Room and Device Meta */}
              <div className="space-y-3 mb-5 text-xs">
                <div className="p-3 bg-slate-50 rounded-xl space-y-1.5 border border-slate-100">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Classroom:</span>
                    <span className="font-bold text-slate-900">
                      {selectedComplaint.classroom_name || selectedComplaint.room_no || 'Campus Room'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Device Hardware:</span>
                    <span className="font-semibold text-slate-800 capitalize">
                      {selectedComplaint.device_type?.replace('_', ' ')} ({selectedComplaint.device_model || 'Standard'})
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Created:</span>
                    <span className="text-slate-600">
                      {new Date(selectedComplaint.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </div>

                {/* Problem Description */}
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Problem Reported
                  </span>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs text-slate-800 font-medium leading-relaxed">
                    "{selectedComplaint.problem_description}"
                  </div>
                </div>

                {/* Assigned Technician */}
                {selectedComplaint.technician_name && (
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                      Assigned Field Technician
                    </span>
                    <div className="p-3 rounded-xl bg-indigo-50/50 border border-indigo-100 flex items-center justify-between">
                      <div>
                        <div className="font-bold text-xs text-indigo-950">
                          {selectedComplaint.technician_name}
                        </div>
                        <div className="text-[11px] text-indigo-600">
                          {selectedComplaint.technician_phone || 'campus-support@campus.edu'}
                        </div>
                      </div>
                      <span className="text-[10px] font-bold bg-indigo-600 text-white px-2 py-0.5 rounded">
                        Routed
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Panel Actions */}
            <div className="pt-4 border-t border-slate-100 space-y-2">
              <button
                onClick={() => onNavigateToChat(selectedComplaint)}
                className="w-full py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-sm shadow-indigo-500/20 transition-colors"
              >
                <span>Launch AI Diagnostic Session</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import {
  FileText,
  Search,
  ChevronDown,
  ChevronRight,
  Clock,
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  History,
  Shield,
  RefreshCw,
} from 'lucide-react';
import api from '../services/api';

export default function ComplaintLogsPage() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedComplaintId, setSelectedComplaintId] = useState(null);
  const [events, setEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);

  const loadComplaints = async () => {
    try {
      setLoading(true);
      const data = await api.getComplaints({ limit: 100 });
      setComplaints(data);
      if (data.length > 0 && !selectedComplaintId) {
        setSelectedComplaintId(data[0].id);
        loadEvents(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load complaints:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadEvents = async cid => {
    setEventsLoading(true);
    try {
      const evs = await api.getComplaintAuditTrail(cid);
      setEvents(evs);
    } catch (err) {
      console.error('Failed to load events:', err);
    } finally {
      setEventsLoading(false);
    }
  };

  useEffect(() => {
    loadComplaints();
  }, []);

  const handleSelectComplaint = comp => {
    setSelectedComplaintId(comp.id);
    loadEvents(comp.id);
  };

  const filtered = complaints.filter(c =>
    search === '' ||
    c.id?.toLowerCase().includes(search.toLowerCase()) ||
    c.complaint_code?.toLowerCase().includes(search.toLowerCase()) ||
    c.classroom_name?.toLowerCase().includes(search.toLowerCase()) ||
    c.device_type?.toLowerCase().includes(search.toLowerCase())
  );

  const selectedComp = complaints.find(c => c.id === selectedComplaintId);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-130px)]">
      {/* Left Table / List (7 Cols) */}
      <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Incident Audit Logs</h2>
            <p className="text-xs text-slate-500">Immutable chronological transaction records</p>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 w-36 sm:w-48"
              />
            </div>
            <button
              onClick={loadComplaints}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider sticky top-0 border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3.5">Ticket</th>
                <th className="py-2.5 px-3.5">Room</th>
                <th className="py-2.5 px-3.5">Device</th>
                <th className="py-2.5 px-3.5">Status</th>
                <th className="py-2.5 px-3.5">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700 font-medium">
              {filtered.map(comp => (
                <tr
                  key={comp.id}
                  onClick={() => handleSelectComplaint(comp)}
                  className={`hover:bg-indigo-50/40 cursor-pointer transition-colors ${
                    selectedComplaintId === comp.id ? 'bg-indigo-50/70 font-semibold' : ''
                  }`}
                >
                  <td className="py-3 px-3.5 font-mono text-indigo-600 font-bold">
                    {comp.complaint_code || comp.id?.slice(0, 8)}
                  </td>
                  <td className="py-3 px-3.5 text-slate-900 font-bold">
                    {comp.classroom_name || comp.room_no || 'Room'}
                  </td>
                  <td className="py-3 px-3.5 capitalize">
                    {comp.device_type?.replace('_', ' ')}
                  </td>
                  <td className="py-3 px-3.5">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        comp.status === 'resolved'
                          ? 'bg-emerald-50 text-emerald-700'
                          : comp.status === 'escalated'
                          ? 'bg-rose-50 text-rose-700'
                          : comp.status === 'in_progress'
                          ? 'bg-amber-50 text-amber-700'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {comp.status}
                    </span>
                  </td>
                  <td className="py-3 px-3.5 text-slate-400 text-[11px]">
                    {new Date(comp.created_at).toLocaleDateString([], {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Right Column: Chronological Audit Timeline (5 Cols) */}
      <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between overflow-y-auto">
        {selectedComp ? (
          <div className="space-y-4">
            <div className="border-b border-slate-100 pb-3">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Event Timeline Stream
              </span>
              <h3 className="text-sm font-bold text-slate-900 font-mono">
                {selectedComp.complaint_code || selectedComp.id}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {selectedComp.classroom_name} • {selectedComp.device_type}
              </p>
            </div>

            {/* Timeline Stream */}
            {eventsLoading ? (
              <div className="py-12 text-center text-xs text-slate-400">
                Loading immutable timeline events...
              </div>
            ) : events.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400">
                No events recorded for this complaint.
              </div>
            ) : (
              <div className="relative pl-6 space-y-5 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                {events.map((ev, idx) => (
                  <div key={ev.id || idx} className="relative group">
                    {/* Timeline Node Icon */}
                    <div className="absolute -left-6 top-0.5 w-4 h-4 rounded-full bg-white border-2 border-indigo-600 flex items-center justify-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-600"></div>
                    </div>

                    <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 text-xs space-y-1">
                      <div className="flex items-center justify-between text-slate-400 text-[10px]">
                        <span className="font-bold uppercase tracking-wider text-indigo-600">
                          {ev.event_type?.replace(/_/g, ' ')}
                        </span>
                        <span>
                          {new Date(ev.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })}
                        </span>
                      </div>

                      <div className="text-xs font-bold text-slate-900">
                        {ev.actor_name} <span className="font-normal text-slate-500">({ev.actor_role})</span>
                      </div>

                      {ev.details && (
                        <div className="text-[11px] text-slate-600 font-mono bg-white p-2 rounded border border-slate-100 overflow-x-auto">
                          {typeof ev.details === 'string' ? ev.details : JSON.stringify(ev.details, null, 2)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-slate-400 text-xs">
            Select a complaint from the table to view its full event audit stream.
          </div>
        )}
      </div>
    </div>
  );
}

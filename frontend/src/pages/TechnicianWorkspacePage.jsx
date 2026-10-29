import React, { useState, useEffect } from 'react';
import {
  Briefcase,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Send,
  MessageSquare,
  FileEdit,
  Check,
  UserCheck,
  RefreshCw,
} from 'lucide-react';
import api from '../services/api';

export default function TechnicianWorkspacePage({ currentUser, onNavigateToChat }) {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeModal, setActiveModal] = useState(null); // { type: 'note' | 'resolve', complaint: obj }
  const [modalText, setModalText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadTechnicianQueue = async () => {
    try {
      setLoading(true);
      const data = await api.getComplaints({ limit: 100 });
      setComplaints(data);
    } catch (err) {
      console.error('Failed to load technician queue:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTechnicianQueue();
  }, []);

  const handleAcknowledge = async complaintId => {
    try {
      await api.updateComplaintStatus(complaintId, {
        status: 'in_progress',
        actor_name: currentUser?.full_name || 'Alex Martinez (Tech)',
        actor_role: 'technician',
        resolution_notes: 'Technician acknowledged dispatch and is en route.',
        resolved_by_user_id: currentUser?.id,
      });
      loadTechnicianQueue();
    } catch (err) {
      console.error('Error acknowledging:', err);
    }
  };

  const handleModalSubmit = async e => {
    e.preventDefault();
    if (!activeModal || !modalText.trim() || submitting) return;

    setSubmitting(true);
    try {
      if (activeModal.type === 'resolve') {
        await api.updateComplaintStatus(activeModal.complaint.id, {
          status: 'resolved',
          actor_name: currentUser?.full_name || 'Alex Martinez (Tech)',
          actor_role: 'technician',
          resolution_notes: modalText,
          resolved_by_user_id: currentUser?.id,
        });
      } else if (activeModal.type === 'note') {
        await api.updateComplaintStatus(activeModal.complaint.id, {
          status: activeModal.complaint.status,
          actor_name: currentUser?.full_name || 'Alex Martinez (Tech)',
          actor_role: 'technician',
          resolution_notes: `Field Note: ${modalText}`,
          resolved_by_user_id: currentUser?.id,
        });
      }
      setActiveModal(null);
      setModalText('');
      loadTechnicianQueue();
    } catch (err) {
      console.error('Error submitting action:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const assignedCount = complaints.filter(c => c.status === 'pending' || c.status === 'escalated').length;
  const inProgressCount = complaints.filter(c => c.status === 'in_progress' || c.status === 'acknowledged').length;
  const resolvedCount = complaints.filter(c => c.status === 'resolved').length;

  return (
    <div className="space-y-6">
      {/* 3 Metric Cards matching Figma */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Assigned Queue</span>
            <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {assignedCount}
          </div>
          <p className="text-xs text-slate-500 mt-1">Pending physical response</p>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">In Progress</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Briefcase className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {inProgressCount}
          </div>
          <p className="text-xs text-slate-500 mt-1">Under active inspection</p>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Resolved Today</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
            {resolvedCount}
          </div>
          <p className="text-xs text-slate-500 mt-1">Recorded with technician sign-off</p>
        </div>
      </div>

      {/* Main Queue List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">Field Service Work Orders</h2>
            <p className="text-xs text-slate-500">Live service orders assigned to campus AV support staff</p>
          </div>
          <button
            onClick={loadTechnicianQueue}
            className="p-2 rounded-xl border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
          {complaints.length === 0 ? (
            <div className="col-span-2 py-10 text-center text-slate-400">
              No tickets currently assigned.
            </div>
          ) : (
            complaints.map(comp => (
              <div
                key={comp.id}
                className="rounded-2xl border border-slate-200 p-5 bg-white shadow-sm space-y-3 flex flex-col justify-between hover:border-slate-300 transition-all"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold text-indigo-600">
                      {comp.complaint_code || comp.id?.slice(0, 10)}
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                        comp.status === 'resolved'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : comp.status === 'escalated'
                          ? 'bg-rose-50 text-rose-700 border border-rose-200'
                          : comp.status === 'in_progress'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200'
                          : 'bg-slate-100 text-slate-700 border border-slate-200'
                      }`}
                    >
                      {comp.status}
                    </span>
                  </div>

                  <div className="text-sm font-bold text-slate-900">
                    {comp.classroom_name || comp.room_no || 'Room'} •{' '}
                    <span className="capitalize font-semibold text-slate-600">
                      {comp.device_type?.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="text-xs text-slate-600 mt-1 leading-relaxed">
                    "{comp.problem_description}"
                  </div>

                  {comp.resolution_notes && (
                    <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-700 font-medium">
                      <span className="font-bold">Latest Note: </span>
                      {comp.resolution_notes}
                    </div>
                  )}
                </div>

                {/* Technician Action Buttons */}
                <div className="pt-3 border-t border-slate-100 flex items-center gap-2 flex-wrap">
                  {comp.status === 'pending' || comp.status === 'escalated' ? (
                    <button
                      onClick={() => handleAcknowledge(comp.id)}
                      className="px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs flex items-center gap-1 shadow-sm transition-colors"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      <span>Acknowledge</span>
                    </button>
                  ) : null}

                  {comp.status !== 'resolved' && (
                    <>
                      <button
                        onClick={() => {
                          setActiveModal({ type: 'note', complaint: comp });
                          setModalText('');
                        }}
                        className="px-3 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold text-xs flex items-center gap-1 transition-colors"
                      >
                        <FileEdit className="w-3.5 h-3.5" />
                        <span>Add Note</span>
                      </button>

                      <button
                        onClick={() => {
                          setActiveModal({ type: 'resolve', complaint: comp });
                          setModalText('');
                        }}
                        className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center gap-1 shadow-sm transition-colors"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Resolve</span>
                      </button>
                    </>
                  )}

                  <button
                    onClick={() => onNavigateToChat(comp)}
                    className="ml-auto p-1.5 text-slate-400 hover:text-indigo-600 rounded-lg"
                    title="View Copilot Chat"
                  >
                    <MessageSquare className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Action Modal (Note or Resolve) */}
      {activeModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-6 animate-in zoom-in-95 duration-150">
            <h3 className="text-base font-bold text-slate-900 mb-1">
              {activeModal.type === 'resolve'
                ? 'Resolve Classroom Incident'
                : 'Append Diagnostic Note'}
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              {activeModal.type === 'resolve'
                ? `Provide the final resolution summary for ${activeModal.complaint.classroom_name || 'classroom'}.`
                : 'Record your field findings into the immutable complaint event stream.'}
            </p>

            <form onSubmit={handleModalSubmit} className="space-y-4">
              <textarea
                rows={4}
                value={modalText}
                onChange={e => setModalText(e.target.value)}
                placeholder={
                  activeModal.type === 'resolve'
                    ? 'e.g. Replaced faulty HDMI patch cable and verified video signal with teacher laptop.'
                    : 'e.g. Inspected projector filter; fan spinning normally, tested alternate source input.'
                }
                required
                className="w-full py-2.5 px-3.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-none leading-relaxed"
              />

              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setActiveModal(null)}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !modalText.trim()}
                  className={`px-4 py-2 rounded-xl text-xs font-bold text-white transition-colors flex items-center gap-1.5 shadow-sm ${
                    activeModal.type === 'resolve'
                      ? 'bg-emerald-600 hover:bg-emerald-700'
                      : 'bg-indigo-600 hover:bg-indigo-700'
                  }`}
                >
                  <span>{activeModal.type === 'resolve' ? 'Confirm Resolution' : 'Save Note'}</span>
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

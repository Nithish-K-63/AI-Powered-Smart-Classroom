import React, { useState, useEffect } from 'react';
import {
  Wrench,
  Send,
  AlertTriangle,
  CheckCircle2,
  PhoneCall,
  UserCheck,
  ShieldCheck,
} from 'lucide-react';
import api from '../services/api';

export default function RaiseRequestPage({ initialData, currentUser, onNavigateToMyComplaints }) {
  const [classrooms, setClassrooms] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [selectedClassroomId, setSelectedClassroomId] = useState('');
  const [deviceType, setDeviceType] = useState('projector');
  const [deviceModel, setDeviceModel] = useState('');
  const [urgency, setUrgency] = useState('Medium');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    const initData = async () => {
      try {
        const [rooms, techs] = await Promise.all([
          api.getClassrooms(),
          api.getTechnicians(),
        ]);
        setClassrooms(rooms);
        setTechnicians(techs);

        if (initialData?.classroom_id) {
          setSelectedClassroomId(initialData.classroom_id);
          if (initialData.device_type) setDeviceType(initialData.device_type);
        } else if (rooms.length > 0) {
          setSelectedClassroomId(rooms[0].id);
        }
      } catch (err) {
        console.error('Failed to load classrooms or techs:', err);
      }
    };
    initData();
  }, [initialData]);

  const assignedTech = technicians.find(t =>
    t.assigned_categories?.toLowerCase().includes(deviceType) ||
    t.assigned_blocks?.length > 0
  ) || technicians[0];

  const handleSubmit = async e => {
    e.preventDefault();
    if (!description.trim() || loading) return;

    setLoading(true);
    try {
      const payload = {
        classroom_id: selectedClassroomId,
        device_type: deviceType,
        device_model: deviceModel || 'Standard',
        urgency: urgency,
        problem_description: description,
        reporter_user_id: currentUser?.id || 'teacher1',
      };

      const complaint = await api.submitComplaint(payload);

      // Auto-escalate to technician since this is a formal dispatch request
      if (complaint.id) {
        await api.escalateComplaint({
          complaint_id: complaint.id,
          reason: `Direct technician dispatch raised: ${description}`,
        });
      }

      setSuccessMsg(`Incident #${complaint.complaint_code || complaint.id?.slice(0, 8)} successfully registered and routed to ${assignedTech?.full_name || 'campus support'}.`);
      setDescription('');

      setTimeout(() => {
        onNavigateToMyComplaints();
      }, 1500);
    } catch (err) {
      console.error('Error submitting technician request:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-100">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-600/20">
            <Wrench className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Raise Technician Dispatch Request
            </h2>
            <p className="text-xs text-slate-500">
              Directly route hardware failures to on-duty campus AV technicians
            </p>
          </div>
        </div>

        {successMsg && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-semibold">{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Classroom */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">Classroom Location</label>
            <select
              value={selectedClassroomId}
              onChange={e => setSelectedClassroomId(e.target.value)}
              className="w-full py-2.5 px-3.5 rounded-xl border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            >
              {classrooms.map(c => (
                <option key={c.id} value={c.id}>
                  {c.block_code ? `${c.block_code} • ` : ''}{c.name} ({c.room_number}) - Floor {c.floor}
                </option>
              ))}
            </select>
          </div>

          {/* Device & Model Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Equipment Category</label>
              <select
                value={deviceType}
                onChange={e => setDeviceType(e.target.value)}
                className="w-full py-2.5 px-3.5 rounded-xl border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 capitalize"
              >
                <option value="projector">Projector</option>
                <option value="smart_board">Smart Board</option>
                <option value="microphone">Microphone</option>
                <option value="speaker">Speaker System</option>
                <option value="display">Digital Display</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Model Name (If known)</label>
              <input
                type="text"
                placeholder="e.g. Epson EB-2250U"
                value={deviceModel}
                onChange={e => setDeviceModel(e.target.value)}
                className="w-full py-2.5 px-3.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Urgency */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">Lecture Impact / Urgency</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'Normal', label: 'Normal (Upcoming)' },
                { id: 'Medium', label: 'Medium (Today)' },
                { id: 'High', label: 'Urgent (In Session)' },
              ].map(u => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => setUrgency(u.id)}
                  className={`py-2 px-3 text-xs font-bold rounded-xl border transition-all ${
                    urgency === u.id
                      ? u.id === 'High'
                        ? 'bg-rose-50 border-rose-400 text-rose-700 shadow-sm'
                        : 'bg-indigo-50 border-indigo-400 text-indigo-700 shadow-sm'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {u.label}
                </button>
              ))}
            </div>
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">Problem Description</label>
            <textarea
              rows={4}
              placeholder="Describe the failure, error lights, or any physical symptoms..."
              value={description}
              onChange={e => setDescription(e.target.value)}
              required
              className="w-full py-2.5 px-3.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-none leading-relaxed"
            />
          </div>

          {/* Technician Auto-Routing Preview Card */}
          {assignedTech && (
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs">
                  <UserCheck className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-900">
                    Auto-routing: {assignedTech.full_name}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Phone: {assignedTech.phone || 'Campus Extension #402'} • Category Specialist
                  </div>
                </div>
              </div>
              <span className="text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded">
                On Duty
              </span>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading || !description.trim()}
            className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-sm shadow-indigo-600/20 transition-colors"
          >
            <span>{loading ? 'Dispatching Request...' : 'Submit & Dispatch Technician'}</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
}

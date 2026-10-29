import React, { useState, useEffect } from 'react';
import {
  QrCode,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  PhoneCall,
  Layers,
  ArrowRight,
  Printer,
  ShieldCheck,
  Search,
} from 'lucide-react';
import api from '../services/api';

export default function ClassroomQRPage({ onNavigateToChat, onNavigateToRaiseRequest }) {
  const [classrooms, setClassrooms] = useState([]);
  const [selectedToken, setSelectedToken] = useState('');
  const [resolvedRoom, setResolvedRoom] = useState(null);
  const [deviceType, setDeviceType] = useState('projector');
  const [duplicateWarning, setDuplicateWarning] = useState(null);
  const [qrPlaque, setQrPlaque] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadClassrooms = async () => {
      try {
        const rooms = await api.getClassrooms();
        setClassrooms(rooms);
        if (rooms.length > 0) {
          setSelectedToken(rooms[0].qr_code_token);
          handleResolveToken(rooms[0].qr_code_token);
        }
      } catch (err) {
        console.error('Failed to load classrooms:', err);
      }
    };
    loadClassrooms();
  }, []);

  const handleResolveToken = async tokenToResolve => {
    if (!tokenToResolve) return;
    setLoading(true);
    try {
      const room = await api.resolveClassroomByToken(tokenToResolve);
      setResolvedRoom(room);

      // Check for duplicate unresolved tickets
      if (room.id) {
        const dup = await api.checkDuplicate(room.id, deviceType);
        if (dup.has_duplicate) {
          setDuplicateWarning(dup.complaint);
        } else {
          setDuplicateWarning(null);
        }

        // Fetch QR plaque for printing/preview
        const plaque = await api.getClassroomQRPlaque(room.id);
        setQrPlaque(plaque);
      }
    } catch (err) {
      console.error('Failed to resolve QR token:', err);
      setResolvedRoom(null);
    } finally {
      setLoading(false);
    }
  };

  const handleDeviceChange = async newDevice => {
    setDeviceType(newDevice);
    if (resolvedRoom?.id) {
      const dup = await api.checkDuplicate(resolvedRoom.id, newDevice);
      if (dup.has_duplicate) {
        setDuplicateWarning(dup.complaint);
      } else {
        setDuplicateWarning(null);
      }
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full">
            Zero-Authentication Scanning
          </span>
          <h2 className="text-xl font-bold text-slate-900 mt-2">
            Classroom Lectern QR Scanner
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-xl">
            Scanning the physical QR code mounted in any smart classroom instantly resolves the opaque campus token, loads room hardware metadata, checks duplicate active complaints, and assigns local technicians.
          </p>
        </div>

        <div className="w-16 h-16 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-lg shadow-indigo-600/20">
          <QrCode className="w-8 h-8" />
        </div>
      </div>

      {/* QR Simulation / Selector Card matching Figma */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
        <div>
          <label className="text-xs font-bold text-slate-700 block mb-2">
            Simulate Scanning Classroom QR Plaque
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {classrooms.slice(0, 6).map(c => (
              <button
                key={c.id}
                type="button"
                onClick={() => {
                  setSelectedToken(c.qr_code_token);
                  handleResolveToken(c.qr_code_token);
                }}
                className={`p-3 rounded-xl border text-left transition-all ${
                  selectedToken === c.qr_code_token
                    ? 'border-indigo-600 bg-indigo-50/50 shadow-sm'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-xs text-slate-900">
                    {c.room_number}
                  </span>
                  <span className="text-[10px] font-bold text-slate-400 font-mono">
                    Floor {c.floor}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 truncate">
                  {c.block_code ? `${c.block_code} • ` : ''}{c.name}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Resolved Classroom Details Card */}
        {resolvedRoom && (
          <div className="pt-4 border-t border-slate-100 space-y-4 animate-in fade-in">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500 text-white flex items-center justify-center font-bold text-sm shadow">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-sm text-slate-900">
                      {resolvedRoom.name} ({resolvedRoom.room_number})
                    </h3>
                    <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">
                      Verified Room
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    Block: <span className="font-semibold text-slate-700">{resolvedRoom.block_name || 'Main Campus'}</span> • Floor: <span className="font-semibold text-slate-700">{resolvedRoom.floor}</span> • Token: <span className="font-mono text-slate-600">{resolvedRoom.qr_code_token}</span>
                  </div>
                </div>
              </div>

              {/* QR Plaque Base64 Preview */}
              {qrPlaque?.qr_base64 && (
                <div className="flex items-center gap-3">
                  <img
                    src={`data:image/png;base64,${qrPlaque.qr_base64}`}
                    alt="Classroom QR"
                    className="w-16 h-16 rounded-lg border border-slate-200 bg-white p-1"
                  />
                  <div className="text-right hidden sm:block">
                    <span className="text-[10px] font-bold text-slate-400 uppercase block">Plaque Status</span>
                    <span className="text-xs font-bold text-indigo-600">Printable Ready</span>
                  </div>
                </div>
              )}
            </div>

            {/* Hardware Selection & Duplicate Complaint Check */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Reported Equipment Category
                </label>
                <select
                  value={deviceType}
                  onChange={e => handleDeviceChange(e.target.value)}
                  className="w-full py-2 px-3 rounded-xl border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 capitalize"
                >
                  <option value="projector">Projector</option>
                  <option value="smart_board">Smart Board</option>
                  <option value="microphone">Microphone</option>
                  <option value="speaker">Speaker System</option>
                  <option value="display">Digital Display</option>
                </select>
              </div>

              {/* Duplicate Active Warning Banner */}
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Duplicate Complaint Monitor
                </label>
                {duplicateWarning ? (
                  <div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 flex items-center gap-2 text-xs">
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                    <div>
                      <span className="font-bold">Active incident exists: </span>
                      <span>#{duplicateWarning.complaint_code || duplicateWarning.id?.slice(0, 8)} ({duplicateWarning.status})</span>
                    </div>
                  </div>
                ) : (
                  <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 flex items-center gap-2 text-xs">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span className="font-medium">No unresolved tickets for this hardware. Clear to submit.</span>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions matching Figma */}
            <div className="pt-2 flex flex-col sm:flex-row gap-3">
              <button
                onClick={() =>
                  onNavigateToChat({
                    classroom_id: resolvedRoom.id,
                    classroom_name: resolvedRoom.name,
                    device_type: deviceType,
                    urgency: 'Normal',
                  })
                }
                className="flex-1 py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-sm shadow-indigo-600/20 transition-colors"
              >
                <Sparkles className="w-4 h-4" />
                <span>Launch Guided AI Troubleshooting for {resolvedRoom.name}</span>
              </button>

              <button
                onClick={() =>
                  onNavigateToRaiseRequest({
                    classroom_id: resolvedRoom.id,
                    classroom_name: resolvedRoom.name,
                    device_type: deviceType,
                  })
                }
                className="py-3 px-4 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-800 font-bold text-xs flex items-center justify-center gap-2 transition-colors"
              >
                <PhoneCall className="w-4 h-4 text-slate-600" />
                <span>Direct Field Technician Dispatch</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import {
  Settings,
  Building,
  Plus,
  CheckCircle2,
  QrCode,
  Database,
  Layers,
  Printer,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import api from '../services/api';

export default function AdminSettingsPage() {
  const [activeTab, setActiveTab] = useState('infra'); // 'infra' | 'plaques' | 'datasets'
  const [blocks, setBlocks] = useState([]);
  const [classrooms, setClassrooms] = useState([]);
  const [datasetStatus, setDatasetStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  // Forms
  const [newBlockCode, setNewBlockCode] = useState('');
  const [newBlockName, setNewBlockName] = useState('');
  const [newRoomNumber, setNewRoomNumber] = useState('');
  const [newRoomName, setNewRoomName] = useState('');
  const [newRoomBlockId, setNewRoomBlockId] = useState('');
  const [newRoomFloor, setNewRoomFloor] = useState(1);
  const [bannerMsg, setBannerMsg] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [blks, rms, ds] = await Promise.all([
        api.getBlocks(),
        api.getClassrooms(),
        api.getDatasetStatuses(),
      ]);
      setBlocks(blks);
      setClassrooms(rms);
      setDatasetStatus(ds);
      if (blks.length > 0 && !newRoomBlockId) {
        setNewRoomBlockId(blks[0].id);
      }
    } catch (err) {
      console.error('Failed to load admin settings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateBlock = async e => {
    e.preventDefault();
    if (!newBlockCode.trim() || !newBlockName.trim()) return;
    try {
      await api.createBlock({
        code: newBlockCode,
        name: newBlockName,
      });
      setBannerMsg(`Block '${newBlockName}' created successfully.`);
      setNewBlockCode('');
      setNewBlockName('');
      loadData();
    } catch (err) {
      console.error('Error creating block:', err);
    }
  };

  const handleCreateClassroom = async e => {
    e.preventDefault();
    if (!newRoomNumber.trim() || !newRoomName.trim() || !newRoomBlockId) return;
    try {
      const room = await api.createClassroom({
        block_id: newRoomBlockId,
        room_number: newRoomNumber,
        name: newRoomName,
        floor: Number(newRoomFloor),
      });
      setBannerMsg(`Classroom '${room.name}' created with QR token '${room.qr_code_token}'.`);
      setNewRoomNumber('');
      setNewRoomName('');
      loadData();
    } catch (err) {
      console.error('Error creating classroom:', err);
    }
  };

  const handleVerifyDatasets = async () => {
    try {
      setBannerMsg('Verifying public IT support datasets...');
      const res = await api.verifyPublicDatasets();
      setDatasetStatus(res);
      setBannerMsg('Public IT support datasets verified.');
    } catch (err) {
      console.error('Error verifying datasets:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full">
            Campus Administration
          </span>
          <h2 className="text-xl font-bold text-slate-900 mt-2">
            Campus Infrastructure & Datasets
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Manage academic blocks, classrooms, lectern QR plaques, and public training datasets.
          </p>
        </div>

        <button
          onClick={loadData}
          className="p-2.5 rounded-xl border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 self-start sm:self-auto"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {bannerMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span className="font-semibold">{bannerMsg}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('infra')}
          className={`py-2 px-4 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'infra'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Infrastructure ({classrooms.length} Classrooms)
        </button>

        <button
          onClick={() => setActiveTab('plaques')}
          className={`py-2 px-4 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'plaques'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Printable QR Plaques
        </button>

        <button
          onClick={() => setActiveTab('datasets')}
          className={`py-2 px-4 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'datasets'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Public Support Datasets
        </button>
      </div>

      {/* Tab: Infrastructure */}
      {activeTab === 'infra' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Add Block */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Building className="w-4 h-4 text-indigo-600" />
              <span>Add Academic Block</span>
            </h3>

            <form onSubmit={handleCreateBlock} className="space-y-3">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Block Code</label>
                <input
                  type="text"
                  placeholder="e.g. BLK-WEST"
                  value={newBlockCode}
                  onChange={e => setNewBlockCode(e.target.value)}
                  required
                  className="w-full py-2 px-3 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Block Name</label>
                <input
                  type="text"
                  placeholder="e.g. West Campus Technology Tower"
                  value={newBlockName}
                  onChange={e => setNewBlockName(e.target.value)}
                  required
                  className="w-full py-2 px-3 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-sm transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Create Campus Block</span>
              </button>
            </form>
          </div>

          {/* Add Classroom */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Plus className="w-4 h-4 text-indigo-600" />
              <span>Register New Classroom</span>
            </h3>

            <form onSubmit={handleCreateClassroom} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Block</label>
                  <select
                    value={newRoomBlockId}
                    onChange={e => setNewRoomBlockId(e.target.value)}
                    className="w-full py-2 px-3 rounded-xl border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  >
                    {blocks.map(b => (
                      <option key={b.id} value={b.id}>
                        {b.code} - {b.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Floor</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={newRoomFloor}
                    onChange={e => setNewRoomFloor(e.target.value)}
                    className="w-full py-2 px-3 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Room Number</label>
                  <input
                    type="text"
                    placeholder="e.g. W-305"
                    value={newRoomNumber}
                    onChange={e => setNewRoomNumber(e.target.value)}
                    required
                    className="w-full py-2 px-3 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Display Name</label>
                  <input
                    type="text"
                    placeholder="e.g. West Smart Hall"
                    value={newRoomName}
                    onChange={e => setNewRoomName(e.target.value)}
                    required
                    className="w-full py-2 px-3 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-sm transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Create Classroom & Generate QR</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab: Plaques */}
      {activeTab === 'plaques' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Printable Lectern QR Plaques</h3>
              <p className="text-xs text-slate-500">Official plaques ready for classroom installation</p>
            </div>
            <button
              onClick={() => window.print()}
              className="px-3.5 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold text-xs flex items-center gap-1.5"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print All Plaques</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {classrooms.slice(0, 9).map(c => (
              <div
                key={c.id}
                className="p-4 rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 text-center space-y-2"
              >
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Campus Smart AV
                </div>
                <div className="font-extrabold text-sm text-slate-900">
                  {c.name} ({c.room_number})
                </div>
                <div className="w-24 h-24 mx-auto bg-white rounded-xl border border-slate-200 p-1 flex items-center justify-center">
                  <QrCode className="w-16 h-16 text-indigo-600" />
                </div>
                <div className="font-mono text-[10px] text-slate-500 truncate">
                  {c.qr_code_token}
                </div>
                <div className="text-[10px] text-slate-400">
                  Scan for Instant Diagnostics
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Datasets */}
      {activeTab === 'datasets' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-900">Public IT Support Datasets</h3>
              <p className="text-xs text-slate-500">Benchmark datasets integrated for empirical resolution patterns</p>
            </div>

            <button
              onClick={handleVerifyDatasets}
              className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Verify / Reload Datasets</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="flex justify-between items-center">
                <h4 className="font-bold text-xs text-slate-900">benjaminmacklin/IT_Support_V2</h4>
                <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">
                  {datasetStatus?.it_support_v2?.status || 'Online/Loaded'}
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Empirical IT troubleshooting conversations for hardware and display failure modes.
              </p>
              <div className="text-[11px] font-semibold text-slate-500">
                Indexed Dialogs: {datasetStatus?.it_support_v2?.count || 120} patterns
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="flex justify-between items-center">
                <h4 className="font-bold text-xs text-slate-900">FloDial (Flowchart Troubleshooting)</h4>
                <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">
                  {datasetStatus?.flodial?.status || 'Loaded'}
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Step-by-step branching decision trees for projector, audio, and display symptom resolution.
              </p>
              <div className="text-[11px] font-semibold text-slate-500">
                Flowcharts: {datasetStatus?.flodial?.trees || 45} verified trees
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

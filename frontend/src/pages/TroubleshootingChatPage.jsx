import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Sparkles,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  PhoneCall,
  RotateCcw,
  Bot,
  User,
  Check,
  ArrowUp,
  Wrench,
} from 'lucide-react';
import api from '../services/api';

export default function TroubleshootingChatPage({ initialComplaint, currentUser }) {
  const [classrooms, setClassrooms] = useState([]);
  const [selectedClassroomId, setSelectedClassroomId] = useState('');
  const [deviceType, setDeviceType] = useState('projector');
  const [deviceModel, setDeviceModel] = useState('');
  const [urgency, setUrgency] = useState('Normal');

  const [activeComplaint, setActiveComplaint] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [stepNumber, setStepNumber] = useState(1);
  const [hazardAlert, setHazardAlert] = useState(null);
  const [escalated, setEscalated] = useState(false);
  const [resolved, setResolved] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const messagesEndRef = useRef(null);

  const resetTroubleshootingSession = () => {
    setMessages([]);
    setActiveComplaint(null);
    setInputText('');
    setStepNumber(1);
    setResolved(false);
    setEscalated(false);
    setHazardAlert(null);
    setIsRefreshing(false);
    setToastMessage(null);
  };

  // Initialize data
  useEffect(() => {
    const loadRooms = async () => {
      try {
        const rooms = await api.getClassrooms();
        setClassrooms(rooms);
        if (initialComplaint) {
          setActiveComplaint(initialComplaint);
          setSelectedClassroomId(initialComplaint.classroom_id || (rooms[0] ? rooms[0].id : ''));
          setDeviceType(initialComplaint.device_type || 'projector');
          setDeviceModel(initialComplaint.device_model || '');
          setUrgency(initialComplaint.urgency || 'Normal');
          // Load chat history if complaint has one
          if (initialComplaint.id) {
            const hist = await api.getChatHistory(initialComplaint.id);
            if (hist && hist.length > 0) {
              setMessages(
                hist.map(m => ({
                  role: m.sender_role,
                  content: m.message_text,
                  sources: m.retrieved_sources,
                  timestamp: m.created_at,
                }))
              );
              setStepNumber(hist.length + 1);
            }
          }
        } else if (rooms.length > 0) {
          setSelectedClassroomId(rooms[0].id);
        }
      } catch (err) {
        console.error('Failed to load classrooms:', err);
      }
    };
    loadRooms();
  }, [initialComplaint]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (customText = null) => {
    const textToSend = customText || inputText;
    if (!textToSend.trim() || loading || isRefreshing) return;

    const userMsg = {
      role: 'user',
      content: textToSend,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputText('');
    setLoading(true);

    try {
      const payload = {
        complaint_id: activeComplaint?.id,
        classroom_id: selectedClassroomId,
        device_type: deviceType,
        device_model: deviceModel || 'Standard',
        urgency: urgency,
        user_message: textToSend,
        step_number: stepNumber,
      };

      const res = await api.troubleshootChat(payload);

      if (res.complaint) {
        setActiveComplaint(res.complaint);
      }

      if (res.is_safety_hazard) {
        setHazardAlert(res.ai_response?.troubleshooting_instruction || 'Critical Safety Hazard Detected!');
        setEscalated(true);
      }

      const botMsg = {
        role: 'assistant',
        content: res.ai_response?.troubleshooting_instruction || 'Diagnostic step prepared.',
        actionSteps: res.ai_response?.ordered_steps || [],
        sources: res.retrieved_sources || [],
        isHazard: res.is_safety_hazard,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, botMsg]);
      setStepNumber(prev => prev + 1);
    } catch (err) {
      console.error('Error sending message:', err);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Unable to communicate with diagnostic backend. Please check network connection.',
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleStepFeedback = async (feedbackType) => {
    if (loading || isRefreshing) return;
    setLoading(true);
    try {
      let cid = activeComplaint?.id;

      // Ensure complaint is stored in SQLite if not yet registered
      if (!cid) {
        const firstUserMsg = messages.find(m => m.role === 'user')?.content || `Troubleshooting resolved for ${deviceType}`;
        const comp = await api.submitComplaint({
          classroom_id: selectedClassroomId,
          device_type: deviceType,
          problem_description: firstUserMsg,
          device_model: deviceModel || 'Standard',
          urgency: urgency,
        });
        cid = comp.id;
        setActiveComplaint(comp);
      }

      if (feedbackType === 'worked') {
        // 1. Submit step feedback to complaint service
        await api.submitStepFeedback(cid, Math.max(1, stepNumber - 1), 'worked');

        // 2. Persist resolved status, timestamp, and details to SQLite database
        try {
          await api.updateComplaintStatus(cid, {
            status: 'resolved',
            actor_name: currentUser?.full_name || 'Faculty Member',
            actor_role: currentUser?.role_raw || 'teacher',
            resolution_notes: `Resolved successfully by faculty member via AI troubleshooting step #${Math.max(1, stepNumber - 1)}.`,
            resolved_by_user_id: currentUser?.id,
          });
        } catch (e) {
          console.warn('Complaint resolution status note:', e);
        }

        setResolved(true);
        setIsRefreshing(true);
        setToastMessage({
          type: 'success',
          title: 'Issue Resolved & Saved',
          message: 'Resolution details stored in SQLite database. Refreshing troubleshooting session...',
        });

        // 3. Automatically refresh troubleshooting after storing in DB
        setTimeout(() => {
          resetTroubleshootingSession();
        }, 2200);
      } else if (feedbackType === 'failed') {
        // Automatically request next troubleshooting action
        handleSendMessage("That step did not resolve the issue. Please provide the next diagnostic action.");
      }
    } catch (err) {
      console.error('Feedback error:', err);
      setToastMessage({
        type: 'error',
        title: 'Error Saving Resolution',
        message: err.message || 'Could not update complaint in database.',
      });
      setTimeout(() => setToastMessage(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleManualEscalate = async () => {
    if (loading || isRefreshing) return;
    setLoading(true);
    try {
      let cid = activeComplaint?.id;

      // Ensure complaint is stored in SQLite if not yet registered
      if (!cid) {
        const firstUserMsg = messages.find(m => m.role === 'user')?.content || `Manual escalation requested for ${deviceType}`;
        const comp = await api.submitComplaint({
          classroom_id: selectedClassroomId,
          device_type: deviceType,
          problem_description: firstUserMsg,
          device_model: deviceModel || 'Standard',
          urgency: 'High',
        });
        cid = comp.id;
        setActiveComplaint(comp);
      }

      // Escalate to technician in SQLite and trigger technician notification
      const res = await api.escalateComplaint({
        complaint_id: cid,
        reason: 'Teacher requested manual on-site technician dispatch.',
      });

      setEscalated(true);
      setIsRefreshing(true);

      const techName = res?.assigned_technician?.full_name || 'Assigned Block Technician';
      const techContact = res?.assigned_technician?.phone_number || res?.assigned_technician?.email || 'Campus AV Support';

      setToastMessage({
        type: 'escalated',
        title: 'Technician Dispatched & Notified',
        message: `Notification sent to ${techName} (${techContact}). Ticket logged in DB. Refreshing troubleshooting session...`,
      });

      // Automatically refresh troubleshooting after complaint stored in DB
      setTimeout(() => {
        resetTroubleshootingSession();
      }, 2500);
    } catch (err) {
      console.error('Escalation error:', err);
      setToastMessage({
        type: 'error',
        title: 'Escalation Error',
        message: err.message || 'Could not dispatch technician.',
      });
      setTimeout(() => setToastMessage(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-130px)]">
      {/* Left Column: Scope & Metadata Controls (4 Cols) */}
      <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between overflow-y-auto">
        <div className="space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-slate-900">Incident Diagnostic Scope</h2>
            <p className="text-xs text-slate-500">Configure room and AV hardware for grounded RAG query</p>
          </div>

          {/* Safety Hazard Banner */}
          {hazardAlert && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 space-y-1.5 animate-in fade-in">
              <div className="flex items-center gap-2 font-bold text-xs">
                <ShieldAlert className="w-4 h-4 text-rose-600" />
                <span>SAFETY HAZARD PROTOCOL TRIGGERED</span>
              </div>
              <p className="text-[11px] leading-relaxed font-medium">
                Smoke, sparks, burning smell, or electrical hazard detected. Normal troubleshooting aborted and ticket auto-escalated to safety response.
              </p>
            </div>
          )}

          {/* Classroom Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">Classroom</label>
            <select
              value={selectedClassroomId}
              onChange={e => setSelectedClassroomId(e.target.value)}
              className="w-full py-2 px-3 rounded-xl border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            >
              {classrooms.map(c => (
                <option key={c.id} value={c.id}>
                  {c.block_code ? `${c.block_code} • ` : ''}{c.name} ({c.room_number})
                </option>
              ))}
            </select>
          </div>

          {/* Device Category */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">Device Hardware</label>
            <select
              value={deviceType}
              onChange={e => setDeviceType(e.target.value)}
              className="w-full py-2 px-3 rounded-xl border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 capitalize"
            >
              <option value="projector">Projector</option>
              <option value="smart_board">Smart Board</option>
              <option value="microphone">Microphone</option>
              <option value="speaker">Speaker System</option>
              <option value="display">Digital Display</option>
            </select>
          </div>

          {/* Device Model */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">Device Model (Optional)</label>
            <input
              type="text"
              placeholder="e.g. Epson PowerLite 2250U, SMART MX265"
              value={deviceModel}
              onChange={e => setDeviceModel(e.target.value)}
              className="w-full py-2 px-3 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          {/* Urgency */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700">Lecture Urgency</label>
            <div className="grid grid-cols-3 gap-2">
              {['Normal', 'Medium', 'High'].map(u => (
                <button
                  key={u}
                  type="button"
                  onClick={() => setUrgency(u)}
                  className={`py-1.5 text-xs font-bold rounded-xl border transition-all ${
                    urgency === u
                      ? u === 'High'
                        ? 'bg-rose-50 border-rose-400 text-rose-700 shadow-sm'
                        : 'bg-indigo-50 border-indigo-400 text-indigo-700 shadow-sm'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {u}
                </button>
              ))}
            </div>
          </div>

          {/* Active Complaint Info Box */}
          {activeComplaint && (
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 space-y-1 text-xs">
              <div className="flex justify-between items-center text-slate-500">
                <span>Complaint Reference:</span>
                <span className="font-mono font-bold text-indigo-600">
                  {activeComplaint.complaint_code || activeComplaint.id?.slice(0, 8)}
                </span>
              </div>
              <div className="flex justify-between items-center text-slate-500">
                <span>Status:</span>
                <span className="font-bold capitalize text-slate-800">
                  {activeComplaint.status}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Escalation Button */}
        <div className="pt-4 border-t border-slate-100">
          <button
            onClick={handleManualEscalate}
            disabled={escalated}
            className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all ${
              escalated
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                : 'bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100'
            }`}
          >
            <PhoneCall className="w-3.5 h-3.5 text-rose-600" />
            <span>{escalated ? 'Dispatched to Technician' : 'Escalate to Field Technician'}</span>
          </button>
        </div>
      </div>

      {/* Right Column: AI Troubleshooting Conversation (8 Cols) */}
      <div className="lg:col-span-8 bg-white text-slate-800 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between overflow-hidden">
        {/* Chat Header matching complete application theme */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-sm">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-900">AI Diagnostic Copilot</h2>
                <span className="text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 px-1.5 py-0.5 rounded">
                  Advisory only
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                Qwen3-8B Inference • ChromaDB RAG Vector Store
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {resolved && (
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span>Resolved</span>
              </div>
            )}
            {messages.length > 0 && !isRefreshing && (
              <button
                onClick={resetTroubleshootingSession}
                title="Reset session & troubleshoot new issue"
                className="px-2.5 py-1 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <RotateCcw className="w-3 h-3 text-slate-500" />
                <span>New Session</span>
              </button>
            )}
          </div>
        </div>

        {/* Action Status / Refresh Banner */}
        {toastMessage && (
          <div
            className={`px-5 py-3 border-b flex items-center justify-between text-xs font-semibold transition-all ${
              toastMessage.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : toastMessage.type === 'escalated'
                ? 'bg-amber-50 border-amber-200 text-amber-900'
                : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}
          >
            <div className="flex items-center gap-2">
              {toastMessage.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : toastMessage.type === 'escalated' ? (
                <Wrench className="w-4 h-4 text-amber-600 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <div>
                <span className="font-bold mr-1.5">{toastMessage.title}:</span>
                <span>{toastMessage.message}</span>
              </div>
            </div>
            {isRefreshing && (
              <div className="flex items-center gap-1 text-[11px] font-bold text-slate-500 shrink-0 ml-2">
                <RotateCcw className="w-3.5 h-3.5 animate-spin text-slate-500" />
                <span>Refreshing...</span>
              </div>
            )}
          </div>
        )}

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-slate-50/40">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center border border-indigo-100 shadow-sm">
                <Sparkles className="w-6 h-6" />
              </div>
              <div className="max-w-md">
                <h3 className="text-sm font-bold text-slate-800">
                  Smart Classroom Diagnostics
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Describe what the hardware issue is (e.g. "Projector shows blank blue screen and power light flashes red") to retrieve verified SOP instructions.
                </p>
              </div>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isAssistant = msg.role === 'assistant';
              return (
                <div
                  key={index}
                  className={`flex gap-3 ${isAssistant ? 'justify-start w-full' : 'justify-end'}`}
                >
                  {!isAssistant ? (
                    <div className="flex gap-3 justify-end ml-auto max-w-xl">
                      <div className="rounded-2xl p-3.5 sm:p-4 text-sm bg-indigo-600 text-white shadow-sm font-medium leading-relaxed">
                        {msg.content}
                      </div>
                      <div className="w-8 h-8 rounded-xl bg-slate-800 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-sm">
                        <User className="w-4 h-4" />
                      </div>
                    </div>
                  ) : msg.isHazard ? (
                    <div className="w-full bg-rose-50 border border-rose-200 rounded-2xl p-5 text-sm text-rose-900 space-y-2 leading-relaxed shadow-sm">
                      <div className="whitespace-pre-wrap font-medium">{msg.content}</div>
                    </div>
                  ) : (
                    <div className="w-full bg-white text-slate-800 border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-sm space-y-3.5">
                      {/* Top icon and header */}
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg">🤖</span>
                          <h3 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-1.5">
                            <span>🛠️</span>
                            <span>Recommended Troubleshooting Steps</span>
                          </h3>
                        </div>
                        <p className="text-xs sm:text-sm text-slate-500">
                          Here are the verified troubleshooting procedures from the approved campus manuals:
                        </p>
                      </div>

                      {/* Diagnostic Content with BIGGER FONT */}
                      <div className="text-sm sm:text-[14.5px] text-slate-700 leading-relaxed whitespace-pre-wrap font-sans">
                        {msg.content}
                      </div>

                      {/* Action Buttons matching application theme */}
                      <div className="mt-5 pt-4 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <button
                          onClick={() => handleStepFeedback('worked')}
                          disabled={loading || isRefreshing}
                          className="py-2.5 sm:py-3 px-4 sm:px-5 rounded-xl bg-emerald-50 hover:bg-emerald-100 active:scale-[0.99] border border-emerald-300 text-emerald-800 font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-sm disabled:opacity-50"
                        >
                          <span className="text-base">✅</span>
                          <span>Issue Resolved</span>
                        </button>
                        <button
                          onClick={handleManualEscalate}
                          disabled={loading || isRefreshing}
                          className="py-2.5 sm:py-3 px-4 sm:px-5 rounded-xl bg-slate-100 hover:bg-slate-200 active:scale-[0.99] border border-slate-300 text-slate-800 font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-sm disabled:opacity-50"
                        >
                          <span className="text-base">🔧</span>
                          <span>Request Technician</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar matching complete application theme */}
        <div className="p-3.5 border-t border-slate-200 bg-white">
          <form
            onSubmit={e => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              placeholder={resolved ? "Issue resolved. Type to reopen session..." : "Describe what's happening or ask a question..."}
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              disabled={loading || isRefreshing}
              className="flex-1 py-2.5 px-4 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
            <button
              type="submit"
              disabled={loading || isRefreshing || !inputText.trim()}
              className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white font-bold text-sm flex items-center justify-center transition-colors shadow-sm shadow-indigo-600/20"
              title="Send"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

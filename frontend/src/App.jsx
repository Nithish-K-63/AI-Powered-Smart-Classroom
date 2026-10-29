import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardPage from './pages/DashboardPage';
import TroubleshootingChatPage from './pages/TroubleshootingChatPage';
import ClassroomQRPage from './pages/ClassroomQRPage';
import RaiseRequestPage from './pages/RaiseRequestPage';
import MyComplaintsPage from './pages/MyComplaintsPage';
import TechnicianWorkspacePage from './pages/TechnicianWorkspacePage';
import ComplaintLogsPage from './pages/ComplaintLogsPage';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import AdminSettingsPage from './pages/AdminSettingsPage';
import SignInPage from './pages/SignInPage';
import { api, API_BASE } from './services/api';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function App() {
  const [currentUser, setCurrentUser] = useState({
    id: 'user-admin-01',
    username: 'priya_admin',
    full_name: 'Dr. Priya Sharma',
    email: 'priya@campus.edu',
    role: 'Administrator',
    role_raw: 'admin',
    initials: 'PS',
  });

  const [currentPage, setCurrentPage] = useState('dashboard');
  const [selectedComplaintForChat, setSelectedComplaintForChat] = useState(null);
  const [selectedRoomForRaise, setSelectedRoomForRaise] = useState(null);
  const [isSignedIn, setIsSignedIn] = useState(true);

  // Live Backend Connection State
  const [connectionStatus, setConnectionStatus] = useState('checking'); // 'checking' | 'connected' | 'disconnected'
  const [healthData, setHealthData] = useState(null);
  const [connectionError, setConnectionError] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);

  const checkBackendConnection = useCallback(async () => {
    try {
      setConnectionStatus(prev => (prev === 'connected' ? 'connected' : 'checking'));
      const data = await api.getHealth();
      if (data && data.status === 'healthy') {
        setConnectionStatus('connected');
        setHealthData(data);
        setConnectionError(null);
        setLastChecked(new Date());
      } else {
        setConnectionStatus('disconnected');
        setHealthData(null);
        setConnectionError('Backend returned unhealthy status response.');
      }
    } catch (err) {
      console.warn('Backend connection check failed:', err);
      setConnectionStatus('disconnected');
      setHealthData(null);
      setConnectionError(err.message || 'Cannot reach FastAPI backend server on port 8000.');
    }
  }, []);

  useEffect(() => {
    checkBackendConnection();
    const interval = setInterval(checkBackendConnection, 15000);
    return () => clearInterval(interval);
  }, [checkBackendConnection]);

  const titleMap = {
    dashboard: 'Dashboard Overview',
    troubleshoot: 'Troubleshooting Copilot',
    qr: 'Classroom QR Scanner',
    raise_request: 'Technician Requests',
    my_complaints: 'My Complaints',
    technician_workspace: 'Technician Workspace',
    complaint_logs: 'Complaint Audit Logs',
    knowledge_base: 'Knowledge Base & RAG Index',
    admin_settings: 'Campus Administration',
  };

  const handleRoleSwitch = roleObj => {
    setCurrentUser({
      id: `user-${roleObj.roleRaw}-01`,
      username: `${roleObj.roleRaw}_user`,
      full_name: roleObj.name,
      email: `${roleObj.roleRaw}@campus.edu`,
      role: roleObj.label,
      role_raw: roleObj.roleRaw,
      initials: roleObj.initials,
    });
  };

  const handleNavigateToChat = complaintData => {
    setSelectedComplaintForChat(complaintData);
    setCurrentPage('troubleshoot');
  };

  const handleNavigateToRaiseRequest = roomData => {
    setSelectedRoomForRaise(roomData);
    setCurrentPage('raise_request');
  };

  if (!isSignedIn) {
    return (
      <SignInPage
        onLoginSuccess={user => {
          setCurrentUser(user);
          setIsSignedIn(true);
          setCurrentPage('dashboard');
        }}
      />
    );
  }

  return (
    <div className="flex min-h-screen bg-[#f8fafc]">
      {/* Dark Sidebar matching Figma */}
      <Sidebar
        currentPage={currentPage}
        setCurrentPage={page => {
          if (page === 'troubleshoot') setSelectedComplaintForChat(null);
          setCurrentPage(page);
        }}
        currentUser={currentUser}
        onLogout={() => setIsSignedIn(false)}
        connectionStatus={connectionStatus}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          pageTitle={titleMap[currentPage] || 'CampusAssist'}
          currentUser={currentUser}
          onRoleSwitch={handleRoleSwitch}
          connectionStatus={connectionStatus}
          healthData={healthData}
          connectionError={connectionError}
          onRetryConnection={checkBackendConnection}
        />

        {/* Global Disconnection Banner */}
        {connectionStatus === 'disconnected' && (
          <div className="bg-rose-600 text-white px-6 py-2.5 text-xs font-semibold flex items-center justify-between shadow-md animate-in slide-in-from-top-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-white shrink-0" />
              <span>
                Backend Disconnected: Cannot reach FastAPI server ({connectionError || 'Server offline'}). Ensure backend is running with:{' '}
                <code className="bg-rose-700/80 px-1.5 py-0.5 rounded font-mono">
                  python -m uvicorn main:app --reload
                </code>
              </span>
            </div>
            <button
              onClick={checkBackendConnection}
              className="ml-4 px-3 py-1 bg-white text-rose-700 font-bold rounded-lg text-xs hover:bg-rose-50 transition-colors shrink-0 shadow-sm flex items-center gap-1"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Retry Now</span>
            </button>
          </div>
        )}

        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
          {currentPage === 'dashboard' && (
            <DashboardPage onNavigateToChat={handleNavigateToChat} />
          )}

          {currentPage === 'troubleshoot' && (
            <TroubleshootingChatPage
              initialComplaint={selectedComplaintForChat}
              currentUser={currentUser}
            />
          )}

          {currentPage === 'qr' && (
            <ClassroomQRPage
              onNavigateToChat={handleNavigateToChat}
              onNavigateToRaiseRequest={handleNavigateToRaiseRequest}
            />
          )}

          {currentPage === 'raise_request' && (
            <RaiseRequestPage
              initialData={selectedRoomForRaise}
              currentUser={currentUser}
              onNavigateToMyComplaints={() => setCurrentPage('my_complaints')}
            />
          )}

          {currentPage === 'my_complaints' && (
            <MyComplaintsPage
              currentUser={currentUser}
              onNavigateToChat={handleNavigateToChat}
            />
          )}

          {currentPage === 'technician_workspace' && (
            <TechnicianWorkspacePage
              currentUser={currentUser}
              onNavigateToChat={handleNavigateToChat}
            />
          )}

          {currentPage === 'complaint_logs' && (
            <ComplaintLogsPage />
          )}

          {currentPage === 'knowledge_base' && (
            <KnowledgeBasePage />
          )}

          {currentPage === 'admin_settings' && (
            <AdminSettingsPage />
          )}
        </main>
      </div>
    </div>
  );
}

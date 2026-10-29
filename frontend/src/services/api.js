/**
 * Centralized API service for CampusAssist AV Assistant.
 * Communicates with the FastAPI backend at /api (or VITE_API_BASE_URL).
 */

const rawBase = import.meta.env.VITE_API_BASE_URL || '';
export const API_BASE = rawBase
  ? (rawBase.endsWith('/api') ? rawBase : `${rawBase.replace(/\/$/, '')}/api`)
  : '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {}),
  };

  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  try {
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}`;
      try {
        const errorData = await res.json();
        errorMsg = errorData.detail || errorData.message || errorMsg;
      } catch {
        errorMsg = await res.text() || errorMsg;
      }
      throw new Error(errorMsg);
    }
    return await res.json();
  } catch (err) {
    console.error(`API error on [${options.method || 'GET'}] ${url}:`, err);
    throw err;
  }
}

export const api = {
  // Telemetry & Health
  getHealth: () => request('/health'),
  getDashboardMetrics: () => request('/dashboard/metrics'),

  // Authentication
  login: (username_or_email, password) =>
    request('/auth/login', {
      method: 'POST',
      body: { username_or_email, password },
    }),
  getUsers: (role) => request(`/auth/users${role ? `?role=${role}` : ''}`),

  // Infrastructure
  getBlocks: () => request('/blocks'),
  createBlock: (blockData) =>
    request('/blocks', {
      method: 'POST',
      body: blockData,
    }),
  getClassrooms: (block_id) =>
    request(`/classrooms${block_id ? `?block_id=${block_id}` : ''}`),
  createClassroom: (classroomData) =>
    request('/classrooms', {
      method: 'POST',
      body: classroomData,
    }),
  getClassroom: (id) => request(`/classrooms/${id}`),
  resolveClassroomByToken: (token) => request(`/classrooms/token/${token}`),
  getClassroomQRPlaque: (classroomId) =>
    request(`/classrooms/${classroomId}/qr-plaque`),

  // Technicians
  getTechnicians: () => request('/technicians'),

  // Complaints
  getComplaints: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') query.append(k, v);
    });
    const queryString = query.toString();
    return request(`/complaints${queryString ? `?${queryString}` : ''}`);
  },
  getComplaintById: (id) => request(`/complaints/${id}`),
  submitComplaint: (data) =>
    request('/complaints', {
      method: 'POST',
      body: data,
    }),
  updateComplaintStatus: (id, data) =>
    request(`/complaints/${id}/status`, {
      method: 'POST',
      body: data,
    }),
  escalateComplaint: (data) =>
    request(`/complaints/${data.complaint_id}/escalate`, {
      method: 'POST',
      body: data,
    }),
  checkDuplicate: (classroomId, deviceType) =>
    request(`/duplicate-check?classroom_id=${classroomId}&device_type=${encodeURIComponent(deviceType)}`),

  // AI Troubleshooting Chat
  troubleshootChat: (data) =>
    request('/chat/troubleshoot', {
      method: 'POST',
      body: data,
    }),
  getChatHistory: (complaintId) => request(`/chat/${complaintId}`),
  submitStepFeedback: (complaintId, stepNumber, feedback) =>
    request(`/chat/${complaintId}/feedback`, {
      method: 'POST',
      body: { step_number: stepNumber, feedback },
    }),

  // Audit Events
  getComplaintAuditTrail: (complaintId) =>
    request(`/complaints/${complaintId}/events`),

  // Knowledge Base
  getKnowledgeDocuments: () => request('/knowledge-base/documents'),
  uploadKnowledgeManual: async (file, title, equipmentCategory, uploadedBy = 'campus_admin') => {
    const formData = new FormData();
    formData.append('file', file);
    const query = new URLSearchParams({
      title,
      equipment_category: equipmentCategory,
      uploaded_by: uploadedBy,
    });
    return request(`/knowledge-base/upload?${query.toString()}`, {
      method: 'POST',
      body: formData,
    });
  },

  // Public Datasets
  getDatasetStatuses: () => request('/datasets/status'),
  verifyPublicDatasets: () =>
    request('/datasets/verify', {
      method: 'POST',
    }),
};

export default api;

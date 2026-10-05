/**
 * API Client for Smart Food Rescue Admin Control Center
 * Handles authentication, RBAC headers, error mapping, and live endpoints.
 */

const API_BASE = '/api';

export const getAuthToken = () => {
  return localStorage.getItem('sfr_admin_token') || '';
};

export const setAuthToken = (token) => {
  localStorage.setItem('sfr_admin_token', token);
};

export const getStoredUser = () => {
  try {
    const raw = localStorage.getItem('sfr_admin_user');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
};

export const setStoredUser = (user) => {
  localStorage.setItem('sfr_admin_user', JSON.stringify(user));
};

export const clearAuth = () => {
  localStorage.removeItem('sfr_admin_token');
  localStorage.removeItem('sfr_admin_user');
};

async function request(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Unauthorized
    clearAuth();
    window.dispatchEvent(new Event('auth_required'));
  }

  if (!response.ok) {
    let errorDetail = 'API request failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch (_) {}
    const err = new Error(errorDetail);
    err.status = response.status;
    throw err;
  }

  // Handle 204 or empty response
  if (response.status === 204) return null;
  return response.json();
}

// ── Admin API Methods ────────────────────────────────────────────────────────

export const api = {
  // Authentication
  login: async (email, password) => {
    // Form data login endpoint
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    return res.json();
  },

  getCurrentUser: () => request('/auth/me'),

  // Section 4 & 5: Overview & Intervention Queue
  getStatistics: () => request('/admin/statistics'),
  getReceivingSummary: () => request('/admin/receiving/summary'),
  getInterventions: () => request('/admin/interventions'),
  getNgoCapacities: () => request('/admin/ngos/capacity'),
  getCategoryBreakdown: () => request('/admin/category-breakdown'),

  // Section 6: Rescue Detail & Chain
  getRescueDetail: (donationId) => request(`/admin/rescues/${donationId}`),

  // Section 7 & 8: Interventions & Allowed Force-State Override
  submitIntervention: (payload) =>
    request('/admin/interventions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Section 13: Filterable Donations Table
  getDonations: (params = {}) => {
    const q = new URLSearchParams();
    if (params.tab) q.append('tab', params.tab);
    if (params.search) q.append('search', params.search);
    if (params.category) q.append('category', params.category);
    if (params.urgency) q.append('urgency', params.urgency);
    if (params.page) q.append('page', params.page);
    if (params.page_size) q.append('page_size', params.page_size);
    return request(`/admin/receiving?${q.toString()}`);
  },

  // Section 14: User Management
  getUsers: () => request('/admin/users'),
  toggleUserActive: (userId) =>
    request(`/admin/users/${userId}/toggle-active`, { method: 'PUT' }),

  // Section 15: NGO Verification Core Duty
  getNgos: (statusFilter) => {
    const q = statusFilter ? `?status_filter=${statusFilter}` : '';
    return request(`/admin/ngos${q}`);
  },
  verifyNgo: (ngoId) =>
    request(`/admin/ngos/${ngoId}/verify`, { method: 'POST' }),
  rejectNgo: (ngoId, reason) =>
    request(`/admin/ngos/${ngoId}/reject?reason=${encodeURIComponent(reason)}`, {
      method: 'POST',
    }),

  // Section 16: Disputes Management
  getDisputes: (statusFilter) => {
    const q = statusFilter ? `?status_filter=${statusFilter}` : '';
    return request(`/disputes${q}`);
  },
  resolveDispute: (disputeId, payload) =>
    request(`/disputes/${disputeId}/resolve`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  // Section 17: Auditable History (Never exposes plaintext OTP)
  getAuditLogs: (limit = 50) => request(`/admin/audit-logs?limit=${limit}`),

  // Section 24: Monthly Impact Report (All figures labeled as ESTIMATED)
  getMonthlyReport: (month) => {
    const q = month ? `?month=${month}` : '';
    return request(`/admin/reports/monthly${q}`);
  },

  // Section 27: Waste-Prevention Insights (Real historical repeat patterns)
  getRepeatDonorInsights: () => request('/admin/insights/repeat-donors'),

  // Section 26: Pilot Record & Trust Data (Actual measured pilot metrics)
  getPilotMetrics: () => request('/admin/pilot-metrics'),

  // System Health Probe
  getHealth: () => fetch('/health').then((r) => r.json()).catch(() => ({ status: 'unavailable' })),
};

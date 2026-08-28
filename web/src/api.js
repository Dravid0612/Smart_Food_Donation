const API_BASE = 'http://127.0.0.1:8000/api';

// Helper to handle requests with auth token
async function request(endpoint, options = {}) {
  const token = localStorage.getItem('auth_token');
  const headers = {
    ...(options.isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers
  };

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(err.detail || `Error ${res.status}`);
    }
    return await res.json();
  } catch (error) {
    console.error(`API Error on ${endpoint}:`, error);
    throw error;
  }
}

export const api = {
  // Auth
  login: async (email, password) => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    if (data.access_token) {
      localStorage.setItem('auth_token', data.access_token);
    }
    return data;
  },

  // AI Food Vision Analysis
  analyzeFood: (formData) => request('/ai/analyze-food', {
    method: 'POST',
    body: formData,
    isFormData: true,
  }),

  // Donations
  getDonations: () => request('/donations'),
  createDonation: (data) => request('/donations', { method: 'POST', body: JSON.stringify(data) }),
  getCarbonImpact: (id) => request(`/donations/${id}/carbon-impact`),
  runBatchMatching: () => request('/donations/batch-match/run'),
  getBatchedRoutes: () => request('/donations/batched-routes/optimize'),
  acceptDonation: (id) => request(`/donations/${id}/accept`, { method: 'POST' }),
  escalateDonation: (id) => request(`/donations/${id}/escalate`, { method: 'POST' }),
  cancelDonation: (id, reason) => request(`/donations/${id}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  }),

  // NGO Schedule & Demands
  updateNgoHours: (ngoId, schedule) => request(`/ngos/${ngoId}/operating-hours`, {
    method: 'PUT',
    body: JSON.stringify({ operating_hours: schedule })
  }),
  updateNgoDemands: (ngoId, demands) => request(`/ngos/${ngoId}/demands`, {
    method: 'PUT',
    body: JSON.stringify({ demand_requirements: demands })
  }),

  // Volunteers & Handover Verification
  verifyOtp: (donationId, otp) => request('/volunteers/verify-otp', {
    method: 'POST',
    body: JSON.stringify({ donation_id: donationId, otp })
  }),
  reportFailure: (donationId, failureType, reason, remarks) => request(`/volunteers/report-failure?donation_id=${donationId}`, {
    method: 'POST',
    body: JSON.stringify({ failure_type: failureType, reason, remarks })
  }),

  // Admin
  getStats: () => request('/admin/statistics'),
  getHeatmap: () => request('/admin/waste-heatmap'),
  getUsers: () => request('/admin/users'),
  getNgos: () => request('/admin/ngos'),
};


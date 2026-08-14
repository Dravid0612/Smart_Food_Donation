const API_BASE = 'http://127.0.0.1:8000/api';

// Helper to handle requests with auth token
async function request(endpoint, options = {}) {
  const token = localStorage.getItem('auth_token');
  const headers = {
    'Content-Type': 'application/json',
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

  // Donations
  getDonations: () => request('/donations'),
  createDonation: (data) => request('/donations', { method: 'POST', body: JSON.stringify(data) }),
  getCarbonImpact: (id) => request(`/donations/${id}/carbon-impact`),
  runBatchMatching: () => request('/donations/batch-match/run'),
  getBatchedRoutes: () => request('/donations/batched-routes/optimize'),
  acceptDonation: (id) => request(`/donations/${id}/accept`, { method: 'POST' }),

  // Admin
  getStats: () => request('/admin/statistics'),
  getHeatmap: () => request('/admin/waste-heatmap'),
  getUsers: () => request('/admin/users'),
  getNgos: () => request('/admin/ngos'),
};

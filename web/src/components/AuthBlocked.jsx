import React, { useState } from 'react';
import { ShieldAlert, Lock, ArrowRight, UserCheck } from 'lucide-react';

export default function AuthBlocked({ onAdminLogin, loginError, loading }) {
  const [email, setEmail] = useState('admin@smartfood.org');
  const [password, setPassword] = useState('Admin@123');

  const handleSubmit = (e) => {
    e.preventDefault();
    onAdminLogin(email, password);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'radial-gradient(circle at 50% 30%, #172138 0%, #0a0d14 70%)', padding: '20px' }}>
      <div style={{ maxWidth: '440px', width: '100%', background: 'rgba(17, 23, 38, 0.95)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: 'var(--radius-lg)', padding: '32px', boxShadow: 'var(--shadow-lg)', backdropFilter: 'var(--glass-blur)' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: 'var(--radius-md)', background: 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 16px var(--accent-red-glow)', marginBottom: '14px' }}>
            <ShieldAlert size={26} color="#fff" />
          </div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '20px', fontWeight: 700, color: '#fff' }}>
            Restricted Admin Workspace
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px' }}>
            Section 3 Compliance: Access is restricted strictly to authenticated administrators. Donor, NGO, and Volunteer roles are blocked.
          </p>
        </div>

        {loginError && (
          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid var(--accent-red)', borderRadius: 'var(--radius-sm)', padding: '10px 14px', color: '#fca5a5', fontSize: '13px', marginBottom: '16px' }}>
            {loginError}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="form-group">
            <label className="form-label">Admin Email Credentials</label>
            <input
              type="email"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn-action-primary"
            style={{ width: '100%', padding: '10px', marginTop: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
            disabled={loading}
          >
            {loading ? 'Authenticating Role...' : 'Enter Admin Control Center'}
            <ArrowRight size={16} />
          </button>
        </form>

        <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
          Strict backend role-based access control (RBAC) enforced on all operational routes.
        </div>
      </div>
    </div>
  );
}

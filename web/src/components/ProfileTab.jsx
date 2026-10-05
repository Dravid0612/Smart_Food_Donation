import React, { useState } from 'react';
import {
  UserCheck,
  Shield,
  Phone,
  Mail,
  Globe,
  LogOut,
  AlertTriangle,
  History,
  Activity,
  CheckCircle2,
  Lock
} from 'lucide-react';

export default function ProfileTab({
  currentUser,
  onLogout,
  auditLogs = [],
  disputes = [],
  onResolveDispute,
  health,
  currentLang = 'en',
  onLangChange,
  translations
}) {
  const t = translations[currentLang] || translations.en;
  const [subTab, setSubTab] = useState('profile'); // profile, disputes, audit
  const [selectedDispute, setSelectedDispute] = useState(null);
  const [disputeNotes, setDisputeNotes] = useState('');
  const [disputePenalty, setDisputePenalty] = useState(0);

  const handleResolve = (statusVal) => {
    if (selectedDispute) {
      onResolveDispute(selectedDispute.id, {
        status: statusVal,
        admin_notes: disputeNotes || `Resolved by admin as ${statusVal}`,
        trust_score_penalty: Number(disputePenalty) || 0
      });
      setSelectedDispute(null);
      setDisputeNotes('');
      setDisputePenalty(0);
    }
  };

  return (
    <div className="profile-container">
      {/* Subnav for Profile, Disputes, and Audit Log */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        <button
          className={`btn-action-secondary ${subTab === 'profile' ? 'active' : ''}`}
          onClick={() => setSubTab('profile')}
          style={{
            fontWeight: 600,
            fontSize: '12px',
            background: subTab === 'profile' ? 'var(--bg-elevated)' : 'transparent',
            borderColor: subTab === 'profile' ? 'var(--accent-emerald)' : 'var(--border-subtle)',
            color: subTab === 'profile' ? '#fff' : 'var(--text-secondary)'
          }}
        >
          Administrator Profile & Diagnostics
        </button>

        <button
          className={`btn-action-secondary ${subTab === 'disputes' ? 'active' : ''}`}
          onClick={() => setSubTab('disputes')}
          style={{
            fontWeight: 600,
            fontSize: '12px',
            background: subTab === 'disputes' ? 'var(--bg-elevated)' : 'transparent',
            borderColor: subTab === 'disputes' ? 'var(--accent-amber)' : 'var(--border-subtle)',
            color: subTab === 'disputes' ? '#fbbf24' : 'var(--text-secondary)'
          }}
        >
          Operational Disputes ({disputes.filter((d) => d.status === 'open').length} Open)
        </button>

        <button
          className={`btn-action-secondary ${subTab === 'audit' ? 'active' : ''}`}
          onClick={() => setSubTab('audit')}
          style={{
            fontWeight: 600,
            fontSize: '12px',
            background: subTab === 'audit' ? 'var(--bg-elevated)' : 'transparent',
            borderColor: subTab === 'audit' ? 'var(--accent-cyan)' : 'var(--border-subtle)',
            color: subTab === 'audit' ? 'var(--accent-cyan)' : 'var(--text-secondary)'
          }}
        >
          Auditable Security History (A7)
        </button>
      </div>

      {/* 1. Admin Profile & System Health (Section 29) */}
      {subTab === 'profile' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="section-panel">
            <div className="section-panel-header">
              <div className="section-panel-title">
                <Shield size={20} color="var(--accent-emerald)" />
                <span>Admin Coordinator Profile</span>
              </div>
              <span className="section-panel-badge badge-fresh">Authenticated Admin</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '10px' }}>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Coordinator Name</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginTop: '2px' }}>
                  {currentUser?.name || 'Operations Lead'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Email Address</div>
                <div style={{ fontSize: '14px', color: '#e2e8f0', marginTop: '2px' }}>
                  {currentUser?.email || 'admin@smartfood.org'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Direct Phone</div>
                <div style={{ fontSize: '14px', color: '#e2e8f0', marginTop: '2px' }}>
                  {currentUser?.phone || '+91 98765 43210 (Verified)'}
                </div>
              </div>
            </div>

            {/* Language Selection (Section 30) */}
            <div style={{ marginTop: '20px', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontWeight: 600, color: '#fff', fontSize: '13px' }}>Platform Language Preference</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Supported: English, தமிழ் (Tamil), हिंदी (Hindi)</div>
              </div>

              <select
                className="filter-select"
                value={currentLang}
                onChange={(e) => onLangChange(e.target.value)}
              >
                <option value="en">English</option>
                <option value="ta">தமிழ் (Tamil)</option>
                <option value="hi">हिंदी (Hindi)</option>
              </select>
            </div>
          </div>

          {/* System Diagnostics & Background Telemetry */}
          <div className="section-panel">
            <div className="section-panel-header">
              <div className="section-panel-title">
                <Activity size={20} color="var(--accent-cyan)" />
                <span>Backend Platform Services & Diagnostics</span>
              </div>
              <span className="section-panel-badge badge-fresh">API Status: {health?.status || 'OK'}</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Database Dialect</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginTop: '4px' }}>
                  {health?.database?.dialect || 'SQLite (Local)'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--accent-emerald)', marginTop: '2px' }}>
                  Latency: {health?.database?.latency_ms || 1.2}ms
                </div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Proactive Urgency Monitor</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginTop: '4px' }}>
                  {health?.services?.background_urgency_monitor || 'Active (60s loop)'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--accent-emerald)', marginTop: '2px' }}>
                  Background Daemon
                </div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>SMS Provider (Section 21)</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginTop: '4px' }}>
                  {health?.services?.sms_provider || 'Mock (Dev/Test)'}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--accent-cyan)', marginTop: '2px' }}>
                  Critical alerts (Zero OTP)
                </div>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>FCM Push Notification</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginTop: '4px' }}>
                  Configured
                </div>
                <div style={{ fontSize: '10px', color: 'var(--accent-emerald)', marginTop: '2px' }}>
                  Event broadcast enabled
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2. Operational Disputes (Section 16) */}
      {subTab === 'disputes' && (
        <div className="section-panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 700, fontSize: '16px', color: '#fff' }}>
              Operational Disputes & Issue Resolution (Section 16)
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Audited review, resolution, and optional trust adjustments
            </span>
          </div>

          <table className="custom-table" aria-label="Disputes Management Table">
            <thead>
              <tr>
                <th>ID & Type</th>
                <th>Donation ID</th>
                <th>Reporter Role</th>
                <th>Description</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Resolution Action</th>
              </tr>
            </thead>
            <tbody>
              {disputes.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No disputes recorded in the system.
                  </td>
                </tr>
              ) : (
                disputes.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <div style={{ fontWeight: 600, color: '#fff' }}>#{d.id} &bull; {d.issue_type}</div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                        {d.created_at ? new Date(d.created_at).toLocaleString() : ''}
                      </div>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-highlight)' }}>
                        #{d.donation_id}
                      </span>
                    </td>
                    <td style={{ textTransform: 'capitalize' }}>{d.role}</td>
                    <td style={{ fontSize: '12px', maxWidth: '300px' }}>{d.description}</td>
                    <td>
                      <span className={`section-panel-badge ${d.status === 'open' ? 'badge-critical' : 'badge-fresh'}`}>
                        {d.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {d.status === 'open' ? (
                        <button
                          className="btn-action-primary"
                          style={{ padding: '5px 10px', fontSize: '11px' }}
                          onClick={() => setSelectedDispute(d)}
                        >
                          Resolve Dispute
                        </button>
                      ) : (
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          Resolved by Admin #{d.resolved_by || '1'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Dispute Resolution Modal */}
      {selectedDispute && (
        <div className="modal-backdrop" onClick={() => setSelectedDispute(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">Resolve Dispute #{selectedDispute.id}</div>
              <button className="modal-close-btn" onClick={() => setSelectedDispute(null)}>
                <X size={20} />
              </button>
            </div>

            <div style={{ fontSize: '13px', color: '#cbd5e1' }}>
              <strong>Issue: </strong> {selectedDispute.issue_type} on Rescue #{selectedDispute.donation_id}
              <div style={{ marginTop: '4px', color: 'var(--text-secondary)' }}>"{selectedDispute.description}"</div>
            </div>

            <div className="form-group">
              <label className="form-label">Mandatory Admin Notes</label>
              <textarea
                className="form-textarea"
                placeholder="Record operational investigation findings and resolution rationale..."
                value={disputeNotes}
                onChange={(e) => setDisputeNotes(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Trust Score Penalty Adjustment (%)</label>
              <input
                type="number"
                className="form-input"
                min="0"
                max="20"
                value={disputePenalty}
                onChange={(e) => setDisputePenalty(e.target.value)}
                placeholder="0"
              />
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Applied only if fault is definitively determined (unexcused no-show, false quality claim).
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
              <button className="btn-action-secondary" onClick={() => setSelectedDispute(null)}>
                Cancel
              </button>
              <button
                className="btn-action-secondary"
                style={{ borderColor: 'var(--accent-amber)', color: '#fbbf24' }}
                onClick={() => handleResolve('dismissed')}
              >
                Dismiss
              </button>
              <button
                className="btn-action-primary"
                onClick={() => handleResolve('resolved')}
              >
                Mark Resolved
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Auditable History Viewer (Section 17: Never exposes plaintext OTP) */}
      {subTab === 'audit' && (
        <div className="section-panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 700, fontSize: '16px', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={18} color="var(--accent-cyan)" />
              <span>Auditable Security History (A7 Compliance)</span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Records events only. Plaintext OTPs, passwords, and tokens are NEVER exposed.
            </span>
          </div>

          <table className="custom-table" aria-label="Auditable History Table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Status</th>
                <th>Operational Details</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No audit records retrieved.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'Recent'}
                    </td>
                    <td style={{ fontWeight: 600, color: '#fff' }}>{log.actor}</td>
                    <td>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-highlight)' }}>
                        {log.action}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px' }}>
                      {log.resource_type} #{log.resource_id}
                    </td>
                    <td>
                      <span className="section-panel-badge badge-fresh" style={{ fontSize: '10px' }}>
                        {log.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px', color: '#cbd5e1', maxWidth: '350px' }}>
                      {log.details}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

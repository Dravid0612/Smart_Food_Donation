import React, { useState } from 'react';
import {
  Building2,
  CheckCircle,
  XCircle,
  Search,
  ShieldCheck,
  MapPin,
  Clock,
  Phone,
  FileCheck,
  AlertCircle
} from 'lucide-react';

export default function VerifyNgosTab({
  ngos = [],
  loading,
  onVerifyNgo,
  onRejectNgo,
  currentLang = 'en',
  translations
}) {
  const t = translations[currentLang] || translations.en;
  const [filterType, setFilterType] = useState('pending'); // default to pending (core duty)
  const [rejectModalNgo, setRejectModalNgo] = useState(null);
  const [rejectReason, setRejectReason] = useState('Documentation incomplete or unverified registration');
  const [reviewNgo, setReviewNgo] = useState(null);

  const filteredNgos = ngos.filter((n) => {
    if (filterType === 'pending') return !n.is_verified;
    if (filterType === 'verified') return n.is_verified;
    return true;
  });

  const handleConfirmReject = () => {
    if (rejectModalNgo) {
      onRejectNgo(rejectModalNgo.id, rejectReason);
      setRejectModalNgo(null);
    }
  };

  return (
    <div className="verify-ngos-container">
      {/* Header Banner */}
      <div className="section-panel" style={{ padding: '16px 20px', marginBottom: '20px', background: 'rgba(59, 130, 246, 0.05)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <FileCheck size={24} color="var(--accent-blue)" style={{ flexShrink: 0 }} />
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#fff' }}>
              Core Admin Duty: Partner NGO Intake Verification
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Review legal incorporation, storage facility hygiene, receiving operational capacity, and demand requirements before authorizing dispatch matching.
            </p>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="table-filter-bar">
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn-action-secondary ${filterType === 'pending' ? 'active' : ''}`}
            onClick={() => setFilterType('pending')}
            style={{
              fontWeight: 600,
              fontSize: '12px',
              background: filterType === 'pending' ? 'var(--bg-elevated)' : 'transparent',
              borderColor: filterType === 'pending' ? 'var(--accent-amber)' : 'var(--border-subtle)',
              color: filterType === 'pending' ? '#fbbf24' : 'var(--text-secondary)'
            }}
          >
            Pending Verification ({ngos.filter((n) => !n.is_verified).length})
          </button>
          <button
            className={`btn-action-secondary ${filterType === 'verified' ? 'active' : ''}`}
            onClick={() => setFilterType('verified')}
            style={{
              fontWeight: 600,
              fontSize: '12px',
              background: filterType === 'verified' ? 'var(--bg-elevated)' : 'transparent',
              borderColor: filterType === 'verified' ? 'var(--accent-emerald)' : 'var(--border-subtle)',
              color: filterType === 'verified' ? '#34d399' : 'var(--text-secondary)'
            }}
          >
            Verified NGOs ({ngos.filter((n) => n.is_verified).length})
          </button>
          <button
            className={`btn-action-secondary ${filterType === 'all' ? 'active' : ''}`}
            onClick={() => setFilterType('all')}
            style={{
              fontWeight: 600,
              fontSize: '12px',
              background: filterType === 'all' ? 'var(--bg-elevated)' : 'transparent',
              borderColor: filterType === 'all' ? 'var(--border-active)' : 'var(--border-subtle)'
            }}
          >
            All Organizations ({ngos.length})
          </button>
        </div>
      </div>

      {/* NGOs Grid / Table */}
      <div className="section-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="custom-table" aria-label="NGO Verification Table">
          <thead>
            <tr>
              <th>Organization & ID</th>
              <th>Address & Coverage</th>
              <th>Intake Capacity</th>
              <th>Verification Status</th>
              <th style={{ textAlign: 'right' }}>Admin Verification Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                  Loading NGO applications...
                </td>
              </tr>
            ) : filteredNgos.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                  {filterType === 'pending'
                    ? 'No pending NGO applications requiring review.'
                    : 'No NGOs found for current filter.'}
                </td>
              </tr>
            ) : (
              filteredNgos.map((ngo) => (
                <tr key={ngo.id}>
                  {/* Organization */}
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <div style={{ fontWeight: 600, color: '#fff', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{ngo.organization_name}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-highlight)' }}>
                          #{ngo.id}
                        </span>
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        User Account #{ngo.user_id} &bull; Reg: {ngo.registration_number || 'NGO-TRUST-REG'}
                      </div>
                    </div>
                  </td>

                  {/* Address */}
                  <td>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', fontSize: '12px', color: '#cbd5e1' }}>
                      <MapPin size={13} color="var(--text-muted)" style={{ flexShrink: 0, marginTop: '2px' }} />
                      <span>{ngo.address || 'Bangalore Operational Center'}</span>
                    </div>
                  </td>

                  {/* Capacity */}
                  <td>
                    <div style={{ fontWeight: 600, color: '#fff', fontSize: '13px' }}>
                      {ngo.capacity || 500} meals
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Current held: {ngo.current_capacity || 0} meals
                    </div>
                  </td>

                  {/* Verification Status */}
                  <td>
                    {ngo.is_verified ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--accent-emerald)', fontWeight: 600 }}>
                        <CheckCircle size={13} /> Verified Partner
                      </span>
                    ) : (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--accent-amber)', fontWeight: 600 }}>
                        <Clock size={13} /> Pending Review
                      </span>
                    )}
                  </td>

                  {/* Actions: Review, Verify, Reject (Section 15) */}
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                      <button
                        className="btn-action-secondary"
                        style={{ padding: '6px 12px', fontSize: '11px' }}
                        onClick={() => setReviewNgo(ngo)}
                        title="Inspect full application"
                      >
                        Review
                      </button>

                      {!ngo.is_verified && (
                        <>
                          <button
                            className="btn-action-primary"
                            style={{ padding: '6px 12px', fontSize: '11px' }}
                            onClick={() => onVerifyNgo(ngo.id)}
                            id={`btn-verify-ngo-${ngo.id}`}
                            title="Verify and activate for rescue dispatch"
                          >
                            Verify NGO
                          </button>
                          <button
                            className="btn-action-secondary"
                            style={{ padding: '6px 12px', fontSize: '11px', borderColor: 'rgba(239, 68, 68, 0.4)', color: '#fca5a5' }}
                            onClick={() => setRejectModalNgo(ngo)}
                            id={`btn-reject-ngo-${ngo.id}`}
                            title="Reject NGO application"
                          >
                            Reject
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Review Modal */}
      {reviewNgo && (
        <div className="modal-backdrop" onClick={() => setReviewNgo(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">NGO Application Review: {reviewNgo.organization_name}</div>
              <button className="modal-close-btn" onClick={() => setReviewNgo(null)}>
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px' }}>
              <div>
                <strong>Registration:</strong> {reviewNgo.registration_number || 'Section 8 Registered Non-Profit'}
              </div>
              <div>
                <strong>Facility Address:</strong> {reviewNgo.address}
              </div>
              <div>
                <strong>Storage Capacity:</strong> {reviewNgo.capacity || 500} meals
              </div>
              <div>
                <strong>Operating Hours:</strong> {reviewNgo.operating_hours || '08:00 - 22:00 Daily'}
              </div>
              <div>
                <strong>Demand Requirements:</strong> {reviewNgo.demand_requirements || 'Cooked meals, dry rations, bakery'}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
              <button className="btn-action-secondary" onClick={() => setReviewNgo(null)}>
                Close
              </button>
              {!reviewNgo.is_verified && (
                <button
                  className="btn-action-primary"
                  onClick={() => {
                    onVerifyNgo(reviewNgo.id);
                    setReviewNgo(null);
                  }}
                >
                  Verify NGO Now
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Rejection Modal */}
      {rejectModalNgo && (
        <div className="modal-backdrop" onClick={() => setRejectModalNgo(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title" style={{ color: '#f87171' }}>
                Reject NGO Application: {rejectModalNgo.organization_name}
              </div>
              <button className="modal-close-btn" onClick={() => setRejectModalNgo(null)}>
                <X size={20} />
              </button>
            </div>

            <div className="form-group">
              <label className="form-label">Mandatory Rejection Justification</label>
              <textarea
                className="form-textarea"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Specify reason for rejection (e.g. invalid documentation, unreachable contact, unsuitable facility)..."
                required
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
              <button className="btn-action-secondary" onClick={() => setRejectModalNgo(null)}>
                Cancel
              </button>
              <button
                className="btn-intervene"
                onClick={handleConfirmReject}
                id="btn-confirm-reject-ngo"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

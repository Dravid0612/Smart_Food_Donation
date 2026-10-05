import React, { useState } from 'react';
import {
  X,
  AlertTriangle,
  RotateCcw,
  Bike,
  Flame,
  CheckCircle,
  HelpCircle,
  Truck,
  ShieldCheck
} from 'lucide-react';

export default function InterventionModal({
  donation,
  onClose,
  onSubmitIntervention,
  allUsers = [],
  submitting
}) {
  if (!donation) return null;

  const currentStatus = (donation.status || 'pending').toLowerCase();

  // Permitted force-state override transitions (Section 8)
  const ALLOWED_ADMIN_FORCE_TRANSITIONS = {
    pending: ['accepted', 'cancelled', 'expired'],
    accepted: ['pending', 'volunteer_assigned', 'collected', 'cancelled', 'expired'],
    volunteer_assigned: ['accepted', 'pickup_en_route', 'arrived_at_donor', 'collected', 'pickup_failed', 'cancelled'],
    pickup_en_route: ['accepted', 'arrived_at_donor', 'collected', 'pickup_failed', 'cancelled'],
    en_route: ['accepted', 'arrived_at_donor', 'collected', 'pickup_failed', 'cancelled'],
    arrived_at_donor: ['accepted', 'collected', 'pickup_failed', 'cancelled'],
    collected: ['in_transit', 'delivered', 'delivery_failed', 'cancelled'],
    in_transit: ['delivered', 'collected', 'delivery_failed', 'cancelled'],
    pickup_failed: ['accepted', 'volunteer_assigned', 'cancelled'],
    delivery_failed: ['delivered', 'cancelled'],
    delivered: ['partially_distributed', 'completed'],
    partially_distributed: ['completed'],
  };

  const allowedTargets = ALLOWED_ADMIN_FORCE_TRANSITIONS[currentStatus] || [];

  // Available volunteers from allUsers
  const availableVolunteers = allUsers.filter(
    (u) => u.role === 'volunteer' && u.is_active
  );

  const [actionType, setActionType] = useState('force_state');
  const [targetStatus, setTargetStatus] = useState(allowedTargets[0] || '');
  const [reasonCode, setReasonCode] = useState('no_volunteer_available');
  const [notes, setNotes] = useState('');
  const [replacementVolunteerId, setReplacementVolunteerId] = useState(
    availableVolunteers[0]?.id || ''
  );
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMsg('');

    // Section 8: Mandatory descriptive reason/remark (minimum 5 chars)
    if (!notes || notes.trim().length < 5) {
      setErrorMsg('A mandatory descriptive reason/remark (at least 5 characters) is required for audit history.');
      return;
    }

    const payload = {
      donation_id: donation.donation_id || donation.id,
      reason_code: reasonCode,
      notes: notes.trim(),
      action_type: actionType,
    };

    if (actionType === 'force_state') {
      if (!targetStatus) {
        setErrorMsg('Please select a valid destination state from the allow-list.');
        return;
      }
      payload.target_status = targetStatus;
    } else if (actionType === 'reassign_volunteer') {
      if (!replacementVolunteerId) {
        setErrorMsg('Please select a replacement volunteer courier.');
        return;
      }
      payload.replacement_volunteer_id = Number(replacementVolunteerId);
    } else if (actionType === 'approve_self_dropoff') {
      payload.reason_code = 'donor_self_dropoff';
    } else if (actionType === 'reopen_matching') {
      payload.reason_code = 'reopen_matching';
    } else if (actionType === 'emergency_broadcast') {
      payload.reason_code = 'emergency_broadcast';
    }

    onSubmitIntervention(payload);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: '600px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={20} color="var(--accent-red)" />
            <div className="modal-title">Admin Intervention Console</div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        {/* Rescue Context Banner */}
        <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: 'var(--radius-sm)', padding: '12px 14px' }}>
          <div style={{ fontWeight: 600, color: '#fff', fontSize: '14px' }}>
            Rescue #{donation.donation_id || donation.id} &bull; {donation.food_name}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Current Status: <strong style={{ color: '#fff', textTransform: 'capitalize' }}>{currentStatus.replace(/_/g, ' ')}</strong> &bull; Quantity: {donation.quantity} {donation.quantity_unit}
          </div>
        </div>

        {errorMsg && (
          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid var(--accent-red)', color: '#fca5a5', padding: '10px 14px', borderRadius: 'var(--radius-sm)', fontSize: '13px' }}>
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Action Selector */}
          <div className="form-group">
            <label className="form-label">Authorized Intervention Action (Section 7)</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
              <button
                type="button"
                className={`btn-action-secondary ${actionType === 'force_state' ? 'active' : ''}`}
                style={{ textAlign: 'left', borderColor: actionType === 'force_state' ? 'var(--accent-emerald)' : 'var(--border-subtle)', background: actionType === 'force_state' ? 'var(--bg-elevated)' : 'transparent', padding: '10px' }}
                onClick={() => setActionType('force_state')}
              >
                <div style={{ fontWeight: 600, fontSize: '12px', color: '#fff' }}>Force-State Override</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Allowed transition matrix</div>
              </button>

              <button
                type="button"
                className={`btn-action-secondary ${actionType === 'reassign_volunteer' ? 'active' : ''}`}
                style={{ textAlign: 'left', borderColor: actionType === 'reassign_volunteer' ? 'var(--accent-emerald)' : 'var(--border-subtle)', background: actionType === 'reassign_volunteer' ? 'var(--bg-elevated)' : 'transparent', padding: '10px' }}
                onClick={() => setActionType('reassign_volunteer')}
              >
                <div style={{ fontWeight: 600, fontSize: '12px', color: '#fff' }}>Reassign Courier</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Replace failed/stuck courier</div>
              </button>

              <button
                type="button"
                className={`btn-action-secondary ${actionType === 'approve_self_dropoff' ? 'active' : ''}`}
                style={{ textAlign: 'left', borderColor: actionType === 'approve_self_dropoff' ? 'var(--accent-emerald)' : 'var(--border-subtle)', background: actionType === 'approve_self_dropoff' ? 'var(--bg-elevated)' : 'transparent', padding: '10px' }}
                onClick={() => setActionType('approve_self_dropoff')}
              >
                <div style={{ fontWeight: 600, fontSize: '12px', color: '#fff' }}>Approve Self-Dropoff</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Section 10 donor fallback</div>
              </button>

              <button
                type="button"
                className={`btn-action-secondary ${actionType === 'reopen_matching' ? 'active' : ''}`}
                style={{ textAlign: 'left', borderColor: actionType === 'reopen_matching' ? 'var(--accent-emerald)' : 'var(--border-subtle)', background: actionType === 'reopen_matching' ? 'var(--bg-elevated)' : 'transparent', padding: '10px' }}
                onClick={() => setActionType('reopen_matching')}
              >
                <div style={{ fontWeight: 600, fontSize: '12px', color: '#fff' }}>Re-open Matching</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Wave broadcast restart</div>
              </button>
            </div>
          </div>

          {/* Conditional Input based on Action */}
          {actionType === 'force_state' && (
            <div className="form-group">
              <label className="form-label">
                Permitted Destination State (Section 8 Allow-List)
              </label>
              {allowedTargets.length === 0 ? (
                <div style={{ color: 'var(--accent-amber)', fontSize: '12px' }}>
                  No further overrides permitted from terminal state '{currentStatus}'.
                </div>
              ) : (
                <select
                  className="form-select"
                  value={targetStatus}
                  onChange={(e) => setTargetStatus(e.target.value)}
                  id="select-target-status"
                >
                  {allowedTargets.map((st) => (
                    <option key={st} value={st}>
                      {st.replace(/_/g, ' ').toUpperCase()}
                    </option>
                  ))}
                </select>
              )}
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Enforced by allow-list. Arbitrary transitions are blocked. Forced completion will NOT inflate unconfirmed intake meals.
              </span>
            </div>
          )}

          {actionType === 'reassign_volunteer' && (
            <div className="form-group">
              <label className="form-label">Select Replacement Volunteer Courier</label>
              <select
                className="form-select"
                value={replacementVolunteerId}
                onChange={(e) => setReplacementVolunteerId(e.target.value)}
                id="select-replacement-volunteer"
              >
                {availableVolunteers.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.phone || 'Phone verified'}) &bull; Trust: {v.reliability_score || 95}%
                  </option>
                ))}
              </select>
            </div>
          )}

          {actionType === 'approve_self_dropoff' && (
            <div className="info-banner">
              <ShieldCheck size={18} color="var(--accent-emerald)" style={{ flexShrink: 0 }} />
              <div>
                <strong style={{ color: '#fff' }}>Section 10 Donor Self-Dropoff:</strong>
                <div>
                  Converts courier dispatch mode to donor self-dropoff. Verifies receiving NGO readiness and remaining rescue window. Full intake verification remains intact.
                </div>
              </div>
            </div>
          )}

          {/* Operational Reason Code */}
          <div className="form-group">
            <label className="form-label">Intervention Reason Code</label>
            <select
              className="form-select"
              value={reasonCode}
              onChange={(e) => setReasonCode(e.target.value)}
              id="select-reason-code"
            >
              <option value="no_volunteer_available">No Feasible Volunteer Available</option>
              <option value="ngo_unavailable">NGO Capacity / Availability Issue</option>
              <option value="pickup_delayed">Courier Delayed at Donor</option>
              <option value="delivery_delayed">Courier Delayed in Transit</option>
              <option value="food_condition_concern">Sensory / Temperature Discrepancy</option>
              <option value="quantity_mismatch">Quantity Mismatch at Handover</option>
              <option value="transport_failure">Vehicle Breakdown / Transit Impediment</option>
              <option value="donor_self_dropoff">Donor Self Drop-off Approved</option>
              <option value="reassign_volunteer">Volunteer Reassignment</option>
              <option value="reopen_matching">Re-open Proactive Matching Waves</option>
              <option value="emergency_broadcast">Critical Emergency Escalation</option>
              <option value="other">Other Operational Disruption</option>
            </select>
          </div>

          {/* Mandatory Reason/Remark (Section 8) */}
          <div className="form-group">
            <label className="form-label">
              Mandatory Operational Remark / Justification (Min 5 chars)
            </label>
            <textarea
              className="form-textarea"
              placeholder="Explain the operational justification for this intervention. This will be permanently recorded in the auditable history and notified to affected parties."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              id="input-intervention-notes"
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              type="button"
              className="btn-action-secondary"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-intervene"
              id="btn-submit-intervention"
              disabled={submitting}
            >
              {submitting ? 'Applying Intervention...' : 'Confirm & Log Intervention'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { 
  X, ShieldAlert, AlertTriangle, CheckCircle2, ArrowRight, 
  HelpCircle, FileText, Send 
} from 'lucide-react';
import { api } from '../api';

export default function AdminInterventionModal({ donation, onClose, onSuccess }) {
  const [reasonCode, setReasonCode] = useState('no_volunteer_available');
  const [actionType, setActionType] = useState('reassign_volunteer');
  const [targetStatus, setTargetStatus] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!donation) return null;

  // Detect specific failure category for contextual banner
  const detectIssueType = (d) => {
    const status = (d.status || '').toLowerCase();
    if (d.has_quantity_mismatch) return 'Quantity Mismatch';
    if (d.ai_visual_condition && ['CONCERNING', 'POOR', 'SPOILAGE_SUSPECTED'].includes(d.ai_visual_condition.toUpperCase())) return 'Food-Safety / Condition Issue';
    if (d.remaining_minutes <= 0) return 'Expired Rescue Window';
    if (status === 'pickup_failed') return 'Volunteer Cancellation / Pickup Failure';
    if (status === 'delivery_failed') return 'Delivery Failure / NGO Rejection';
    if (status === 'pending' && d.remaining_minutes <= 60) return 'Critical Unmatched Donation';
    if (d.feasibility_status && ['INFEASIBLE', 'AT_RISK', 'RESCUE_UNLIKELY'].includes(d.feasibility_status.toUpperCase())) return 'Feasibility Failure';
    if (d.is_emergency) return 'Critical Emergency Escalation';
    return 'Operational Attention Required';
  };

  const detectedIssue = detectIssueType(donation);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!notes.trim()) {
      setError('Please provide administrative audit notes for this intervention.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const payload = {
        donation_id: donation.id,
        reason_code: reasonCode,
        action_type: actionType,
        target_status: targetStatus || undefined,
        notes: notes.trim()
      };

      const res = await api.submitIntervention(payload);
      alert(`✅ Admin intervention recorded! Audit Log ID: #${res.audit_log_id || 'OK'}`);
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Intervention request failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 130, padding: '20px' }}>
      <div className="glass-panel fade-in" style={{ maxWidth: '620px', width: '100%', borderRadius: '24px', padding: '28px' }}>
        
        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '18px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <ShieldAlert color="#ef4444" size={20} />
              <h2 style={{ fontSize: '18px', fontWeight: '800', color: '#fff' }}>
                Admin Operations Intervention
              </h2>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Donation #{donation.id}: {donation.food_name} ({donation.quantity} {donation.quantity_unit})
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: '50%', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        {/* Issue Identification Banner */}
        <div style={{ background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.35)', borderRadius: '12px', padding: '12px 16px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={16} color="#ef4444" />
            <strong style={{ fontSize: '13px', color: '#f87171' }}>Detected Condition: {detectedIssue}</strong>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Every action executes through backend audit logging with strict state machine validation.
          </div>
        </div>

        {error && (
          <div style={{ background: 'rgba(244, 63, 94, 0.15)', border: '1px solid #f43f5e', borderRadius: '8px', padding: '10px 14px', marginBottom: '16px', color: '#f87171', fontSize: '13px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Reason Code */}
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '6px' }}>
              Intervention Reason Code *
            </label>
            <select 
              value={reasonCode} 
              onChange={e => setReasonCode(e.target.value)}
              className="glass-input"
              style={{ background: '#0f172a' }}
            >
              <option value="no_volunteer_available">No Volunteer Available / Capacity Limit</option>
              <option value="ngo_unavailable">NGO Unavailable / Capacity Full</option>
              <option value="pickup_delayed">Pickup Delayed / Approaching Expiry</option>
              <option value="delivery_delayed">Delivery Delayed / Transit Impediment</option>
              <option value="transport_failure">Transport Failure / Vehicle Issue</option>
              <option value="quantity_mismatch">Quantity Mismatch on Intake</option>
              <option value="food_condition_concern">Food Condition / Safety Concern</option>
              <option value="other">Other Operational Justification</option>
            </select>
          </div>

          {/* Action Type */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Action Type *
              </label>
              <select 
                value={actionType} 
                onChange={e => setActionType(e.target.value)}
                className="glass-input"
                style={{ background: '#0f172a' }}
              >
                <option value="reassign_volunteer">Reassign Volunteer / Dynamic Rematch</option>
                <option value="force_emergency_escalation">Force 2x Radius Emergency Escalation</option>
                <option value="override_status">State Machine Transition Override</option>
                <option value="cancel_with_audit">Cancel Rescue with Audit Trail</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Target Status (Optional Override)
              </label>
              <select 
                value={targetStatus} 
                onChange={e => setTargetStatus(e.target.value)}
                className="glass-input"
                style={{ background: '#0f172a' }}
              >
                <option value="">Keep Existing ({donation.status})</option>
                <option value="pending">pending (Re-enter Matching)</option>
                <option value="accepted">accepted (Awaiting Courier)</option>
                <option value="volunteer_assigned">volunteer_assigned</option>
                <option value="collected">collected (In Transit)</option>
                <option value="delivered">delivered (Intake Received)</option>
                <option value="completed">completed (Waste Averted)</option>
                <option value="cancelled">cancelled (Terminated)</option>
              </select>
            </div>
          </div>

          {/* Mandatory Notes */}
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '6px' }}>
              Operational Audit Notes *
            </label>
            <textarea
              rows={3}
              placeholder="Detail reasons, coordinator observations, and physical verification notes..."
              value={notes}
              onChange={e => setNotes(e.target.value)}
              className="glass-input"
              style={{ resize: 'vertical' }}
              required
            />
          </div>

          {/* Buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-primary" 
              disabled={submitting}
              style={{ background: '#ef4444', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Send size={15} />
              {submitting ? 'Submitting Intervention...' : 'Execute Authorized Intervention'}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}

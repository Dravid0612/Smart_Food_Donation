import React from 'react';
import {
  X,
  Clock,
  Sparkles,
  MapPin,
  Building2,
  Bike,
  ShieldCheck,
  AlertTriangle,
  Radio,
  CheckCircle2,
  Share2,
  Lock,
  Layers,
  FileText
} from 'lucide-react';

export default function RescueDetailModal({
  donationId,
  detail,
  loading,
  onClose,
  onOpenIntervention
}) {
  if (!donationId) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: '840px' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="modal-title">Rescue Lifecycle Chain</div>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--text-highlight)' }}>
              #{donationId}
            </span>
            {detail?.blocked_reason && (
              <span className="section-panel-badge badge-critical" style={{ fontSize: '11px' }}>
                Blocked: {detail.blocked_reason}
              </span>
            )}
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        {loading || !detail ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Retrieving complete rescue chain telemetry...
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Top Overview Strip */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', background: 'rgba(255,255,255,0.02)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Food & Quantity</div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#fff', marginTop: '2px' }}>
                  {detail.food_name}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {detail.quantity} {detail.quantity_unit} &bull; {detail.food_category}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Window & Urgency</div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: detail.remaining_minutes <= 30 ? 'var(--accent-red)' : 'var(--accent-amber)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Clock size={14} />
                  <span>{detail.remaining_minutes !== null ? `${detail.remaining_minutes} min` : 'Active'}</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {detail.rescue_urgency_level || 'FRESH'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Dispatch Wave (Section 11)</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--accent-cyan)', marginTop: '2px' }}>
                  {detail.wave_name || 'Wave 1 (NGO Direct)'}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Offers Dispatched: {detail.offers_count || 1}
                </div>
              </div>

              {/* Section 18: OTP Privacy — strictly state, NEVER plaintext */}
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Pickup OTP State</div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: detail.otp_state === 'VERIFIED' ? 'var(--accent-emerald)' : 'var(--accent-amber)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Lock size={13} />
                  <span>{detail.otp_state}</span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  Plaintext hidden per security policy
                </div>
              </div>
            </div>

            {/* AI Advisory & Storage Guidelines */}
            <div style={{ background: 'rgba(139, 92, 246, 0.05)', border: '1px solid rgba(139, 92, 246, 0.2)', borderRadius: 'var(--radius-md)', padding: '12px 16px', display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <Sparkles size={18} color="var(--accent-purple)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ fontSize: '12px', color: '#e2e8f0', lineHeight: '1.4' }}>
                <strong style={{ color: '#fff' }}>AI Quality & Storage Advisory: </strong>
                {detail.ai_advisory || 'Standard cooked food parameters verified.'} Storage: {detail.storage_method || 'Ambient / Insulated'}. Packaging: {detail.packaging_condition || 'Clean Food-grade Containers'}.
              </div>
            </div>

            {/* Section 22: WhatsApp / Public Claim Link Visibility */}
            {detail.has_claim_token && (
              <div style={{ background: 'rgba(6, 182, 212, 0.05)', border: '1px solid rgba(6, 182, 212, 0.2)', borderRadius: 'var(--radius-md)', padding: '10px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#cbd5e1' }}>
                  <Share2 size={16} color="var(--accent-cyan)" />
                  <span>Public claim link active for frictionless volunteer pickup. (Address masked pre-claim).</span>
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-highlight)' }}>
                  token: {detail.claim_token ? `${detail.claim_token.substring(0, 8)}...` : 'ACTIVE'}
                </span>
              </div>
            )}

            {/* Participants Chain Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
              {/* Donor */}
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>1. Donor Premise</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginTop: '4px' }}>
                  {detail.donor_name || 'Donor'}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {detail.donor_phone ? `Phone: ${detail.donor_phone}` : 'Contact recorded'}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  {detail.pickup_address}
                </div>
              </div>

              {/* Courier / Volunteer */}
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>2. Courier Assigned</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: detail.volunteer_name ? 'var(--accent-emerald)' : 'var(--accent-amber)', marginTop: '4px' }}>
                  {detail.volunteer_name || 'Awaiting Courier'}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {detail.volunteer_phone ? `Phone: ${detail.volunteer_phone}` : (detail.pickup_mode === 'self_pickup' ? 'NGO Direct Self-Pickup' : 'Dispatch in progress')}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Mode: {detail.pickup_mode} &bull; Feasibility: {detail.feasibility_status || 'FEASIBLE'}
                </div>
              </div>

              {/* Partner NGO */}
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>3. Partner NGO Facility</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: detail.ngo_name ? 'var(--text-highlight)' : 'var(--accent-amber)', marginTop: '4px' }}>
                  {detail.ngo_name || 'Awaiting Receiving NGO'}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Capacity: {detail.ngo_capacity_available ? 'Available' : 'Capacity Constrained'}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Intake Confirmed: {detail.received_quantity !== null ? `${detail.received_quantity} meals` : 'Pending Arrival'}
                </div>
              </div>
            </div>

            {/* 9-Stage Linear Stepper (Auditable History) */}
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
                9-Stage Auditable Rescue Stepper
              </div>

              <div className="lifecycle-stepper">
                {(detail.timeline || []).map((step, idx) => (
                  <div
                    key={idx}
                    className={`stepper-step ${step.is_completed ? 'completed' : ''} ${step.is_current ? 'current' : ''}`}
                  >
                    <div className="stepper-node">
                      {step.is_completed ? <CheckCircle2 size={12} /> : idx + 1}
                    </div>
                    <div className="stepper-label">{step.label}</div>
                    <div className="stepper-details">
                      {step.actor_name && <strong>{step.actor_name}: </strong>}
                      {step.details}
                      {step.timestamp && (
                        <span style={{ marginLeft: '6px', color: 'var(--text-muted)', fontSize: '11px' }}>
                          ({new Date(step.timestamp).toLocaleTimeString()})
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Bottom Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                {detail.issue_count > 0 ? `${detail.issue_count} active issue recorded on this rescue` : 'No active operational disputes'}
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button className="btn-action-secondary" onClick={onClose}>
                  Close
                </button>
                <button
                  className="btn-intervene"
                  onClick={() => {
                    onClose();
                    onOpenIntervention(detail);
                  }}
                >
                  Intervene On Rescue
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

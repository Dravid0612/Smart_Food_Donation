import React, { useState, useEffect } from 'react';
import { 
  X, AlertTriangle, CheckCircle2, Clock, MapPin, Truck, 
  Building2, User, Sparkles, AlertCircle, ArrowDown, ShieldAlert
} from 'lucide-react';
import { api } from '../api';

export default function LiveRescueFlowModal({ donationId, onClose, onIntervene }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (donationId) {
      loadRescueDetail();
    }
  }, [donationId]);

  const loadRescueDetail = async () => {
    setLoading(true);
    try {
      const data = await api.getRescueDetail(donationId);
      setDetail(data);
    } catch (err) {
      console.error('Failed to load rescue detail:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!donationId) return null;

  // The 8-stage operational flow as required by Phase 8 specification:
  // DONOR -> MATCHING -> NGO / VOLUNTEER -> PICKUP -> TRANSIT -> NGO RECEIVING -> DISTRIBUTION -> COMPLETED
  const getFlowStages = (d) => {
    if (!d) return [];
    const status = (d.status || '').toLowerCase();
    const isFailed = ['pickup_failed', 'delivery_failed', 'cancelled'].includes(status);
    const hasVolunteer = Boolean(d.volunteer_name || d.assigned_volunteer_id);
    const hasNgo = Boolean(d.ngo_name || d.assigned_ngo_id);

    return [
      {
        id: 'DONOR',
        label: 'Donor',
        sub: d.donor_name || 'Donor Kitchen',
        details: d.pickup_address,
        isCompleted: true,
        isCurrent: false,
        isFailed: false,
        icon: User
      },
      {
        id: 'MATCHING',
        label: 'Matching',
        sub: d.ai_visual_condition ? `AI: ${d.ai_visual_condition}` : 'Proactive Wave Engine',
        details: `${d.remaining_minutes || 0}m ERW Window`,
        isCompleted: hasNgo || ['accepted', 'volunteer_assigned', 'collected', 'delivered', 'completed'].includes(status),
        isCurrent: status === 'pending',
        isFailed: status === 'pending' && (d.remaining_minutes <= 0),
        icon: Sparkles
      },
      {
        id: 'NGO_VOLUNTEER',
        label: 'NGO / Volunteer',
        sub: d.ngo_name ? `NGO: ${d.ngo_name}` : 'Awaiting Acceptance',
        details: hasVolunteer ? `Courier: ${d.volunteer_name}` : (d.pickup_mode === 'self_pickup' ? 'Direct Self-Pickup' : 'Awaiting Courier'),
        isCompleted: ['accepted', 'volunteer_assigned', 'collected', 'delivered', 'completed'].includes(status),
        isCurrent: status === 'accepted' || status === 'volunteer_assigned',
        isFailed: isFailed && ['accepted', 'volunteer_assigned'].includes(status),
        icon: Building2
      },
      {
        id: 'PICKUP',
        label: 'Pickup',
        sub: status === 'collected' || ['delivered', 'completed'].includes(status) ? 'OTP Verified' : 'En Route / At Donor',
        details: d.collected_at ? new Date(d.collected_at).toLocaleTimeString() : 'Pending Handover',
        isCompleted: ['collected', 'delivered', 'completed'].includes(status),
        isCurrent: status === 'arrived_at_donor' || status === 'pickup_en_route',
        isFailed: status === 'pickup_failed',
        icon: CheckCircle2
      },
      {
        id: 'TRANSIT',
        label: 'Transit',
        sub: d.volunteer_name ? `${d.volunteer_name} in transit` : 'Transporting',
        details: d.eta_minutes ? `ETA: ~${Math.round(d.eta_minutes)} min` : 'Active Route',
        isCompleted: ['delivered', 'partially_distributed', 'completed'].includes(status),
        isCurrent: status === 'collected' || status === 'in_transit',
        isFailed: status === 'delivery_failed',
        icon: Truck
      },
      {
        id: 'NGO_RECEIVING',
        label: 'NGO Receiving',
        sub: d.ngo_name || 'Intake Center',
        details: d.has_quantity_mismatch 
          ? `⚠️ Mismatch: ${d.discrepancy_amount} ${d.quantity_unit} discrepancy` 
          : `${d.received_quantity || d.quantity} ${d.quantity_unit} received`,
        isCompleted: ['delivered', 'partially_distributed', 'completed'].includes(status),
        isCurrent: status === 'delivered',
        isFailed: false,
        icon: Building2
      },
      {
        id: 'DISTRIBUTION',
        label: 'Distribution',
        sub: 'Beneficiary Serving',
        details: d.distributed_quantity ? `${d.distributed_quantity} meals served` : 'Queued for meal service',
        isCompleted: status === 'completed',
        isCurrent: status === 'partially_distributed',
        isFailed: false,
        icon: CheckCircle2
      },
      {
        id: 'COMPLETED',
        label: 'Completed',
        sub: 'Rescue Averted Waste',
        details: 'Audit Log Closed',
        isCompleted: status === 'completed',
        isCurrent: false,
        isFailed: false,
        icon: CheckCircle2
      }
    ];
  };

  const stages = getFlowStages(detail);
  const isUrgentOrCritical = detail && (
    (detail.rescue_urgency_level || '').toUpperCase() === 'CRITICAL' || 
    (detail.rescue_urgency_level || '').toUpperCase() === 'URGENT' ||
    detail.remaining_minutes <= 45 ||
    ['pickup_failed', 'delivery_failed'].includes((detail.status || '').toLowerCase())
  );

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 120, padding: '20px' }}>
      <div className={`glass-panel fade-in ${isUrgentOrCritical ? 'rescue-card-critical' : ''}`} style={{ maxWidth: '840px', width: '100%', maxHeight: '90vh', overflowY: 'auto', borderRadius: '24px', padding: '28px' }}>
        
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <span className={`badge ${isUrgentOrCritical ? 'badge-critical' : 'badge-fresh'}`}>
                {detail?.rescue_urgency_level || 'RESCUE FLOW'}
              </span>
              <h2 style={{ fontSize: '20px', fontWeight: '800', color: '#fff' }}>
                Live Rescue Flow: {detail?.food_name || `Donation #${donationId}`}
              </h2>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              {detail ? `${detail.quantity} ${detail.quantity_unit} • ${detail.food_category} • Remaining: ${detail.remaining_minutes || 0}m` : 'Loading...'}
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: '50%', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        {/* Urgent Warning Banner if Endangered */}
        {isUrgentOrCritical && (
          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '12px', padding: '14px 18px', marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <ShieldAlert color="#ef4444" size={24} />
              <div>
                <strong style={{ color: '#f87171', fontSize: '14px' }}>OPERATIONAL INTERVENTION REQUIRED</strong>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Rescue is at high risk of expiry or transit failure. Take prompt action.
                </div>
              </div>
            </div>
            {onIntervene && (
              <button 
                onClick={() => { onClose(); onIntervene(detail); }}
                className="btn-primary" 
                style={{ background: '#ef4444', padding: '8px 16px', fontSize: '13px' }}
              >
                Intervene Now
              </button>
            )}
          </div>
        )}

        {/* 8-Stage Connected Stepper */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            Loading live rescue flow telemetry...
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
            {stages.map((st, idx) => {
              const Icon = st.icon;
              return (
                <div key={st.id} style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  {/* Step Indicator */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '36px' }}>
                    <div style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '50%',
                      background: st.isFailed 
                        ? '#ef4444' 
                        : (st.isCompleted ? '#10b981' : (st.isCurrent ? '#38bdf8' : 'rgba(255,255,255,0.08)')),
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: st.isCurrent ? '0 0 14px #38bdf8' : (st.isFailed ? '0 0 14px #ef4444' : 'none'),
                      color: st.isCompleted || st.isFailed || st.isCurrent ? '#fff' : 'var(--text-muted)'
                    }}>
                      <Icon size={18} />
                    </div>
                    {idx < stages.length - 1 && (
                      <div style={{ width: '2px', height: '24px', background: st.isCompleted ? '#10b981' : 'rgba(255,255,255,0.1)', margin: '4px 0' }}></div>
                    )}
                  </div>

                  {/* Step Card */}
                  <div style={{
                    flex: 1,
                    background: st.isCurrent ? 'rgba(56, 189, 248, 0.08)' : (st.isFailed ? 'rgba(239, 68, 68, 0.08)' : 'rgba(15, 23, 42, 0.6)'),
                    border: `1px solid ${st.isCurrent ? '#38bdf8' : (st.isFailed ? '#ef4444' : 'rgba(255,255,255,0.08)')}`,
                    borderRadius: '12px',
                    padding: '12px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: '700', fontSize: '14px', color: st.isCurrent ? '#38bdf8' : (st.isFailed ? '#ef4444' : '#fff') }}>
                          {st.label}
                        </span>
                        {st.isCurrent && (
                          <span style={{ background: '#38bdf8', color: '#090d16', fontSize: '10px', fontWeight: '800', padding: '2px 6px', borderRadius: '4px' }}>
                            ACTIVE NOW
                          </span>
                        )}
                        {st.isFailed && (
                          <span style={{ background: '#ef4444', color: '#fff', fontSize: '10px', fontWeight: '800', padding: '2px 6px', borderRadius: '4px' }}>
                            IMPEDED
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {st.sub}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', fontSize: '12px', color: 'var(--text-muted)' }}>
                      {st.details}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Footer Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '18px' }}>
          {onIntervene && (
            <button 
              className="btn-secondary"
              onClick={() => { onClose(); onIntervene(detail); }}
              style={{ color: '#f59e0b', borderColor: 'rgba(245, 158, 11, 0.4)' }}
            >
              Open Intervention Drawer
            </button>
          )}
          <button className="btn-primary" onClick={onClose}>
            Close Rescue Flow
          </button>
        </div>

      </div>
    </div>
  );
}

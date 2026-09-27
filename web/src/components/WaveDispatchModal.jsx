import React, { useState, useEffect } from 'react';
import { 
  X, Zap, Radio, Clock, AlertTriangle, CheckCircle2, 
  XCircle, RefreshCw, Send, ShieldAlert, Users, Building2 
} from 'lucide-react';
import { api } from '../api';

export default function WaveDispatchModal({ donationId, onClose }) {
  const [dispatchData, setDispatchData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    if (donationId) {
      loadDispatchStatus();
    }
  }, [donationId]);

  const loadDispatchStatus = async () => {
    setLoading(true);
    try {
      const data = await api.getDispatchStatus(donationId);
      setDispatchData(data);
    } catch (err) {
      console.error('Failed to load dispatch status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerNextWave = async () => {
    setTriggering(true);
    try {
      await api.triggerProactiveDispatch(donationId);
      await loadDispatchStatus();
    } catch (err) {
      alert('Dispatch trigger error: ' + err.message);
    } finally {
      setTriggering(false);
    }
  };

  if (!donationId) return null;

  const currentWave = dispatchData?.current_alert_wave || 1;
  const offers = dispatchData?.offers || [];

  // Calculate Wave Metrics
  const offersSent = offers.length;
  const acceptedCount = offers.filter(o => o.status === 'accepted').length;
  const declinedCount = offers.filter(o => o.status === 'rejected').length;
  const timeoutCount = offers.filter(o => o.status === 'timeout').length;
  const rematchedCount = (dispatchData?.alert_history || []).filter(h => h.reason?.includes('rematch') || h.action === 'rematch').length;
  const isEscalated = currentWave >= 3 || dispatchData?.status === 'emergency';

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 120, padding: '20px' }}>
      <div className="glass-panel fade-in" style={{ maxWidth: '860px', width: '100%', maxHeight: '90vh', overflowY: 'auto', borderRadius: '24px', padding: '28px' }}>
        
        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
              <span className="badge badge-usesoon">
                <Radio size={13} />
                PROACTIVE DISPATCH ENGINE
              </span>
              <h2 style={{ fontSize: '20px', fontWeight: '800', color: '#fff' }}>
                Wave Visualization: {dispatchData?.food_name || `Donation #${donationId}`}
              </h2>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              {dispatchData ? `${dispatchData.quantity} ${dispatchData.quantity_unit} • Urgency: ${dispatchData.urgency_level} • Remaining: ${dispatchData.remaining_minutes || 0}m` : 'Loading...'}
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: '50%', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        {/* 3-Wave Flow Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', marginBottom: '24px' }}>
          {/* WAVE 1 — NGO SELF-PICKUP */}
          <div className={`wave-step-card ${currentWave === 1 ? 'active' : (currentWave > 1 ? 'completed' : '')}`}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', fontWeight: '800', color: currentWave === 1 ? '#38bdf8' : (currentWave > 1 ? '#10b981' : 'var(--text-muted)') }}>
                WAVE 1
              </span>
              {currentWave === 1 ? (
                <span className="pulse-dot" style={{ background: '#38bdf8' }}></span>
              ) : (currentWave > 1 ? <CheckCircle2 size={16} color="#10b981" /> : null)}
            </div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: '#fff', marginBottom: '4px' }}>
              NGO Self-Pickup
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Direct advisory offers sent to matching partner NGOs within 5km radius.
            </div>
          </div>

          {/* WAVE 2 — VOLUNTEERS */}
          <div className={`wave-step-card ${currentWave === 2 ? 'active' : (currentWave > 2 ? 'completed' : '')}`}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', fontWeight: '800', color: currentWave === 2 ? '#38bdf8' : (currentWave > 2 ? '#10b981' : 'var(--text-muted)') }}>
                WAVE 2
              </span>
              {currentWave === 2 ? (
                <span className="pulse-dot" style={{ background: '#38bdf8' }}></span>
              ) : (currentWave > 2 ? <CheckCircle2 size={16} color="#10b981" /> : null)}
            </div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: '#fff', marginBottom: '4px' }}>
              Volunteers
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Feasible community couriers dispatched with vehicle capacity & route buffer gating.
            </div>
          </div>

          {/* WAVE 3 — EMERGENCY / ADMIN */}
          <div className={`wave-step-card ${currentWave === 3 ? 'active' : ''}`} style={currentWave === 3 ? { borderColor: '#ef4444', background: 'rgba(239, 68, 68, 0.15)' } : {}}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', fontWeight: '800', color: currentWave === 3 ? '#f87171' : 'var(--text-muted)' }}>
                WAVE 3
              </span>
              {currentWave === 3 && <span className="pulse-dot" style={{ background: '#ef4444' }}></span>}
            </div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: currentWave === 3 ? '#f87171' : '#fff', marginBottom: '4px' }}>
              Emergency / Admin
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              2x expanded radius broadcast and urgent operator intervention console alert.
            </div>
          </div>
        </div>

        {/* Dispatch Metrics Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '10px', marginBottom: '24px' }}>
          {[
            { label: 'Offers Sent', val: offersSent, color: '#38bdf8' },
            { label: 'Accepted', val: acceptedCount, color: '#10b981' },
            { label: 'Declined', val: declinedCount, color: '#f43f5e' },
            { label: 'Timeout', val: timeoutCount, color: '#f59e0b' },
            { label: 'Rematched', val: rematchedCount, color: '#a855f7' },
            { label: 'Escalated', val: isEscalated ? 'YES' : 'NO', color: isEscalated ? '#ef4444' : 'var(--text-muted)' },
          ].map(m => (
            <div key={m.label} style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '12px', textAlign: 'center' }}>
              <div style={{ fontSize: '18px', fontWeight: '800', color: m.color }}>{m.val}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{m.label}</div>
            </div>
          ))}
        </div>

        {/* Candidate Offers Table */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: '700', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={16} color="#38bdf8" />
            Candidate Offer Dispatches ({offers.length})
          </h3>

          {offers.length === 0 ? (
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '24px', borderRadius: '12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              No proactive offers generated yet for this rescue.
            </div>
          ) : (
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase' }}>
                    <th style={{ padding: '12px 16px' }}>Wave</th>
                    <th style={{ padding: '12px 16px' }}>Candidate Type</th>
                    <th style={{ padding: '12px 16px' }}>Candidate ID</th>
                    <th style={{ padding: '12px 16px' }}>Fit Score</th>
                    <th style={{ padding: '12px 16px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Response Time</th>
                  </tr>
                </thead>
                <tbody>
                  {offers.map(o => {
                    const st = (o.status || '').toLowerCase();
                    const statusColor = st === 'accepted' ? '#10b981' : (st === 'rejected' ? '#f43f5e' : (st === 'timeout' ? '#f59e0b' : '#38bdf8'));
                    return (
                      <tr key={o.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                        <td style={{ padding: '12px 16px', fontWeight: '700' }}>Wave {o.wave_number || 1}</td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            {o.candidate_type === 'ngo' ? <Building2 size={14} color="#10b981" /> : <Users size={14} color="#38bdf8" />}
                            {o.candidate_type?.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>#{o.candidate_id}</td>
                        <td style={{ padding: '12px 16px', fontWeight: '600' }}>{o.score?.toFixed(1) || 'N/A'}</td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{ 
                            background: `${statusColor}22`, 
                            color: statusColor, 
                            padding: '3px 8px', 
                            borderRadius: '6px', 
                            fontSize: '11px', 
                            fontWeight: '700',
                            border: `1px solid ${statusColor}44`
                          }}>
                            {o.status?.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>
                          {o.response_time_seconds ? `${o.response_time_seconds}s` : 'Pending'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '18px' }}>
          <button 
            className="btn-secondary" 
            onClick={handleTriggerNextWave}
            disabled={triggering}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <RefreshCw size={14} className={triggering ? 'animate-spin' : ''} />
            {triggering ? 'Advancing Wave...' : 'Force Advance Next Wave'}
          </button>

          <button className="btn-primary" onClick={onClose}>
            Close Visualization
          </button>
        </div>

      </div>
    </div>
  );
}

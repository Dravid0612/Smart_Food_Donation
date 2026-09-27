import React, { useState } from 'react';
import { 
  Flame, AlertOctagon, ShieldCheck, Truck, AlertTriangle, 
  HelpCircle, RefreshCw, Zap, Clock, ShieldAlert, ArrowRight
} from 'lucide-react';
import { api } from '../api';

export default function OperationalStatusBar({ summary, interventions, onTabSelect, onRefresh }) {
  const [runningWatchdog, setRunningWatchdog] = useState(false);

  const handleRunWatchdog = async () => {
    setRunningWatchdog(true);
    try {
      const res = await api.runUrgencyMonitorCycle();
      alert(`⚡ Watchdog Cycle Executed: ${res?.total_evaluated || 0} rescues evaluated, ${res?.dispatched_count || 0} proactive dispatches triggered!`);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert('Watchdog error: ' + err.message);
    } finally {
      setRunningWatchdog(false);
    }
  };

  const activeRescues = summary?.active_rescues || 0;
  const criticalRescues = summary?.critical_rescues || 0;
  const urgentRescues = summary?.urgent_rescues || 0;
  const foodAtRiskMeals = Math.round(summary?.food_at_risk_meals || 0);
  const inTransitCount = summary?.in_transit || 0;
  const issuesOpen = summary?.issues_open || (interventions?.total_interventions_needed || 0);
  const receivedToday = Math.round(summary?.received_today || 0);

  return (
    <div style={{ marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* Top Urgent Alert Strip if Critical Rescues Exist */}
      {(criticalRescues > 0 || issuesOpen > 0) && (
        <div style={{
          background: 'linear-gradient(90deg, rgba(239, 68, 68, 0.2) 0%, rgba(249, 115, 22, 0.15) 100%)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: '16px',
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 4px 20px rgba(239, 68, 68, 0.15)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'rgba(239, 68, 68, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <ShieldAlert color="#ef4444" size={22} className="pulse-urgent" />
            </div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: '800', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>OPERATIONAL ATTENTION:</span>
                <span style={{ color: '#f87171' }}>{criticalRescues} Critical Rescues</span>
                <span style={{ color: 'rgba(255,255,255,0.4)' }}>•</span>
                <span style={{ color: '#fbbf24' }}>{foodAtRiskMeals} Meals At Risk</span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                {issuesOpen} rescues require administrative intervention to avert expiration or transit stalls.
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button 
              className="btn-secondary"
              onClick={() => onTabSelect('ISSUES')}
              style={{ background: 'rgba(239, 68, 68, 0.2)', borderColor: 'rgba(239, 68, 68, 0.4)', color: '#f87171', fontSize: '13px', padding: '8px 14px' }}
            >
              Filter Issues Tab
              <ArrowRight size={14} />
            </button>
            <button 
              className="btn-primary"
              onClick={handleRunWatchdog}
              disabled={runningWatchdog}
              style={{ background: 'var(--gradient-emerald)', fontSize: '13px', padding: '8px 16px' }}
            >
              <Zap size={14} />
              {runningWatchdog ? 'Running Watchdog...' : 'Run Watchdog Cycle'}
            </button>
          </div>
        </div>
      )}

      {/* 6 Operator Question Panels */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px' }}>
        
        {/* 1. WHAT FOOD NEEDS HELP? */}
        <div className="glass-panel" style={{ padding: '18px', borderLeft: '4px solid #ef4444' }}>
          <div style={{ fontSize: '11px', fontWeight: '800', color: '#f87171', letterSpacing: '0.5px', marginBottom: '4px' }}>
            WHAT FOOD NEEDS HELP?
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>
            {criticalRescues + urgentRescues} <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-muted)' }}>urgent items</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            <strong style={{ color: '#ef4444' }}>{foodAtRiskMeals}</strong> meals at risk
          </div>
        </div>

        {/* 2. WHY IS IT URGENT? */}
        <div className="glass-panel" style={{ padding: '18px', borderLeft: '4px solid #f59e0b' }}>
          <div style={{ fontSize: '11px', fontWeight: '800', color: '#fbbf24', letterSpacing: '0.5px', marginBottom: '4px' }}>
            WHY IS IT URGENT?
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>
            {criticalRescues > 0 ? '< 30m' : '< 90m'} <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-muted)' }}>decay window</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Server ERW deadline active
          </div>
        </div>

        {/* 3. WHO HAS ACCEPTED? */}
        <div className="glass-panel" style={{ padding: '18px', borderLeft: '4px solid #10b981' }}>
          <div style={{ fontSize: '11px', fontWeight: '800', color: '#34d399', letterSpacing: '0.5px', marginBottom: '4px' }}>
            WHO HAS ACCEPTED?
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>
            {receivedToday} <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-muted)' }}>meals received</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Intake capacity verified
          </div>
        </div>

        {/* 4. WHO IS ON THE WAY? */}
        <div className="glass-panel" style={{ padding: '18px', borderLeft: '4px solid #38bdf8' }}>
          <div style={{ fontSize: '11px', fontWeight: '800', color: '#38bdf8', letterSpacing: '0.5px', marginBottom: '4px' }}>
            WHO IS ON THE WAY?
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>
            {inTransitCount} <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-muted)' }}>in transit</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Active volunteer delivery
          </div>
        </div>

        {/* 5. WHAT IS FAILING? */}
        <div className="glass-panel" style={{ padding: '18px', borderLeft: '4px solid #f43f5e' }}>
          <div style={{ fontSize: '11px', fontWeight: '800', color: '#fb7185', letterSpacing: '0.5px', marginBottom: '4px' }}>
            WHAT IS FAILING?
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: issuesOpen > 0 ? '#f43f5e' : '#10b981' }}>
            {issuesOpen} <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-muted)' }}>open issues</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            {issuesOpen === 0 ? 'No active delivery stalls' : 'Transit / intake impediments'}
          </div>
        </div>

        {/* 6. WHAT NEEDS INTERVENTION? */}
        <div className="glass-panel" style={{ padding: '18px', borderLeft: '4px solid #a855f7' }}>
          <div style={{ fontSize: '11px', fontWeight: '800', color: '#c084fc', letterSpacing: '0.5px', marginBottom: '4px' }}>
            WHAT NEEDS INTERVENTION?
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>
            {interventions?.total_interventions_needed || issuesOpen} <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-muted)' }}>flagged items</span>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Authorized admin action ready
          </div>
        </div>

      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { 
  Clock, MapPin, Building2, User, Truck, AlertTriangle, 
  CheckCircle2, Radio, Sparkles, Search, Filter, ShieldAlert,
  ArrowRight, ShieldCheck, Flame, Layers
} from 'lucide-react';

export default function RescueQueue({ 
  donations, 
  activeTab, 
  onTabChange, 
  onSelectFlow, 
  onSelectWave, 
  onSelectIntervene 
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');

  const tabs = [
    { key: 'ALL', label: 'All Rescues' },
    { key: 'EXPECTED', label: 'Expected' },
    { key: 'ARRIVING', label: 'Arriving' },
    { key: 'RECEIVED', label: 'Received' },
    { key: 'DISTRIBUTING', label: 'Distributing' },
    { key: 'COMPLETED', label: 'Completed' },
    { key: 'ISSUES', label: 'Issues & At-Risk' },
  ];

  // Tab Filtering
  let filtered = donations.filter(d => {
    const st = (d.status || '').toLowerCase();
    if (activeTab === 'EXPECTED') {
      return ['accepted', 'volunteer_assigned', 'en_route', 'pickup_en_route'].includes(st);
    }
    if (activeTab === 'ARRIVING') {
      return ['collected', 'in_transit', 'arrived_at_donor'].includes(st);
    }
    if (activeTab === 'RECEIVED') {
      return st === 'delivered';
    }
    if (activeTab === 'DISTRIBUTING') {
      return st === 'partially_distributed';
    }
    if (activeTab === 'COMPLETED') {
      return st === 'completed';
    }
    if (activeTab === 'ISSUES') {
      const urg = (d.rescue_urgency_level || d.urgency_level || '').toUpperCase();
      const rem = d.remaining_minutes;
      return ['pickup_failed', 'delivery_failed', 'cancelled'].includes(st) ||
        ['AT_RISK', 'RESCUE_UNLIKELY', 'INFEASIBLE'].includes((d.feasibility_status || '').toUpperCase()) ||
        urg === 'CRITICAL' ||
        d.is_emergency ||
        d.has_quantity_mismatch ||
        (rem !== undefined && rem <= 30);
    }
    return true;
  });

  // Search Filter
  if (searchTerm.trim()) {
    const q = searchTerm.toLowerCase();
    filtered = filtered.filter(d => 
      (d.food_name || '').toLowerCase().includes(q) ||
      (d.donor_name || '').toLowerCase().includes(q) ||
      (d.ngo_name || '').toLowerCase().includes(q) ||
      (d.volunteer_name || '').toLowerCase().includes(q) ||
      (d.pickup_address || '').toLowerCase().includes(q) ||
      String(d.id).includes(q)
    );
  }

  // Category Filter
  if (selectedCategory !== 'ALL') {
    filtered = filtered.filter(d => 
      (d.food_category || '').toLowerCase().includes(selectedCategory.toLowerCase())
    );
  }

  // Visual Urgency Prioritization Sorting:
  // 1. Critical rescues
  // 2. Urgent rescues
  // 3. Approaching rescues
  // 4. Normal / Fresh rescues
  // 5. Completed
  const getUrgencyWeight = (d) => {
    const st = (d.status || '').toLowerCase();
    if (['pickup_failed', 'delivery_failed'].includes(st)) return 0;
    const urg = (d.rescue_urgency_level || d.urgency_level || '').toUpperCase();
    const rem = d.remaining_minutes !== undefined ? d.remaining_minutes : 9999;
    if (urg === 'CRITICAL' || rem <= 30 || d.is_emergency) return 1;
    if (urg === 'URGENT' || rem <= 90) return 2;
    if (urg === 'APPROACHING' || rem <= 180) return 3;
    if (st === 'completed') return 10;
    return 4;
  };

  const prioritizedDonations = [...filtered].sort((a, b) => {
    const wA = getUrgencyWeight(a);
    const wB = getUrgencyWeight(b);
    if (wA !== wB) return wA - wB;
    return (a.remaining_minutes || 999) - (b.remaining_minutes || 999);
  });

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      
      {/* Top Header & Operational Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers color="#10b981" size={20} />
          <h2 style={{ fontSize: '18px', fontWeight: '800', color: '#fff' }}>
            Rescue Operations Queue
          </h2>
          <span style={{ background: 'rgba(255,255,255,0.08)', padding: '2px 8px', borderRadius: '12px', fontSize: '12px', fontWeight: '700', color: '#10b981' }}>
            {prioritizedDonations.length} Active
          </span>
        </div>

        {/* Tab Pills */}
        <div style={{ display: 'flex', background: 'rgba(15, 23, 42, 0.7)', padding: '4px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)', overflowX: 'auto' }}>
          {tabs.map(tab => {
            const isSel = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => onTabChange(tab.key)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '8px',
                  border: 'none',
                  background: isSel ? (tab.key === 'ISSUES' ? '#ef4444' : 'var(--gradient-emerald)') : 'transparent',
                  color: isSel ? '#fff' : 'var(--text-muted)',
                  fontSize: '12px',
                  fontWeight: isSel ? '700' : '500',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '240px', position: 'relative' }}>
          <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Search by food name, donor, NGO, volunteer, or ID..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="glass-input"
            style={{ paddingLeft: '38px', fontSize: '13px' }}
          />
        </div>

        <select
          value={selectedCategory}
          onChange={e => setSelectedCategory(e.target.value)}
          className="glass-input"
          style={{ width: '180px', background: '#0f172a', fontSize: '13px' }}
        >
          <option value="ALL">All Food Categories</option>
          <option value="Cooked Food">Cooked Food</option>
          <option value="Bakery">Bakery & Bread</option>
          <option value="Packaged">Packaged Goods</option>
          <option value="Produce">Fruits & Vegetables</option>
          <option value="Dairy">Dairy & Eggs</option>
        </select>
      </div>

      {/* Cards List */}
      {prioritizedDonations.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)', background: 'rgba(15, 23, 42, 0.4)', borderRadius: '16px' }}>
          <CheckCircle2 size={36} color="#10b981" style={{ margin: '0 auto 12px' }} />
          <div style={{ fontSize: '16px', fontWeight: '700', color: '#fff' }}>No Rescues in this View</div>
          <div style={{ fontSize: '13px', marginTop: '4px' }}>All food donations in this category are operating smoothly.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '16px' }}>
          {prioritizedDonations.map(d => {
            const urgency = (d.rescue_urgency_level || d.urgency_level || 'FRESH').toUpperCase();
            const isCritical = urgency === 'CRITICAL' || (d.remaining_minutes !== undefined && d.remaining_minutes <= 30) || ['pickup_failed', 'delivery_failed'].includes((d.status || '').toLowerCase());
            const isUrgent = urgency === 'URGENT' || (d.remaining_minutes !== undefined && d.remaining_minutes <= 90);
            const isApproaching = urgency === 'APPROACHING';

            let cardClass = 'rescue-card';
            let badgeClass = 'badge-fresh';
            if (isCritical) {
              cardClass += ' rescue-card-critical';
              badgeClass = 'badge-critical';
            } else if (isUrgent) {
              cardClass += ' rescue-card-urgent';
              badgeClass = 'badge-urgent';
            } else if (isApproaching) {
              cardClass += ' rescue-card-approaching';
              badgeClass = 'badge-approaching';
            }

            return (
              <div key={d.id} className={cardClass}>
                
                {/* Card Top Row */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '11px', fontWeight: '800', background: 'rgba(255,255,255,0.08)', padding: '2px 6px', borderRadius: '4px', color: 'var(--text-muted)' }}>
                      #{d.id}
                    </span>
                    <span style={{ fontSize: '11px', fontWeight: '700', color: '#10b981', textTransform: 'uppercase' }}>
                      {d.food_category || 'Cooked Food'}
                    </span>
                  </div>

                  <span className={`badge ${badgeClass}`}>
                    {isCritical ? 'CRITICAL RESCUE' : (isUrgent ? 'URGENT' : (isApproaching ? 'APPROACHING' : 'NORMAL'))}
                  </span>
                </div>

                {/* Food Name & Quantity */}
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div>
                    <h3 style={{ fontSize: '16px', fontWeight: '800', color: '#fff', marginBottom: '2px' }}>
                      {d.food_name}
                    </h3>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={12} />
                      Remaining: <strong style={{ color: isCritical ? '#f87171' : (isUrgent ? '#fb923c' : '#10b981') }}>
                        {d.remaining_minutes !== undefined ? `${d.remaining_minutes}m` : '120m'}
                      </strong>
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '16px', fontWeight: '800', color: '#10b981' }}>
                      {d.quantity} {d.quantity_unit || 'Meals'}
                    </div>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: '4px' }}>
                      Status: {d.status?.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Logistics Actor Chain */}
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', borderRadius: '10px', padding: '10px 12px', marginBottom: '14px', fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <User size={13} color="var(--text-muted)" />
                    <span style={{ color: 'var(--text-muted)' }}>Donor:</span>
                    <strong style={{ color: '#fff' }}>{d.donor_name || 'Donor Kitchen'}</strong>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Building2 size={13} color="#10b981" />
                    <span style={{ color: 'var(--text-muted)' }}>NGO:</span>
                    <strong style={{ color: d.ngo_name ? '#10b981' : '#f59e0b' }}>
                      {d.ngo_name || 'Awaiting Partner NGO Acceptance'}
                    </strong>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Truck size={13} color="#38bdf8" />
                    <span style={{ color: 'var(--text-muted)' }}>Volunteer:</span>
                    <strong style={{ color: d.volunteer_name ? '#38bdf8' : 'var(--text-muted)' }}>
                      {d.volunteer_name || (d.pickup_mode === 'self_pickup' ? 'NGO Self-Pickup' : 'Dispatching Courier')}
                    </strong>
                  </div>

                  {d.has_quantity_mismatch && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f87171', fontWeight: '700', marginTop: '2px' }}>
                      <AlertTriangle size={13} />
                      Mismatch: Expected {d.expected_quantity} vs Received {d.received_quantity}
                    </div>
                  )}
                </div>

                {/* Card Action Buttons */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                  <button 
                    className="btn-secondary"
                    onClick={() => onSelectFlow(d.id)}
                    style={{ fontSize: '11px', padding: '8px 4px', justifyContent: 'center' }}
                  >
                    Live Flow
                  </button>

                  <button 
                    className="btn-secondary"
                    onClick={() => onSelectWave(d.id)}
                    style={{ fontSize: '11px', padding: '8px 4px', justifyContent: 'center', color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.3)' }}
                  >
                    Wave Dispatch
                  </button>

                  <button 
                    className="btn-secondary"
                    onClick={() => onSelectIntervene(d)}
                    style={{ fontSize: '11px', padding: '8px 4px', justifyContent: 'center', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                  >
                    Intervene
                  </button>
                </div>

              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}

import React, { useState } from 'react';
import {
  Search,
  Filter,
  Eye,
  AlertTriangle,
  Clock,
  CheckCircle,
  Truck,
  Building,
  User,
  ShoppingBag
} from 'lucide-react';

export default function DonationsTab({
  donations = [],
  loading,
  onOpenRescueDetail,
  onOpenIntervention,
  onFilterChange,
  currentFilters,
  totalCount,
  currentLang = 'en',
  translations
}) {
  const t = translations[currentLang] || translations.en;
  const [searchQuery, setSearchQuery] = useState(currentFilters.search || '');

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    onFilterChange({ ...currentFilters, search: searchQuery, page: 1 });
  };

  const handleTabSelect = (tabName) => {
    onFilterChange({ ...currentFilters, tab: tabName, page: 1 });
  };

  const handleCategorySelect = (category) => {
    onFilterChange({ ...currentFilters, category, page: 1 });
  };

  const handleUrgencySelect = (urgency) => {
    onFilterChange({ ...currentFilters, urgency, page: 1 });
  };

  const tabs = [
    { id: 'ALL', label: 'All Rescues' },
    { id: 'LIVE_ACTIVE', label: 'Live Active' },
    { id: 'EXPECTED', label: 'Expected at NGO' },
    { id: 'ARRIVING', label: 'In Transit' },
    { id: 'RECEIVED', label: 'Received' },
    { id: 'COMPLETED', label: 'Completed' },
    { id: 'ISSUES', label: 'Issues & Blocked' },
  ];

  return (
    <div className="donations-container">
      {/* Tab Filter Subnav */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '18px', overflowX: 'auto', paddingBottom: '4px' }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabSelect(tab.id)}
            className={`btn-action-secondary ${currentFilters.tab === tab.id ? 'active' : ''}`}
            style={{
              padding: '8px 16px',
              fontSize: '12px',
              fontWeight: 600,
              background: currentFilters.tab === tab.id ? 'var(--bg-elevated)' : 'rgba(255,255,255,0.03)',
              borderColor: currentFilters.tab === tab.id ? 'var(--accent-emerald)' : 'var(--border-subtle)',
              color: currentFilters.tab === tab.id ? '#fff' : 'var(--text-secondary)'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Filter Bar */}
      <div className="table-filter-bar">
        <form onSubmit={handleSearchSubmit} className="search-input-wrap">
          <Search size={15} color="var(--text-muted)" />
          <input
            type="text"
            className="search-input"
            placeholder="Search by ID, Food, Donor, NGO, Courier..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </form>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Category Filter */}
          <select
            className="filter-select"
            value={currentFilters.category || ''}
            onChange={(e) => handleCategorySelect(e.target.value)}
          >
            <option value="">All Categories</option>
            <option value="Cooked Food">Cooked Food</option>
            <option value="Bakery">Bakery</option>
            <option value="Packaged Foods">Packaged Foods</option>
            <option value="Fresh Produce">Fresh Produce</option>
            <option value="Dairy">Dairy</option>
          </select>

          {/* Urgency Filter */}
          <select
            className="filter-select"
            value={currentFilters.urgency || ''}
            onChange={(e) => handleUrgencySelect(e.target.value)}
          >
            <option value="">All Urgencies</option>
            <option value="CRITICAL">Critical (&le; 30m)</option>
            <option value="URGENT">Urgent (&le; 90m)</option>
            <option value="APPROACHING">Approaching (&le; 180m)</option>
            <option value="FRESH">Fresh</option>
          </select>

          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Showing {donations.length} of {totalCount} rescues
          </span>
        </div>
      </div>

      {/* Filterable Table (Section 13) */}
      <div className="section-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="custom-table" aria-label="Rescue Operations Table">
          <thead>
            <tr>
              <th>ID & Food</th>
              <th>Quantity</th>
              <th>Urgency / Window</th>
              <th>Current State</th>
              <th>Assigned Actors</th>
              <th>Operational Notes</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                  Loading rescue telemetry...
                </td>
              </tr>
            ) : donations.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                  No donations matching current filters.
                </td>
              </tr>
            ) : (
              donations.map((d) => {
                const remMin = d.remaining_minutes;
                const isCritical = (d.rescue_urgency_level === 'CRITICAL' || (remMin !== null && remMin <= 30));
                const isUrgent = (d.rescue_urgency_level === 'URGENT' || (remMin !== null && remMin <= 90));
                const isSmallDonation = d.quantity <= 10; // Section 23 Small Donation Operation

                return (
                  <tr key={d.id}>
                    {/* Food & ID */}
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <div style={{ fontWeight: 600, color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>{d.food_name}</span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-highlight)' }}>
                            #{d.id}
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {d.food_category} &bull; {d.pickup_address ? d.pickup_address.split(',')[0] : 'Indiranagar'}
                        </div>
                      </div>
                    </td>

                    {/* Quantity & Small Donation Indicator (Section 23) */}
                    <td>
                      <div style={{ fontWeight: 600, color: '#e2e8f0' }}>
                        {d.quantity} {d.quantity_unit}
                      </div>
                      {isSmallDonation && (
                        <span style={{ fontSize: '10px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', padding: '1px 5px', borderRadius: '3px', fontWeight: 600 }}>
                          Self-pickup preferred
                        </span>
                      )}
                    </td>

                    {/* Urgency & Remaining Window */}
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                        <Clock size={13} color={isCritical ? 'var(--accent-red)' : isUrgent ? 'var(--accent-amber)' : 'var(--accent-emerald)'} />
                        <span style={{ fontWeight: 600, fontSize: '12px', color: isCritical ? 'var(--accent-red)' : isUrgent ? 'var(--accent-amber)' : '#e2e8f0' }}>
                          {remMin !== null ? `${remMin} min` : 'Active'}
                        </span>
                      </div>
                      <span className={`section-panel-badge ${isCritical ? 'badge-critical' : isUrgent ? 'badge-urgent' : 'badge-fresh'}`} style={{ marginTop: '2px', display: 'inline-block' }}>
                        {d.rescue_urgency_level || 'FRESH'}
                      </span>
                    </td>

                    {/* Current State */}
                    <td>
                      <span style={{ fontWeight: 600, textTransform: 'capitalize', color: '#fff' }}>
                        {d.status.replace(/_/g, ' ')}
                      </span>
                      {d.has_quantity_mismatch && (
                        <div style={{ fontSize: '10px', color: '#f87171', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '3px' }}>
                          <AlertTriangle size={10} />
                          <span>Mismatch: {d.discrepancy_amount} meals</span>
                        </div>
                      )}
                    </td>

                    {/* Assigned Actors (Donor, NGO, Volunteer) */}
                    <td>
                      <div style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <div style={{ color: '#cbd5e1' }}>
                          <strong>D:</strong> {d.donor_name || 'Donor'}
                        </div>
                        <div style={{ color: d.ngo_name ? 'var(--text-highlight)' : 'var(--text-muted)' }}>
                          <strong>NGO:</strong> {d.ngo_name || 'Awaiting Partner'}
                        </div>
                        <div style={{ color: d.volunteer_name ? 'var(--accent-emerald)' : 'var(--text-muted)' }}>
                          <strong>Courier:</strong> {d.volunteer_name || 'Awaiting Dispatch'}
                        </div>
                      </div>
                    </td>

                    {/* Operational Notes / Issues */}
                    <td>
                      {d.discrepancy_reason ? (
                        <div style={{ fontSize: '11px', color: '#fca5a5' }}>
                          {d.discrepancy_reason}
                        </div>
                      ) : d.issue_count > 0 ? (
                        <span style={{ fontSize: '11px', color: '#f87171', fontWeight: 600 }}>
                          {d.issue_count} issue reported
                        </span>
                      ) : (
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          Normal progress
                        </span>
                      )}
                    </td>

                    {/* Actions: Inspect & Intervene */}
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                        <button
                          className="btn-action-secondary"
                          style={{ padding: '5px 9px', display: 'flex', alignItems: 'center', gap: '4px' }}
                          onClick={() => onOpenRescueDetail(d.id)}
                          title="View 9-stage complete lifecycle"
                        >
                          <Eye size={13} />
                          <span>Inspect</span>
                        </button>
                        <button
                          className="btn-intervene"
                          style={{ padding: '5px 9px', fontSize: '11px' }}
                          onClick={() => onOpenIntervention({ donation_id: d.id, food_name: d.food_name, status: d.status, quantity: d.quantity, quantity_unit: d.quantity_unit })}
                          title="Administrative intervention"
                        >
                          Intervene
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

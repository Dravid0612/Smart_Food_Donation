import React from 'react';
import {
  LayoutDashboard,
  Package,
  Users,
  Building2,
  UserCheck,
  AlertTriangle,
  Globe,
  LogOut,
  ShieldCheck
} from 'lucide-react';

export default function Navigation({
  activeTab,
  setActiveTab,
  currentUser,
  onLogout,
  criticalCount = 0,
  currentLang = 'en',
  onLangChange,
  translations
}) {
  const t = translations[currentLang] || translations.en;

  const tabs = [
    { id: 'overview', label: t.tabOverview, icon: LayoutDashboard, badge: criticalCount > 0 ? criticalCount : null },
    { id: 'donations', label: t.tabDonations, icon: Package },
    { id: 'users', label: t.tabUsers, icon: Users },
    { id: 'verify-ngos', label: t.tabVerifyNgos, icon: Building2 },
    { id: 'profile', label: t.tabProfile, icon: UserCheck },
  ];

  return (
    <header className="control-header">
      <div className="brand-section">
        <div className="brand-logo">
          <ShieldCheck size={22} color="#fff" />
        </div>
        <div className="brand-title-wrap">
          <div className="brand-title">
            Smart Food Rescue
            <span className="brand-badge">Admin Ops</span>
          </div>
          <div className="brand-subtitle">Operational Control & Exception Management Center</div>
        </div>
      </div>

      {/* Exactly 5 Navigation Tabs (Section 2) */}
      <nav className="nav-tabs" aria-label="Admin Navigation">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              className={`nav-tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              id={`tab-btn-${tab.id}`}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
              {tab.badge && (
                <span className="nav-tab-badge" title="Rescues requiring immediate intervention">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Header Actions: Live Telemetry & Profile */}
      <div className="header-actions">
        <div className="live-indicator" title="Connected to proactive dispatch and exception telemetry">
          <div className="pulse-dot" />
          <span>Live Ops</span>
        </div>

        {/* Section 30: Trilingual Language Switcher (EN, TA, HI) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Globe size={15} color="var(--text-muted)" />
          <select
            className="filter-select"
            style={{ padding: '4px 8px', fontSize: '11px' }}
            value={currentLang}
            onChange={(e) => onLangChange(e.target.value)}
          >
            <option value="en">English</option>
            <option value="ta">தமிழ் (Tamil)</option>
            <option value="hi">हिंदी (Hindi)</option>
          </select>
        </div>

        <div className="user-profile-badge">
          <div className="user-avatar">
            {currentUser?.name ? currentUser.name.charAt(0).toUpperCase() : 'A'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>
              {currentUser?.name || 'Operations Lead'}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Admin Role</span>
          </div>
        </div>

        <button
          className="btn-action-secondary"
          style={{ padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
          onClick={onLogout}
          title="Sign out of control center"
        >
          <LogOut size={14} />
          <span style={{ fontSize: '11px' }}>Sign Out</span>
        </button>
      </div>
    </header>
  );
}

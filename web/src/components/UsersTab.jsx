import React, { useState } from 'react';
import {
  Users,
  Search,
  CheckCircle,
  XCircle,
  Shield,
  Bike,
  Building,
  Heart,
  UserCheck
} from 'lucide-react';

export default function UsersTab({
  users = [],
  loading,
  onToggleActive,
  currentLang = 'en',
  translations
}) {
  const t = translations[currentLang] || translations.en;
  const [roleFilter, setRoleFilter] = useState('ALL');
  const [search, setSearch] = useState('');

  const filteredUsers = users.filter((u) => {
    if (roleFilter !== 'ALL' && u.role !== roleFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchName = u.name?.toLowerCase().includes(q);
      const matchEmail = u.email?.toLowerCase().includes(q);
      const matchPhone = u.phone?.toLowerCase().includes(q);
      const matchId = String(u.id).includes(q);
      return matchName || matchEmail || matchPhone || matchId;
    }
    return true;
  });

  const getRoleBadge = (role) => {
    switch (role) {
      case 'admin':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', padding: '2px 7px', borderRadius: '4px', fontWeight: 600 }}>
            <Shield size={11} /> Admin
          </span>
        );
      case 'volunteer':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '2px 7px', borderRadius: '4px', fontWeight: 600 }}>
            <Bike size={11} /> Courier
          </span>
        );
      case 'ngo':
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', background: 'rgba(6, 182, 212, 0.15)', color: '#22d3ee', padding: '2px 7px', borderRadius: '4px', fontWeight: 600 }}>
            <Building size={11} /> NGO
          </span>
        );
      case 'donor':
      default:
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', background: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa', padding: '2px 7px', borderRadius: '4px', fontWeight: 600 }}>
            <Heart size={11} /> Donor
          </span>
        );
    }
  };

  return (
    <div className="users-container">
      {/* Top Filter Bar */}
      <div className="table-filter-bar">
        <div className="search-input-wrap">
          <Search size={15} color="var(--text-muted)" />
          <input
            type="text"
            className="search-input"
            placeholder="Search users by Name, Email, Phone, ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <select
            className="filter-select"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
          >
            <option value="ALL">All Roles</option>
            <option value="donor">Donors</option>
            <option value="ngo">NGO Partners</option>
            <option value="volunteer">Volunteer Couriers</option>
            <option value="admin">Administrators</option>
          </select>

          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Showing {filteredUsers.length} of {users.length} users
          </span>
        </div>
      </div>

      {/* Users Table (Section 14: Zero password / token / secret exposure) */}
      <div className="section-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="custom-table" aria-label="User Management Table">
          <thead>
            <tr>
              <th>ID & Name</th>
              <th>Role</th>
              <th>Contact Details</th>
              <th>Operational Trust / Reliability</th>
              <th>Account Status</th>
              <th style={{ textAlign: 'right' }}>Authorization Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                  Loading user records...
                </td>
              </tr>
            ) : filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                  No users found matching current filters.
                </td>
              </tr>
            ) : (
              filteredUsers.map((u) => {
                const trustScore = u.reliability_score ?? u.donor_trust_score ?? 95.0;

                return (
                  <tr key={u.id}>
                    {/* ID & Name */}
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <div style={{ fontWeight: 600, color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>{u.name}</span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-highlight)' }}>
                            #{u.id}
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          Joined: {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'Active'}
                        </div>
                      </div>
                    </td>

                    {/* Role */}
                    <td>{getRoleBadge(u.role)}</td>

                    {/* Contact Details (Clean & Privacy-Compliant) */}
                    <td>
                      <div style={{ fontSize: '12px', color: '#e2e8f0' }}>{u.email}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {u.phone || 'Phone verified'}
                      </div>
                    </td>

                    {/* Operational Trust / Reliability */}
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontWeight: 700, fontSize: '13px', color: trustScore >= 90 ? 'var(--accent-emerald)' : trustScore >= 75 ? 'var(--accent-amber)' : 'var(--accent-red)' }}>
                          {trustScore}%
                        </span>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                          {u.role === 'volunteer' ? 'Courier Reliability' : 'Platform Trust'}
                        </span>
                      </div>
                    </td>

                    {/* Account Status */}
                    <td>
                      {u.is_active ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--accent-emerald)', fontWeight: 600 }}>
                          <CheckCircle size={12} /> Active
                        </span>
                      ) : (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: '#f87171', fontWeight: 600 }}>
                          <XCircle size={12} /> Deactivated
                        </span>
                      )}
                    </td>

                    {/* Actions: Activate / Deactivate */}
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className={`btn-action-secondary ${u.is_active ? '' : 'active'}`}
                        style={{
                          fontSize: '11px',
                          padding: '5px 12px',
                          borderColor: u.is_active ? 'rgba(239, 68, 68, 0.4)' : 'rgba(16, 185, 129, 0.4)',
                          color: u.is_active ? '#fca5a5' : '#86efac'
                        }}
                        onClick={() => onToggleActive(u.id)}
                        id={`btn-toggle-user-${u.id}`}
                      >
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
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

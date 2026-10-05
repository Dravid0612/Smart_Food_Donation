import React, { useState, useEffect, useCallback } from 'react';
import Navigation from './components/Navigation';
import OverviewTab from './components/OverviewTab';
import DonationsTab from './components/DonationsTab';
import UsersTab from './components/UsersTab';
import VerifyNgosTab from './components/VerifyNgosTab';
import ProfileTab from './components/ProfileTab';
import RescueDetailModal from './components/RescueDetailModal';
import InterventionModal from './components/InterventionModal';
import AuthBlocked from './components/AuthBlocked';
import { api, getAuthToken, setAuthToken, setStoredUser, clearAuth } from './api';

// Trilingual Localization Dictionary (Section 30)
const TRANSLATIONS = {
  en: {
    tabOverview: 'Overview',
    tabDonations: 'Donations',
    tabUsers: 'Users',
    tabVerifyNgos: 'Verify NGOs',
    tabProfile: 'Profile',
    metricActive: 'Active Rescues',
    metricUrgent: 'Urgent Rescues',
    metricCritical: 'Critical Rescues',
    metricCompletedToday: 'Completed Rescues',
    interventionQueueTitle: 'Intervention Queue',
    btnIntervene: 'INTERVENE',
    btnInspect: 'Inspect Chain',
  },
  ta: {
    tabOverview: 'கண்ணோட்டம்',
    tabDonations: 'நன்கொடைகள்',
    tabUsers: 'பயனர்கள்',
    tabVerifyNgos: 'NGO சரிபார்ப்பு',
    tabProfile: 'சுயவிவரம்',
    metricActive: 'செயலில் உள்ளவை',
    metricUrgent: 'அவசர மீட்புகள்',
    metricCritical: 'மிகவும் ஆபத்தானவை',
    metricCompletedToday: 'முடிந்த மீட்புகள்',
    interventionQueueTitle: 'தலையீட்டு வரிசை',
    btnIntervene: 'தலையிடு',
    btnInspect: 'ஆய்வு செய்',
  },
  hi: {
    tabOverview: 'अवलोकन',
    tabDonations: 'दान सूची',
    tabUsers: 'उपयोगकर्ता',
    tabVerifyNgos: 'NGO सत्यापन',
    tabProfile: 'प्रोफ़ाइल',
    metricActive: 'सक्रिय बचाव',
    metricUrgent: 'अति आवश्यक',
    metricCritical: 'गंभीर स्थिति',
    metricCompletedToday: 'पूर्ण बचाव',
    interventionQueueTitle: 'हस्तक्षेप कतार',
    btnIntervene: 'हस्तक्षेप करें',
    btnInspect: 'जांच करें',
  },
};

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [loginError, setLoginError] = useState('');

  // Exactly 5 Navigation Tabs (Section 2)
  const [activeTab, setActiveTab] = useState('overview'); // overview, donations, users, verify-ngos, profile
  const [currentLang, setCurrentLang] = useState('en');

  // Operational State
  const [stats, setStats] = useState(null);
  const [summary, setSummary] = useState(null);
  const [interventions, setInterventions] = useState([]);
  const [ngoCapacities, setNgoCapacities] = useState([]);
  const [pilotMetrics, setPilotMetrics] = useState(null);
  const [donorInsights, setDonorInsights] = useState(null);
  const [monthlyReport, setMonthlyReport] = useState(null);
  const [health, setHealth] = useState(null);

  // Donations Table State
  const [donations, setDonations] = useState([]);
  const [donationsTotal, setDonationsTotal] = useState(0);
  const [donationsLoading, setDonationsLoading] = useState(false);
  const [donationFilters, setDonationFilters] = useState({
    tab: 'ALL',
    search: '',
    category: '',
    urgency: '',
    page: 1,
    page_size: 25,
  });

  // Users State
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);

  // NGOs State
  const [ngos, setNgos] = useState([]);
  const [ngosLoading, setNgosLoading] = useState(false);

  // Disputes & Audit Logs
  const [disputes, setDisputes] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);

  // Modals & Drawers
  const [selectedDonationId, setSelectedDonationId] = useState(null);
  const [rescueDetail, setRescueDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [activeInterventionDonation, setActiveInterventionDonation] = useState(null);
  const [submittingIntervention, setSubmittingIntervention] = useState(false);

  // 1. Initial Authentication Check (Section 3: Strict RBAC)
  const verifyAuth = useCallback(async () => {
    setAuthLoading(true);
    try {
      const user = await api.getCurrentUser();
      if (user && user.role === 'admin') {
        setCurrentUser(user);
        setStoredUser(user);
      } else {
        // Non-admin blocked per Section 3
        setCurrentUser(null);
        clearAuth();
      }
    } catch (_) {
      setCurrentUser(null);
    } finally {
      setAuthLoading(false);
    }
  }, []);

  useEffect(() => {
    verifyAuth();
  }, [verifyAuth]);

  // 2. Fetch Live Telemetry when Authenticated
  const fetchOverviewData = useCallback(async () => {
    if (!currentUser || currentUser.role !== 'admin') return;

    try {
      const [sumRes, intRes, capRes, pilotRes, repRes, donRes, hRes] = await Promise.allSettled([
        api.getReceivingSummary(),
        api.getInterventions(),
        api.getNgoCapacities(),
        api.getPilotMetrics(),
        api.getMonthlyReport(),
        api.getRepeatDonorInsights(),
        api.getHealth(),
      ]);

      if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
      if (intRes.status === 'fulfilled') setInterventions(intRes.value?.items || []);
      if (capRes.status === 'fulfilled') setNgoCapacities(capRes.value || []);
      if (pilotRes.status === 'fulfilled') setPilotMetrics(pilotRes.value);
      if (repRes.status === 'fulfilled') setMonthlyReport(repRes.value);
      if (donRes.status === 'fulfilled') setDonorInsights(donRes.value);
      if (hRes.status === 'fulfilled') setHealth(hRes.value);
    } catch (err) {
      console.error('[Telemetry] Fetch error:', err);
    }
  }, [currentUser]);

  const fetchDonationsData = useCallback(async () => {
    if (!currentUser || currentUser.role !== 'admin') return;
    setDonationsLoading(true);
    try {
      const data = await api.getDonations(donationFilters);
      setDonations(data.items || []);
      setDonationsTotal(data.total || 0);
    } catch (err) {
      console.error('[Donations] Fetch error:', err);
    } finally {
      setDonationsLoading(false);
    }
  }, [currentUser, donationFilters]);

  const fetchUsersData = useCallback(async () => {
    if (!currentUser || currentUser.role !== 'admin') return;
    setUsersLoading(true);
    try {
      const data = await api.getUsers();
      setUsers(data || []);
    } catch (err) {
      console.error('[Users] Fetch error:', err);
    } finally {
      setUsersLoading(false);
    }
  }, [currentUser]);

  const fetchNgosData = useCallback(async () => {
    if (!currentUser || currentUser.role !== 'admin') return;
    setNgosLoading(true);
    try {
      const data = await api.getNgos();
      setNgos(data || []);
    } catch (err) {
      console.error('[NGOs] Fetch error:', err);
    } finally {
      setNgosLoading(false);
    }
  }, [currentUser]);

  const fetchDisputesAndAudit = useCallback(async () => {
    if (!currentUser || currentUser.role !== 'admin') return;
    try {
      const [disp, audit] = await Promise.allSettled([
        api.getDisputes(),
        api.getAuditLogs(50),
      ]);
      if (disp.status === 'fulfilled') setDisputes(disp.value || []);
      if (audit.status === 'fulfilled') setAuditLogs(audit.value || []);
    } catch (err) {
      console.error('[Disputes/Audit] Fetch error:', err);
    }
  }, [currentUser]);

  // Initial and Periodic Telemetry Polling (Section 20: Near-real-time updates)
  useEffect(() => {
    if (!currentUser || currentUser.role !== 'admin') return;

    fetchOverviewData();
    fetchDonationsData();
    fetchUsersData();
    fetchNgosData();
    fetchDisputesAndAudit();

    // 15-second background refresh for live exception triage
    const timer = setInterval(() => {
      fetchOverviewData();
      fetchDonationsData();
    }, 15000);

    return () => clearInterval(timer);
  }, [currentUser, fetchOverviewData, fetchDonationsData, fetchUsersData, fetchNgosData, fetchDisputesAndAudit]);

  // 3. Admin Authentication Login Handler (Section 3)
  const handleAdminLogin = async (email, password) => {
    setLoginError('');
    try {
      const tokenRes = await api.login(email, password);
      if (tokenRes && tokenRes.access_token) {
        setAuthToken(tokenRes.access_token);
        const me = await api.getCurrentUser();
        if (me && me.role === 'admin') {
          setCurrentUser(me);
          setStoredUser(me);
        } else {
          clearAuth();
          setLoginError(`Role '${me?.role}' is not authorized to access the Admin Control Center.`);
        }
      }
    } catch (err) {
      setLoginError(err.message || 'Login failed. Check your credentials.');
    }
  };

  const handleLogout = () => {
    clearAuth();
    setCurrentUser(null);
  };

  // 4. Modal Handlers
  const handleOpenRescueDetail = async (id) => {
    setSelectedDonationId(id);
    setDetailLoading(true);
    try {
      const data = await api.getRescueDetail(id);
      setRescueDetail(data);
    } catch (err) {
      console.error('[Detail] Failed to load rescue detail:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCloseRescueDetail = () => {
    setSelectedDonationId(null);
    setRescueDetail(null);
  };

  const handleOpenIntervention = (donation) => {
    setActiveInterventionDonation(donation);
  };

  const handleCloseIntervention = () => {
    setActiveInterventionDonation(null);
  };

  const handleSubmitIntervention = async (payload) => {
    setSubmittingIntervention(true);
    try {
      await api.submitIntervention(payload);
      handleCloseIntervention();
      // Refresh telemetry and records immediately
      fetchOverviewData();
      fetchDonationsData();
      fetchDisputesAndAudit();
    } catch (err) {
      alert(`Intervention Error: ${err.message}`);
    } finally {
      setSubmittingIntervention(false);
    }
  };

  const handleToggleUserActive = async (userId) => {
    try {
      await api.toggleUserActive(userId);
      fetchUsersData();
    } catch (err) {
      alert(`User update failed: ${err.message}`);
    }
  };

  const handleVerifyNgo = async (ngoId) => {
    try {
      await api.verifyNgo(ngoId);
      fetchNgosData();
      fetchOverviewData();
    } catch (err) {
      alert(`Verification failed: ${err.message}`);
    }
  };

  const handleRejectNgo = async (ngoId, reason) => {
    try {
      await api.rejectNgo(ngoId, reason);
      fetchNgosData();
      fetchOverviewData();
    } catch (err) {
      alert(`Rejection failed: ${err.message}`);
    }
  };

  const handleResolveDispute = async (disputeId, payload) => {
    try {
      await api.resolveDispute(disputeId, payload);
      fetchDisputesAndAudit();
    } catch (err) {
      alert(`Dispute resolution failed: ${err.message}`);
    }
  };

  // Role Gate: Only Admin users allowed (Section 3)
  if (authLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)', color: '#fff' }}>
        Verifying administrator authorization...
      </div>
    );
  }

  if (!currentUser || currentUser.role !== 'admin') {
    return (
      <AuthBlocked
        onAdminLogin={handleAdminLogin}
        loginError={loginError}
        loading={authLoading}
      />
    );
  }

  return (
    <div className="app-container">
      {/* 5-Tab Navigation Bar (Section 2) */}
      <Navigation
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentUser={currentUser}
        onLogout={handleLogout}
        criticalCount={interventions.length}
        currentLang={currentLang}
        onLangChange={setCurrentLang}
        translations={TRANSLATIONS}
      />

      {/* Main Tab Content Surface */}
      <main className="main-surface">
        {/* Tab 1: Overview (Exceptions First) */}
        {activeTab === 'overview' && (
          <OverviewTab
            stats={stats}
            summary={summary}
            interventions={interventions}
            ngoCapacities={ngoCapacities}
            pilotMetrics={pilotMetrics}
            donorInsights={donorInsights}
            monthlyReport={monthlyReport}
            onOpenIntervention={handleOpenIntervention}
            onOpenRescueDetail={handleOpenRescueDetail}
            currentLang={currentLang}
            translations={TRANSLATIONS}
          />
        )}

        {/* Tab 2: Donations (Filterable Table) */}
        {activeTab === 'donations' && (
          <DonationsTab
            donations={donations}
            loading={donationsLoading}
            totalCount={donationsTotal}
            onOpenRescueDetail={handleOpenRescueDetail}
            onOpenIntervention={handleOpenIntervention}
            onFilterChange={setDonationFilters}
            currentFilters={donationFilters}
            currentLang={currentLang}
            translations={TRANSLATIONS}
          />
        )}

        {/* Tab 3: Users (Authorized User Management) */}
        {activeTab === 'users' && (
          <UsersTab
            users={users}
            loading={usersLoading}
            onToggleActive={handleToggleUserActive}
            currentLang={currentLang}
            translations={TRANSLATIONS}
          />
        )}

        {/* Tab 4: Verify NGOs (Core Admin Duty) */}
        {activeTab === 'verify-ngos' && (
          <VerifyNgosTab
            ngos={ngos}
            loading={ngosLoading}
            onVerifyNgo={handleVerifyNgo}
            onRejectNgo={handleRejectNgo}
            currentLang={currentLang}
            translations={TRANSLATIONS}
          />
        )}

        {/* Tab 5: Profile (Coordinator Details, Disputes, Audit History) */}
        {activeTab === 'profile' && (
          <ProfileTab
            currentUser={currentUser}
            onLogout={handleLogout}
            auditLogs={auditLogs}
            disputes={disputes}
            onResolveDispute={handleResolveDispute}
            health={health}
            currentLang={currentLang}
            onLangChange={setCurrentLang}
            translations={TRANSLATIONS}
          />
        )}
      </main>

      {/* Rescue Detail Modal / Drawer (Section 6) */}
      {selectedDonationId && (
        <RescueDetailModal
          donationId={selectedDonationId}
          detail={rescueDetail}
          loading={detailLoading}
          onClose={handleCloseRescueDetail}
          onOpenIntervention={handleOpenIntervention}
        />
      )}

      {/* Intervention Modal (Section 7, 8, 9, 10) */}
      {activeInterventionDonation && (
        <InterventionModal
          donation={activeInterventionDonation}
          onClose={handleCloseIntervention}
          onSubmitIntervention={handleSubmitIntervention}
          allUsers={users}
          submitting={submittingIntervention}
        />
      )}
    </div>
  );
}

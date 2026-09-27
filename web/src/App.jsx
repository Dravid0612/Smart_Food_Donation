import React, { useState, useEffect } from 'react';
import { 
  HeartHandshake, ShieldCheck, Truck, BarChart3, Leaf, Plus, Sparkles, 
  MapPin, Clock, Award, CheckCircle2, ArrowRight, Zap, RefreshCw, AlertTriangle, 
  Layers, Droplets, Utensils, QrCode, Lock, AlertOctagon, Check, X, ShieldAlert,
  Flame, Sliders, Calendar, Radio
} from 'lucide-react';
import { api } from './api';
import OperationalStatusBar from './components/OperationalStatusBar';
import RescueQueue from './components/RescueQueue';
import LiveRescueFlowModal from './components/LiveRescueFlowModal';
import WaveDispatchModal from './components/WaveDispatchModal';
import AdminInterventionModal from './components/AdminInterventionModal';

export default function App() {
  const [role, setRole] = useState('donor'); // donor, ngo, volunteer, admin
  const [donations, setDonations] = useState([]);
  const [stats, setStats] = useState(null);
  const [heatmap, setHeatmap] = useState(null);
  const [batchResults, setBatchResults] = useState(null);
  const [batchedRoutes, setBatchedRoutes] = useState([]);
  const [selectedCarbonDonation, setSelectedCarbonDonation] = useState(null);
  const [carbonImpactData, setCarbonImpactData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [serverOnline, setServerOnline] = useState(true);

  // AI Vision Studio State
  const [aiImageFile, setAiImageFile] = useState(null);
  const [aiStorageMethod, setAiStorageMethod] = useState('Room Temperature');
  const [aiStorageHours, setAiStorageHours] = useState(2);
  const [aiPackaging, setAiPackaging] = useState('Sealed / Covered');
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const [aiResult, setAiResult] = useState(null);

  // Form State
  const [foodName, setFoodName] = useState('');
  const [category, setCategory] = useState('Cooked Food');
  const [quantity, setQuantity] = useState(40);
  const [unit, setUnit] = useState('Meals');
  const [pickupAddress, setPickupAddress] = useState('MG Road, Bangalore');
  const [expiryHours, setExpiryHours] = useState(4);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // NGO Management State
  const [ngoDemands, setNgoDemands] = useState({
    'Cooked Rice Meals': 80,
    'Bread & Bakery': 40,
    'Packaged Food': 60,
    'Fruits & Vegetables': 30
  });
  const [ngoHours, setNgoHours] = useState({
    'monday': { open: '09:00', close: '22:00', status: 'open' },
    'tuesday': { open: '09:00', close: '22:00', status: 'open' },
    'wednesday': { open: '09:00', close: '22:00', status: 'open' },
    'thursday': { open: '09:00', close: '22:00', status: 'open' },
    'friday': { open: '09:00', close: '22:00', status: 'open' },
    'saturday': { open: '10:00', close: '23:00', status: 'open' },
    'sunday': { open: '10:00', close: '20:00', status: 'open' },
  });

  // Verification & Failure Dialog State
  const [selectedDonationForOtp, setSelectedDonationForOtp] = useState(null);
  const [otpInput, setOtpInput] = useState('');
  const [otpMessage, setOtpMessage] = useState(null);
  const [cancelDialogDonation, setCancelDialogDonation] = useState(null);
  const [cancelReason, setCancelReason] = useState('Donor unavailable');

  // Admin Operational Control Center State
  const [adminSummary, setAdminSummary] = useState(null);
  const [adminInterventions, setAdminInterventions] = useState(null);
  const [activeQueueTab, setActiveQueueTab] = useState('ALL');
  const [receivingQueue, setReceivingQueue] = useState([]);
  const [queueLoading, setQueueLoading] = useState(false);

  // Operations Control Modals
  const [selectedRescueFlowId, setSelectedRescueFlowId] = useState(null);
  const [selectedWaveDonationId, setSelectedWaveDonationId] = useState(null);
  const [selectedInterventionDonation, setSelectedInterventionDonation] = useState(null);

  useEffect(() => {
    autoLoginRole(role);
  }, [role]);

  const autoLoginRole = async (targetRole) => {
    const roleCredentials = {
      donor: { email: 'donor1@hotel.com', pass: 'pass123' },
      ngo: { email: 'ngo1@greenhope.org', pass: 'pass123' },
      volunteer: { email: 'vol1@volunteer.org', pass: 'pass123' },
      admin: { email: 'admin@fooddonation.org', pass: 'admin123' },
    };
    try {
      const cred = roleCredentials[targetRole];
      await api.login(cred.email, cred.pass);
      setServerOnline(true);
      fetchRoleData(targetRole);
    } catch (err) {
      console.error('Login error:', err);
      setServerOnline(false);
    }
  };

  const fetchRoleData = async (activeRole) => {
    setLoading(true);
    try {
      const dons = await api.getDonations().catch(() => []);
      setDonations(dons);

      if (activeRole === 'admin') {
        const [s, h, summaryRes, queueRes, intervRes] = await Promise.all([
          api.getStats().catch(() => null),
          api.getHeatmap().catch(() => null),
          api.getReceivingSummary().catch(() => null),
          api.getReceivingQueue({ tab: activeQueueTab }).catch(() => ({ items: [] })),
          api.getInterventions().catch(() => null),
        ]);
        setStats(s);
        setHeatmap(h);
        setAdminSummary(summaryRes);
        setReceivingQueue(queueRes?.items || queueRes || []);
        setAdminInterventions(intervRes);
      } else if (activeRole === 'volunteer') {
        const routes = await api.getBatchedRoutes().catch(() => []);
        setBatchedRoutes(routes);
      }
    } catch (err) {
      console.error('Fetch data error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleQueueTabChange = async (newTab) => {
    setActiveQueueTab(newTab);
    setQueueLoading(true);
    try {
      const res = await api.getReceivingQueue({ tab: newTab });
      setReceivingQueue(res?.items || res || []);
    } catch (err) {
      console.error('Queue tab change error:', err);
    } finally {
      setQueueLoading(false);
    }
  };

  const handleRefreshAdminOperations = async () => {
    try {
      const [summaryRes, queueRes, intervRes, dons] = await Promise.all([
        api.getReceivingSummary().catch(() => null),
        api.getReceivingQueue({ tab: activeQueueTab }).catch(() => ({ items: [] })),
        api.getInterventions().catch(() => null),
        api.getDonations().catch(() => []),
      ]);
      setAdminSummary(summaryRes);
      setReceivingQueue(queueRes?.items || queueRes || []);
      setAdminInterventions(intervRes);
      setDonations(dons);
    } catch (err) {
      console.error('Admin refresh error:', err);
    }
  };

  const handleRunAiAnalysis = async (e) => {
    e.preventDefault();
    setAiAnalyzing(true);
    setAiResult(null);
    try {
      const formData = new FormData();
      if (aiImageFile) formData.append('image', aiImageFile);
      formData.append('food_category', category);
      formData.append('quantity', quantity);
      formData.append('storage_method', aiStorageMethod);
      formData.append('storage_duration_hours', aiStorageHours);
      formData.append('packaging_condition', aiPackaging);

      const res = await api.analyzeFood(formData);
      setAiResult(res);
      if (res.food_detected && !foodName) {
        setFoodName(res.food_detected);
      }
    } catch (err) {
      alert('AI Vision Analysis error: ' + err.message);
    } finally {
      setAiAnalyzing(false);
    }
  };

  const handleCreateDonation = async (e) => {
    e.preventDefault();
    if (!foodName) return;
    setIsSubmitting(true);
    try {
      const prepTime = new Date();
      const expiryTime = new Date(Date.now() + expiryHours * 3600 * 1000);

      await api.createDonation({
        food_name: foodName,
        description: `Freshly prepared ${foodName.toLowerCase()} ready for distribution.`,
        food_category: category,
        quantity: parseFloat(quantity),
        quantity_unit: unit,
        preparation_time: prepTime.toISOString(),
        expiry_time: expiryTime.toISOString(),
        pickup_address: pickupAddress,
        storage_method: aiStorageMethod,
        storage_duration_hours: parseFloat(aiStorageHours),
        packaging_condition: aiPackaging,
        ai_food_detected: aiResult?.food_detected || foodName,
        ai_visible_spoilage: aiResult?.visible_spoilage || 'Not detected',
        ai_discoloration: aiResult?.discoloration || 'Normal',
        ai_packaging_intact: aiResult?.packaging || 'Intact',
        ai_visual_condition: aiResult?.visual_condition || 'GOOD',
        ai_confidence_score: aiResult?.confidence || 0.88,
        condition_score: aiResult?.condition_score || 85,
        latitude: 12.9750,
        longitude: 77.6080
      });

      setFoodName('');
      setAiResult(null);
      fetchRoleData(role);
      alert('🎉 Donation created with AI assessment and cryptographically verified OTP / QR tokens!');
    } catch (err) {
      alert('Error creating donation: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEscalateDonation = async (id) => {
    try {
      await api.escalateDonation(id);
      fetchRoleData(role);
      alert('🚨 Priority Escalation Broadcasted! 2x radius active.');
    } catch (err) {
      alert('Escalation error: ' + err.message);
    }
  };

  const handleCancelDonation = async () => {
    if (!cancelDialogDonation) return;
    try {
      await api.cancelDonation(cancelDialogDonation.id, cancelReason);
      setCancelDialogDonation(null);
      fetchRoleData(role);
      alert('Donation cancelled with reason.');
    } catch (err) {
      alert('Cancellation error: ' + err.message);
    }
  };

  const handleVerifyOtp = async () => {
    if (!selectedDonationForOtp || !otpInput) return;
    try {
      const res = await api.verifyOtp(selectedDonationForOtp.id, otpInput);
      setOtpMessage({ type: 'success', text: res.message || 'OTP Verified!' });
      fetchRoleData(role);
    } catch (err) {
      setOtpMessage({ type: 'error', text: err.message || 'Invalid OTP code.' });
    }
  };

  const handleSaveNgoSchedule = async () => {
    try {
      await api.updateNgoDemands(1, ngoDemands);
      await api.updateNgoHours(1, ngoHours);
      alert('✅ NGO operating hours and demand targets updated successfully in matching algorithm!');
    } catch (err) {
      alert('Update error: ' + err.message);
    }
  };

  const handleRunBatchMatch = async () => {
    setLoading(true);
    try {
      const res = await api.runBatchMatching();
      setBatchResults(res);
      fetchRoleData(role);
    } catch (err) {
      alert('Batch matching error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewCarbonImpact = async (donation) => {
    setSelectedCarbonDonation(donation);
    try {
      const impact = await api.getCarbonImpact(donation.id);
      setCarbonImpactData(impact);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header Bar */}
      <header className="glass-panel" style={{ margin: '16px 24px', padding: '16px 28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderRadius: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'var(--gradient-emerald)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 14px var(--emerald-glow)' }}>
            <Utensils color="#fff" size={24} />
          </div>
          <div>
            <h1 style={{ fontSize: '20px', fontWeight: '800', letterSpacing: '-0.5px', background: 'linear-gradient(90deg, #fff 0%, #cbd5e1 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Smart Food Rescue Platform
            </h1>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: serverOnline ? '#10b981' : '#f43f5e', boxShadow: serverOnline ? '0 0 10px #10b981' : 'none' }}></span>
              FastAPI Server: {serverOnline ? 'Connected (127.0.0.1:8000)' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Role Selector Tabs */}
        <div style={{ display: 'flex', background: 'rgba(15, 23, 42, 0.7)', padding: '4px', borderRadius: '14px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          {[
            { key: 'donor', label: 'Donor & AI Vision', icon: HeartHandshake },
            { key: 'ngo', label: 'NGO & Demands', icon: ShieldCheck },
            { key: 'volunteer', label: 'Volunteer Logistics', icon: Truck },
            { key: 'admin', label: 'Operations Control Center', icon: BarChart3 },
          ].map(tab => {
            const Icon = tab.icon;
            const active = role === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setRole(tab.key)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  borderRadius: '10px',
                  border: 'none',
                  background: active ? 'var(--gradient-emerald)' : 'transparent',
                  color: active ? '#fff' : 'var(--text-muted)',
                  fontWeight: active ? '700' : '500',
                  fontSize: '13px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: active ? '0 4px 12px var(--emerald-glow)' : 'none'
                }}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </header>

      {/* Hero Stats Banner */}
      <div style={{ margin: '0 24px 24px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Sparkles color="#10b981" size={24} />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>Real AI Vision</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Metadata Decision Fusion</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Calendar color="#38bdf8" size={24} />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>Operating Hours</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Dynamic NGO Demands</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'rgba(245, 158, 11, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Lock color="#f59e0b" size={24} />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>OTP & QR Handover</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Backend-Verified Security</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'rgba(244, 63, 94, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Flame color="#f43f5e" size={24} />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>Emergency Engine</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Auto & Manual Escalations</div>
          </div>
        </div>
      </div>

      {/* Main Content Body */}
      <main style={{ margin: '0 24px 32px', flex: 1 }}>
        {/* DONOR PORTAL & AI VISION STUDIO */}
        {role === 'donor' && (
          <div className="fade-in" style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.3fr', gap: '24px' }}>
            {/* AI Vision Studio + Donation Creation Form */}
            <div className="glass-panel" style={{ padding: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
                <Sparkles color="#10b981" size={22} />
                <h2 style={{ fontSize: '18px', fontWeight: '700' }}>AI Vision Studio & Donation Intake</h2>
              </div>

              {/* AI Vision Testing Card */}
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '14px', border: '1px solid rgba(16, 185, 129, 0.25)', marginBottom: '20px' }}>
                <div style={{ fontSize: '13px', fontWeight: '700', color: '#10b981', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Zap size={14} /> Multi-Feature Vision & Metadata Decision Fusion
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                  <div>
                    <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Storage Method</label>
                    <select className="glass-input" value={aiStorageMethod} onChange={e => setAiStorageMethod(e.target.value)} style={{ background: '#0f172a', fontSize: '12px' }}>
                      <option value="Room Temperature">Room Temperature</option>
                      <option value="Refrigerated">Refrigerated</option>
                      <option value="Heated/Insulated">Heated / Insulated</option>
                      <option value="Frozen">Frozen</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Packaging Condition</label>
                    <select className="glass-input" value={aiPackaging} onChange={e => setAiPackaging(e.target.value)} style={{ background: '#0f172a', fontSize: '12px' }}>
                      <option value="Sealed / Covered">Sealed / Covered</option>
                      <option value="Open Container">Open Container</option>
                      <option value="Individual Packets">Individual Packets</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '12px' }}>
                  <input type="file" accept="image/*" onChange={e => setAiImageFile(e.target.files[0])} style={{ fontSize: '12px', color: 'var(--text-muted)' }} />
                  <button type="button" className="btn-secondary" onClick={handleRunAiAnalysis} disabled={aiAnalyzing} style={{ fontSize: '12px', padding: '6px 14px' }}>
                    {aiAnalyzing ? 'Analyzing...' : 'Run Real AI Vision'}
                  </button>
                </div>

                {/* AI Structured Results Card */}
                {aiResult && (
                  <div style={{ marginTop: '12px', padding: '14px', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '12px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontWeight: '800', color: '#10b981', fontSize: '14px' }}>Visual Condition: {aiResult.visual_condition}</span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Score: {aiResult.condition_score}/100 • Confidence: {(aiResult.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                      <div>🍱 Detected: <strong style={{ color: '#fff' }}>{aiResult.food_detected}</strong></div>
                      <div>🔴 Spoilage: <strong style={{ color: aiResult.visible_spoilage === 'Not detected' ? '#10b981' : '#f59e0b' }}>{aiResult.visible_spoilage}</strong></div>
                      <div>🎨 Discoloration: <strong style={{ color: '#fff' }}>{aiResult.discoloration}</strong></div>
                      <div>📦 Packaging: <strong style={{ color: '#fff' }}>{aiResult.packaging}</strong></div>
                    </div>
                    <div style={{ marginTop: '8px', fontSize: '11px', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.1)', padding: '6px 10px', borderRadius: '8px' }}>
                      ⚠️ {aiResult.warning}
                    </div>
                  </div>
                )}
              </div>

              {/* Create Donation Form */}
              <form onSubmit={handleCreateDonation} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Food Name / Title</label>
                  <input className="glass-input" placeholder="e.g. Rice + Dal Curry" value={foodName} onChange={e => setFoodName(e.target.value)} required />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Category</label>
                    <select className="glass-input" value={category} onChange={e => setCategory(e.target.value)} style={{ background: '#0f172a' }}>
                      <option value="Cooked Food">Cooked Food (Fast Decay)</option>
                      <option value="Bakery">Bakery Items</option>
                      <option value="Fruits">Fruits & Produce</option>
                      <option value="Vegetables">Vegetables</option>
                      <option value="Packaged Food">Packaged Goods</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Quantity</label>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <input className="glass-input" type="number" value={quantity} onChange={e => setQuantity(e.target.value)} required />
                      <select className="glass-input" value={unit} onChange={e => setUnit(e.target.value)} style={{ width: '90px', background: '#0f172a' }}>
                        <option value="Meals">Meals</option>
                        <option value="Kg">Kg</option>
                        <option value="Packets">Packets</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Pickup Address</label>
                  <input className="glass-input" value={pickupAddress} onChange={e => setPickupAddress(e.target.value)} required />
                </div>

                <button type="submit" className="btn-primary" disabled={isSubmitting} style={{ marginTop: '6px', justifyContent: 'center' }}>
                  {isSubmitting ? 'Publishing...' : 'Publish Food Surplus with Real Verification'}
                  <ArrowRight size={16} />
                </button>
              </form>
            </div>

            {/* Active Donations Feed with OTP, QR & Emergency Buttons */}
            <div className="glass-panel" style={{ padding: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '18px', fontWeight: '700' }}>Active Platform Donations ({donations.length})</h2>
                <button className="btn-secondary" onClick={() => fetchRoleData('donor')}>
                  <RefreshCw size={14} /> Refresh
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxHeight: '580px', overflowY: 'auto' }}>
                {donations.map(d => (
                  <div key={d.id} className="glass-panel" style={{ padding: '16px', borderRadius: '14px', borderLeft: d.is_emergency ? '4px solid #f43f5e' : '1px solid rgba(255,255,255,0.1)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: '700', fontSize: '15px' }}>{d.food_name}</span>
                          {d.is_emergency && (
                            <span style={{ background: '#f43f5e', color: '#fff', fontSize: '10px', fontWeight: '800', padding: '2px 8px', borderRadius: '6px' }}>
                              🚨 EMERGENCY
                            </span>
                          )}
                          <span className={`badge badge-${d.urgency_level?.toLowerCase().replace(' ', '') || 'fresh'}`}>
                            {d.urgency_level || 'Fresh'}
                          </span>
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                          📦 {d.quantity} {d.quantity_unit} • 📍 {d.pickup_address}
                        </div>
                      </div>

                      <span style={{ fontSize: '11px', padding: '4px 8px', borderRadius: '8px', background: 'rgba(255,255,255,0.08)', textTransform: 'capitalize', color: d.status === 'cancelled' || d.status?.includes('failed') ? '#f43f5e' : '#10b981' }}>
                        {d.status}
                      </span>
                    </div>

                    {/* AI Assessment & Verification OTP Info */}
                    <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '10px 12px', borderRadius: '10px', margin: '8px 0', fontSize: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>AI Condition: </span>
                        <strong style={{ color: '#10b981' }}>{d.ai_visual_condition || 'GOOD'} ({d.condition_score || 85}/100)</strong>
                      </div>
                      {d.verification_otp && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ color: 'var(--text-muted)' }}>Pickup OTP:</span>
                          <span style={{ color: '#38bdf8', fontWeight: '800', letterSpacing: '2px', background: 'rgba(56, 189, 248, 0.15)', padding: '2px 8px', borderRadius: '6px' }}>
                            {d.verification_otp}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Action Buttons */}
                    <div style={{ display: 'flex', gap: '8px', marginTop: '10px', flexWrap: 'wrap' }}>
                      <button className="btn-secondary" onClick={() => setSelectedRescueFlowId(d.id)} style={{ fontSize: '11px', padding: '5px 10px', color: '#10b981' }}>
                        Live Flow
                      </button>
                      <button className="btn-secondary" onClick={() => setSelectedWaveDonationId(d.id)} style={{ fontSize: '11px', padding: '5px 10px', color: '#38bdf8' }}>
                        Wave Dispatch
                      </button>
                      <button className="btn-secondary" onClick={() => handleViewCarbonImpact(d)} style={{ fontSize: '11px', padding: '5px 10px' }}>
                        <Leaf size={12} color="#10b981" /> Carbon
                      </button>
                      {!d.is_emergency && !['completed', 'cancelled'].includes(d.status) && (
                        <button className="btn-secondary" onClick={() => handleEscalateDonation(d.id)} style={{ fontSize: '11px', padding: '5px 10px', color: '#f59e0b' }}>
                          <Flame size={12} /> Escalate Emergency
                        </button>
                      )}
                      {!['collected', 'delivered', 'completed', 'cancelled'].includes(d.status) && (
                        <button className="btn-secondary" onClick={() => setCancelDialogDonation(d)} style={{ fontSize: '11px', padding: '5px 10px', color: '#f43f5e' }}>
                          <X size={12} /> Cancel
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* NGO PORTAL & DEMANDS SCHEDULE */}
        {role === 'ngo' && (
          <div className="fade-in" style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '24px' }}>
            {/* Global Hungarian Algorithm Execution Card */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div className="glass-panel" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(56, 189, 248, 0.05) 100%)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <Sparkles color="#10b981" size={22} />
                      <h2 style={{ fontSize: '18px', fontWeight: '800' }}>Hungarian Bipartite Match Engine</h2>
                    </div>
                    <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '550px' }}>
                      Fuses NGO operating hours schedules and dynamic beneficiary demands with city-wide food batches for mathematically optimal recovery.
                    </p>
                  </div>
                  <button className="btn-primary" onClick={handleRunBatchMatch} disabled={loading} style={{ padding: '12px 22px', fontSize: '14px' }}>
                    <Zap size={16} /> Run Global Match
                  </button>
                </div>

                {batchResults && (
                  <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <div style={{ display: 'flex', gap: '24px', marginBottom: '14px' }}>
                      <div>
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Matches</span>
                        <div style={{ fontSize: '20px', fontWeight: '800', color: '#10b981' }}>{batchResults.total_matched} Donations</div>
                      </div>
                      <div>
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Efficiency</span>
                        <div style={{ fontSize: '20px', fontWeight: '800', color: '#38bdf8' }}>{batchResults.global_efficiency_score} / 100</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Available Feed */}
              <div className="glass-panel" style={{ padding: '24px' }}>
                <h2 style={{ fontSize: '17px', fontWeight: '700', marginBottom: '14px' }}>Available Nearby Donations</h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {donations.filter(d => d.status === 'pending').map(d => (
                    <div key={d.id} className="glass-panel" style={{ padding: '16px', borderRadius: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ fontWeight: '700', fontSize: '14px' }}>{d.food_name}</span>
                        <span style={{ fontSize: '12px', color: '#10b981' }}>AI Condition: {d.ai_visual_condition || 'GOOD'}</span>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                        {d.quantity} {d.quantity_unit} • {d.pickup_address}
                      </div>
                      <button className="btn-primary" onClick={() => api.acceptDonation(d.id).then(() => fetchRoleData('ngo'))} style={{ width: '100%', justifyContent: 'center', padding: '8px' }}>
                        Accept Donation Intake
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* NGO Demands & Operating Hours Schedule Management */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <Sliders color="#38bdf8" size={20} />
                <h2 style={{ fontSize: '18px', fontWeight: '700' }}>Beneficiary Demand & Schedule</h2>
              </div>

              {/* Demands Editor */}
              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '13px', fontWeight: '700', color: '#38bdf8', marginBottom: '8px' }}>Target Category Demands (Meals)</div>
                {Object.entries(ngoDemands).map(([cat, val]) => (
                  <div key={cat} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '12px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{cat}</span>
                    <input
                      type="number"
                      value={val}
                      onChange={e => setNgoDemands({ ...ngoDemands, [cat]: parseInt(e.target.value) || 0 })}
                      className="glass-input"
                      style={{ width: '80px', padding: '4px 8px', fontSize: '12px', textAlign: 'center' }}
                    />
                  </div>
                ))}
              </div>

              {/* Operating Hours Editor */}
              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '13px', fontWeight: '700', color: '#38bdf8', marginBottom: '8px' }}>Weekly Operating Schedule</div>
                {Object.entries(ngoHours).map(([day, sched]) => (
                  <div key={day} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', fontSize: '11px' }}>
                    <span style={{ textTransform: 'capitalize', color: 'var(--text-muted)' }}>{day}</span>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <span style={{ color: sched.status === 'open' ? '#10b981' : '#f43f5e' }}>{sched.status === 'open' ? `${sched.open}-${sched.close}` : 'Closed'}</span>
                      <button
                        type="button"
                        onClick={() => setNgoHours({
                          ...ngoHours,
                          [day]: { ...sched, status: sched.status === 'open' ? 'closed' : 'open' }
                        })}
                        style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', cursor: 'pointer' }}
                      >
                        Toggle
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <button className="btn-primary" onClick={handleSaveNgoSchedule} style={{ width: '100%', justifyContent: 'center' }}>
                Save Demand & Schedule Rules
              </button>
            </div>
          </div>
        )}

        {/* VOLUNTEER PORTAL */}
        {role === 'volunteer' && (
          <div className="fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {/* Active Tasks & Handover Verification */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <Truck color="#a855f7" size={22} />
                <h2 style={{ fontSize: '18px', fontWeight: '700' }}>Volunteer Tasks & Handover</h2>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {donations.filter(d => ['accepted', 'volunteer_assigned', 'collected'].includes(d.status)).map(d => (
                  <div key={d.id} className="glass-panel" style={{ padding: '16px', borderRadius: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                      <div>
                        <div style={{ fontWeight: '700', fontSize: '14px' }}>{d.food_name}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>📍 Pickup: {d.pickup_address}</div>
                      </div>
                      <span style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '2px 6px', borderRadius: '6px' }}>
                        {d.status}
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                      <button className="btn-primary" onClick={() => setSelectedDonationForOtp(d)} style={{ fontSize: '12px', padding: '6px 14px' }}>
                        <Lock size={12} /> Verify Handover OTP
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 5-Factor Weighted Score Breakdown Preview */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <Award color="#10b981" size={22} />
                <h2 style={{ fontSize: '18px', fontWeight: '700' }}>5-Factor Weighted Volunteer Algorithm</h2>
              </div>

              <div style={{ background: 'rgba(15,23,42,0.6)', padding: '16px', borderRadius: '12px', marginBottom: '16px' }}>
                <div style={{ fontSize: '13px', fontWeight: '700', color: '#10b981', marginBottom: '10px' }}>Algorithm Weights Breakdown</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>📍 Proximity to Donor (30%)</span>
                    <strong style={{ color: '#fff' }}>30 pts</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>⚡ Volunteer Availability (25%)</span>
                    <strong style={{ color: '#fff' }}>25 pts</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>🚗 Carrying Capacity (20%)</span>
                    <strong style={{ color: '#fff' }}>20 pts</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>⚖️ Current Workload Balance (15%)</span>
                    <strong style={{ color: '#fff' }}>15 pts</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>⭐ Reliability & Rating (10%)</span>
                    <strong style={{ color: '#fff' }}>10 pts</strong>
                  </div>
                </div>
              </div>

              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Vehicle capacity automatically gates assignments: walking (10 meals), bike (50 meals), car (100 meals), van (500 meals).
              </div>
            </div>
          </div>
        )}

        {/* ADMIN OPERATIONS CONTROL CENTER */}
        {role === 'admin' && (
          <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Operational Status Bar - 6 Key Operator Inquiries & Urgency Watchdog */}
            <OperationalStatusBar 
              summary={adminSummary}
              interventions={adminInterventions}
              onTabSelect={(tabKey) => handleQueueTabChange(tabKey)}
              onRefresh={handleRefreshAdminOperations}
            />

            {/* Rescue Operations Queue with Visual Urgency Prioritization */}
            <RescueQueue 
              donations={receivingQueue.length > 0 ? receivingQueue : donations}
              activeTab={activeQueueTab}
              onTabChange={handleQueueTabChange}
              onSelectFlow={(id) => setSelectedRescueFlowId(id)}
              onSelectWave={(id) => setSelectedWaveDonationId(id)}
              onSelectIntervene={(item) => setSelectedInterventionDonation(item)}
            />

            {/* Spatial Grid Heatmap & System Audit */}
            <div className="glass-panel" style={{ padding: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <Layers color="#38bdf8" size={24} />
                <h2 style={{ fontSize: '20px', fontWeight: '800' }}>Surplus Food Waste Grid Heatmap & System Audit</h2>
              </div>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '20px' }}>
                Renders spatial grid clusters across city coordinates with real-time audit logs of AI conditions and OTP handovers.
              </p>

              {heatmap && heatmap.clusters && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '14px' }}>
                  {heatmap.clusters.map((cluster, idx) => (
                    <div key={idx} className="glass-panel" style={{ padding: '16px', borderRadius: '12px', background: 'rgba(15, 23, 42, 0.7)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <MapPin color="#f43f5e" size={16} />
                        <span style={{ fontWeight: '700', fontSize: '14px' }}>Grid ({cluster.latitude}, {cluster.longitude})</span>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div>Donations Density: <strong style={{ color: '#fff' }}>{cluster.total_donations} items</strong></div>
                        <div>Total Volume: <strong style={{ color: '#10b981' }}>{cluster.total_meals} Meals</strong></div>
                        <div>Active Urgent: <strong style={{ color: cluster.active_urgent_count > 0 ? '#f87171' : 'var(--text-muted)' }}>{cluster.active_urgent_count} items</strong></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Handover OTP Modal */}
      {selectedDonationForOtp && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="glass-panel fade-in" style={{ padding: '28px', maxWidth: '400px', width: '90%', borderRadius: '20px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '800', marginBottom: '8px' }}>Backend Pickup Handover Verification</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Enter the 6-digit OTP code shown on the donor's screen to securely verify pickup on the backend server.
            </p>
            <input
              type="text"
              maxLength="6"
              placeholder="• • • • • •"
              value={otpInput}
              onChange={e => setOtpInput(e.target.value)}
              className="glass-input"
              style={{ fontSize: '22px', textAlign: 'center', letterSpacing: '6px', marginBottom: '14px' }}
            />
            {otpMessage && (
              <div style={{ marginBottom: '14px', fontSize: '12px', color: otpMessage.type === 'success' ? '#10b981' : '#f43f5e' }}>
                {otpMessage.text}
              </div>
            )}
            <div style={{ display: 'flex', gap: '10px' }}>
              <button className="btn-primary" onClick={handleVerifyOtp} style={{ flex: 1, justifyContent: 'center' }}>
                Validate OTP
              </button>
              <button className="btn-secondary" onClick={() => { setSelectedDonationForOtp(null); setOtpMessage(null); setOtpInput(''); }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Donation Modal */}
      {cancelDialogDonation && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="glass-panel fade-in" style={{ padding: '28px', maxWidth: '400px', width: '90%', borderRadius: '20px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '800', marginBottom: '8px', color: '#f43f5e' }}>Cancel Food Donation</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Please select a structured cancellation reason to record in the platform audit timeline.
            </p>
            <select
              value={cancelReason}
              onChange={e => setCancelReason(e.target.value)}
              className="glass-input"
              style={{ background: '#0f172a', marginBottom: '16px' }}
            >
              <option value="Donor unavailable">Donor unavailable</option>
              <option value="Food expired / spoiled">Food expired / spoiled</option>
              <option value="Quantity mismatch">Quantity mismatch</option>
              <option value="Kitchen operational issue">Kitchen operational issue</option>
              <option value="Other reason">Other reason</option>
            </select>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button className="btn-primary" onClick={handleCancelDonation} style={{ flex: 1, justifyContent: 'center', background: '#f43f5e' }}>
                Confirm Cancel
              </button>
              <button className="btn-secondary" onClick={() => setCancelDialogDonation(null)}>
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Carbon Impact Modal */}
      {selectedCarbonDonation && carbonImpactData && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="glass-panel fade-in" style={{ padding: '32px', maxWidth: '440px', width: '90%', borderRadius: '24px', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
            <div style={{ textAlign: 'center', marginBottom: '20px' }}>
              <div style={{ width: '60px', height: '60px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.2)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px' }}>
                <Leaf color="#10b981" size={32} />
              </div>
              <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Environmental Savings Certificate</h3>
              <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{carbonImpactData.food_name} ({carbonImpactData.quantity} {carbonImpactData.unit})</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '24px' }}>
              <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '16px', borderRadius: '16px', textAlign: 'center', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                <div style={{ fontSize: '24px', fontWeight: '800', color: '#10b981' }}>{carbonImpactData.co2_saved_kg} kg</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>CO₂ Prevented</div>
              </div>
              <div style={{ background: 'rgba(56, 189, 248, 0.1)', padding: '16px', borderRadius: '16px', textAlign: 'center', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                <div style={{ fontSize: '24px', fontWeight: '800', color: '#38bdf8' }}>{carbonImpactData.water_saved_liters} L</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Water Preserved</div>
              </div>
            </div>

            <button className="btn-primary" onClick={() => setSelectedCarbonDonation(null)} style={{ width: '100%', justifyContent: 'center' }}>
              Close Certificate
            </button>
          </div>
        </div>
      )}

      {/* Live Rescue Flow Modal (8-Stage Operational Flow) */}
      {selectedRescueFlowId && (
        <LiveRescueFlowModal 
          donationId={selectedRescueFlowId}
          onClose={() => setSelectedRescueFlowId(null)}
          onIntervene={(item) => setSelectedInterventionDonation(item)}
        />
      )}

      {/* Wave Dispatch Proactive Modal (3-Wave Dispatch Process) */}
      {selectedWaveDonationId && (
        <WaveDispatchModal 
          donationId={selectedWaveDonationId}
          onClose={() => setSelectedWaveDonationId(null)}
        />
      )}

      {/* Admin Authorized Intervention Modal */}
      {selectedInterventionDonation && (
        <AdminInterventionModal 
          donation={selectedInterventionDonation}
          onClose={() => setSelectedInterventionDonation(null)}
          onSuccess={() => handleRefreshAdminOperations()}
        />
      )}
    </div>
  );
}


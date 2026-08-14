import React, { useState, useEffect } from 'react';
import { 
  HeartHandshake, ShieldCheck, Truck, BarChart3, Leaf, Plus, Sparkles, 
  MapPin, Clock, Award, CheckCircle2, ArrowRight, Zap, RefreshCw, AlertTriangle, Layers, Droplets, Utensils
} from 'lucide-react';
import { api } from './api';

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

  // Form State
  const [foodName, setFoodName] = useState('');
  const [category, setCategory] = useState('Cooked Food');
  const [quantity, setQuantity] = useState(40);
  const [unit, setUnit] = useState('Meals');
  const [pickupAddress, setPickupAddress] = useState('MG Road, Bangalore');
  const [expiryHours, setExpiryHours] = useState(4);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Login as default role on change
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
        const s = await api.getStats().catch(() => null);
        const h = await api.getHeatmap().catch(() => null);
        setStats(s);
        setHeatmap(h);
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
        latitude: 12.9750,
        longitude: 77.6080
      });

      setFoodName('');
      fetchRoleData(role);
    } catch (err) {
      alert('Error creating donation: ' + err.message);
    } finally {
      setIsSubmitting(false);
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
              Smart Food Rescue
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
            { key: 'donor', label: 'Donor Portal', icon: HeartHandshake },
            { key: 'ngo', label: 'NGO Portal', icon: ShieldCheck },
            { key: 'volunteer', label: 'Volunteer Portal', icon: Truck },
            { key: 'admin', label: 'Admin Intelligence', icon: BarChart3 },
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
            <Utensils color="#10b981" size={24} />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>580+ Meals</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Rescued this Month</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Leaf color="#38bdf8" size={24} />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>1,450 kg CO₂</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Carbon Prevented</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'rgba(245, 158, 11, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Sparkles color="#f59e0b" size={24} />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>Hungarian Matching</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Global Bipartite Engine</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '20px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'rgba(168, 85, 247, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Truck color="#a855f7" size={24} />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: '800', color: '#fff' }}>VRPTW Routes</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Batched Volunteer Logistics</div>
          </div>
        </div>
      </div>

      {/* Main Content Body */}
      <main style={{ margin: '0 24px 32px', flex: 1 }}>
        {/* DONOR PORTAL */}
        {role === 'donor' && (
          <div className="fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '24px' }}>
            {/* Create Donation Form */}
            <div className="glass-panel" style={{ padding: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
                <Plus color="#10b981" size={20} />
                <h2 style={{ fontSize: '18px', fontWeight: '700' }}>Post Food Surplus</h2>
              </div>

              <form onSubmit={handleCreateDonation} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>Food Name / Title</label>
                  <input className="glass-input" placeholder="e.g. Fresh Vegetable Biryani" value={foodName} onChange={e => setFoodName(e.target.value)} required />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>Category</label>
                    <select className="glass-input" value={category} onChange={e => setCategory(e.target.value)} style={{ background: '#0f172a' }}>
                      <option value="Cooked Food">Cooked Food (Fast Decay)</option>
                      <option value="Bakery">Bakery Items</option>
                      <option value="Fruits">Fruits & Produce</option>
                      <option value="Vegetables">Vegetables</option>
                      <option value="Packaged Food">Packaged Goods</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>Quantity</label>
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
                  <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>Pickup Location</label>
                  <input className="glass-input" value={pickupAddress} onChange={e => setPickupAddress(e.target.value)} required />
                </div>

                <div>
                  <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>Expiry Window: {expiryHours} Hours</label>
                  <input type="range" min="1" max="24" value={expiryHours} onChange={e => setExpiryHours(e.target.value)} style={{ width: '100%', accentColor: '#10b981' }} />
                </div>

                <button type="submit" className="btn-primary" disabled={isSubmitting} style={{ marginTop: '8px', justifyContent: 'center' }}>
                  {isSubmitting ? 'Posting...' : 'Publish Donation Item'}
                  <ArrowRight size={16} />
                </button>
              </form>
            </div>

            {/* Active Donations Feed */}
            <div className="glass-panel" style={{ padding: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '18px', fontWeight: '700' }}>Your Food Donations ({donations.length})</h2>
                <button className="btn-secondary" onClick={() => fetchRoleData('donor')}>
                  <RefreshCw size={14} /> Refresh
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxHeight: '500px', overflowY: 'auto' }}>
                {donations.map(d => (
                  <div key={d.id} className="glass-panel" style={{ padding: '16px', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                        <span style={{ fontWeight: '700', fontSize: '15px' }}>{d.food_name}</span>
                        <span className={`badge badge-${d.urgency_level?.toLowerCase().replace(' ', '') || 'fresh'}`}>
                          <Clock size={12} /> {d.urgency_level || 'Fresh'}
                        </span>
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'flex', gap: '16px' }}>
                        <span>📦 {d.quantity} {d.quantity_unit}</span>
                        <span>📍 {d.pickup_address}</span>
                      </div>
                    </div>
                    <button className="btn-secondary" onClick={() => handleViewCarbonImpact(d)} style={{ fontSize: '12px', padding: '6px 12px' }}>
                      <Leaf size={14} color="#10b981" /> Carbon Impact
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* NGO PORTAL */}
        {role === 'ngo' && (
          <div className="fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
            {/* Global Hungarian Algorithm Execution Card */}
            <div className="glass-panel" style={{ padding: '28px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(56, 189, 248, 0.05) 100%)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <Sparkles color="#10b981" size={22} />
                    <h2 style={{ fontSize: '20px', fontWeight: '800' }}>Global Hungarian Bipartite Match Engine</h2>
                  </div>
                  <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '650px' }}>
                    Solves multi-demand assignment using <code style={{ color: '#38bdf8' }}>scipy.optimize.linear_sum_assignment</code>. Matches all pending city-wide food donations with available NGOs simultaneously for global optimal food recovery.
                  </p>
                </div>
                <button className="btn-primary" onClick={handleRunBatchMatch} disabled={loading} style={{ padding: '14px 28px', fontSize: '15px' }}>
                  <Zap size={18} /> Execute City-Wide Batch Match
                </button>
              </div>

              {/* Batch Match Results */}
              {batchResults && (
                <div style={{ marginTop: '24px', paddingTop: '20px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <div style={{ display: 'flex', gap: '24px', marginBottom: '16px' }}>
                    <div>
                      <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Optimal Matches Found</span>
                      <div style={{ fontSize: '22px', fontWeight: '800', color: '#10b981' }}>{batchResults.total_matched} Donations</div>
                    </div>
                    <div>
                      <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Global Efficiency Score</span>
                      <div style={{ fontSize: '22px', fontWeight: '800', color: '#38bdf8' }}>{batchResults.global_efficiency_score} / 100</div>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                    {batchResults.matched_pairs.map((pair, idx) => (
                      <div key={idx} className="glass-panel" style={{ padding: '14px', borderRadius: '12px', background: 'rgba(15, 23, 42, 0.6)' }}>
                        <div style={{ fontWeight: '700', fontSize: '14px', color: '#fff' }}>🍱 {pair.food_name}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0' }}>Matched with: <strong style={{ color: '#38bdf8' }}>{pair.ngo_name}</strong></div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginTop: '8px' }}>
                          <span style={{ color: '#10b981' }}>Score: {pair.match_score}%</span>
                          <span style={{ color: 'var(--text-muted)' }}>📍 {pair.distance_km} km away</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Available Feed */}
            <div className="glass-panel" style={{ padding: '28px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px' }}>Available Nearby Donations ({donations.length})</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
                {donations.map(d => (
                  <div key={d.id} className="glass-panel" style={{ padding: '20px', borderRadius: '14px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                      <h3 style={{ fontSize: '16px', fontWeight: '700' }}>{d.food_name}</h3>
                      <span className={`badge badge-${d.urgency_level?.toLowerCase().replace(' ', '') || 'fresh'}`}>
                        {d.urgency_level || 'Fresh'}
                      </span>
                    </div>
                    <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '14px' }}>{d.description}</p>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '16px' }}>
                      <div>📦 Quantity: <strong style={{ color: '#fff' }}>{d.quantity} {d.quantity_unit}</strong></div>
                      <div>📍 Pickup: <strong style={{ color: '#fff' }}>{d.pickup_address}</strong></div>
                      <div>Status: <span style={{ color: '#10b981', textTransform: 'capitalize' }}>{d.status}</span></div>
                    </div>
                    {d.status === 'pending' && (
                      <button className="btn-primary" onClick={() => api.acceptDonation(d.id).then(() => fetchRoleData('ngo'))} style={{ width: '100%', justifyContent: 'center' }}>
                        Accept Donation Intake
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* VOLUNTEER PORTAL */}
        {role === 'volunteer' && (
          <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div className="glass-panel" style={{ padding: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <Truck color="#a855f7" size={24} />
                <h2 style={{ fontSize: '20px', fontWeight: '800' }}>VRPTW Batched Multi-Stop Logistics</h2>
              </div>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '20px' }}>
                Clusters nearby pickups within a 3km radius into single consolidated routes for volunteer drivers. Reduces total driving distance by up to 40%.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
                {batchedRoutes.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', padding: '20px' }}>No active batched pickup clusters at this moment. Accept pending donations in NGO portal first!</div>
                ) : batchedRoutes.map((route, idx) => (
                  <div key={idx} className="glass-panel" style={{ padding: '20px', borderRadius: '16px', borderLeft: '4px solid #a855f7' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <span style={{ fontWeight: '700', fontSize: '15px' }}>Route Cluster #{idx + 1}</span>
                      <span style={{ fontSize: '12px', background: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', padding: '4px 10px', borderRadius: '12px' }}>
                        {route.total_pickups} Multi-Stop Pickups
                      </span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '16px' }}>
                      <div>👤 Assigned Driver: <strong style={{ color: '#fff' }}>{route.volunteer_name}</strong></div>
                      <div>🍱 Total Meals: <strong style={{ color: '#10b981' }}>{route.total_meals} Meals</strong></div>
                      <div>🚗 Est. Route Distance: <strong style={{ color: '#38bdf8' }}>{route.estimated_route_distance_km} km</strong></div>
                    </div>
                    <button className="btn-primary" style={{ width: '100%', justifyContent: 'center', background: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)' }}>
                      Start Multi-Stop Route Navigation
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ADMIN PORTAL */}
        {role === 'admin' && (
          <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div className="glass-panel" style={{ padding: '28px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <Layers color="#38bdf8" size={24} />
                <h2 style={{ fontSize: '20px', fontWeight: '800' }}>Surplus Food Waste Grid Heatmap</h2>
              </div>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '20px' }}>
                Renders spatial grid clusters across city coordinates to pinpoint food surplus hot-spots and high-urgency zones.
              </p>

              {heatmap && (
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
    </div>
  );
}

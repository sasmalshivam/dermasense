import { useState, useEffect } from 'react';
import {
  Lock,
  ShieldCheck,
  AlertTriangle,
  Activity,
  BarChart3,
  TrendingUp,
  MapPin,
  Star,
  RefreshCw,
  LogOut,
  Users,
} from 'lucide-react';
import { fetchAdminMetrics, verifyAdminPassword } from '../api';

export default function AdminView() {
  const [password, setPassword] = useState(sessionStorage.getItem('dermasense_admin_token') || '');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [inputPassword, setInputPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [fetchError, setFetchError] = useState('');

  const loadMetrics = async (pwd) => {
    setLoading(true);
    setFetchError('');
    try {
      const data = await fetchAdminMetrics(pwd);
      setMetrics(data);
      setIsAuthenticated(true);
    } catch (err) {
      setFetchError(err.message || 'Failed to load epidemiological metrics.');
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  // Attempt auto-login if password in sessionStorage
  useEffect(() => {
    let isMounted = true;
    if (password) {
      const runAuth = async () => {
        setLoading(true);
        try {
          const data = await fetchAdminMetrics(password);
          if (isMounted) {
            setMetrics(data);
            setIsAuthenticated(true);
          }
        } catch (err) {
          if (isMounted) {
            setFetchError(err.message || 'Failed to load epidemiological metrics.');
            setIsAuthenticated(false);
          }
        } finally {
          if (isMounted) setLoading(false);
        }
      };
      runAuth();
    }
    return () => {
      isMounted = false;
    };
  }, [password]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoading(true);

    try {
      const verifyRes = await verifyAdminPassword(inputPassword);
      if (verifyRes.valid) {
        sessionStorage.setItem('dermasense_admin_token', inputPassword);
        setPassword(inputPassword);
        setIsAuthenticated(true);
        await loadMetrics(inputPassword);
      } else {
        setLoginError('Invalid administrator password. Please try again.');
      }
    } catch {
      setLoginError('Could not connect to backend server.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('dermasense_admin_token');
    setPassword('');
    setIsAuthenticated(false);
    setMetrics(null);
  };

  // 1. Login Gate View
  if (!isAuthenticated) {
    return (
      <div className="max-w-md mx-auto px-4 py-16">
        <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-xl text-center">
          <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-blue-200 shadow-sm">
            <Lock className="w-8 h-8" />
          </div>

          <h1 className="text-xl font-black text-slate-900 mb-1">Epidemiological Surveillance Admin</h1>
          <p className="text-xs text-slate-500 mb-6">
            Smart India Hackathon 2025 | Disease cluster tracking & public health analytics portal.
          </p>

          <form onSubmit={handleLogin} className="space-y-4 text-left">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Admin Password
              </label>
              <input
                type="password"
                placeholder="Enter admin password (env: DERMASENSE_ADMIN_PASSWORD)"
                value={inputPassword}
                onChange={(e) => setInputPassword(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-blue-600 font-mono"
                required
              />
              <span className="text-[11px] text-slate-400 mt-1 block">
                Default demonstration key: <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-600 font-bold">derma_admin_2025</code>
              </span>
            </div>

            {loginError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-semibold flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
                <span>{loginError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 active:scale-98 text-white font-bold text-sm rounded-xl transition shadow-md cursor-pointer flex items-center justify-center gap-2"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
              <span>{loading ? 'Authenticating...' : 'Access Surveillance Dashboard'}</span>
            </button>
          </form>
        </div>
      </div>
    );
  }

  // 2. Main Admin Dashboard View
  const spikes = metrics?.spikes || [];
  const activeSpikes = spikes.filter((s) => s.is_spike);
  const byCondition = metrics?.by_condition || {};
  const byRegion = metrics?.by_region || {};
  const feedback = metrics?.feedback_summary || {};
  const totalTelemetry = metrics?.total_records || 0;

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Top Bar with Title & Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></span>
            <h1 className="text-xl sm:text-2xl font-black text-slate-900">
              National Skin Disease Surveillance Dashboard
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            SIH 2025 Public Health Telemetry • Team Healthnautix • Zero-PII Opt-In Surveillance Store
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => loadMetrics(password)}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleLogout}
            className="px-3.5 py-2 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-xl text-xs font-bold transition flex items-center gap-1.5 cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {fetchError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-2xl text-red-700 text-sm mb-6 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{fetchError}</span>
        </div>
      )}

      {/* Zero-PII Privacy Notice Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 mb-6 text-xs text-blue-900 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div>
          <strong>Zero-PII Privacy Guarantee:</strong> In strict compliance with Indian digital healthcare guidelines,
          all records in this database are collected strictly with explicit citizen opt-in. Zero uploaded photographs,
          zero IP addresses, and zero device identifiers are ever persisted. Only the coarse district/region and statistical
          possible condition are stored for epidemiological trend analysis.
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-bold uppercase mb-2">
            <span>Opt-In Reports</span>
            <Users className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">{totalTelemetry}</div>
          <div className="text-[11px] text-emerald-600 font-semibold mt-1">Past 30 Days</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-bold uppercase mb-2">
            <span>Spike Alerts</span>
            <TrendingUp className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-black text-amber-600">{activeSpikes.length}</div>
          <div className="text-[11px] text-slate-500 font-semibold mt-1">&gt; Mean + 2σ Threshold</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-bold uppercase mb-2">
            <span>Districts Active</span>
            <MapPin className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">{Object.keys(byRegion).length}</div>
          <div className="text-[11px] text-slate-500 font-semibold mt-1">Indian Regions</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs font-bold uppercase mb-2">
            <span>Citizen Rating</span>
            <Star className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-black text-slate-900">{feedback.average_rating || '5.0'} / 5</div>
          <div className="text-[11px] text-slate-500 font-semibold mt-1">{feedback.total_submissions || 0} reviews</div>
        </div>
      </div>

      {/* Outbreak / Spike Alert Banner */}
      {activeSpikes.length > 0 && (
        <section className="bg-amber-50 border-2 border-amber-500 rounded-2xl p-4 sm:p-5 mb-6 shadow-sm">
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-amber-500 text-white flex items-center justify-center shrink-0 shadow">
              <AlertTriangle className="w-6 h-6 animate-bounce" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="bg-amber-600 text-white text-[10px] font-black uppercase px-2 py-0.5 rounded-full">
                  Epidemiological Cluster Warning
                </span>
                <span className="text-xs text-amber-900 font-bold">
                  Weekly incidence exceeds historical mean + 2 standard deviations (Z &ge; 2.0)
                </span>
              </div>

              <div className="mt-3 space-y-2">
                {activeSpikes.map((spk, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-white border border-amber-300 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 shadow-xs"
                  >
                    <div>
                      <div className="font-bold text-slate-900 text-sm">
                        {spk.condition_name} in <span className="text-blue-700">{spk.region}</span>
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        Current Week: <b className="text-amber-700">{spk.current_week_count} cases</b> • Baseline Mean: {spk.baseline_mean} (σ = {spk.baseline_std}) • Alert Threshold: {spk.threshold}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="text-xs font-bold px-2.5 py-1 bg-red-100 text-red-800 rounded-lg">
                        Z-Score: +{spk.z_score}σ
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Charts Grid: Condition Distribution & Regional Spread */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Condition Distribution Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <h2 className="font-bold text-slate-900 text-sm flex items-center gap-2 mb-4 pb-2 border-b border-slate-100">
            <BarChart3 className="w-4 h-4 text-blue-600" />
            <span>Reported Condition Distribution</span>
          </h2>

          <div className="space-y-3">
            {Object.entries(byCondition).map(([cid, data]) => {
              const pct = totalTelemetry > 0 ? ((data.count / totalTelemetry) * 100).toFixed(1) : 0;
              return (
                <div key={cid}>
                  <div className="flex items-center justify-between text-xs font-semibold mb-1">
                    <span className="text-slate-800">{data.name}</span>
                    <span className="text-slate-500 font-mono">
                      {data.count} ({pct}%)
                    </span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-600 rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Regional Distribution Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <h2 className="font-bold text-slate-900 text-sm flex items-center gap-2 mb-4 pb-2 border-b border-slate-100">
            <MapPin className="w-4 h-4 text-purple-600" />
            <span>Geographic Distribution (Coarse Districts)</span>
          </h2>

          <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
            {Object.entries(byRegion).map(([reg, count]) => {
              const pct = totalTelemetry > 0 ? ((count / totalTelemetry) * 100).toFixed(1) : 0;
              return (
                <div key={reg}>
                  <div className="flex items-center justify-between text-xs font-semibold mb-1">
                    <span className="text-slate-800">{reg}</span>
                    <span className="text-slate-500 font-mono">
                      {count} ({pct}%)
                    </span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-purple-600 rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Citizen & Clinician Feedback Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h2 className="font-bold text-slate-900 text-sm flex items-center gap-2 mb-4 pb-2 border-b border-slate-100">
          <Activity className="w-4 h-4 text-emerald-600" />
          <span>Citizen Feedback & Clinician Review Metrics</span>
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-4 bg-slate-50 rounded-2xl border border-slate-200">
            <div className="text-4xl font-black text-slate-900">{feedback.average_rating || '5.0'}</div>
            <div className="flex items-center justify-center gap-1 text-amber-500 my-1">
              {[...Array(5)].map((_, i) => (
                <Star key={i} className="w-4 h-4 fill-amber-400" />
              ))}
            </div>
            <div className="text-xs text-slate-500 font-semibold">{feedback.total_submissions || 0} Total Citizen Ratings</div>
          </div>

          <div className="space-y-1.5 md:col-span-2">
            <div className="text-xs font-bold text-slate-700 mb-2">Rating Distribution:</div>
            {[5, 4, 3, 2, 1].map((star) => {
              const starCount = feedback.rating_distribution?.[star] || 0;
              const total = feedback.total_submissions || 1;
              const pct = ((starCount / total) * 100).toFixed(0);
              return (
                <div key={star} className="flex items-center gap-3 text-xs">
                  <span className="w-12 font-semibold text-slate-600">{star} Stars</span>
                  <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-400 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="w-10 text-right text-slate-400 font-mono text-[11px]">{starCount}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

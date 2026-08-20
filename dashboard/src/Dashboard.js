import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertTriangle, Database, Lock, Activity, Clock, CheckCircle, XCircle } from 'lucide-react';
import logo from './assets/favicon.png';
import './Dashboard.css';

const API_URL = 'http://localhost:8000';

// ── small helpers ──────────────────────────────────────────
function timeStr(date) {
  return date.toLocaleTimeString('en-US', {
    hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
}

function elapsed(date) {
  const s = Math.floor((Date.now() - date.getTime()) / 1000);
  if (s < 60)  return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

// ── Merkle verification modal ──────────────────────────────
function MerkleModal({ result, onClose }) {
  if (!result) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>🔒 Merkle Chain Verification</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="modal-row">
            <span className="modal-label">Status</span>
            <span className={`status-badge ${result.chain_valid ? 'status-valid' : 'status-invalid'}`}>
              {result.chain_valid ? '✅ VALID' : '❌ INVALID'}
            </span>
          </div>
          <div className="modal-row">
            <span className="modal-label">Entries</span>
            <span className="modal-value">{result.total_entries ?? '—'}</span>
          </div>
          <div className="modal-row">
            <span className="modal-label">Merkle Root</span>
            <code className="merkle-root modal-root">{result.merkle_root ? result.merkle_root.slice(0, 20) + '…' : '—'}</code>
          </div>
          <div className="modal-row">
            <span className="modal-label">Message</span>
            <span className="modal-value modal-msg">{result.message ?? result.chain_message ?? '—'}</span>
          </div>
          <div className="modal-row">
            <span className="modal-label">Verified At</span>
            <span className="modal-value">{timeStr(new Date())}</span>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-primary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────
function Dashboard() {
  const [stats, setStats]                   = useState(null);
  const [violationHistory, setViolationHistory] = useState([]);
  const [loading, setLoading]               = useState(true);
  const [error, setError]                   = useState(null);
  const [lastUpdate, setLastUpdate]         = useState(new Date());
  const [lastVerified, setLastVerified]     = useState(null);   // date of last verify click
  const [merkleResult, setMerkleResult]     = useState(null);   // modal data
  const [recentEvents, setRecentEvents]     = useState([]);     // [{time, verdict}]
  const [detectionBreakdown, setDetectionBreakdown] = useState({ ANOMALY: 0, TAMPER: 0, CLONE: 0 });
  const [deviceLastSeen, setDeviceLast]     = useState({});     // {uid: Date}
  const prevViolations                      = useRef({});

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await axios.get(`${API_URL}/stats`);
        const data = res.data;
        setStats(data);
        setLoading(false);
        const now = new Date();
        setLastUpdate(now);

        // ── violation history for chart ──
        const totalV = Object.values(data.violations || {}).reduce((a, b) => a + b, 0);
        setViolationHistory(prev => [
          ...prev,
          {
            time: timeStr(now),
            total: totalV,
            quarantined: data.quarantined_devices?.length || 0
          }
        ].slice(-30));

        // ── detect new violations → recent events + breakdown ──
        const prev = prevViolations.current;
        const curr = data.violations || {};
        Object.entries(curr).forEach(([uid, count]) => {
          if (count > (prev[uid] || 0)) {
            // Updated dynamically via /recent-events endpoint setup
          }
        });
        prevViolations.current = { ...curr };

        // ── detection breakdown from verdict_breakdown if backend sends it ──
        if (data.verdict_breakdown) {
          const vb = data.verdict_breakdown;
          setDetectionBreakdown({
            ANOMALY: (vb['ANOMALY'] || 0) + (vb['ML_FLAGGED'] || 0),
            TAMPER:  vb['TAMPER']  || 0,
            CLONE:   vb['CLONE']   || 0,
          });
        }

        // ── device last seen ──
        const seen = {};
        Object.keys(data.violations || {}).forEach(uid => { seen[uid] = now; });
        setDeviceLast(prev => ({ ...prev, ...seen }));

      } catch (err) {
        console.error('Fetch error:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchStats();
    const iv = setInterval(fetchStats, 2000);
    return () => clearInterval(iv);
  }, []);

  // ── also poll /verify-logs silently to keep merkle info fresh ──
  useEffect(() => {
    const pollVerify = async () => {
      try {
        const res = await axios.get(`${API_URL}/verify-logs`);
        setStats(prev => prev ? {
          ...prev,
          merkle_chain: {
            ...prev.merkle_chain,
            chain_valid: res.data.chain_valid,
            message: res.data.message,
          }
        } : prev);
      } catch (_) {}
    };
    const iv = setInterval(pollVerify, 10000);
    return () => clearInterval(iv);
  }, []);

  // ── poll /recent-events every 3s ──
  useEffect(() => {
    const pollEvents = async () => {
      try {
        const res = await axios.get(`${API_URL}/recent-events`);
        if (res.data.events?.length > 0) {
          setRecentEvents(res.data.events);
        }
      } catch (_) {}
    };
    pollEvents();
    const iv = setInterval(pollEvents, 3000);
    return () => clearInterval(iv);
  }, []);

  const verifyMerkleChain = async () => {
    try {
      const res = await axios.get(`${API_URL}/verify-logs`);
      setMerkleResult({
        chain_valid:   res.data.chain_valid,
        message:       res.data.message,
        total_entries: stats?.merkle_chain?.total_entries,
        merkle_root:   stats?.merkle_chain?.merkle_root,
      });
      setLastVerified(new Date());
    } catch (err) {
      setMerkleResult({ chain_valid: false, message: err.message });
    }
  };

  const releaseQuarantine = async (uid) => {
    if (!window.confirm(`Release ${uid} from quarantine?`)) return;
    try {
      await axios.post(`${API_URL}/quarantine/${uid}/release`);
    } catch (err) {
      alert(`Failed to release: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Connecting to IDS Backend...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <AlertTriangle size={48} />
        <h2>Connection Error</h2>
        <p>{error}</p>
        <p className="error-hint">Make sure FastAPI backend is running on port 8000</p>
      </div>
    );
  }

  const totalViolations = Object.values(stats?.violations || {}).reduce((a, b) => a + b, 0);
  const merkleEntries   = stats?.merkle_chain?.total_entries || 0;
  const merkleValid     = stats?.merkle_chain?.chain_valid ?? true;
  const merkleRoot      = stats?.merkle_chain?.merkle_root || '';

  return (
    <div className="dashboard">
      {/* Merkle Modal */}
      {merkleResult && <MerkleModal result={merkleResult} onClose={() => setMerkleResult(null)} />}

      {/* Header */}
      <header className="header">
        <div className="header-left">
          {/* FIXED: changed lassName to className below */}
          <img
            src={logo}
            alt="PhantomGuard"
            className="logo-image"
          />
          <div>
            <h1>PhantomGuard</h1>
            <p className="subtitle">Real-time Behavioral Analysis &amp; Dual-Layer Blockchain Logging</p>
          </div>
        </div>
        <div className="header-right">
          <div className="status-badge status-online">
            <span className="status-dot"></span>
            System Online
          </div>
          <div className="last-update">
            <Clock size={16} />
            <span>Updated: {lastUpdate.toLocaleTimeString()}</span>
          </div>
        </div>
      </header>

      {/* Metric Cards */}
      <div className="metrics-grid">
        <MetricCard
          icon={<Database />}
          title="Devices Tracked"
          value={stats?.devices_tracked || 0}
          color="#3b82f6"
          trend="Active monitoring"
        />
        <MetricCard
          icon={<AlertTriangle />}
          title="Total Violations"
          value={totalViolations}
          color="#f59e0b"
          trend="Rule-based detections"
        />
        <MetricCard
          icon={<Lock />}
          title="Audit Entries"
          value={merkleEntries}
          color="#10b981"
          trend={merkleValid ? '✅ Chain valid' : '❌ Chain invalid'}
        />
        <MetricCard
          icon={<Activity />}
          title="Blockchain Txns"
          value={stats?.hlf_stats?.total_submitted || 0}
          color="#8b5cf6"
          trend={`✅ ${stats?.hlf_stats?.successful || 0} ok  ❌ ${stats?.hlf_stats?.failed || 0} failed`}
        />
      </div>

      {/* Quarantine alert banner */}
      {stats?.quarantined_devices?.length > 0 && (
        <div className="alert alert-danger">
          <AlertTriangle size={24} />
          <div className="alert-content">
            <strong>🚨 Active Quarantine</strong>
            <p>
              {stats.quarantined_devices.length} device{stats.quarantined_devices.length > 1 ? 's' : ''} blocked:{' '}
              <code>{stats.quarantined_devices.join(', ')}</code>
            </p>
          </div>
        </div>
      )}

      {/* Charts + Merkle row */}
      <div className="charts-row">
        <div className="card chart-card">
          <div className="card-header">
            <h2>📈 Violations Over Time</h2>
            <span className="badge badge-info">{violationHistory.length} points</span>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={violationHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#94a3b8" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: '8px', color: '#e2e8f0' }} />
              <Line type="monotone" dataKey="total" stroke="#f59e0b" strokeWidth={2} name="Violations" dot={{ fill: '#f59e0b', r: 3 }} />
              <Line type="monotone" dataKey="quarantined" stroke="#ef4444" strokeWidth={2} name="Quarantined" dot={{ fill: '#ef4444', r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Cryptographic Audit */}
        <div className="card">
          <div className="card-header">
            <h2>🔒 Cryptographic Audit</h2>
            <button className="btn btn-primary" onClick={verifyMerkleChain}>Verify Chain</button>
          </div>
          <div className="merkle-info">
            <div className="info-item">
              <span className="info-label">Chain Status</span>
              <span className={`status-badge ${merkleValid ? 'status-valid' : 'status-invalid'}`}>
                {merkleValid
                  ? <><CheckCircle size={13} style={{marginRight:4}}/>Valid</>
                  : <><XCircle size={13} style={{marginRight:4}}/>Invalid</>}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Total Entries</span>
              <span className="info-value">{merkleEntries} logged</span>
            </div>
            <div className="info-item">
              <span className="info-label">Merkle Root</span>
              <code className="merkle-root">{merkleRoot ? merkleRoot.slice(0, 16) + '…' : 'N/A'}</code>
            </div>
            <div className="info-item">
              <span className="info-label">Last Verified</span>
              <span className="info-value">
                {lastVerified ? elapsed(lastVerified) : 'Not yet verified'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">HLF Txns</span>
              <span className="info-value">
                {stats?.hlf_stats?.total_submitted || 0} submitted &nbsp;·&nbsp;
                {stats?.hlf_stats?.successful || 0} ok &nbsp;·&nbsp;
                {stats?.hlf_queue_size || 0} pending
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Detection Breakdown + Recent Events Row */}
      <div className="charts-row">
        {/* Detection Breakdown */}
        <div className="card">
          <div className="card-header">
            <h2>🛡️ Detection Breakdown</h2>
            <span className="badge badge-secondary">rule-based</span>
          </div>
          <div className="breakdown-grid">
            <div className="breakdown-item breakdown-anomaly">
              <span className="breakdown-label">ANOMALY</span>
              <span className="breakdown-value">
                {detectionBreakdown.ANOMALY}
              </span>
              <span className="breakdown-hint">Sensor / interval out of range</span>
            </div>
            <div className="breakdown-item breakdown-tamper">
              <span className="breakdown-label">TAMPER</span>
              <span className="breakdown-value">
                {detectionBreakdown.TAMPER}
              </span>
              <span className="breakdown-hint">Firmware hash mismatch</span>
            </div>
            <div className="breakdown-item breakdown-clone">
              <span className="breakdown-label">STEALTHY</span>
              <span className="breakdown-value">{detectionBreakdown.CLONE || '—'}</span>
              <span className="breakdown-hint">ML-only detections (post-training)</span>
            </div>
          </div>
          <p className="breakdown-note">
            Full per-type breakdown available after ML model training.
          </p>
        </div>

        {/* Recent Security Events */}
        <div className="card">
          <div className="card-header">
            <h2>⚡ Recent Security Events</h2>
            <span className="badge badge-secondary">last 5</span>
          </div>
          {recentEvents.length === 0 ? (
            <div className="empty-state" style={{padding:'1.5rem'}}>
              <Activity size={32} style={{opacity:0.4}}/>
              <p style={{marginTop:'0.5rem'}}>Waiting for events…</p>
              <p className="empty-hint">Violations will appear here in real time</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="violations-table">
                <thead>
                  <tr><th>Time</th><th>Type</th><th>Device</th></tr>
                </thead>
                <tbody>
                  {recentEvents.slice(-5).reverse().map((ev, i) => (
                    <tr key={i}>
                      <td style={{color:'var(--text-secondary)', fontSize:'0.8rem'}}>{ev.time}</td>
                      <td>
                        <span className={`badge ${
                          ev.verdict.includes('TAMPER') ? 'badge-danger' :
                          ev.verdict.includes('ANOMALY') ? 'badge-warning' :
                          'badge-info'
                        }`}>{ev.verdict}</span>
                      </td>
                      <td><code className="uid-code" style={{fontSize:'0.7rem'}}>{ev.uid?.slice(0,8)}…</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Device Violation Table */}
      <div className="card">
        <div className="card-header">
          <h2>📊 Device Violation Tracking</h2>
          <span className="badge badge-secondary">
            {Object.keys(stats?.violations || {}).length} devices monitored
          </span>
        </div>
        {Object.keys(stats?.violations || {}).length === 0 ? (
          <div className="empty-state">
            <img
              src={logo}
              alt="PhantomGuard"
              className="empty-logo"
            />
            <p>No violations detected yet</p>
            <p className="empty-hint">System is monitoring all incoming telemetry</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="violations-table">
              <thead>
                <tr>
                  <th>Device UID</th>
                  <th>Violations</th>
                  <th>Last Seen</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(stats?.violations || {})
                  .sort(([, a], [, b]) => b - a)
                  .map(([uid, count]) => {
                    const isQ = stats.quarantined_devices?.includes(uid);
                    const seen = deviceLastSeen[uid];
                    return (
                      <tr key={uid} className={isQ ? 'row-quarantined' : ''}>
                        <td><code className="uid-code">{uid}</code></td>
                        <td>
                          <span className={`badge ${count >= 3 ? 'badge-danger' : count >= 2 ? 'badge-warning' : 'badge-info'}`}>
                            {count} violation{count !== 1 ? 's' : ''}
                          </span>
                        </td>
                        <td style={{color:'var(--text-secondary)', fontSize:'0.8rem'}}>
                          {seen ? timeStr(seen) : '—'}
                        </td>
                        <td>
                          {isQ
                            ? <span className="status-quarantined"><AlertTriangle size={14}/> Quarantined</span>
                            : <span className="status-monitoring"><Activity size={14}/> Monitoring</span>}
                        </td>
                        <td>
                          {isQ && (
                            <button className="btn btn-small btn-danger" onClick={() => releaseQuarantine(uid)}>
                              Release
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <footer className="footer">
        <p>IoT IDS Dashboard v4.0 | Behavioral Fingerprinting + Dual-Layer Blockchain Architecture</p>
        <p className="footer-tech">React + FastAPI + InfluxDB + Merkle Tree + Hyperledger Fabric</p>
      </footer>
    </div>
  );
}

function MetricCard({ icon, title, value, color, trend }) {
  return (
    <div className="metric-card" style={{ borderLeftColor: color }}>
      <div className="metric-icon" style={{ color }}>{icon}</div>
      <div className="metric-content">
        <div className="metric-title">{title}</div>
        <div className="metric-value">{value}</div>
        {trend && <div className="metric-trend">{trend}</div>}
      </div>
    </div>
  );
}

export default Dashboard;
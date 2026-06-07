import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Shield, AlertTriangle, Database, Lock, Activity, Clock } from 'lucide-react';
import './Dashboard.css';

const API_URL = 'http://localhost:8000';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [violationHistory, setViolationHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get(`${API_URL}/stats`);
        setStats(response.data);
        setLoading(false);
        setLastUpdate(new Date());

        // Update violation history for chart
        const totalViolations = Object.values(response.data.violations || {})
          .reduce((sum, count) => sum + count, 0);
        
        setViolationHistory(prev => {
          const newHistory = [
            ...prev,
            {
              time: new Date().toLocaleTimeString('en-US', { 
                hour12: false, 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
              }),
              total: totalViolations,
              quarantined: response.data.quarantined_devices?.length || 0
            }
          ];
          // Keep last 30 data points
          return newHistory.slice(-30);
        });

      } catch (err) {
        console.error('Fetch error:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchStats(); // Initial fetch
    const interval = setInterval(fetchStats, 2000); // Update every 2s

    return () => clearInterval(interval);
  }, []);

  const verifyMerkleChain = async () => {
    try {
      const response = await axios.get(`${API_URL}/verify-logs`);
      alert(
        `Merkle Chain Verification:\n\n` +
        `Status: ${response.data.chain_valid ? '✅ VALID' : '❌ INVALID'}\n` +
        `Total Entries: ${response.data.total_entries}\n` +
        `Merkle Root: ${response.data.merkle_root}\n` +
        `Message: ${response.data.chain_message}`
      );
    } catch (err) {
      alert(`Verification failed: ${err.message}`);
    }
  };

  const releaseQuarantine = async (uid) => {
    if (!window.confirm(`Release ${uid} from quarantine?`)) return;
    
    try {
      await axios.post(`${API_URL}/quarantine/${uid}/release`);
      alert(`✅ ${uid} released from quarantine`);
    } catch (err) {
      alert(`❌ Failed to release: ${err.message}`);
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

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <Shield size={32} className="logo" />
          <div>
            <h1>IoT Intrusion Detection System</h1>
            <p className="subtitle">Real-time Behavioral Analysis & Blockchain Logging</p>
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

      {/* Metrics Grid */}
      <div className="metrics-grid">
        <MetricCard
          icon={<Database />}
          title="Devices Tracked"
          value={stats?.devices_tracked || 0}
          color="#3b82f6"
          trend="+2 this session"
        />
        <MetricCard
          icon={<AlertTriangle />}
          title="Total Violations"
          value={Object.values(stats?.violations || {}).reduce((a, b) => a + b, 0)}
          color="#f59e0b"
          trend="Real-time monitoring"
        />
        <MetricCard
          icon={<Shield />}
          title="Quarantined Devices"
          value={stats?.quarantined_devices?.length || 0}
          color="#ef4444"
          trend={stats?.quarantined_devices?.length > 0 ? "Active defense!" : "All clear"}
        />
        <MetricCard
          icon={<Lock />}
          title="Merkle Chain"
          value={stats?.merkle_chain?.total_entries || 0}
          color="#10b981"
          trend={stats?.merkle_chain?.chain_valid ? "✅ Valid" : "❌ Invalid"}
        />
      </div>

      {/* Quarantine Alert Banner */}
      {stats?.quarantined_devices?.length > 0 && (
        <div className="alert alert-danger">
          <AlertTriangle size={24} />
          <div className="alert-content">
            <strong>🚨 Active Quarantine</strong>
            <p>
              {stats.quarantined_devices.length} device{stats.quarantined_devices.length > 1 ? 's' : ''} currently blocked: {' '}
              <code>{stats.quarantined_devices.join(', ')}</code>
            </p>
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="charts-row">
        {/* Violation History Chart */}
        <div className="card chart-card">
          <div className="card-header">
            <h2>📈 Violations Over Time</h2>
            <span className="badge badge-info">{violationHistory.length} data points</span>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={violationHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                dataKey="time" 
                stroke="#94a3b8" 
                tick={{ fontSize: 12 }}
                interval="preserveStartEnd"
              />
              <YAxis stroke="#94a3b8" />
              <Tooltip 
                contentStyle={{ 
                  background: '#1e293b', 
                  border: '1px solid #475569',
                  borderRadius: '8px',
                  color: '#e2e8f0'
                }} 
              />
              <Line 
                type="monotone" 
                dataKey="total" 
                stroke="#f59e0b" 
                strokeWidth={2}
                name="Total Violations"
                dot={{ fill: '#f59e0b', r: 3 }}
              />
              <Line 
                type="monotone" 
                dataKey="quarantined" 
                stroke="#ef4444" 
                strokeWidth={2}
                name="Quarantined"
                dot={{ fill: '#ef4444', r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Merkle Chain Info */}
        <div className="card">
          <div className="card-header">
            <h2>🔒 Cryptographic Verification</h2>
            <button className="btn btn-primary" onClick={verifyMerkleChain}>
              Verify Chain
            </button>
          </div>
          <div className="merkle-info">
            <div className="info-item">
              <span className="info-label">Chain Status:</span>
              <span className={`status-badge ${stats?.merkle_chain?.chain_valid ? 'status-valid' : 'status-invalid'}`}>
                {stats?.merkle_chain?.chain_valid ? '✅ Valid' : '❌ Invalid'}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">Total Entries:</span>
              <span className="info-value">{stats?.merkle_chain?.total_entries || 0}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Merkle Root:</span>
              <code className="merkle-root">{stats?.merkle_chain?.merkle_root || 'N/A'}</code>
            </div>
            <div className="info-item">
              <span className="info-label">HLF Queue:</span>
              <span className="info-value">
                {stats?.hlf_queue_size || 0} pending
                {stats?.hlf_queue_size > 0 && <Activity size={14} className="pulse-icon" />}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Violations Table */}
      <div className="card">
        <div className="card-header">
          <h2>📊 Device Violation Tracking</h2>
          <span className="badge badge-secondary">
            {Object.keys(stats?.violations || {}).length} devices monitored
          </span>
        </div>
        
        {Object.keys(stats?.violations || {}).length === 0 ? (
          <div className="empty-state">
            <Shield size={48} />
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
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(stats?.violations || {})
                  .sort(([, a], [, b]) => b - a) // Sort by violations (highest first)
                  .map(([uid, count]) => {
                    const isQuarantined = stats.quarantined_devices?.includes(uid);
                    return (
                      <tr key={uid} className={isQuarantined ? 'row-quarantined' : ''}>
                        <td>
                          <code className="uid-code">{uid}</code>
                        </td>
                        <td>
                          <span className={`badge ${
                            count >= 3 ? 'badge-danger' : 
                            count >= 2 ? 'badge-warning' : 
                            'badge-info'
                          }`}>
                            {count} violation{count !== 1 ? 's' : ''}
                          </span>
                        </td>
                        <td>
                          {isQuarantined ? (
                            <span className="status-quarantined">
                              <AlertTriangle size={16} />
                              Quarantined
                            </span>
                          ) : (
                            <span className="status-monitoring">
                              <Activity size={16} />
                              Monitoring
                            </span>
                          )}
                        </td>
                        <td>
                          {isQuarantined && (
                            <button 
                              className="btn btn-small btn-danger"
                              onClick={() => releaseQuarantine(uid)}
                            >
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

      {/* Footer */}
      <footer className="footer">
        <p>IoT IDS Dashboard v3.0 | Behavioral Fingerprinting + Hybrid Blockchain Architecture</p>
        <p className="footer-tech">React + FastAPI + InfluxDB + Merkle Tree + Hyperledger Fabric</p>
      </footer>
    </div>
  );
}

function MetricCard({ icon, title, value, color, trend }) {
  return (
    <div className="metric-card" style={{ borderLeftColor: color }}>
      <div className="metric-icon" style={{ color }}>
        {icon}
      </div>
      <div className="metric-content">
        <div className="metric-title">{title}</div>
        <div className="metric-value">{value}</div>
        {trend && <div className="metric-trend">{trend}</div>}
      </div>
    </div>
  );
}

export default Dashboard;
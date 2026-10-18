import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, ShieldOff, BarChart3, RefreshCw, Search, Clock, Hash, AlertOctagon } from 'lucide-react';

export default function AuditDashboardView() {
  const [telemetry, setTelemetry] = useState({
    total_scans: 0,
    allowed_count: 0,
    redacted_count: 0,
    blocked_count: 0,
    avg_risk_score: 0.0,
    scans: [],
    recent_audit_logs: [],
  });
  const [isLoading, setIsLoading] = useState(false);
  const [filterAction, setFilterAction] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchTelemetry = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/scans');
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (err) {
      console.error('Error fetching telemetry:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
  }, []);

  const filteredScans = telemetry.scans.filter((s) => {
    const matchesAction = filterAction === 'ALL' || s.action_taken === filterAction;
    const matchesSearch =
      !searchQuery ||
      s.request_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.detected_entity_types?.some((e) => e.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesAction && matchesSearch;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: '100%', overflowY: 'auto' }}>
      {/* Top Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        <MetricCard
          title="Total Scans Processed"
          value={telemetry.total_scans}
          subtitle="All intercepted prompts"
          icon={<BarChart3 size={20} color="var(--color-cyan)" />}
        />
        <MetricCard
          title="Safe (Allowed)"
          value={telemetry.allowed_count}
          subtitle="Passed directly to LLM"
          icon={<ShieldCheck size={20} color="var(--color-allow)" />}
          badgeColor="var(--color-allow)"
        />
        <MetricCard
          title="Sanitized (Redacted)"
          value={telemetry.redacted_count}
          subtitle="PII masked with placeholders"
          icon={<ShieldAlert size={20} color="var(--color-redact)" />}
          badgeColor="var(--color-redact)"
        />
        <MetricCard
          title="Threats (Blocked)"
          value={telemetry.blocked_count}
          subtitle="Critical credentials intercepted"
          icon={<ShieldOff size={20} color="var(--color-block)" />}
          badgeColor="var(--color-block)"
        />
        <MetricCard
          title="Average Risk Score"
          value={telemetry.avg_risk_score.toFixed(2)}
          subtitle="Heuristic risk baseline"
          icon={<AlertOctagon size={20} color="#a5b4fc" />}
        />
      </div>

      {/* Audit Log Table Section */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '600' }}>PostgreSQL Privacy Audit Trail</h2>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Verifiable log of all firewall interceptions. Raw sensitive inputs are never persisted.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Filter buttons */}
            <div style={{ display: 'flex', background: 'rgba(255, 255, 255, 0.04)', borderRadius: '8px', padding: '2px' }}>
              {['ALL', 'ALLOW', 'REDACT', 'BLOCK'].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilterAction(f)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: 'none',
                    fontSize: '11px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    background: filterAction === f ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
                    color: filterAction === f ? '#fff' : 'var(--text-muted)',
                  }}
                >
                  {f}
                </button>
              ))}
            </div>

            {/* Refresh */}
            <button
              onClick={fetchTelemetry}
              disabled={isLoading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-medium)',
                background: 'rgba(255, 255, 255, 0.04)',
                color: 'var(--text-secondary)',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              <RefreshCw size={13} style={{ animation: isLoading ? 'spinSlow 1s linear infinite' : 'none' }} />
              Refresh
            </button>
          </div>
        </div>

        {/* Search bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 14px',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(0, 0, 0, 0.25)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <Search size={14} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search by Request UUID or Entity Category (e.g. EMAIL_ADDRESS, API_KEY)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--text-primary)',
              fontSize: '13px',
            }}
          />
        </div>

        {/* Audit Log Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-medium)', color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase' }}>
                <th style={{ padding: '10px 12px' }}>Request ID</th>
                <th style={{ padding: '10px 12px' }}>Action</th>
                <th style={{ padding: '10px 12px' }}>Risk Score</th>
                <th style={{ padding: '10px 12px' }}>Detected Entities</th>
                <th style={{ padding: '10px 12px' }}>Output Scan</th>
                <th style={{ padding: '10px 12px' }}>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {filteredScans.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No scan records found matching filter.
                  </td>
                </tr>
              ) : (
                filteredScans.map((s, idx) => {
                  const isBlock = s.action_taken === 'BLOCK';
                  const isRedact = s.action_taken === 'REDACT';
                  const color = isBlock ? 'var(--color-block)' : isRedact ? 'var(--color-redact)' : 'var(--color-allow)';
                  const bg = isBlock ? 'var(--color-block-bg)' : isRedact ? 'var(--color-redact-bg)' : 'var(--color-allow-bg)';

                  return (
                    <tr
                      key={s.request_id || idx}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        transition: 'background 0.2s',
                      }}
                    >
                      <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-cyan)' }}>
                        {s.request_id ? `${s.request_id.slice(0, 16)}...` : 'N/A'}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span
                          style={{
                            padding: '3px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: '600',
                            fontFamily: 'var(--font-mono)',
                            background: bg,
                            color: color,
                          }}
                        >
                          {s.action_taken}
                        </span>
                      </td>
                      <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', fontWeight: '600', color: color }}>
                        {s.risk_score !== undefined ? s.risk_score.toFixed(2) : '-'}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {s.detected_entity_types && s.detected_entity_types.length > 0 ? (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {s.detected_entity_types.map((e) => (
                              <span
                                key={e}
                                style={{
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  fontSize: '10px',
                                  background: 'rgba(255, 255, 255, 0.06)',
                                  color: 'var(--text-secondary)',
                                  fontFamily: 'var(--font-mono)',
                                }}
                              >
                                {e}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>None</span>
                        )}
                      </td>
                      <td style={{ padding: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {s.output_action || 'N/A'}
                      </td>
                      <td style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '11px', whiteSpace: 'nowrap' }}>
                        {s.created_at ? new Date(s.created_at).toLocaleTimeString() : 'Recent'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, subtitle, icon, badgeColor }) {
  return (
    <div
      className="glass-panel"
      style={{
        padding: '18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        borderLeft: badgeColor ? `3px solid ${badgeColor}` : undefined,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '500' }}>{title}</span>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: '26px', fontWeight: '700', fontFamily: 'var(--font-heading)', color: badgeColor || '#fff' }}>
          {value}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{subtitle}</div>
      </div>
    </div>
  );
}

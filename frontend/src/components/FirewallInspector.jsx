import React, { useState } from 'react';
import FirewallShield3D from './FirewallShield3D';
import { ShieldAlert, ShieldCheck, ShieldOff, Eye, Code, Terminal, KeyRound, AlertTriangle } from 'lucide-react';

export default function FirewallInspector({ lastScan, isScanning }) {
  const [activeDiffTab, setActiveDiffTab] = useState('sanitized');

  const action = lastScan?.action || 'IDLE';
  const riskScore = lastScan?.risk_score ?? 0.0;
  const detectedEntities = lastScan?.detected_entities || [];
  const entityCounts = lastScan?.entity_counts || {};
  const requestId = lastScan?.request_id || 'Waiting for prompt...';

  // Threshold colors
  const actionColor =
    action === 'BLOCK'
      ? 'var(--color-block)'
      : action === 'REDACT'
      ? 'var(--color-redact)'
      : action === 'ALLOW'
      ? 'var(--color-allow)'
      : 'var(--text-muted)';

  const actionBg =
    action === 'BLOCK'
      ? 'var(--color-block-bg)'
      : action === 'REDACT'
      ? 'var(--color-redact-bg)'
      : action === 'ALLOW'
      ? 'var(--color-allow-bg)'
      : 'rgba(255, 255, 255, 0.03)';

  const actionBorder =
    action === 'BLOCK'
      ? 'var(--color-block-border)'
      : action === 'REDACT'
      ? 'var(--color-redact-border)'
      : action === 'ALLOW'
      ? 'var(--color-allow-border)'
      : 'var(--border-subtle)';

  return (
    <aside
      className="glass-panel"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        padding: '20px',
        height: '100%',
        overflowY: 'auto',
      }}
    >
      {/* 3D Privacy Core Canvas */}
      <div
        style={{
          background: 'radial-gradient(circle at center, rgba(6, 182, 212, 0.06) 0%, transparent 70%)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          padding: '8px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', padding: '0 8px' }}>
          <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            3D Firewall Telemetry
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Realtime
          </span>
        </div>
        <FirewallShield3D status={action} riskScore={riskScore} isScanning={isScanning} />
      </div>

      {/* Decision Card */}
      <div
        style={{
          background: actionBg,
          border: `1px solid ${actionBorder}`,
          borderRadius: 'var(--radius-md)',
          padding: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {action === 'BLOCK' ? (
            <ShieldOff size={22} style={{ color: actionColor }} />
          ) : action === 'REDACT' ? (
            <ShieldAlert size={22} style={{ color: actionColor }} />
          ) : (
            <ShieldCheck size={22} style={{ color: actionColor }} />
          )}
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
              Policy Decision
            </div>
            <div style={{ fontSize: '16px', fontWeight: '700', color: actionColor, letterSpacing: '0.02em' }}>
              {action}
            </div>
          </div>
        </div>

        {/* Risk Score Pill */}
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Risk Score</div>
          <div style={{ fontSize: '18px', fontWeight: '700', fontFamily: 'var(--font-mono)', color: actionColor }}>
            {riskScore.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Heuristic Risk Meter Bar */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
          <span>ALLOW (&lt;0.3)</span>
          <span>REDACT (0.3-0.7)</span>
          <span>BLOCK (&ge;0.7)</span>
        </div>
        <div
          style={{
            position: 'relative',
            height: '8px',
            borderRadius: '4px',
            background: 'rgba(255, 255, 255, 0.08)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${Math.min(riskScore * 100, 100)}%`,
              background:
                riskScore >= 0.7
                  ? 'var(--color-block)'
                  : riskScore >= 0.3
                  ? 'var(--color-redact)'
                  : 'var(--color-allow)',
              boxShadow: `0 0 10px ${actionColor}`,
              transition: 'width 0.4s ease',
            }}
          />
        </div>
      </div>

      {/* Detected Entities List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)' }}>
            Detected PII &amp; Secrets
          </span>
          <span
            style={{
              fontSize: '11px',
              padding: '2px 6px',
              borderRadius: '10px',
              background: detectedEntities.length > 0 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(255, 255, 255, 0.06)',
              color: detectedEntities.length > 0 ? 'var(--color-redact)' : 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {detectedEntities.length} Types
          </span>
        </div>

        {detectedEntities.length === 0 ? (
          <div
            style={{
              padding: '12px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px dashed var(--border-subtle)',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '12px',
            }}
          >
            No sensitive entities detected in latest prompt.
          </div>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {detectedEntities.map((ent) => {
              const count = entityCounts[ent] || 1;
              const isSecret = ent.includes('KEY') || ent.includes('TOKEN') || ent.includes('PASSWORD');
              return (
                <span
                  key={ent}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '4px 10px',
                    borderRadius: '8px',
                    fontSize: '11px',
                    fontWeight: '500',
                    fontFamily: 'var(--font-mono)',
                    background: isSecret ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                    border: `1px solid ${isSecret ? 'rgba(239, 68, 68, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                    color: isSecret ? '#fca5a5' : '#fcd34d',
                  }}
                >
                  {isSecret ? <KeyRound size={12} /> : <AlertTriangle size={12} />}
                  {ent}
                  <span style={{ opacity: 0.7 }}>&times;{count}</span>
                </span>
              );
            })}
          </div>
        )}
      </div>

      {/* Inspection Trace Details */}
      <div
        style={{
          marginTop: 'auto',
          paddingTop: '14px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Audit Trace ID:</span>
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-cyan)',
              background: 'rgba(6, 182, 212, 0.08)',
              padding: '2px 6px',
              borderRadius: '4px',
              maxWidth: '180px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {requestId}
          </span>
        </div>
      </div>
    </aside>
  );
}

import React, { useEffect, useState } from 'react';
import { Shield, Database, Cpu, Activity, FileText, MessageSquare, BarChart3 } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const [health, setHealth] = useState({
    status: 'checking',
    database: { status: 'checking' },
    llm_provider: { provider: 'mock' },
  });

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/health');
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        } else {
          setHealth({ status: 'error', database: { status: 'offline' }, llm_provider: { provider: 'mock' } });
        }
      } catch (err) {
        setHealth({ status: 'offline', database: { status: 'offline' }, llm_provider: { provider: 'mock' } });
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const isHealthy = health.status === 'ok';

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        background: 'rgba(7, 10, 17, 0.82)',
        backdropFilter: 'var(--glass-blur)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '12px 28px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            width: '38px',
            height: '38px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.2), rgba(99, 102, 241, 0.2))',
            border: '1px solid rgba(6, 182, 212, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-cyan)',
            boxShadow: '0 0 15px rgba(6, 182, 212, 0.2)',
          }}
        >
          <Shield size={20} />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px', fontWeight: '700', letterSpacing: '-0.02em', color: '#fff' }}>
              PrivyAI
            </span>
            <span
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '12px',
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              v0.1.0
            </span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Privacy Firewall & Gateway for AI
          </span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: 'rgba(12, 17, 29, 0.8)',
          padding: '4px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <button
          onClick={() => setActiveTab('chat')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            fontSize: '13px',
            fontWeight: '500',
            cursor: 'pointer',
            transition: 'var(--transition)',
            background: activeTab === 'chat' ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
            color: activeTab === 'chat' ? 'var(--color-cyan)' : 'var(--text-secondary)',
            boxShadow: activeTab === 'chat' ? '0 0 12px rgba(6, 182, 212, 0.15)' : 'none',
          }}
        >
          <MessageSquare size={16} />
          Chat Firewall
        </button>

        <button
          onClick={() => setActiveTab('documents')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            fontSize: '13px',
            fontWeight: '500',
            cursor: 'pointer',
            transition: 'var(--transition)',
            background: activeTab === 'documents' ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
            color: activeTab === 'documents' ? '#a5b4fc' : 'var(--text-secondary)',
            boxShadow: activeTab === 'documents' ? '0 0 12px rgba(99, 102, 241, 0.15)' : 'none',
          }}
        >
          <FileText size={16} />
          Document Vault
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            fontSize: '13px',
            fontWeight: '500',
            cursor: 'pointer',
            transition: 'var(--transition)',
            background: activeTab === 'audit' ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
            color: activeTab === 'audit' ? 'var(--color-allow)' : 'var(--text-secondary)',
            boxShadow: activeTab === 'audit' ? '0 0 12px rgba(16, 185, 129, 0.15)' : 'none',
          }}
        >
          <BarChart3 size={16} />
          Audit Telemetry
        </button>
      </nav>

      {/* System Health Status Pills */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Database Pill */}
        <div
          title={`Database: ${health.database?.status || 'Unknown'}`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: 'var(--radius-full)',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--border-subtle)',
            fontSize: '12px',
            color: 'var(--text-secondary)',
          }}
        >
          <Database size={13} style={{ color: health.database?.status === 'connected' ? 'var(--color-allow)' : '#94a3b8' }} />
          <span style={{ fontSize: '11px', textTransform: 'capitalize' }}>
            {health.database?.status === 'connected' ? 'PostgreSQL' : 'DB Offline'}
          </span>
        </div>

        {/* LLM Mode Pill */}
        <div
          title={`LLM Provider: ${health.llm_provider?.provider || 'mock'}`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: 'var(--radius-full)',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--border-subtle)',
            fontSize: '12px',
            color: 'var(--text-secondary)',
          }}
        >
          <Cpu size={13} style={{ color: 'var(--color-cyan)' }} />
          <span style={{ fontSize: '11px', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
            {health.llm_provider?.provider || 'MOCK'}
          </span>
        </div>

        {/* Global Status Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: 'var(--radius-full)',
            background: isHealthy ? 'var(--color-allow-bg)' : 'var(--color-block-bg)',
            border: `1px solid ${isHealthy ? 'var(--color-allow-border)' : 'var(--color-block-border)'}`,
            fontSize: '11px',
            fontWeight: '600',
            color: isHealthy ? 'var(--color-allow)' : 'var(--color-block)',
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: 'currentColor',
              boxShadow: '0 0 6px currentColor',
            }}
          />
          {isHealthy ? 'Firewall Active' : 'System Degraded'}
        </div>
      </div>
    </header>
  );
}

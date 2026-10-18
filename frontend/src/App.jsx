import React, { useState } from 'react';
import Navbar from './components/Navbar';
import ChatView from './components/ChatView';
import FirewallInspector from './components/FirewallInspector';
import DocumentVaultView from './components/DocumentVaultView';
import AuditDashboardView from './components/AuditDashboardView';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [lastScan, setLastScan] = useState({
    action: 'IDLE',
    risk_score: 0.0,
    detected_entities: [],
    entity_counts: {},
    request_id: 'System Ready',
  });
  const [isScanning, setIsScanning] = useState(false);

  return (
    <div className="app-container">
      {/* Top Navigation */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === 'chat' && (
          <div className="chat-layout">
            <ChatView
              onScanComplete={setLastScan}
              setIsScanning={setIsScanning}
              isScanning={isScanning}
            />
            <FirewallInspector lastScan={lastScan} isScanning={isScanning} />
          </div>
        )}

        {activeTab === 'documents' && <DocumentVaultView />}

        {activeTab === 'audit' && <AuditDashboardView />}
      </main>

      {/* Minimal Footer */}
      <footer className="footer">
        <div>
          <span>PrivyAI Privacy Firewall</span> &bull;{' '}
          <span style={{ color: 'var(--color-cyan)' }}>Active Protection Layer</span>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)' }}>
          Presidio Engine &bull; Soft-Max Heuristic &bull; Zero Raw Data Storage
        </div>
      </footer>
    </div>
  );
}

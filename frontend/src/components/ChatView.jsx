import React, { useState, useRef, useEffect } from 'react';
import { Send, Shield, Sparkles, AlertCircle, CheckCircle, ShieldAlert, KeyRound, User, Bot, HelpCircle } from 'lucide-react';

export default function ChatView({ onScanComplete, setIsScanning, isScanning }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "Hello! I'm connected through the PrivyAI Privacy Firewall. Any sensitive data (emails, credit cards, SSNs, API tokens, passwords) will be detected, scored, and redacted or blocked before reaching the LLM.",
      action: 'ALLOW',
      riskScore: 0.0,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [charLimit] = useState(10000);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isScanning]);

  const handleSend = async (textToSend) => {
    const text = textToSend || input;
    if (!text.trim() || isScanning) return;

    const userMsgId = Date.now().toString();
    const newMsg = {
      id: userMsgId,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, newMsg]);
    setInput('');
    setIsScanning(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });

      const data = await response.json();

      if (response.ok) {
        // Successful response (ALLOW or REDACT)
        onScanComplete({
          action: data.action,
          risk_score: data.risk_score,
          detected_entities: data.detected_entities,
          entity_counts: data.entity_counts,
          output_action: data.output_action,
          request_id: data.request_id,
          mock: data.mock,
        });

        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: data.response,
            action: data.action,
            riskScore: data.risk_score,
            detectedEntities: data.detected_entities,
            requestId: data.request_id,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      } else {
        // Blocked or validation error
        const isBlocked = response.status === 422;
        onScanComplete({
          action: isBlocked ? 'BLOCK' : 'ERROR',
          risk_score: isBlocked ? 0.95 : 0.0,
          detected_entities: ['CRITICAL_CREDENTIAL_OR_PII'],
          entity_counts: { BLOCKED: 1 },
          request_id: 'BLOCKED_REQUEST',
        });

        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            isBlocked: true,
            error: data.error || 'Request was blocked by the privacy policy.',
            action: 'BLOCK',
            riskScore: 0.95,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          error: 'Connection error. Ensure backend is running at http://localhost:8000',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsScanning(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '14px' }}>
      {/* Sample Quick Prompt Chips */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          Test Scenarios:
        </span>
        <button
          onClick={() => handleSend('What are the key benefits of automated PII firewalling in modern AI architecture?')}
          style={chipStyle('allow')}
        >
          <CheckCircle size={12} />
          Safe Prompt (ALLOW)
        </button>
        <button
          onClick={() =>
            handleSend(
              'My email is alexandra.turner@securenet.io and phone is +1-555-0199. Draft a follow-up response for my client.'
            )
          }
          style={chipStyle('redact')}
        >
          <ShieldAlert size={12} />
          Personal PII (REDACT)
        </button>
        <button
          onClick={() =>
            handleSend(
              'Please store this API token for my bot: ghp_99887766554433221100aabbccddeeffgghh and password=SuperSecretPassword123!'
            )
          }
          style={chipStyle('block')}
        >
          <AlertCircle size={12} />
          High-Risk Secrets (BLOCK)
        </button>
      </div>

      {/* Messages Stream */}
      <div
        className="glass-panel"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              gap: '12px',
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '82%',
            }}
          >
            {/* Avatar */}
            {msg.role !== 'user' && (
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: msg.isBlocked
                    ? 'rgba(239, 68, 68, 0.2)'
                    : 'linear-gradient(135deg, rgba(6, 182, 212, 0.2), rgba(99, 102, 241, 0.2))',
                  border: `1px solid ${msg.isBlocked ? 'rgba(239, 68, 68, 0.4)' : 'rgba(6, 182, 212, 0.4)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: msg.isBlocked ? 'var(--color-block)' : 'var(--color-cyan)',
                  flexShrink: 0,
                }}
              >
                {msg.isBlocked ? <ShieldAlert size={16} /> : <Shield size={16} />}
              </div>
            )}

            {/* Bubble */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
              }}
            >
              <div
                style={{
                  padding: '14px 18px',
                  borderRadius: 'var(--radius-md)',
                  background:
                    msg.role === 'user'
                      ? 'linear-gradient(135deg, #1e293b, #0f172a)'
                      : msg.isBlocked
                      ? 'rgba(239, 68, 68, 0.08)'
                      : 'rgba(18, 26, 44, 0.85)',
                  border: `1px solid ${
                    msg.role === 'user'
                      ? 'rgba(255, 255, 255, 0.12)'
                      : msg.isBlocked
                      ? 'var(--color-block-border)'
                      : 'var(--border-subtle)'
                  }`,
                  color: msg.isBlocked ? '#fca5a5' : 'var(--text-primary)',
                  fontSize: '14px',
                  lineHeight: '1.6',
                  whiteSpace: 'pre-wrap',
                  boxShadow: msg.role === 'user' ? '0 4px 14px rgba(0,0,0,0.3)' : 'none',
                }}
              >
                {msg.isBlocked ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '700', color: 'var(--color-block)' }}>
                      <AlertCircle size={16} />
                      Request Blocked by Privacy Firewall
                    </div>
                    <div style={{ fontSize: '13px', opacity: 0.9 }}>
                      {msg.error}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Sensitive credentials or severe PII detected. Prompt was terminated before reaching external LLMs.
                    </div>
                  </div>
                ) : (
                  msg.content
                )}
              </div>

              {/* Message Metadata Tags */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <span>{msg.timestamp}</span>
                {msg.action && (
                  <span
                    style={{
                      padding: '1px 6px',
                      borderRadius: '4px',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '10px',
                      fontWeight: '600',
                      background:
                        msg.action === 'BLOCK'
                          ? 'var(--color-block-bg)'
                          : msg.action === 'REDACT'
                          ? 'var(--color-redact-bg)'
                          : 'var(--color-allow-bg)',
                      color:
                        msg.action === 'BLOCK'
                          ? 'var(--color-block)'
                          : msg.action === 'REDACT'
                          ? 'var(--color-redact)'
                          : 'var(--color-allow)',
                    }}
                  >
                    {msg.action}
                  </span>
                )}
              </div>
            </div>

            {/* User Avatar */}
            {msg.role === 'user' && (
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.08)',
                  border: '1px solid var(--border-medium)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-secondary)',
                  flexShrink: 0,
                }}
              >
                <User size={16} />
              </div>
            )}
          </div>
        ))}

        {/* Loading Indicator */}
        {isScanning && (
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', color: 'var(--color-cyan)', fontSize: '13px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                animation: 'pulseSubtle 0.8s infinite alternate',
              }}
            >
              <Shield size={16} />
            </div>
            <span>Intercepting prompt &bull; Scanning sensitive entities &bull; Evaluating risk score...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div
        className="glass-panel"
        style={{
          padding: '12px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          borderRadius: 'var(--radius-lg)',
        }}
      >
        <textarea
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a message to process through the Privacy Firewall (sensitive data will be redacted)..."
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-body)',
            fontSize: '14px',
            resize: 'none',
            lineHeight: '1.5',
          }}
        />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            {input.length} / {charLimit} chars
          </span>

          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isScanning}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 18px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: !input.trim() || isScanning ? 'rgba(255, 255, 255, 0.05)' : 'var(--color-cyan)',
              color: !input.trim() || isScanning ? 'var(--text-muted)' : '#070a11',
              fontWeight: '600',
              fontSize: '13px',
              cursor: !input.trim() || isScanning ? 'not-allowed' : 'pointer',
              transition: 'var(--transition)',
              boxShadow: input.trim() && !isScanning ? '0 0 15px rgba(6, 182, 212, 0.4)' : 'none',
            }}
          >
            <Send size={14} />
            Scan &amp; Send
          </button>
        </div>
      </div>
    </div>
  );
}

function chipStyle(type) {
  const colors = {
    allow: { bg: 'var(--color-allow-bg)', border: 'var(--color-allow-border)', text: 'var(--color-allow)' },
    redact: { bg: 'var(--color-redact-bg)', border: 'var(--color-redact-border)', text: 'var(--color-redact)' },
    block: { bg: 'var(--color-block-bg)', border: 'var(--color-block-border)', text: 'var(--color-block)' },
  };
  const c = colors[type];
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 12px',
    borderRadius: '16px',
    border: `1px solid ${c.border}`,
    background: c.bg,
    color: c.text,
    fontSize: '11px',
    fontWeight: '500',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    transition: 'var(--transition)',
  };
}

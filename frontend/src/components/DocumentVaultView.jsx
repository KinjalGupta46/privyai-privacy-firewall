import React, { useState, useEffect } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertTriangle, Trash2, Eye, ShieldAlert, KeyRound, HardDrive } from 'lucide-react';

export default function DocumentVaultView() {
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);

  // Fetch document list
  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents');
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error('Error fetching documents:', err);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileUpload = async (file) => {
    if (!file) return;

    // Check size <= 10MB
    if (file.size > 10 * 1024 * 1024) {
      setUploadError('File exceeds maximum allowed size of 10 MB.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (res.ok) {
        setSelectedDoc(data);
        fetchDocuments();
      } else {
        setUploadError(data.detail || data.error || 'Failed to upload document.');
      }
    } catch (err) {
      setUploadError('Network error uploading document to storage.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (storageKey) => {
    try {
      const res = await fetch(`/api/documents/${storageKey}`, { method: 'DELETE' });
      if (res.ok) {
        setDocuments((prev) => prev.filter((d) => d.storage_key !== storageKey));
        if (selectedDoc?.storage_key === storageKey) {
          setSelectedDoc(null);
        }
      }
    } catch (err) {
      console.error('Error deleting document:', err);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: selectedDoc ? '1fr 420px' : '1fr', gap: '20px', height: '100%' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
        {/* Upload Dropzone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          style={{
            border: `2px dashed ${isDragOver ? 'var(--color-cyan)' : 'var(--border-medium)'}`,
            borderRadius: 'var(--radius-lg)',
            background: isDragOver ? 'rgba(6, 182, 212, 0.05)' : 'var(--bg-surface)',
            backdropFilter: 'var(--glass-blur)',
            padding: '36px 20px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            cursor: 'pointer',
            transition: 'var(--transition)',
          }}
          onClick={() => document.getElementById('vault-file-input').click()}
        >
          <input
            id="vault-file-input"
            type="file"
            accept=".pdf,.docx,.txt"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
            }}
          />

          <div
            style={{
              width: '52px',
              height: '52px',
              borderRadius: '14px',
              background: 'rgba(6, 182, 212, 0.1)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-cyan)',
            }}
          >
            <UploadCloud size={26} />
          </div>

          <div>
            <div style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-primary)' }}>
              {isUploading ? 'Encrypting & Storing Document...' : 'Drag & Drop Document for Privacy Scanning'}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Supports PDF, DOCX, TXT up to 10 MB. Files are stored with secure UUID keys.
            </div>
          </div>

          {uploadError && (
            <div style={{ color: 'var(--color-block)', fontSize: '12px', marginTop: '6px' }}>
              {uploadError}
            </div>
          )}
        </div>

        {/* Uploaded Documents List */}
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <HardDrive size={18} style={{ color: 'var(--color-cyan)' }} />
              <h2 style={{ fontSize: '16px', fontWeight: '600' }}>Stored Document Vault</h2>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {documents.length} Files in Storage
            </span>
          </div>

          {documents.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              No documents uploaded yet. Upload a PDF or DOCX file to run an automated PII inspection.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {documents.map((doc) => (
                <div
                  key={doc.storage_key}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-md)',
                    background: selectedDoc?.storage_key === doc.storage_key ? 'rgba(6, 182, 212, 0.1)' : 'rgba(255, 255, 255, 0.02)',
                    border: `1px solid ${selectedDoc?.storage_key === doc.storage_key ? 'rgba(6, 182, 212, 0.4)' : 'var(--border-subtle)'}`,
                    transition: 'var(--transition)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div
                      style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: '8px',
                        background: 'rgba(99, 102, 241, 0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#818cf8',
                      }}
                    >
                      <FileText size={18} />
                    </div>
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>
                        {doc.filename || doc.storage_key}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        Storage Ref: {doc.storage_key.slice(0, 16)}...
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <button
                      onClick={() => setSelectedDoc(doc)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '6px 12px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-medium)',
                        background: 'rgba(255, 255, 255, 0.04)',
                        color: 'var(--text-secondary)',
                        fontSize: '12px',
                        cursor: 'pointer',
                      }}
                    >
                      <Eye size={13} />
                      Inspect
                    </button>
                    <button
                      onClick={() => handleDelete(doc.storage_key)}
                      style={{
                        padding: '6px',
                        borderRadius: 'var(--radius-sm)',
                        border: 'none',
                        background: 'rgba(239, 68, 68, 0.1)',
                        color: 'var(--color-block)',
                        cursor: 'pointer',
                      }}
                      title="Delete document"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Selected Document Inspection Drawer */}
      {selectedDoc && (
        <aside className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '15px', fontWeight: '600' }}>Document Privacy Audit</h3>
            <button
              onClick={() => setSelectedDoc(null)}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '18px' }}
            >
              &times;
            </button>
          </div>

          {/* Privacy Score Card */}
          <div
            style={{
              padding: '14px',
              borderRadius: 'var(--radius-md)',
              background: selectedDoc.action === 'BLOCK' ? 'var(--color-block-bg)' : selectedDoc.action === 'REDACT' ? 'var(--color-redact-bg)' : 'var(--color-allow-bg)',
              border: `1px solid ${selectedDoc.action === 'BLOCK' ? 'var(--color-block-border)' : selectedDoc.action === 'REDACT' ? 'var(--color-redact-border)' : 'var(--color-allow-border)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Scan Verdict</div>
              <div
                style={{
                  fontSize: '16px',
                  fontWeight: '700',
                  color: selectedDoc.action === 'BLOCK' ? 'var(--color-block)' : selectedDoc.action === 'REDACT' ? 'var(--color-redact)' : 'var(--color-allow)',
                }}
              >
                {selectedDoc.action || 'SCANNED'}
              </div>
            </div>
            {selectedDoc.risk_score !== undefined && (
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Risk Score</div>
                <div style={{ fontSize: '18px', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>
                  {selectedDoc.risk_score?.toFixed(2)}
                </div>
              </div>
            )}
          </div>

          {/* Detected Entities */}
          {selectedDoc.detected_entities && (
            <div>
              <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                Flagged Sensitive Spans
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {selectedDoc.detected_entities.map((e) => (
                  <span
                    key={e}
                    style={{
                      padding: '3px 8px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                      background: 'rgba(245, 158, 11, 0.15)',
                      color: '#fbbf24',
                      border: '1px solid rgba(245, 158, 11, 0.3)',
                    }}
                  >
                    {e} {selectedDoc.entity_counts?.[e] ? `(${selectedDoc.entity_counts[e]})` : ''}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Text Preview */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)' }}>
              Extracted Content Preview
            </div>
            <div
              style={{
                flex: 1,
                background: 'rgba(0, 0, 0, 0.3)',
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
                fontSize: '12px',
                lineHeight: '1.6',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                maxHeight: '280px',
              }}
            >
              {selectedDoc.raw_text || selectedDoc.text_preview || 'Parsed document contents will appear here.'}
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}

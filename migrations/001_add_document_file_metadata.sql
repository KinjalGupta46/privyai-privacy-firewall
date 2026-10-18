
-- Adds file metadata columns to the existing documents table.
-- Safe to run more than once.

ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path VARCHAR(1024);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS size_bytes BIGINT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'uploaded';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT now();

CREATE INDEX IF NOT EXISTS ix_documents_status ON documents (status);

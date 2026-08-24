-- ==============================================================================
-- 🚀 SIRINTHANATTH PRIME - Enterprise Database Migration Schema
-- Version: 3.0.1 (Latest Enterprise Standards)
-- ==============================================================================

-- 1. เปิดใช้งาน Vector Extension สำหรับความจำระยะยาวของ AI (RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. สร้างตารางเก็บหน่วยความจำลูกค้า (Customer Memory & Embeddings)
CREATE TABLE IF NOT EXISTS customer_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_user_id TEXT NOT NULL,
    memory_text TEXT NOT NULL,
    embedding vector(768), -- เก็บโครงสร้างความคิดเป็นเวกเตอร์สำหรับ Gemini 2.5 Pro
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- สร้างดัชนี HNSW Vector Index เพื่อให้ AI ค้นหาความจำเก่าของลูกค้าได้เร็วที่สุดในโลก
CREATE INDEX IF NOT EXISTS customer_memory_embedding_idx 
ON customer_memory USING hnsw (embedding vector_cosine_ops);

-- สร้างดัชนีค้นหาตาม LINE ID เพื่อความรวดเร็ว
CREATE INDEX IF NOT EXISTS idx_customer_memory_line_user_id 
ON customer_memory(line_user_id);

-- 3. สร้างตารางเก็บบันทึกความยินยอม PDPA (Zero-Data Retention Compliance)
CREATE TABLE IF NOT EXISTS pdpa_consent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_user_id TEXT NOT NULL,
    consent_type TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_pdpa_line_user_id 
ON pdpa_consent_logs(line_user_id);

-- 4. สร้างตารางจัดการสิทธิ์ VVIP และระบบ Single-use Invite Codes
CREATE TABLE IF NOT EXISTS invite_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    package_tier VARCHAR(50) DEFAULT 'VIP_FOUNDER',
    is_token_exempt BOOLEAN DEFAULT TRUE,
    allowed_features JSONB DEFAULT '["all"]'::jsonb,
    is_used BOOLEAN DEFAULT FALSE,
    used_by_line_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    used_at TIMESTAMP WITH TIME ZONE
);

-- 5. สร้างตารางจัดการกระเป๋าเงินดิจิทัล (Smart Wallet & Credits)
CREATE TABLE IF NOT EXISTS users_wallet (
    user_id TEXT PRIMARY KEY,
    balance NUMERIC(12, 2) DEFAULT 500.00,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 6. สร้างตารางบัญชีผู้ใช้งานระบบหลัก (Users Profile & Roles)
CREATE TABLE IF NOT EXISTS users (
    line_user_id TEXT PRIMARY KEY,
    package_tier VARCHAR(50) DEFAULT 'FREE',
    is_token_exempt BOOLEAN DEFAULT FALSE,
    allowed_features JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(20) DEFAULT 'active',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 7. เปิดระบบความปลอดภัยระดับแถว (Row Level Security - RLS) ทุกตาราง
ALTER TABLE customer_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE pdpa_consent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE invite_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE users_wallet ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 8. กำหนดนโยบายความปลอดภัยเบื้องต้น (Allow Service Role Full Access)
-- เพื่อให้ Backend ของเราใน Cloud Run สามารถอ่าน-เขียนข้อมูลผ่าน Service Key ได้อย่างไร้รอยต่อ
CREATE POLICY IF NOT EXISTS "Enable all access for service role on customer_memory" 
ON customer_memory FOR ALL USING (true);

CREATE POLICY IF NOT EXISTS "Enable all access for service role on pdpa_consent_logs" 
ON pdpa_consent_logs FOR ALL USING (true);

CREATE POLICY IF NOT EXISTS "Enable all access for service role on invite_codes" 
ON invite_codes FOR ALL USING (true);

CREATE POLICY IF NOT EXISTS "Enable all access for service role on users_wallet" 
ON users_wallet FOR ALL USING (true);

CREATE POLICY IF NOT EXISTS "Enable all access for service role on users" 
ON users FOR ALL USING (true);
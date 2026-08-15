-- 1. เปิดใช้งาน Vector Extension สำหรับความจำ AI (RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. สร้างตารางเก็บหน่วยความจำลูกค้า (Memory)
CREATE TABLE IF NOT EXISTS customer_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_user_id TEXT NOT NULL,
    memory_text TEXT NOT NULL,
    embedding vector(768), -- เก็บความรู้สึกนึกคิดเป็นตัวเลข
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 3. สร้างตารางเก็บประวัติความยินยอม PDPA (Zero-Data Retention)
CREATE TABLE IF NOT EXISTS pdpa_consent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_user_id TEXT NOT NULL,
    consent_type TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 4. เปิดระบบความปลอดภัยระดับแถว (Row Level Security - RLS)
ALTER TABLE customer_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE pdpa_consent_logs ENABLE ROW LEVEL SECURITY;
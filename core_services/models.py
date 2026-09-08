import re
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal, List, Optional

# ==========================================
# 🛡️ 1. Core API Schemas (Client Payload Validation)
# ==========================================
class UserRegistrationFlow(BaseModel):
    """
    🛡️ ด่านตรวจ KYC และการยอมรับเงื่อนไขจากหน้าเว็บ
    อัปเกรด: Anti-XSS Sanitization, Agent Code Safety, และ Strict String Stripping
    """
    # 🔒 forbid = ห้ามมีฟิลด์ขยะ | str_strip_whitespace = ลบช่องว่างหัวท้ายอัตโนมัติ
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    
    shop_name: str = Field(..., min_length=2, max_length=100, description="ชื่อร้านค้าหรือองค์กร")
    kyc_document_id: str = Field(..., min_length=13, max_length=20, description="เลขบัตร ปชช. หรือ ทะเบียนนิติบุคคล")
    product_type: str = Field(..., min_length=2, max_length=150, description="ประเภทสินค้า (ห้ามเป็นของผิดกฎหมาย)")
    accepted_terms_and_conditions: bool = Field(..., description="ลูกค้ายอมรับกฎการหักเงิน Wallet และข้อจำกัดการใช้งาน (PDPA)")
    selected_package: Literal["VIP_FOUNDER", "PRIME", "ENTERPRISE", "ESSENTIAL"] = Field(..., description="แพ็กเกจที่เลือกลงทะเบียน")
    agent_code: Optional[str] = Field("NOAGENT", max_length=50, description="รหัสแนะนำจากพันธมิตร (ถ้ามี)")

    @field_validator('shop_name', 'product_type', 'agent_code')
    @classmethod
    def sanitize_text_inputs(cls, v: Optional[str]) -> Optional[str]:
        """ป้องกัน XSS, SQLi และ Prompt Injection โดยลบอักขระพิเศษอันตรายทิ้ง"""
        if v is None: return v
        # ลบแท็ก HTML, เครื่องหมายคำพูดเดี่ยว/คู่ และวงเล็บปีกกา/ก้ามปู
        safe_text = re.sub(r'[<>\[\]{}\'"]', '', v)
        return safe_text

    @field_validator('kyc_document_id')
    @classmethod
    def validate_kyc_format(cls, v: str) -> str:
        """เคลียร์ขีดกลางและช่องว่างทิ้งอัตโนมัติ ก่อนเช็กว่าเป็นตัวเลขล้วนหรือไม่"""
        cleaned_v = re.sub(r'[\s\-]', '', v)
        if not re.match(r'^[0-9]{13,20}$', cleaned_v):
            raise ValueError('เลขเอกสาร KYC ต้องเป็นตัวเลข 13-20 หลักเท่านั้น')
        return cleaned_v
    
    @field_validator('accepted_terms_and_conditions')
    @classmethod
    def validate_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError('ผู้ใช้งานต้องยอมรับเงื่อนไขการให้บริการ (Terms & Conditions) ก่อนดำเนินการต่อ')
        return v

class VerifyInvitePayload(BaseModel):
    """🎫 สคีมาสำหรับระบบ Invite ระดับ Enterprise"""
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    
    invite_token: str = Field(..., min_length=20, max_length=100, description="Token รักษาความปลอดภัยของลิงก์เชิญ")
    user_id: str = Field(..., min_length=33, max_length=33, description="LINE ID ของผู้ที่กดลิงก์ (รูปแบบมาตรฐาน LINE)")

    @field_validator('user_id')
    @classmethod
    def validate_line_id(cls, v: str) -> str:
        """ตรวจสอบความถูกต้องของ LINE ID ป้องกันการ Inject"""
        if not v.startswith('U'):
            raise ValueError("Invalid LINE User ID format")
        return v


# ==========================================
# 🤖 2. Vertex AI Structured Output Schemas (Gemini 3.7 Flash/Pro)
# ==========================================

class SwarmRoutingDecision(BaseModel):
    """🧠 สคีมาสำหรับ Central Boss (Router) จ่ายคิวงานให้แผนกต่างๆ"""
    model_config = ConfigDict(extra='forbid', strict=True)
    
    # อัปเกรด: ใช้ List[str] จาก typing เพื่อความเข้ากันได้ 100% กับ Vertex AI SDK ตัวใหม่
    pipeline: List[str] = Field(..., description="รายชื่อ Worker ที่ต้องรันแบบส่งไม้ต่อ เช่น ['worker_1', 'worker_7']")
    routing_msg: str = Field(..., description="ข้อความแจ้งให้ลูกค้ารออย่างสุภาพ หรูหรา และเป็นทางการ")

class AIComplianceCheckResult(BaseModel):
    """⚖️ สคีมาสำหรับ Worker 2 (Legal & Risk) ตรวจความเสี่ยงทางกฎหมายของสินค้า"""
    model_config = ConfigDict(extra='forbid', strict=True)
    
    is_legal: bool = Field(..., description="สินค้านี้สามารถขายได้อย่างถูกต้องตามกฎหมายหรือไม่")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="ระดับความเสี่ยงของโปรดักส์")
    compliance_reason: str = Field(..., description="คำอธิบายหรือเหตุผลทางกฎหมาย สั้นๆ กระชับ")

class PromoCampaignData(BaseModel):
    """🎉 สคีมาสำหรับ Promo Autopilot บังคับให้คิดแคมเปญให้ครบองค์ประกอบการตลาด"""
    model_config = ConfigDict(extra='forbid', strict=True)
    
    campaign_title: str = Field(..., description="ชื่อแคมเปญที่สั้น กระชับ และดึงดูดสายตา")
    special_offer: str = Field(..., description="ข้อเสนอพิเศษ ส่วนลด หรือโปรโมชันหลัก")
    ad_copy: str = Field(..., description="แคปชันโฆษณาพร้อมใช้งานและ Hashtags (ไม่มีเครื่องหมายคำพูดคลุม)")
    target_audience_advice: str = Field(..., description="คำแนะนำในการยิง Ads และกำหนดกลุ่มเป้าหมาย (Targeting)")
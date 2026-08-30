import re
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal, List

# ==========================================
# 🛡️ 1. Core API Schemas (Client Payload Validation)
# ด่านตรวจความปลอดภัย Zero-Trust จาก Web/LIFF
# ==========================================
class UserRegistrationFlow(BaseModel):
    """
    🛡️ ด่านตรวจ KYC และการยอมรับเงื่อนไขจากหน้าเว็บ
    อัปเกรด: Pydantic v2 Strict Mode + Regex Validation ป้องกันการยิง Payload ปลอม (Anti-Hack)
    """
    model_config = ConfigDict(extra='ignore', strict=True)
    
    shop_name: str = Field(..., min_length=2, max_length=100, description="ชื่อร้านค้าหรือองค์กร")
    kyc_document_id: str = Field(..., min_length=13, max_length=20, description="เลขบัตร ปชช. หรือ ทะเบียนนิติบุคคล")
    product_type: str = Field(..., min_length=2, max_length=150, description="ประเภทสินค้า (ห้ามเป็นของผิดกฎหมาย)")
    
    # บังคับกดยอมรับเงื่อนไข 100%
    accepted_terms_and_conditions: bool = Field(
        ..., 
        description="ลูกค้ายอมรับกฎการหักเงิน Wallet และข้อจำกัดการใช้งาน (PDPA)"
    )
    
    # จำกัดแพ็กเกจที่สมัครได้ ป้องกันการแก้โค้ดจากฝั่ง Client
    selected_package: Literal["VIP_FOUNDER", "PRIME", "ENTERPRISE", "ESSENTIAL"] = Field(
        ..., description="แพ็กเกจที่เลือกลงทะเบียน"
    )

    @field_validator('kyc_document_id')
    @classmethod
    def validate_kyc_format(cls, v: str) -> str:
        """กรองให้เหลือแต่ตัวเลข ป้องกัน Injection Attacks"""
        if not re.match(r'^[0-9]{13,20}$', v):
            raise ValueError('เลขเอกสาร KYC ต้องเป็นตัวเลข 13-20 หลักเท่านั้น')
        return v
    
    @field_validator('accepted_terms_and_conditions')
    @classmethod
    def validate_terms(cls, v: bool) -> bool:
        """บังคับให้ต้องเป็น True เท่านั้น หากเป็น False จะถูกบล็อกตั้งแต่ด่านแรก"""
        if not v:
            raise ValueError('ผู้ใช้งานต้องยอมรับเงื่อนไขการให้บริการ (Terms & Conditions) ก่อนดำเนินการต่อ')
        return v


# ==========================================
# 🤖 2. Vertex AI Structured Output Schemas (Gemini 2.5)
# สคีมาสำหรับบังคับผลลัพธ์ของ AI ให้ออกมาเป็น JSON ตรงตามโครงสร้าง 100%
# ==========================================

class SwarmRoutingDecision(BaseModel):
    """🧠 สคีมาสำหรับ Central Boss (Router) จ่ายคิวงานให้แผนกต่างๆ"""
    pipeline: List[str] = Field(
        ..., 
        description="รายชื่อ Worker ที่ต้องรันแบบส่งไม้ต่อ เช่น ['worker_1', 'worker_7']"
    )
    routing_msg: str = Field(
        ..., 
        description="ข้อความแจ้งให้ลูกค้ารออย่างสุภาพ หรูหรา และเป็นทางการ"
    )

class AIComplianceCheckResult(BaseModel):
    """⚖️ สคีมาสำหรับ Worker 2 (Legal & Risk) ตรวจความเสี่ยงทางกฎหมายของสินค้า"""
    is_legal: bool = Field(..., description="สินค้านี้สามารถขายได้อย่างถูกต้องตามกฎหมายหรือไม่")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="ระดับความเสี่ยงของโปรดักส์")
    compliance_reason: str = Field(..., description="คำอธิบายหรือเหตุผลทางกฎหมาย สั้นๆ กระชับ")

class PromoCampaignData(BaseModel):
    """🎉 สคีมาสำหรับ Promo Autopilot บังคับให้คิดแคมเปญให้ครบองค์ประกอบการตลาด"""
    campaign_title: str = Field(..., description="ชื่อแคมเปญที่สั้น กระชับ และดึงดูดสายตา")
    special_offer: str = Field(..., description="ข้อเสนอพิเศษ ส่วนลด หรือโปรโมชันหลัก")
    ad_copy: str = Field(..., description="แคปชันโฆษณาพร้อมใช้งานและ Hashtags")
    target_audience_advice: str = Field(..., description="คำแนะนำในการยิง Ads และกำหนดกลุ่มเป้าหมาย (Targeting)")
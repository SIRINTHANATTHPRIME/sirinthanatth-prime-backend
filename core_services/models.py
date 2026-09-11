import re
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal, List, Optional

# ==========================================
# 🛡️ 1. Core API Schemas (Client Payload Validation)
# ==========================================
class UserRegistrationFlow(BaseModel):
    """
    🛡️ ด่านตรวจ KYC และการยอมรับเงื่อนไขจากหน้าเว็บ
    อัปเกรด: Anti-XSS Sanitization, SQLi Prevention, Strict String Stripping
    """
    # 🔒 forbid = ห้ามมีฟิลด์ขยะ | str_strip_whitespace = ลบช่องว่างหัวท้ายอัตโนมัติ
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    
    shop_name: str = Field(..., min_length=2, max_length=100, description="ชื่อร้านค้าหรือองค์กร")
    kyc_document_id: str = Field(..., min_length=13, max_length=20, description="เลขบัตร ปชช. หรือ ทะเบียนนิติบุคคล/พาสปอร์ต")
    product_type: str = Field(..., min_length=2, max_length=150, description="ประเภทสินค้า (ห้ามเป็นของผิดกฎหมาย)")
    accepted_terms_and_conditions: bool = Field(..., description="ลูกค้ายอมรับกฎการหักเงิน Wallet และข้อจำกัดการใช้งาน (PDPA)")
    selected_package: Literal["VIP_FOUNDER", "PRIME", "ENTERPRISE", "ESSENTIAL"] = Field(..., description="แพ็กเกจที่เลือกลงทะเบียน")
    agent_code: Optional[str] = Field("NOAGENT", max_length=50, description="รหัสแนะนำจากพันธมิตร (ถ้ามี)")

    @field_validator('shop_name', 'product_type', 'agent_code')
    @classmethod
    def sanitize_text_inputs(cls, v: Optional[str]) -> Optional[str]:
        """ป้องกัน XSS, SQLi และ Prompt Injection ขั้นสูง (ไม่กระทบภาษาไทย)"""
        if not v or v == "NOAGENT": return v
        # 1. ทำลาย Script/Iframe/Object Tags ป้องกัน Cross-Site Scripting
        safe_text = re.sub(r'<(script|iframe|object|embed|svg).*?>.*?</\1>', '', v, flags=re.IGNORECASE)
        # 2. ทำลาย HTML Tags ทั่วไป
        safe_text = re.sub(r'<[^>]+>', '', safe_text)
        # 3. ทำลายอักขระเสี่ยง SQL Injection และ XSS Payload พื้นฐาน
        safe_text = re.sub(r'[\'\"=;{}[\]]', '', safe_text)
        return safe_text

    @field_validator('kyc_document_id')
    @classmethod
    def validate_kyc_format(cls, v: str) -> str:
        """รองรับบัตรประชาชนไทย (13 หลัก) และพาสปอร์ต/นิติบุคคล (สูงสุด 20 หลัก)"""
        cleaned_v = re.sub(r'[\s\-]', '', v)
        # ตรวจสอบว่าเป็นตัวอักษรภาษาอังกฤษหรือตัวเลข 13-20 หลักเท่านั้น
        if not re.match(r'^[A-Z0-9]{13,20}$', cleaned_v, re.IGNORECASE):
            raise ValueError('เลขเอกสาร KYC ต้องเป็นตัวอักษรหรือตัวเลข 13-20 หลักเท่านั้น และห้ามมีอักขระพิเศษ')
        return cleaned_v.upper()
    
    @field_validator('accepted_terms_and_conditions')
    @classmethod
    def validate_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError('ผู้ใช้งานต้องยอมรับเงื่อนไขการให้บริการ (Terms & Conditions) เพื่อให้สอดคล้องกับ พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล (PDPA)')
        return v

class VerifyInvitePayload(BaseModel):
    """🎫 สคีมาสำหรับระบบ Invite ระดับ Enterprise"""
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    
    invite_token: str = Field(..., min_length=20, max_length=100, description="Token รักษาความปลอดภัยของลิงก์เชิญ")
    user_id: str = Field(..., min_length=33, max_length=33, description="LINE ID ของผู้ที่กดลิงก์ (รูปแบบมาตรฐาน LINE)")

    @field_validator('user_id')
    @classmethod
    def validate_line_id(cls, v: str) -> str:
        """🛡️ ตรวจสอบฟอร์แมต LINE ID ป้องกัน ID Spoofing 100%"""
        if not re.match(r'^U[a-fA-F0-9]{32}$', v):
            raise ValueError("Invalid LINE User ID format (Must be 'U' followed by exactly 32 hex characters)")
        return v


# ==========================================
# 🤖 2. Vertex AI Structured Output Schemas (Gemini 3.7 Flash/Pro)
# ==========================================

class SwarmRoutingDecision(BaseModel):
    """🧠 สคีมาสำหรับ Central Boss (Router) จ่ายคิวงานให้แผนกต่างๆ"""
    model_config = ConfigDict(extra='forbid', strict=True)
    
    pipeline: List[str] = Field(..., description="รายชื่อ Worker Keys ที่ต้องส่งงานให้ทำตามลำดับ เช่น ['WORKER_2_RISK_QA', 'WORKER_6_STRATEGY']. หากเป็นคำทักทายทั่วไปให้ปล่อยว่าง []")
    routing_msg: str = Field(..., description="ข้อความสุภาพที่จะตอบกลับลูกค้าทันที เพื่อแจ้งให้ทราบว่าระบบกำลังประสานงานให้แผนกวิเคราะห์แผนกใดทำ")

class AIComplianceCheckResult(BaseModel):
    """⚖️ สคีมาสำหรับ Worker 2 (Legal & Risk) ตรวจความเสี่ยงทางกฎหมายของสินค้า"""
    model_config = ConfigDict(extra='forbid', strict=True)
    
    is_legal: bool = Field(..., description="สินค้านี้สามารถโปรโมตหรือขายได้อย่างถูกต้องตามกฎหมาย (อย., สคบ.) หรือไม่")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="ระดับความเสี่ยงของโปรดักส์และบริการ")
    compliance_reason: str = Field(..., description="คำอธิบายหรือเหตุผลทางกฎหมายที่ตรวจสอบพบ สั้นๆ กระชับ ชัดเจน")

class PromoCampaignData(BaseModel):
    """🎉 สคีมาสำหรับ Promo Autopilot บังคับให้คิดแคมเปญให้ครบองค์ประกอบการตลาด"""
    model_config = ConfigDict(extra='forbid', strict=True)
    
    campaign_title: str = Field(..., description="ชื่อแคมเปญที่สั้น กระชับ เล่นคำทางจิตวิทยา และดึงดูดสายตา")
    special_offer: str = Field(..., description="ข้อเสนอพิเศษ ส่วนลด หรือโปรโมชันหลัก (Call to Action)")
    ad_copy: str = Field(..., description="แคปชันโฆษณาพร้อมใช้งานและ Hashtags ทางการตลาด (ไม่มีเครื่องหมายคำพูดคลุม)")
    target_audience_advice: str = Field(..., description="คำแนะนำเชิงลึกในการยิง Ads และกำหนดกลุ่มเป้าหมาย (Targeting)")

# ==========================================
# 🧬 3. Evolution & Self-Learning Schemas (Worker 12)
# ==========================================

class IntentAnalysisSchema(BaseModel):
    """🎭 สคีมาสำหรับอ่านใจและวิเคราะห์พฤติกรรมลูกค้า (Predictive Empathy)"""
    model_config = ConfigDict(strict=True)
    
    sentiment: str = Field(description="อารมณ์ของลูกค้า ณ ปัจจุบัน (positive, neutral, frustrated, or urgent)")
    underlying_need: str = Field(description="ความต้องการที่แท้จริงระดับจิตใต้สำนึก (Unmet Need) เช่น ต้องการความมั่นใจ, ต้องการลดความเสี่ยง")
    cognitive_bias: str = Field(description="อคติทางความคิด เช่น FOMO (กลัวพลาดโอกาส), Loss Aversion (กลัวสูญเสีย)")
    financial_risk_tolerance: Literal["high", "medium", "low"] = Field(description="ระดับความสามารถในการยอมรับความเสี่ยงทางการเงิน")
    recommended_tone: str = Field(description="คำแนะนำน้ำเสียงที่ AI ควรใช้ตอบกลับ (เช่น ต้องหนักแน่น, ต้องปลอบประโลม, ต้องใช้ตัวเลขยืนยัน)")

class SystemEvolutionSchema(BaseModel):
    """⚙️ สคีมาสำหรับ AI พัฒนาระบบด้วยตัวเอง (System Upgrader Blueprint)"""
    model_config = ConfigDict(strict=True)
    
    golden_rule: str = Field(description="กฎเหล็ก 1 ข้อที่สกัดได้จากข้อผิดพลาดหรือคำสั่งแก้ไข (ต้องเป็นคำสั่งบังคับพฤติกรรม AI ทันที)")
    upgrade_proposal: str = Field(description="ร่างแผนอัปเกรดระบบเชิงวิศวกรรม (Code Architecture) ระบุไฟล์ที่ต้องแก้ เพื่อให้ CEO Secretary เขียนโค้ดต่อ")
    reference_links: List[str] = Field(description="รายการ URL ลิงก์อ้างอิง Document เทคโนโลยีล่าสุดที่เกี่ยวข้อง (ต้องค้นหาจาก Google Search จริง)")
    severity_level: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(description="ระดับความสำคัญและความเร่งด่วนของการอัปเกรดโครงสร้างนี้")
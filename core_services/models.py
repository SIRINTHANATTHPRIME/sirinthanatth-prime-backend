from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

class UserRegistrationFlow(BaseModel):
    """
    🛡️ ด่านตรวจ KYC และการยอมรับเงื่อนไขจากหน้าเว็บ
    อัปเกรด: Pydantic v2 Strict Mode ป้องกันการยิง Payload ปลอม (Anti-Hack)
    """
    model_config = ConfigDict(extra='ignore', strict=True)
    
    shop_name: str = Field(..., min_length=2, max_length=100, description="ชื่อร้านค้าหรือองค์กร")
    kyc_document_id: str = Field(..., min_length=13, max_length=20, description="เลขบัตร ปชช. หรือ ทะเบียนนิติบุคคล")
    product_type: str = Field(..., min_length=2, max_length=150, description="ประเภทสินค้า (ห้ามเป็นของผิดกฎหมาย)")
    
    # บังคับกดยอมรับเงื่อนไข 100%
    accepted_terms_and_conditions: bool = Field(
        ..., 
        description="ลูกค้ายอมรับกฎการหักเงิน Wallet และข้อจำกัดการใช้งาน"
    )
    
    # จำกัดแพ็กเกจที่สมัครได้ ป้องกันการแก้โค้ดจากฝั่ง Client
    selected_package: Literal["VIP_FOUNDER", "PRIME", "ENTERPRISE", "ESSENTIAL"] = Field(
        ..., description="แพ็กเกจที่เลือกลงทะเบียน"
    )
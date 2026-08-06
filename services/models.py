from pydantic import BaseModel, Field

class UserRegistrationFlow(BaseModel):
    """ด่านตรวจ KYC และการยอมรับเงื่อนไขจากหน้าเว็บ"""
    shop_name: str = Field(..., min_length=2)
    kyc_document_id: str = Field(..., description="เลขบัตร ปชช. หรือ ทะเบียนนิติบุคคล")
    product_type: str = Field(..., description="ประเภทสินค้า (ห้ามเป็นของผิดกฎหมาย)")
    
    # บังคับกดยอมรับเงื่อนไข
    accepted_terms_and_conditions: bool = Field(
        ..., 
        description="ลูกค้ายอมรับกฎการหักเงิน Wallet และข้อจำกัดน้ำหนัก Flash Express 1 กก."
    )
    selected_package: str = Field(..., description="VIP_FOUNDER, PRIME, หรือ ENTERPRISE")
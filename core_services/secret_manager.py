import os
import logging
from google.cloud import secretmanager

logger = logging.getLogger("SecretVault")

class PrimeSecretVault:
    """
    🔐 ระบบดึงตัวแปรลับจาก Google Secret Manager โดยตรงเข้าสู่ RAM
    """
    @staticmethod
    def get_secret(secret_id: str, version_id: str = "latest") -> str:
        # หากรันบน Local ให้ใช้ .env ปกติ แต่ถ้าอยู่บน Cloud Run ให้ดึงจาก Vault
        if os.environ.get("ENVIRONMENT") == "local":
            return os.environ.get(secret_id, "")
            
        try:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "sirinthanatth-prime")
            client = secretmanager.SecretManagerServiceClient()
            
            # เส้นทางเข้าถึง Vault ดิจิทัล
            name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
            response = client.access_secret_version(request={"name": name})
            
            # ถอดรหัส Payload เข้าสู่ RAM ทันที
            secret_value = response.payload.data.decode("UTF-8")
            return secret_value
            
        except Exception as e:
            logger.error(f"❌ [Vault Error]: ไม่สามารถดึงกุญแจ {secret_id} จาก Secret Manager ได้ -> {e}")
            return os.environ.get(secret_id, "") # Fallback ไปหา .env กรณีฉุกเฉิน
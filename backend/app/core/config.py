from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "IBVAP"
    database_url: str = "sqlite:///./ibvap.db"
    jwt_secret: str = "ibvap-military-grade-secure-jwt-secret-key-32b-plus-entropy-2026-ops"
    jwt_expire_minutes: int = 60
    redis_url: str = "redis://localhost:6379/0"
    evidence_dir: str = "./data/evidence"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

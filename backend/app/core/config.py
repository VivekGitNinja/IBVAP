from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "IBVAP"
    environment: str = "development"
    database_url: str = "sqlite:///./ibvap.db"
    jwt_secret: str = "ibvap-military-grade-secure-jwt-secret-key-32b-plus-entropy-2026-ops"
    jwt_expire_minutes: int = 1440
    redis_url: str = "redis://localhost:6379/0"
    evidence_dir: str = "./data/evidence"
    allowed_origins: str = "http://localhost:5173,http://localhost:8001,http://127.0.0.1:5173,http://127.0.0.1:8001"
    require_auth: bool = True
    log_level: str = "INFO"
    log_format: str = "json"
    enable_metrics: bool = True
    enable_demo: bool = False
    enable_synthetic_cameras: bool = False
    allow_demo_data: bool = False
    upload_dir: str = "./storage/uploads"
    max_upload_size_mb: int = 500
    allowed_video_extensions: str = "mp4,mov,avi,mkv,webm,jpg,jpeg,png,webp"

    # Computer Vision & Intelligence Extensions
    zone_cooldown_seconds: float = 10.0
    loitering_seconds: float = 60.0
    crowd_min_count: int = 5
    crowd_window_seconds: float = 30.0
    rapid_speed_threshold: float = 200.0
    enable_anpr: bool = True
    anpr_ocr_engine: str = "auto"
    night_luma_threshold: float = 60.0
    night_enhance: bool = True
    enable_face_recognition: bool = False
    face_match_threshold: float = 0.363
    face_blur: bool = True
    ffmpeg_h264_transcode: bool = True
    c2_webhook_url: str = ""
    c2_webhook_secret: str = "c2-tactical-secret-key"

    # Motion Fallback Noise Gating & Confidence Flags
    motion_min_area: int = 600
    motion_persistence_frames: int = 3
    motion_conf_floor: float = 0.55

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

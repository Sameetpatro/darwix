import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Base Directory is workspace root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)


class Settings(BaseModel):
    # Server Settings
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # LLM Settings (DeepSeek)
    deepseek_api_key: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    deepseek_base_url: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    deepseek_model: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    llm_fallback_on_error: bool = Field(
        default_factory=lambda: os.getenv("LLM_FALLBACK_ON_ERROR", "true").lower() in ("true", "1", "yes")
    )

    # Text-To-Speech (TTS)
    tts_provider: str = Field(default_factory=lambda: os.getenv("TTS_PROVIDER", "edge-tts"))
    tts_voice: str = Field(default_factory=lambda: os.getenv("TTS_VOICE", "en-US-EmmaMultilingualNeural"))
    tts_rate: str = Field(default_factory=lambda: os.getenv("TTS_RATE", "+0%"))
    tts_pitch: str = Field(default_factory=lambda: os.getenv("TTS_PITCH", "+0Hz"))

    # Speech-To-Text (ASR)
    asr_provider: str = Field(default_factory=lambda: os.getenv("ASR_PROVIDER", "web-speech"))
    asr_language: str = Field(default_factory=lambda: os.getenv("ASR_LANGUAGE", "en-US"))

    # Directories
    recordings_dir: Path = BASE_DIR / os.getenv("RECORDINGS_DIR", "recordings")
    transcripts_dir: Path = BASE_DIR / os.getenv("TRANSCRIPTS_DIR", "transcripts")
    logs_dir: Path = BASE_DIR / os.getenv("LOGS_DIR", "logs")

    save_audio_recordings: bool = Field(
        default_factory=lambda: os.getenv("SAVE_AUDIO_RECORDINGS", "true").lower() in ("true", "1", "yes")
    )
    save_transcripts: bool = Field(
        default_factory=lambda: os.getenv("SAVE_TRANSCRIPTS", "true").lower() in ("true", "1", "yes")
    )

    def ensure_directories(self):
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()

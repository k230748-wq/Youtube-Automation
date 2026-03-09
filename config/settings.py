import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Flask
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # Database (different name/port from ZEULE)
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ytauto:ytauto_dev@localhost:5433/ytauto")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis / Celery (different port from ZEULE)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # AI / LLM
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

    # Research
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

    # Media
    IDEOGRAM_API_KEY = os.getenv("IDEOGRAM_API_KEY", "")
    BANNERBEAR_API_KEY = os.getenv("BANNERBEAR_API_KEY", "")
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
    PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

    # YouTube
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

    # Voice
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

    # Assets
    ASSETS_DIR = os.getenv("ASSETS_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"))

    # Pipeline defaults
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5


settings = Settings()

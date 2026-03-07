"""Application configuration via environment variables."""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """BotForge application settings loaded from environment variables."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://botforge:botforge@localhost:5432/botforge"  # pragma: allowlist secret
    )
    database_url_test: str = "postgresql+asyncpg://botforge:botforge@localhost:5433/botforge_test"  # pragma: allowlist secret

    @model_validator(mode="after")
    def fix_database_url(self) -> "Settings":
        """Auto-fix DATABASE_URL for async compatibility.

        Some providers give postgresql:// with query params like ?sslmode=require,
        but asyncpg needs postgresql+asyncpg:// and doesn't support sslmode param.
        """
        self.database_url = self._normalize_async_url(self.database_url)
        self.database_url_test = self._normalize_async_url(self.database_url_test)
        return self

    @staticmethod
    def _normalize_async_url(url: str) -> str:
        """Convert a PostgreSQL URL to asyncpg-compatible format."""
        if not url:
            return url
        # Add +asyncpg driver if missing
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Strip query params that asyncpg doesn't support
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True) if parsed.query else {}
        unsupported = {"sslmode", "channel_binding"}
        filtered = {k: v for k, v in params.items() if k not in unsupported}
        # Add ssl=require for remote hosts (asyncpg equivalent of sslmode=require)
        is_remote = parsed.hostname and parsed.hostname not in ("localhost", "127.0.0.1", "::1")
        if is_remote and "ssl" not in filtered:
            filtered["ssl"] = ["require"]
        new_query = urlencode(filtered, doseq=True) if filtered else ""
        url = urlunparse(parsed._replace(query=new_query))
        return url

    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for Alembic migrations.

        Converts asyncpg URL to psycopg2: swaps driver, replaces ssl=require
        with sslmode=require (psycopg2 doesn't support the ssl param).
        """
        url = self.database_url.replace("+asyncpg", "+psycopg2")
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True) if parsed.query else {}
        # Remove asyncpg-specific ssl param
        params.pop("ssl", None)
        is_remote = parsed.hostname and parsed.hostname not in ("localhost", "127.0.0.1", "::1")
        if is_remote and "sslmode" not in params:
            params["sslmode"] = ["require"]
        new_query = urlencode(params, doseq=True) if params else ""
        return urlunparse(parsed._replace(query=new_query))

    # --- Redis ---
    redis_url: str = "redis://localhost:6379"

    # --- Security ---
    secret_key: str = ""  # Set in .env - used for general encryption/signing

    # --- JWT ---
    jwt_secret: str = ""  # Set in .env - used for JWT token signing
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    jwt_cookie_secure: bool = False  # True in production (HTTPS)
    jwt_cookie_samesite: str = "lax"
    jwt_cookie_domain: str = ""  # e.g. ".fenloai.com" to share cookie across subdomains

    # --- Environment ---
    environment: str = "development"  # development, staging, production

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"
    cors_widget_origins: str = "*"

    # --- URLs ---
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # --- Rate Limiting ---
    api_rate_limit: int = 100  # requests per minute per workspace

    # --- Logging ---
    log_format: str = "json"  # json or console
    log_level: str = "INFO"

    # --- App ---
    app_name: str = "BotForge"
    debug: bool = False

    # --- LLM Providers (Phase 1) ---
    groq_api_key: str = ""  # Primary: Groq Llama 3.3 70B (free) - Set in .env
    openai_api_key: str = ""  # Fallback: OpenAI GPT-4o-mini - Set in .env

    # --- Sentry (0.S2) ---
    sentry_dsn: str = ""  # Set in production for error tracking
    sentry_environment: str = "development"  # development, staging, production
    sentry_traces_sample_rate: float = 0.1  # 10% of transactions
    sentry_enabled: bool = False  # Explicitly enable in production

    # --- RAG / Pinecone (Phase 2) ---
    pinecone_api_key: str = ""  # Set in .env for vector storage
    pinecone_environment: str = "us-east-1"  # Pinecone region
    pinecone_index_name: str = "botforge-rag"  # Pinecone index name

    # --- File Storage / AWS S3 (Phase 2) ---
    file_storage_backend: str = "local"  # "local" for dev, "s3" for production
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "botforge-uploads"
    s3_use_instance_role: bool = True  # Use EC2 IAM role (no keys needed)
    aws_access_key_id: str = ""  # Only if not using instance role
    aws_secret_access_key: str = ""

    # --- Voice / Vapi (Phase 3) ---
    vapi_private_key: str = ""  # Vapi private API key - Set in .env
    vapi_public_key: str = ""  # Vapi public key for web SDK - Set in .env
    vapi_webhook_secret: str = ""  # HMAC secret for webhook signature validation
    voice_enabled: bool = False  # Global voice feature flag
    voice_max_concurrent: int = 3  # Max concurrent voice calls (memory budget)

    # --- WhatsApp / Twilio (Phase 4) ---
    twilio_account_sid: str = ""  # Twilio Account SID - Set in .env
    twilio_auth_token: str = ""  # Twilio Auth Token - Set in .env
    twilio_sandbox_phone: str = ""  # Twilio sandbox WhatsApp number (e.g., "+14155238886")
    whatsapp_enabled: bool = False  # Global WhatsApp feature flag

    # --- WhatsApp / Meta Cloud API (Phase 4) ---
    meta_whatsapp_access_token: str = ""  # Meta WhatsApp Cloud API access token
    meta_whatsapp_phone_number_id: str = ""  # Meta phone number ID
    meta_whatsapp_app_secret: str = ""  # Meta app secret for webhook signature validation
    meta_whatsapp_verify_token: str = ""  # Webhook verification token
    meta_whatsapp_api_version: str = "v21.0"  # Graph API version

    # --- Webhooks (Phase 4) ---
    webhook_connect_timeout: int = 5  # seconds — TCP connection timeout
    webhook_read_timeout: int = 10  # seconds — response read timeout
    webhook_max_retries: int = 3  # Max delivery attempts before dead letter
    webhook_retry_backoff: int = 60  # Base backoff in seconds (exponential: 60s, 300s, 900s)

    # --- Insights (Phase 5) ---
    insights_validate_recommendations: bool = True  # LLM self-critique on recommendations
    insights_cache_ttl: int = 3600  # 1 hour cache for weekly insights

    # --- GDPR / Data Lifecycle ---
    retention_days: int = 90  # Default conversation retention period
    auto_archive_enabled: bool = True
    storage_limit_mb: int = 1000  # Per-workspace storage limit

    # --- Arize AX Observability (Phase 9) ---
    arize_space_id: str = ""  # Arize Space ID - from app.arize.com
    arize_api_key: str = ""  # Arize API Key - from app.arize.com
    arize_project_name: str = "fenlo-ai"  # Arize project name

    # --- Feature Flags ---
    registration_enabled: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_cookie_samesite(self) -> str:
        """Auto-detect SameSite policy based on deployment topology.

        Cross-origin (frontend != backend domain): SameSite=None required
        Same-origin (AWS nginx, both on same domain): SameSite=Lax (more secure)
        """
        if self.jwt_cookie_samesite != "lax":
            return self.jwt_cookie_samesite
        from urllib.parse import urlparse

        fe = urlparse(self.frontend_url).hostname or ""
        be = urlparse(self.backend_url).hostname or ""
        if fe and be and fe != be:
            return "none"
        return "lax"

    @property
    def effective_cookie_secure(self) -> bool:
        """Auto-detect Secure flag for cookies.

        SameSite=None requires Secure=True. Also enabled when backend
        is served over HTTPS.
        """
        if self.jwt_cookie_secure:
            return True
        if self.effective_cookie_samesite == "none":
            return True
        return self.backend_url.startswith("https://")


settings = Settings()

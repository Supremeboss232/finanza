from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Override option to use local SQLite database instead of remote Supabase/PostgreSQL
    USE_LOCAL_DB: str = "false"

    # For async postgres with SSH tunnel:
    # RDS is not publicly accessible, must tunnel through EC2 bastion
    # Connection: local 127.0.0.1:5432 -> tunneled -> RDS:5432
    # RDS Instance: database-1.cf2w2gwcmvc8.eu-north-1.rds.amazonaws.com
    # Database: Finanza | Master user: postgres
    DATABASE_URL: str = "postgresql+asyncpg://postgres:Supposedbe5@127.0.0.1:5432/Finanza"
    ALEMBIC_DATABASE_URL: Optional[str] = None
    ADMIN_EMAIL: str = "admin@admin.com"
    ADMIN_PASSWORD: str = "admin123"
    SECRET_KEY: str = "Supremeboss232"  # Change this in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AWS SES Configuration
    AWS_REGION: str = "eu-north-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    SES_SENDER_EMAIL: str = "noreply@finanzabank.com"
    SES_SENDER_NAME: str = "Finanza Bank"
    
    # Email config (Gmail SMTP)
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: str = "noreply@finanzabank.com"
    MAIL_FROM_NAME: str = "Finanza Bank"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    EMAIL_PROVIDER: str = "gmail"
    
    # Admin Notification SMTP Configuration (separate for admin notifications)
    SMTP_SERVER: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SENDER_EMAIL: Optional[str] = "noreply@finanzabank.com"
    SENDER_PASSWORD: Optional[str] = None  # Set via environment variable
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    
    # Email Notification Settings
    NOTIFICATIONS_ENABLED: bool = True
    NOTIFICATION_RETRY_COUNT: int = 3
    NOTIFICATION_RETRY_DELAY: int = 5  # seconds
    
    # Mailtrap Configuration (for email testing/development)
    MAILTRAP_TOKEN: Optional[str] = None
    MAILTRAP_FROM_EMAIL: str = "hello@demomailtrap.co"
    MAILTRAP_FROM_NAME: str = "Finanza Bank"
    
    # ==================== RATE LIMITING CONFIGURATION ====================
    # Rate limiter can use: "memory" (in-process), "redis", or "database"
    RATE_LIMITER_BACKEND: str = "memory"  # memory, redis, or database
    RATE_LIMIT_CLEANUP_INTERVAL: int = 300  # seconds - cleanup old entries
    
    # Default rate limits (requests per minute)
    RATE_LIMIT_ADMIN_ENDPOINTS_PER_MIN: int = 30
    RATE_LIMIT_ADMIN_ENDPOINTS_PER_HOUR: int = 500
    RATE_LIMIT_API_ENDPOINTS_PER_MIN: int = 60
    RATE_LIMIT_API_ENDPOINTS_PER_HOUR: int = 1000
    RATE_LIMIT_AUTH_PER_MIN: int = 5
    RATE_LIMIT_AUTH_PER_HOUR: int = 50
    
    # ==================== APPROVAL WORKFLOW CONFIGURATION ====================
    # Multi-admin approval settings
    APPROVAL_ENABLED: bool = True
    APPROVALS_REQUIRED_FOR_HIGH_VALUE: int = 2  # Number of approvals needed
    APPROVAL_THRESHOLD_BALANCE_ADJUSTMENT: float = 10000.0  # Amount in USD
    APPROVAL_THRESHOLD_ADMIN_CREATION: bool = True  # Always require approval
    APPROVAL_THRESHOLD_ADMIN_REVOCATION: bool = True  # Always require approval
    APPROVAL_EXPIRY_HOURS: int = 24  # Approval requests expire after this many hours
    APPROVAL_SELF_APPROVAL_PREVENTED: bool = True  # Admin cannot approve own requests
    
    # ==================== SCHEDULED ADJUSTMENTS CONFIGURATION ====================
    # Background worker settings for scheduled balance adjustments
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_CHECK_INTERVAL: int = 60  # seconds - how often to check for due adjustments
    SCHEDULER_MAX_RETRIES: int = 3
    SCHEDULER_RETRY_DELAY: int = 300  # seconds
    
    # SSH Tunnel Configuration (for accessing non-public RDS through EC2 bastion)
    # We no longer use SSH tunneling by default; prefer direct DB connections (Supabase)
    USE_SSH_TUNNEL: bool = False
    SSH_KEY_PATH: str = "Super.pem"
    SSH_HOST: str = "13.60.249.107"
    SSH_USER: str = "Administrator"
    RDS_REMOTE_HOST: str = "database-1.cf2w2gwcmvc8.eu-north-1.rds.amazonaws.com"
    RDS_REMOTE_PORT: int = 5432
    
    # Application Environment & API Configuration
    ENVIRONMENT: str = "development"  # development, staging, production
    API_URL: Optional[str] = None  # e.g., "https://api.finanza.example.com" for prod/staging
    FRONTEND_URL: Optional[str] = None  # e.g., "https://finanza.example.com" for CORS
    
    # Dynamic API configuration - used by frontend client
    # For development: uses http://localhost:8000
    # For staging: uses APP_RUNNER_URL or settings.API_URL
    # For production: uses settings.API_URL or https://api.example.com
    
    # ==================== WEBHOOK SECRETS ====================
    # Stripe webhook: https://dashboard.stripe.com/webhooks
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Paystack webhook: https://dashboard.paystack.com/#/webhooks
    PAYSTACK_WEBHOOK_SECRET: Optional[str] = None
    
    # KYC provider (Jumio, Onfido, IDology) - you configure in their dashboard
    KYC_WEBHOOK_SECRET: str = "your-kyc-webhook-secret-change-in-env"
    
    # AWS SNS/SES: Use SNS topic ARN for verification
    SES_SNS_WEBHOOK_SECRET: Optional[str] = None
    
    # ==================== PRICE FEEDS ====================
    # Fixer.io API key for forex rates
    FIXER_IO_API_KEY: Optional[str] = None
    
    # Binance API (public data streams don't need a key)
    BINANCE_WEBSOCKET_URL: str = "wss://stream.binance.us:9443/stream"
    
    # Redis for price caching & real-time updates
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_KEY_PREFIX: str = "finanza:"
    
    # ==================== AWS INFRASTRUCTURE ====================
    # SNS topic for notifications
    SNS_TOPIC_ARN: Optional[str] = None
    
    # Lambda function names (for EventBridge integration)
    LAMBDA_KYC_PROCESSOR: Optional[str] = None
    LAMBDA_FRAUD_DETECTOR: Optional[str] = None
    LAMBDA_SETTLEMENT_PROCESSOR: Optional[str] = None
    
    # EventBridge rule names
    EVENTBRIDGE_PAYMENT_RULE: Optional[str] = None
    EVENTBRIDGE_KYC_RULE: Optional[str] = None
    
    # ElastiCache (if using managed Redis)
    ELASTICACHE_ENDPOINT: Optional[str] = None
    ELASTICACHE_PORT: int = 6379
    
    # ==================== PAYRAIL CONFIGURATION ====================
    PAYRAIL_API_URL: str = "https://payrail-rbb59a.fly.dev"
    PAYRAIL_API_KEY: str = ""  # Set via PAYRAIL_API_KEY env var in production

    # ==================== SUPABASE CONFIGURATION ====================
    # Supabase cloud PostgreSQL database (alternative to direct PostgreSQL)
    # If you provide SUPABASE_DB_URL it will be used as the primary DATABASE_URL
    SUPABASE_DB_URL: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    SUPABASE_SECRET_KEY: Optional[str] = None
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None
    # Common Postgres connection strings (allow legacy env names)
    POSTGRES_URL_NON_POOLING: Optional[str] = None
    POSTGRES_URL: Optional[str] = None
    POSTGRES_PRISMA_URL: Optional[str] = None
    # Optional custom certificate authority for SSL connections
    DB_SSL_CA_CERT: Optional[str] = None

    @model_validator(mode='after')
    def normalize_database_urls(self) -> 'Settings':
        import os
        if os.environ.get("USE_LOCAL_DB") == "true" or getattr(self, "USE_LOCAL_DB", "false") == "true":
            self.DATABASE_URL = "sqlite+aiosqlite:///finanza.db"
            self.ALEMBIC_DATABASE_URL = "sqlite:///finanza.db"
            return self

        # For Supabase: prefer POSTGRES_URL_NON_POOLING (pooler on port 5432)
        # since direct connections to db.*.supabase.co often fail with DNS on some networks
        # Only use DATABASE_URL if no pooler URL is available
        
        if not getattr(self, 'SUPABASE_DB_URL', None):
            for candidate in (getattr(self, 'POSTGRES_URL_NON_POOLING', None), getattr(self, 'POSTGRES_URL', None), getattr(self, 'POSTGRES_PRISMA_URL', None)):
                if candidate:
                    self.SUPABASE_DB_URL = candidate
                    break

        if getattr(self, 'SUPABASE_DB_URL', None):
            self.DATABASE_URL = self.SUPABASE_DB_URL

        if self.DATABASE_URL:
            # Allow .env to keep a plain PostgreSQL URL while the app uses an async driver.
            if self.DATABASE_URL.startswith("postgres://"):
                self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
            elif self.DATABASE_URL.startswith("postgresql://"):
                self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

        if self.DATABASE_URL and not self.ALEMBIC_DATABASE_URL:
            self.ALEMBIC_DATABASE_URL = self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1).replace("?ssl=disable", "")

        return self

settings = Settings()

# Export key settings at module level for legacy import paths
DATABASE_URL = settings.DATABASE_URL
ALEMBIC_DATABASE_URL = settings.ALEMBIC_DATABASE_URL
ADMIN_EMAIL = settings.ADMIN_EMAIL
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
AWS_REGION = settings.AWS_REGION
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
SES_SENDER_EMAIL = settings.SES_SENDER_EMAIL
SES_SENDER_NAME = settings.SES_SENDER_NAME
MAIL_USERNAME = settings.MAIL_USERNAME
MAIL_PASSWORD = settings.MAIL_PASSWORD
MAIL_FROM = settings.MAIL_FROM
MAIL_FROM_NAME = settings.MAIL_FROM_NAME
MAIL_PORT = settings.MAIL_PORT
MAIL_SERVER = settings.MAIL_SERVER
MAIL_STARTTLS = settings.MAIL_STARTTLS
MAIL_SSL_TLS = settings.MAIL_SSL_TLS
EMAIL_PROVIDER = settings.EMAIL_PROVIDER
MAILTRAP_TOKEN = settings.MAILTRAP_TOKEN
MAILTRAP_FROM_EMAIL = settings.MAILTRAP_FROM_EMAIL
MAILTRAP_FROM_NAME = settings.MAILTRAP_FROM_NAME
USE_SSH_TUNNEL = settings.USE_SSH_TUNNEL
SSH_KEY_PATH = settings.SSH_KEY_PATH
SSH_HOST = settings.SSH_HOST
SSH_USER = settings.SSH_USER
RDS_REMOTE_HOST = settings.RDS_REMOTE_HOST
RDS_REMOTE_PORT = settings.RDS_REMOTE_PORT
ENVIRONMENT = settings.ENVIRONMENT
API_URL = settings.API_URL
FRONTEND_URL = settings.FRONTEND_URL
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET
PAYSTACK_WEBHOOK_SECRET = settings.PAYSTACK_WEBHOOK_SECRET
KYC_WEBHOOK_SECRET = settings.KYC_WEBHOOK_SECRET
SES_SNS_WEBHOOK_SECRET = settings.SES_SNS_WEBHOOK_SECRET
FIXER_IO_API_KEY = settings.FIXER_IO_API_KEY
BINANCE_WEBSOCKET_URL = settings.BINANCE_WEBSOCKET_URL
REDIS_URL = settings.REDIS_URL
REDIS_KEY_PREFIX = settings.REDIS_KEY_PREFIX
SNS_TOPIC_ARN = settings.SNS_TOPIC_ARN
LAMBDA_KYC_PROCESSOR = settings.LAMBDA_KYC_PROCESSOR
LAMBDA_FRAUD_DETECTOR = settings.LAMBDA_FRAUD_DETECTOR
LAMBDA_SETTLEMENT_PROCESSOR = settings.LAMBDA_SETTLEMENT_PROCESSOR
EVENTBRIDGE_PAYMENT_RULE = settings.EVENTBRIDGE_PAYMENT_RULE
EVENTBRIDGE_KYC_RULE = settings.EVENTBRIDGE_KYC_RULE
ELASTICACHE_ENDPOINT = settings.ELASTICACHE_ENDPOINT
ELASTICACHE_PORT = settings.ELASTICACHE_PORT
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_DB_URL = settings.SUPABASE_DB_URL
SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY = settings.SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET = settings.SUPABASE_JWT_SECRET
SUPABASE_SECRET_KEY = settings.SUPABASE_SECRET_KEY
SUPABASE_PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
DB_SSL_CA_CERT = settings.DB_SSL_CA_CERT

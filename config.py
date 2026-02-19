from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # For async postgres with SSL:
    # "postgresql+asyncpg://user:password@host:port/dbname?ssl=require"
    # RDS Cluster: arn:aws:rds:eu-north-1:714509060208:cluster:finanza-bank
    # Using SSH tunnel through bastion host for secure access to RDS
    DATABASE_URL: str = "postgresql+asyncpg://finbank:Supposedbe5@localhost:5432/postgres?ssl=require"
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
    
    # Legacy email config (if using FastMail instead of SES)
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: str = "noreply@finanzabank.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    
    # SSH Tunnel Configuration (for local development)
    USE_SSH_TUNNEL: bool = False
    SSH_KEY_PATH: str = "BankingBackendKey.pem"
    SSH_HOST: str = "51.20.190.13"
    SSH_USER: str = "ec2-user"
    RDS_REMOTE_HOST: str = "finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com"
    RDS_REMOTE_PORT: int = 5432

    @model_validator(mode='after')
    def set_alembic_database_url(self) -> 'Settings':
        if self.DATABASE_URL and not self.ALEMBIC_DATABASE_URL:
            self.ALEMBIC_DATABASE_URL = self.DATABASE_URL.replace("postgresql+asyncpg", "postgresql").replace("?ssl=disable", "")
        return self

settings = Settings()
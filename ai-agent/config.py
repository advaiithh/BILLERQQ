"""
Central configuration file for environment variables and default values.
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# --- Database ---
DB_HOST = os.getenv("DB_HOST", "srv1145.hstgr.io")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "u167254999_bqcustomerai")
DB_PASSWORD = os.getenv("DB_PASSWORD", "4U;iQ:3PG^v")
DB_NAME = os.getenv("DB_NAME", "u167254999_BqCustomerAi")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# --- Response/cost controls ---
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "16"))

# --- Model provider switch ---
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "bedrock")

# --- AWS Bedrock (Claude 3 Haiku) ---
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

# --- Auth (JWT) ---
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

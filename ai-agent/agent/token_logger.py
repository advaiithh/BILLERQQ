import os
import json
import logging
from datetime import datetime

# Ensure logs directory exists
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

log_file = os.path.join(LOGS_DIR, "token_usage.log")

# Setup dedicated token logger
logger = logging.getLogger("token_usage")
logger.setLevel(logging.INFO)
# Clear handlers to avoid duplicate configuration on hot reload
if logger.handlers:
    logger.handlers.clear()

file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(file_handler)

def log_llm_usage(
    stage: str,
    company_id: str | None,
    user_id: str | None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    model: str | None = None,
):
    """Log LLM token usage stats in a JSON format to logs/token_usage.log."""
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "stage": stage,
        "company_id": company_id,
        "user_id": user_id,
        "model": model or "claude-haiku",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    logger.info(json.dumps(log_data))

"""
Authentication and token resolution layer.
"""
import hashlib
import logging
from jose import jwt
from config import JWT_SECRET, JWT_ALGORITHM
from database import run_query

logger = logging.getLogger("billerq-auth-db")

def resolve_user_from_token(token: str) -> dict:
    """
    Decodes the Bearer token (either JWT or Sanctum database token format).
    Returns a dict with 'user_id', 'company_id', and 'role' if valid, else None.
    """
    if not token:
        return None
        
    token = token.removeprefix("Bearer ").strip()
    
    # 1. Try to decode as JWT first
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id") or payload.get("sub")
        company_id = payload.get("company_id")
        role = payload.get("role", "staff")
        if user_id and company_id:
            logger.info("Token successfully decoded via JWT. user_id=%s, company_id=%s", user_id, company_id)
            return {
                "user_id": int(user_id),
                "company_id": int(company_id),
                "role": role
            }
    except Exception:
        # Not a JWT or signature verification failed, proceed to DB token check
        pass
        
    # 2. Try looking up in personal_access_tokens table (Sanctum)
    try:
        token_id = None
        token_plain = token
        
        # Laravel Sanctum tokens are structured as "id|plain_text_token"
        if "|" in token:
            token_id_str, token_plain = token.split("|", 1)
            try:
                token_id = int(token_id_str)
            except ValueError:
                token_id = None
                token_plain = token
                
        # Sanctum stores the SHA-256 hash of the plain-text token
        token_hash = hashlib.sha256(token_plain.encode()).hexdigest()
        
        rows = []
        if token_id:
            # Query by token ID
            rows = run_query(
                "SELECT tokenable_id, token FROM personal_access_tokens WHERE id = :id",
                {"id": token_id}
            )
        else:
            # Search by token hash
            rows = run_query(
                "SELECT tokenable_id, token FROM personal_access_tokens WHERE token = :token",
                {"token": token_hash}
            )
            if not rows:
                # Fallback to direct token comparison (in case stored unhashed)
                rows = run_query(
                    "SELECT tokenable_id, token FROM personal_access_tokens WHERE token = :token",
                    {"token": token_plain}
                )
                
        if rows:
            record = rows[0]
            user_id = record.get("tokenable_id")
            if user_id:
                # Query users table to get company_id and role
                user_rows = run_query(
                    "SELECT id, company_id, role_id FROM users WHERE id = :user_id",
                    {"user_id": user_id}
                )
                if user_rows:
                    user_record = user_rows[0]
                    company_id = user_record.get("company_id")
                    
                    # Resolve role name from roles table if role_id is present
                    role_name = "staff"
                    role_id = user_record.get("role_id")
                    if role_id:
                        role_rows = run_query(
                            "SELECT name FROM roles WHERE id = :role_id",
                            {"role_id": role_id}
                        )
                        if role_rows:
                            role_name = role_rows[0].get("name", "staff")
                            
                    logger.info("Token successfully resolved via database lookup. user_id=%s, company_id=%s", user_id, company_id)
                    return {
                        "user_id": int(user_id),
                        "company_id": int(company_id),
                        "role": role_name
                    }
    except Exception as e:
        logger.error("Database-based token resolution failed: %s", e)
        
    return None

import os
import json
import logging
import importlib

logger = logging.getLogger(__name__)

LEARNED_ROUTES_PATH = r"c:\Users\advai\Desktop\BILLERQQ\ai-agent\agent\learned_routes.py"

def save_learned_route(query: str, route: dict):
    """Saves a successfully resolved query mapping back to the learned_routes.py module."""
    q_clean = query.strip().lower()
    
    # 1. Read existing dictionary
    routes = {}
    if os.path.exists(LEARNED_ROUTES_PATH):
        try:
            # We import and force reload to always get the latest state
            import agent.learned_routes
            importlib.reload(agent.learned_routes)
            routes = dict(agent.learned_routes.LEARNED_ROUTES)
        except Exception as e:
            logger.warning("Could not load current LEARNED_ROUTES, resetting: %s", str(e))
            
    # 2. Add/update route mapping
    routes[q_clean] = route
    
    # 3. Write back module structure
    try:
        json_str = json.dumps(routes, indent=4)
        python_str = json_str.replace("null", "None").replace("true", "True").replace("false", "False")
        content = (
            "# Dynamic learned routes mapping user queries to tool configurations\n"
            f"LEARNED_ROUTES = {python_str}\n"
        )
        with open(LEARNED_ROUTES_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("🧠 Saved dynamically learned route mapping for query '%s' to learned_routes.py", q_clean)
        
        # Reload after saving so that any subsequent import in the same lifecycle picks it up
        try:
            import agent.learned_routes
            importlib.reload(agent.learned_routes)
        except Exception:
            pass
    except Exception as e:
        logger.error("Failed to save route to learned_routes.py: %s", str(e))

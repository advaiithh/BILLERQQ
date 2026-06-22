"""
BillerQ AI Assistant — FastAPI Application Entry Point.

Orchestrates the full pipeline:
    User Message → Memory → Planner → Resolver → Executor → Formatter → Response
"""

import os
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agent.planner import Planner
from agent.executor import Executor
from agent.formatter import Formatter
from agent.memory import memory_manager
from api.client import api_client

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("billerq-ai")


# ---------------------------------------------------------------------------
# LLM Provider Setup
# ---------------------------------------------------------------------------
def _create_llm():
    """Create the LLM provider based on .env config."""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "ollama":
        from llm.ollama_provider import OllamaProvider

        model = os.getenv("OLLAMA_MODEL", "qwen3")
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        logger.info("Using Ollama provider: model=%s, host=%s", model, host)
        return OllamaProvider(model=model, host=host)

    elif provider == "bedrock":
        from llm.bedrock_provider import BedrockProvider

        logger.info("Using Bedrock provider")
        return BedrockProvider()

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use 'ollama' or 'bedrock'.")


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("🚀 BillerQ AI Assistant starting up...")
    yield
    logger.info("🛑 Shutting down — closing API client...")
    await api_client.close()


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="BillerQ AI Assistant",
    description="AI-powered subscription management assistant for BillerQ cable TV platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the BillerQ frontend and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
llm = _create_llm()
planner = Planner(llm)
executor = Executor()
formatter = Formatter(llm)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Session ID for conversation continuity",
    )
    billerq_token: str = Field(
        default="",
        description="Optional BillerQ bearer token from the logged-in frontend session",
    )


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI assistant's response")
    session_id: str = Field(..., description="Session ID for follow-up queries")
    metadata: dict = Field(default_factory=dict, description="Debug/info metadata")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "BillerQ AI Assistant",
        "active_sessions": memory_manager.active_sessions,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint — processes user messages through the AI pipeline.

    Pipeline:
        1. Load/create session memory
        2. Resolve pronouns using conversation context
        3. Plan: classify intent + extract entities via LLM
        4. Execute: call the appropriate BillerQ API(s)
        5. Format: convert raw data to human-friendly text
        6. Update memory with results
    """
    message = request.message.strip()
    session_id = request.session_id

    logger.info("Chat request: session=%s, message='%s'", session_id, message[:100])

    try:
        # Step 1: Load session memory
        memory = memory_manager.get_session(session_id)

        # Step 2: Resolve pronouns (his → Joy P's)
        resolved_message = memory.resolve_pronoun(message)
        if resolved_message != message:
            logger.info("Pronoun resolved: '%s' → '%s'", message, resolved_message)

        # Step 3: Plan — classify intent and extract entities
        context = memory.get_context()
        plan = await planner.plan(resolved_message, context)

        intent = plan.get("intent", "UNKNOWN")

        # Handle UNKNOWN intent
        if intent == "UNKNOWN":
            response_text = (
                "I'm not quite sure what you're asking. I can help you with:\n\n"
                "• Customer info — \"Show customer Joy P\"\n"
                "• Payment history — \"Show payment history of Joy P\"\n"
                "• Subscriptions — \"Show Joy P's subscription\"\n"
                "• Overdue payments — \"Who has overdue payments?\"\n"
                "• Reports — \"Show package report\"\n"
                "• Comparisons — \"Compare Joy P and Abhi\"\n"
                "• Analytics — \"How many active customers?\"\n\n"
                "Try asking one of these!"
            )
            memory.add_turn(message, response_text)
            return ChatResponse(
                response=response_text,
                session_id=session_id,
                metadata={"intent": "UNKNOWN", "plan": plan},
            )

        # Step 4: Execute — call the right API(s)
        result = await executor.execute(plan, memory, billerq_token=request.billerq_token)

        # Step 5: Format — make it human-readable
        if result.get("success"):
            response_text = await formatter.format_response(
                intent=intent,
                data=result.get("data", {}),
                original_message=message,
                customer_name=result.get("customer_name"),
            )

            # Update memory with the resolved customer
            if result.get("customer_id"):
                memory.update_customer(
                    result["customer_id"],
                    result["customer_name"],
                )
        else:
            # Format error response
            response_text = await formatter.format_error(
                error_message=result.get("error", "Something went wrong."),
                candidates=result.get("candidates"),
            )

        # Step 6: Update memory
        memory.update_intent(intent)
        memory.add_turn(message, response_text)

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            metadata={
                "intent": intent,
                "customer_id": result.get("customer_id"),
                "customer_name": result.get("customer_name"),
            },
        )

    except Exception as e:
        logger.exception("Unhandled error in chat pipeline")
        return ChatResponse(
            response="I ran into an unexpected issue. Please try again in a moment.",
            session_id=session_id,
            metadata={"error": str(e)},
        )


@app.get("/widget")
async def serve_widget():
    """Serve the chat widget HTML file."""
    widget_path = os.path.join(
        os.path.dirname(__file__), "chat-widget", "chat.html"
    )
    if os.path.exists(widget_path):
        return FileResponse(widget_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="Chat widget not found")

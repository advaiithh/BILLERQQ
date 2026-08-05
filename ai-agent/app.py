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
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agent.planner import Planner
from agent.executor import Executor
from agent.formatter import Formatter
from agent.memory import memory_manager
from api.client import api_client
from agent.agent_loop import BillerQAgent


load_dotenv(override=True)

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
    """Create the AWS Bedrock LLM provider."""
    from llm.bedrock_provider import BedrockProvider
    logger.info("Using AWS Bedrock provider (Claude 3 Haiku / 4.5)")
    return BedrockProvider()


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
agent = BillerQAgent(llm)


def _resolve_redirection_metadata(message: str, response_text: str = "", tool_name: str = None) -> dict:
    """Determine the exact frontend route and button label for the user prompt or tool response."""
    msg_lower = (message or "").lower().strip()
    resp_lower = (response_text or "").lower().strip()
    combined = f"{msg_lower} {resp_lower}"

    if any(k in combined for k in ["package", "packages", "pkg"]):
        if "report" in msg_lower or "summary" in msg_lower:
            return {"redirect_url": "/report/package-summary", "redirect_label": "View Package Report"}
        return {"redirect_url": "/Services/package", "redirect_label": "View Packages"}

    if any(k in combined for k in ["stb", "stbs", "set top box", "modem", "modems"]):
        return {"redirect_url": "/customers/stb", "redirect_label": "View STBs"}

    if any(k in combined for k in ["addon", "addons", "add-on", "add-ons"]):
        if "report" in msg_lower or "summary" in msg_lower:
            return {"redirect_url": "/report/addon-summary", "redirect_label": "View Addon Report"}
        return {"redirect_url": "/Services/addon", "redirect_label": "View Addons"}

    if any(k in combined for k in ["item", "items", "service item", "products"]):
        return {"redirect_url": "/Services/item", "redirect_label": "View Items"}

    if any(k in combined for k in ["archived customer", "deleted customer", "archived", "customer-archive"]):
        return {"redirect_url": "/customers/customer-archive", "redirect_label": "View Archived Customers"}

    if any(k in combined for k in ["wallet", "wallets"]):
        if "report" in msg_lower or "balance" in msg_lower:
            return {"redirect_url": "/report/wallet-balance", "redirect_label": "View Wallet Report"}
        return {"redirect_url": "/customers/wallet", "redirect_label": "View Wallets"}

    if any(k in combined for k in ["unpaid", "unpaid customer", "unpaid customers"]):
        return {"redirect_url": "/report/unpaid-customer", "redirect_label": "View Unpaid Customers"}

    if any(k in combined for k in ["overdue", "payment due", "dues", "outstanding"]):
        return {"redirect_url": "/report/payment-due", "redirect_label": "View Overdue Payments"}

    if any(k in combined for k in ["collection", "collections", "collected", "payment collection"]):
        return {"redirect_url": "/report/payment-collection", "redirect_label": "View Payment Collections"}

    if any(k in combined for k in ["online payment", "online transaction"]):
        return {"redirect_url": "/report/online-payment", "redirect_label": "View Online Payments"}

    if any(k in combined for k in ["customer payment", "payment report", "payment history"]):
        return {"redirect_url": "/report/customer-payment", "redirect_label": "View Payment Report"}

    if any(k in combined for k in ["recurring", "recurring profile", "recurring profiles"]):
        return {"redirect_url": "/billing/recurring", "redirect_label": "View Recurring Profiles"}

    if any(k in combined for k in ["cancelled invoice", "cancelled order", "canceled invoice"]):
        return {"redirect_url": "/billing/cancelled-invoice", "redirect_label": "View Cancelled Invoices"}

    if any(k in combined for k in ["invoice", "invoices", "bill", "bills", "order", "orders"]):
        return {"redirect_url": "/billing/invoice", "redirect_label": "View Invoices"}

    if any(k in combined for k in ["subscription", "subscriptions"]):
        if "report" in msg_lower or "summary" in msg_lower or "expired" in msg_lower:
            return {"redirect_url": "/report/subscription-summary", "redirect_label": "View Subscription Report"}
        return {"redirect_url": "/billing/subscription", "redirect_label": "View Subscriptions"}

    if any(k in combined for k in ["complaint", "complaints", "ticket", "tickets", "problem type"]):
        return {"redirect_url": "/complaints", "redirect_label": "View Complaints"}

    if any(k in combined for k in ["enquiry", "enquiries"]):
        return {"redirect_url": "/lead-manage/enquiry", "redirect_label": "View Enquiries"}

    if any(k in combined for k in ["lead", "leads"]):
        return {"redirect_url": "/lead-manage/lead", "redirect_label": "View Leads"}

    if any(k in combined for k in ["follow up", "follow ups", "followup", "followups"]):
        return {"redirect_url": "/lead-manage/follow-up", "redirect_label": "View Follow-Ups"}

    if any(k in combined for k in ["income", "incomes"]):
        if "report" in msg_lower or "summary" in msg_lower:
            return {"redirect_url": "/report/income-summary", "redirect_label": "View Income Summary"}
        return {"redirect_url": "/expenses-income/income", "redirect_label": "View Income"}

    if any(k in combined for k in ["expense", "expenses"]):
        if "report" in msg_lower or "summary" in msg_lower:
            return {"redirect_url": "/report/expense-summary", "redirect_label": "View Expense Summary"}
        return {"redirect_url": "/expenses-income/expense", "redirect_label": "View Expenses"}

    if any(k in combined for k in ["header", "expense header"]):
        return {"redirect_url": "/expenses-income/header", "redirect_label": "View Headers"}

    if any(k in combined for k in ["vendor", "vendors"]):
        return {"redirect_url": "/expenses-income/vendor", "redirect_label": "View Vendors"}

    if any(k in combined for k in ["account", "bank account", "banking"]):
        return {"redirect_url": "/banking/account", "redirect_label": "View Bank Accounts"}

    if any(k in combined for k in ["transaction", "bank transaction"]):
        return {"redirect_url": "/banking/transaction", "redirect_label": "View Bank Transactions"}

    if any(k in combined for k in ["staff", "employee", "employees"]):
        return {"redirect_url": "/staff/staff", "redirect_label": "View Staff"}

    if any(k in combined for k in ["role", "roles"]):
        return {"redirect_url": "/staff/role", "redirect_label": "View Roles"}

    if any(k in combined for k in ["area", "areas"]):
        return {"redirect_url": "/settings/area", "redirect_label": "View Areas"}

    if any(k in combined for k in ["message credit", "sms credit", "whatsapp credit"]):
        return {"redirect_url": "/settings/message-credit", "redirect_label": "View Message Credits"}

    if any(k in combined for k in ["sms log", "sms logs"]):
        return {"redirect_url": "/report/sms-message-logs", "redirect_label": "View SMS Logs"}

    if any(k in combined for k in ["whatsapp log", "whatsapp logs"]):
        return {"redirect_url": "/report/whatsApp-message-logs", "redirect_label": "View WhatsApp Logs"}

    if any(k in combined for k in ["category", "categories"]):
        return {"redirect_url": "/settings/categories", "redirect_label": "View Categories"}

    if any(k in combined for k in ["tax class", "tax classes"]):
        return {"redirect_url": "/settings/tax-class", "redirect_label": "View Tax Classes"}

    if any(k in combined for k in ["cas provider", "isp provider", "provider", "providers"]):
        return {"redirect_url": "/settings/cas-isp-provider", "redirect_label": "View Providers"}

    if any(k in combined for k in ["customer", "customers", "client"]):
        return {"redirect_url": "/customers/customer", "redirect_label": "View Customers"}

    return {"redirect_url": "/dashboard/default", "redirect_label": "View Dashboard"}


def _build_redirect_metadata(intent: str, plan: dict, result: dict, customer_id: str | None):
    """Map intent/plan/result to a frontend route and label for quick navigation.

    Returns a dict with optional `redirect_url` and `redirect_label`.
    """
    if not intent:
        return {}

    # Normalize
    intent = intent.upper()

    # Reports mapping by report_type entity
    report_map = {
        "package": "/report/package-summary",
        "wallet": "/report/wallet-balance",
        "tax": "/report/tax-report",
    }

    # Intent -> route
    if intent == "ACTIVE_CUSTOMERS":
        return {"redirect_url": "/customers/customer", "redirect_label": "View customers"}
    if intent == "REPORT":
        report_type = (plan or {}).get("entities", {}).get("report_type")
        if report_type and report_type in report_map:
            return {"redirect_url": report_map[report_type], "redirect_label": "View report"}
        return {"redirect_url": "/report/package-summary", "redirect_label": "View report"}
    if intent == "UNPAID_CUSTOMERS":
        return {"redirect_url": "/report/unpaid-customer", "redirect_label": "View unpaid customers"}
    if intent == "OVERDUE":
        return {"redirect_url": "/report/payment-due", "redirect_label": "View overdue payments"}
    if intent == "ANALYTICS":
        return {"redirect_url": "/dashboard/default", "redirect_label": "Open analytics"}
    if intent in ("INVOICE_DETAIL", "INVOICE_SUMMARY"):
        invoice_id = (result or {}).get("invoice_id")
        if customer_id and invoice_id:
            return {
                "redirect_url": f"/customers/{customer_id}/invoices/{invoice_id}",
                "redirect_label": "View invoice",
            }

    return {}


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
    billerq_api_url: str = Field(
        default="",
        description="Optional BillerQ API URL from the logged-in frontend session",
    )
    billerq_user_role: int | None = Field(
        default=None,
        description="Optional BillerQ user role from the logged-in frontend session",
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


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root to the chat widget for convenience in local development."""
    return RedirectResponse(url="/widget")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint — processes user messages through the AI agent loop.

    Pipeline:
        1. Load/create session memory.
        2. Resolve pronouns using context.
        3. Check BillerQ auth.
        4. Run BillerQAgent to dynamically execute tool calls and generate final summary.
        5. Save state and return response.
    """
    message = request.message.strip()
    session_id = request.session_id

    # Log request parameters (safely log token prefix/suffix)
    token_log = "None"
    if request.billerq_token:
        token_log = f"{request.billerq_token[:10]}...{request.billerq_token[-10:]}" if len(request.billerq_token) > 20 else "short_token"
    logger.info("Chat request: session=%s, message='%s', api_url=%s, role=%s, token=%s", 
                session_id, message[:100], request.billerq_api_url, request.billerq_user_role, token_log)

    try:
        # Step 1: Load session memory
        memory = memory_manager.get_session(session_id)

        # Safety Check for illegal/malicious activities
        message_lower = message.lower()
        unsafe_keywords = [
            "drop table", "drop database", "delete database", "delete table",
            "hack", "crack password", "bypass admin", "bypass login", 
            "steal data", "steal customer", "forge invoice", "forge payment",
            "fake invoice", "fake payment", "illegal activity", "make illegal",
            "sql injection", "database injection"
        ]
        if any(kw in message_lower for kw in unsafe_keywords):
            response_text = "I cannot perform those actions. Please contact your BillerQ administrator or support for assistance."
            memory.add_turn(message, response_text)
            return ChatResponse(
                response=response_text,
                session_id=session_id,
                metadata={"safety_blocked": True}
            )

        # Step 2: Resolve pronouns (his → Joy P's)
        resolved_message = memory.resolve_pronoun(message)
        if resolved_message != message:
            logger.info("Pronoun resolved: '%s' → '%s'", message, resolved_message)

        # Prompt limit check per day (sliding 24-hour window)
        import time
        prompt_limit = int(os.getenv("PROMPT_LIMIT_PER_DAY", "0"))
        remaining_prompts = None
        if prompt_limit > 0:
            if not hasattr(memory, "prompt_timestamps"):
                memory.prompt_timestamps = []
            now = time.time()
            memory.prompt_timestamps = [t for t in memory.prompt_timestamps if now - t < 86400]
            if len(memory.prompt_timestamps) >= prompt_limit:
                response_text = f"You have reached your daily limit of {prompt_limit} prompts. Please try again later to save credits."
                memory.add_turn(message, response_text)
                return ChatResponse(
                    response=response_text,
                    session_id=session_id,
                    metadata={
                        "rate_limited": True,
                        "llm_provider": "bedrock",
                        "prompt_limit": prompt_limit,
                        "remaining_prompts": 0
                    }
                )
            memory.prompt_timestamps.append(now)
            remaining_prompts = max(0, prompt_limit - len(memory.prompt_timestamps))

        # Check BillerQ authorization token
        if not request.billerq_token and not api_client.auto_login:
            response_text = (
                "Please log in to BillerQ first. Use the login panel in the widget "
                "or send a valid frontend session token."
            )
            memory.add_turn(message, response_text)
            return ChatResponse(
                response=response_text,
                session_id=session_id,
                metadata={"error": "login_required"},
            )

        # Resolve company_id from bearer token (JWT or Laravel Sanctum)
        company_id = 1
        if request.billerq_token:
            try:
                from auth_db import resolve_user_from_token
                user_info = resolve_user_from_token(request.billerq_token)
                if user_info:
                    company_id = user_info.get("company_id", 1)
                    logger.info("Resolved company_id=%d from token", company_id)
            except Exception as auth_err:
                logger.warning("Could not resolve company_id from token: %s", auth_err)

        # ----------------------------------------------------------------
        # PRIMARY PATH: DB Agent
        # The DB agent handles ALL BillerQ questions — customer lookups,
        # payment history, wallet comparisons, year-over-year analytics,
        # anything. It uses get_schema + query_data to answer questions
        # that were never anticipated at design time.
        # ----------------------------------------------------------------
        response_text = None
        metadata = {}

        try:
            # Build conversation history for the DB agent
            history = []
            for turn in memory.get_context().get("history", []):
                if turn.get("user"):
                    history.append({"role": "user", "content": turn["user"]})
                if turn.get("assistant"):
                    history.append({"role": "assistant", "content": turn["assistant"]})
            history.append({"role": "user", "content": resolved_message})

            from agent.db_agent import run_agent as run_db_agent
            logger.info("Routing to DB agent (primary)")
            response_text, _ = run_db_agent(history, company_id=company_id)
            metadata = {"agent_type": "db_agent", "company_id": company_id}

        except Exception as db_err:
            # ----------------------------------------------------------------
            # FALLBACK: REST Agent
            # Only reached when the database is completely unreachable
            # (e.g. port-3306 firewall on a local machine).
            # ----------------------------------------------------------------
            logger.warning(
                "DB agent unavailable (%s). Falling back to REST agent.", db_err
            )
            try:
                context = memory.get_context()
                response_text, metadata = await agent.run(
                    message=resolved_message,
                    context=context,
                    billerq_token=request.billerq_token,
                    billerq_api_url=request.billerq_api_url,
                    billerq_user_role=request.billerq_user_role,
                )
                metadata["agent_type"] = "rest_agent"
            except Exception as rest_err:
                logger.exception("REST agent also failed")
                response_text = "I'm having trouble reaching the data right now. Please try again in a moment."
                metadata = {"agent_type": "error", "error": str(rest_err)}

        metadata["llm_provider"] = "bedrock"
        if prompt_limit > 0:
            metadata["prompt_limit"] = prompt_limit
            metadata["remaining_prompts"] = remaining_prompts

        # Resolve accurate redirection link if missing or defaulting to home page
        if not metadata.get("redirect_url") or metadata.get("redirect_url") == "/dashboard/default":
            redir = _resolve_redirection_metadata(resolved_message, response_text, tool_name=metadata.get("tool"))
            if redir.get("redirect_url"):
                metadata.update(redir)

        # Step 3: Update session memory with details resolved by agent
        if metadata.get("customer_id") and metadata.get("customer_name"):
            memory.update_customer(
                metadata["customer_id"],
                metadata["customer_name"],
            )

        # Save turn to conversation memory
        memory.add_turn(message, response_text)

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            metadata=metadata,
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


class LoginRequest(BaseModel):
    email: str = Field(..., description="BillerQ login email")
    password: str = Field(..., description="BillerQ login password")


class LoginResponse(BaseModel):
    token: str = Field(..., description="BillerQ bearer token")
    message: str = Field(..., description="Login status message")


@app.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    """Manual login endpoint for BillerQ credentials."""
    try:
        token = await api_client.login(payload.email, payload.password)
        return LoginResponse(
            token=token,
            message="Login successful. Use this token for subsequent /chat requests.",
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

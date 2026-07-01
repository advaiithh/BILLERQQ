# BillerQ AI Assistant — Architecture & Execution Flow Documentation

This document explains the internal architecture, design patterns, file layouts, and end-to-end execution flow of the BillerQ AI chatbot system. It serves as a comprehensive technical guide for developers and system operators.

---

## 1. Directory Structure & Key Files

The codebase is organized into modular layers handling server communications, decision-making, entity resolution, database requests, and text formatting.

```
ai-agent/
├── app.py                      # fastapi server entrypoint
├── requirements.txt            # python dependencies
├── .env                        # environment variables (OLLAMA_MODEL, host, etc.)
├── agent/
│   ├── agent_loop.py           # orchestration loop, tool dispatcher, rules formatter
│   ├── planner.py              # intent parser and entity extractor (Planner LLM)
│   ├── resolver.py             # maps text queries (names/IDs) to database records
│   └── formatter.py            # LLM-based message generator and data truncator
├── tools/                      # API modules querying the BillerQ backend
│   ├── customer.py
│   ├── payment.py
│   ├── subscription.py
│   ├── complaints.py
│   ├── lead.py
│   ├── banking.py
│   ├── expenses_income.py
│   └── reports.py
├── api/
│   └── client.py               # http wrapper configured for Laravel API endpoints
└── llm/
    └── ollama_provider.py      # interface wrapper for the local Ollama LLM service
```

---

## 2. Global Execution Workflow

```
[ User Prompt ]
       │
       ▼
1. FastAPI Server (app.py) ──► Receives HTTP POST Request
       │
       ▼
2. Agent Loop (agent_loop.py)
       │
       ▼
3. Intent Planner (planner.py) ──► Query parsed by LLM/Regex to identify tool & filters
       │
       ▼
4. Entity Resolver (resolver.py) ──► Looks up customer name, package, addon, or item IDs
       │
       ▼
5. Tool Execution (tools/*) ──► Queries Laravel PHP backend database via API Client
       │
       ▼
6. Response Formatter (agent_loop.py) ──► Safely extracts total counts & builds user message
       │
       ▼
7. Redirect Metadata Builder ──► Maps query to correct capitalized frontend route
       │
       ▼
[ JSON Output with text & redirect_url ]
```

---

## 3. Detailed Component Breakdown

### A. FastAPI Server (`app.py`)
*   **Role**: Host API endpoints for the React frontend chat widget.
*   **Key Endpoint**: `POST /api/chat`
*   **Input Schema**:
    ```json
    {
      "message": "Show all open complaints",
      "context": {
        "history": [ ... ],
        "last_customer_id": 44350
      }
    }
    ```
*   **Header Handling**: Extracts Authorization headers (`billerq-token`, `billerq-api-url`, and `billerq-user-role`) and overrides the API client instance context dynamically for multi-tenant requests.

### B. Intent Planner (`agent/planner.py`)
*   **Role**: Decides *which action* the user wants to take.
*   **Execution Paths**:
    1.  **Fast Rule Matcher**: Checks regular expressions for common tasks (e.g., `"total customers"`, `"open complaints"`, `"this month collection"`) to bypass LLM latency.
    2.  **LLM Planner**: If regex match fails, constructs a system prompt list of all available BillerQ tool functions. The local LLM outputs a structured JSON block containing the selected `tool` name and extracted parameter arguments.

### C. Entity Resolver (`agent/resolver.py` & Fallbacks)
*   **Role**: Translates language inputs into exact primary keys.
*   **Customer Lookup**: Runs a query matching names, emails, or subscriber IDs to resolved database IDs.
*   **Dynamic Product Fallbacks**: If name lookup fails, it loops through:
    *   **Packages** (`get_packages` / `view_package` endpoint)
    *   **Add-ons** (`get_all_addons` / `show_addon` endpoint)
    *   **Items** (`get_items` / `show_item` endpoint)
    It checks both exact and fuzzy matches for titles and names, formatting matching specifications directly (price, duration, connection type) and redirecting users to the relevant catalog section.

### D. API Client (`api/client.py`)
*   **Role**: Wrapper for `httpx.AsyncClient` that configures host URLs, authorization tokens, company tenant headers, and handles connection timeouts or error catching.

### E. List Formatter & Safety System (`agent/agent_loop.py`)
*   **Role**: Generates the final output response.
*   **Pagination Shielding**: Because the server paginates list responses (e.g., returning 5 items per page), this module reads the database count parameter (`total`) directly from the pagination headers. Applying status filter keywords locally (like `"open"` complaints) preserves the true total counts in the message template rather than overriding it with the screen list length.
*   **Text Truncation**: Prunes nested JSON dictionaries to prevent payload inflation or context window overflows before passing context to the formatting LLM.

### F. Frontend Redirect Builder
*   **Role**: Attaches redirect metadata block to the HTTP response.
*   **Casing Matching**: Maps backend tool definitions to capitalization-sensitive routes used in React Router:
    *   `get_complaints` ──► `/complaints`
    *   `get_packages` ──► `/Services/packages`
    *   `get_addon` ──► `/Services/addon`
    *   `get_connection_data` (collection search) ──► `/report/payment-collection`

---

## 4. Environment Configuration (`.env`)
```ini
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
DEMO_MODE=false
LOG_LEVEL=INFO
```
What the Documentation Explains:
Directory Layout: Where all orchestration, planners, resolvers, api-clients, and individual tools reside.
Visual Flow Diagram: A step-by-step flowchart tracking a user query (like "Show all open complaints") from raw text input to UI button display.
Core Components:
FastAPI Server (app.py): Intercepting incoming headers (billerq-token, billerq-api-url) for safe multi-tenant company requests.
Intent Planner (agent/planner.py): Regex filters bypassing LLM latency, fallbacks, and parameter extraction.
Entity Resolver (agent/resolver.py): Resolving subscriber IDs, names, and smart fallback queries (checking catalog items when customer matches fail).
Pagination Shields (agent/agent_loop.py): How it preserves server database pagination metadata instead of overriding list counts locally.
Frontend Redirect Builder: Mapping tools to exact capitalization-sensitive routes (/Services/packages, /Services/addon, /Services/item, etc.).S
# BillerQ AI Assistant

BillerQ AI Assistant is an intelligent, multi-agent query and analytics system designed for the BillerQ cable TV subscription management platform. It allows admins to interact with system statistics, customer profiles, payment logs, subscriptions, set-top boxes, and complaints using natural language.

The application utilizes a local Large Language Model (LLM) for intent planning and output formatting, while dynamically interfacing with live, tenant-specific BillerQ API endpoints.

---

## Table of Contents
1. [End-to-End Architecture](#1-end-to-end-architecture)
2. [Directory and Code Breakdown](#2-directory-and-code-breakdown)
   - [Core Agent Logic](#core-agent-logic)
   - [API Integration layer](#api-integration-layer)
   - [Natural Language Tools](#natural-language-tools)
   - [UI Integration](#ui-integration)
3. [API Fetching and Authentication Flow](#3-api-fetching-and-authentication-flow)
   - [Dynamic Login & Tenant Redirection](#dynamic-login--tenant-redirection)
   - [401 Token Refresh & Retries](#401-token-refresh--retries)
   - [Frontend Token Passing & Decryption](#frontend-token-passing--decryption)
4. [How Data Truncation and Resolution Were Fixed](#4-how-data-truncation-and-resolution-were-fixed)
5. [Running Locally](#5-running-locally)

---

## 1. End-to-End Architecture

Every request sent by a user goes through a unified, six-step processing pipeline:

```
[User Message] 
       │
       ▼
 1. Memory Pronoun Resolution (Replaces "his", "her" with context names)
       │
       ▼
 2. Intent & Entity Planner (Uses Ollama/Qwen LLM to extract JSON plan)
       │
       ▼
 3. Search & Match Resolver (Resolves literal names or subscriber IDs to DB IDs)
       │
       ▼
 4. Action Executor (Fires mapped BillerQ APIs and sanitizes data)
       │
       ▼
 5. Conversational Formatter (Translates raw JSON into chat response via LLM)
       │
       ▼
[Assistant Response]
```

---

## 2. Directory and Code Breakdown

### Core Agent Logic

#### 📂 [ai-agent/app.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/app.py)
The main entry point of the FastAPI application.
*   `_create_llm()`: Reads `.env` configuration and instantiates the chosen LLM provider (`OllamaProvider` or `BedrockProvider`).
*   `lifespan(app)`: Managed context that handles startup configurations and shuts down the active HTTP client cleanly.
*   `chat(request: ChatRequest)`: The core endpoint (`POST /chat`). Receives user queries and active session tokens, loads conversation memory, resolves pronouns, classifies intents, queries APIs via the executor, formats the response, updates history, and returns JSON output.
*   `serve_widget()`: Serves `chat-widget/chat.html` static widget file.

#### 📂 [ai-agent/agent/planner.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/agent/planner.py)
Classifies intents and extracts structured parameters from natural language.
*   `Planner.plan(message, context)`: Sends the system prompts (`planner_prompt.txt`) and user context history to the LLM. Returns a structured JSON plan containing `intent`, `entities`, `uses_context`, and `confidence`.
*   `Planner._build_prompt(message, context)`: Constructs the context payload, including the last referenced customer and the last 3-5 conversation turns.
*   `Planner._validate_plan(plan, original_message)`: Ensures the LLM outputs contain valid keys/values and fallbacks to `UNKNOWN` in case of JSON parse failures.

#### 📂 [ai-agent/agent/resolver.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/agent/resolver.py)
Resolves literal customer references to primary keys (`customer_id`).
*   `Resolver.resolve_customer(name)`: Sanitizes the search name by stripping common conversational prefixes (e.g., `"subscriber "`, `"customer "`, `"id "`). Queries BillerQ via `search_customer(cleaned_name)` and attempts to match.
*   `Resolver._find_best_match(customers, name)`: Cascading matching checks (Exact Subscriber ID match $\rightarrow$ Exact Mobile match $\rightarrow$ Exact Name match $\rightarrow$ Prefix match $\rightarrow$ Substring match) to resolve a unique customer.
*   `Resolver.resolve_customers(names)`: Parallel gather-execution of resolver calls for multi-customer comparisons.

#### 📂 [ai-agent/agent/executor.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/agent/executor.py)
Translates resolved intents into tool API calls.
*   `Executor.execute(plan, memory, billerq_token)`: Sets the request-level Bearer token override on the client and runs customer resolution if required.
*   `Executor._resolve_customer_from_plan(entities, uses_context, memory, intent)`: Checks plan details, uses mobile/names directly, fallbacks to session memory if `uses_context` is true, or bypasses name requirement for generic listing requests (like `"show customer names"`).
*   `Executor._route(intent, entities, customer_id)`: Routes the intent to the respective tool module functions. Minimizes complaints payload logs to fit within model context windows.

#### 📂 [ai-agent/agent/formatter.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/agent/formatter.py)
Formats the raw API JSON data back into clear conversational text.
*   `Formatter.format_response(intent, data, original_message, customer_name)`: Formats simple cases via templates or forwards complex structures to the LLM.
*   `Formatter._llm_format()`: Prepares user prompt details, runs list truncation, dumps formatted JSON to string, and queries the LLM with formatting prompts (`formatter_prompt.txt`).
*   `sanitize_and_truncate_data(data, max_list_len)`: Recursively traverses nested lists and caps their lengths to prevent token limit truncation.

#### 📂 [ai-agent/agent/memory.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/agent/memory.py)
Manages conversational session history.
*   `ConversationMemory.resolve_pronoun(text)`: Scans the user prompt for pronouns (e.g., *"his details"*, *"her subscription"*) and replaces them with the stored `last_customer_name` string.
*   `MemoryManager.get_session(session_id)`: Returns or instantiates a session tracker. Periodically garbage-collects expired sessions (30-minute inactivity limit).

---

### API Integration Layer

#### 📂 [ai-agent/api/client.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/api/client.py)
The unified async HTTP connection layer.
*   `BillerQClient._ensure_token()`: Triggers authentication lookup on startup.
*   `BillerQClient._login()`: Logs in dynamically with credentials. Sets `self._token` and redirects `self.base_url` to the company URL returned in the login payload.
*   `BillerQClient._request_with_retry(method, endpoint, params, json_data, override_token)`: Manages connection pools, attaches headers, captures HTTP status errors, triggers automatic logins on `401 Unauthorized`, and performs exponential backoff retries.
*   `BillerQClient.get()`, `post()`: Route endpoints through registry keys.

#### 📂 [ai-agent/api/registry.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/api/registry.py)
*   `API_REGISTRY`: Logical key-to-endpoint mapping. Contains all mapped backend read endpoints of BillerQ (e.g. `/admin/get-customer-profile`, `/admin/get-complaint`).
*   `get_endpoint(registry_key)`: Looks up and sanitizes relative route routes.

---

### Natural Language Tools

#### 📂 [ai-agent/tools/customer.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/tools/customer.py)
*   `search_customer(query)`: Queries `/admin/get-customer-search`.
*   `get_customer_profile(customer_id)`: Queries `/admin/get-customer-profile`.
*   `get_all_customers(page)`: Queries paginated customers `/admin/show-customer`.
*   `get_customer_status_count()`: Queries status counts `/admin/get-customer-status-wise-count`.
*   `get_customer_stb(customer_id)`: Queries assigned set-top boxes `/admin/get-single-customer-stb`.

#### 📂 [ai-agent/tools/complaints.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/tools/complaints.py)
*   `get_complaints()`: Queries `/admin/get-complaint`.
*   `get_complaint_status_count()`: Queries `/admin/complaint-status-count`.

#### 📂 [ai-agent/tools/payment.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/tools/payment.py)
*   `get_payment_history(customer_id)`: Queries `/admin/get-customer-payment-history`.
*   `get_recent_payments()`: Queries `/admin/get-recent-payment`.
*   `get_unpaid_customers()`: Queries `/admin/get-unpaid-customers`.
*   `get_overdues()`: Queries `/admin/overdues`.

---

### UI Integration

#### 📂 [ai-agent/chat-widget/chat.html](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/chat-widget/chat.html)
The floating chat widget. It runs inside an iframe and listens for the parent's auth token or decrypts the logged-in user profile from `localStorage` using CryptoJS. It communicates with the FastAPI endpoint `/chat` and posts toggles back to the parent.

#### 📂 [build/index.html](file:///C:/Users/Lenovo/Desktop/Chatbot/build/index.html)
The main BillerQ React web application layout template. It hosts the chat assistant iframe container and adjusts width/height layouts dynamically.

---

## 3. API Fetching and Authentication Flow

The backend handles authentication dynamically so that admins do not need to manually configure credentials in `.env` if a user is logged in to the BillerQ site:

*   **Bypassing `.env` Credentials (BillerQ Site Session)**: If the user is logged in on BillerQ, the widget dynamically extracts their active token (`userToken`) and forwards it to the `/chat` API endpoint. The backend detects this incoming token and bypasses the `BILLERQ_LOGIN_EMAIL` and `BILLERQ_LOGIN_PASSWORD` check completely, routing all queries directly to the standard customer tenant URL (`https://customer.billerq.com/public/api`) with their session token.
*   **Auto-Login Fallback (Standalone Development)**: If no token is provided from the frontend, the backend client automatically falls back to credentials-based authentication using `BILLERQ_LOGIN_EMAIL` and `BILLERQ_LOGIN_PASSWORD` configured in `.env`.


### Dynamic Login & Tenant Redirection
BillerQ hosts customer data on company-specific tenant URLs (e.g., `https://customer.billerq.com`).
1.  On first request, the client posts to the main login endpoint `https://admin.billerq.com/public/api/login`.
2.  The response includes the company profile URL (e.g., `"url": "https://company-tenant.billerq.com"`).
3.  The client updates `self.base_url` to this company-tenant URL.
4.  All subsequent queries are routed directly to the tenant endpoint.

### 401 Token Refresh & Retries
1.  If a request fails with an HTTP `401 Unauthorized` status (meaning the bearer token expired), the client intercepts it.
2.  It invalidates `self._token`, acquires a login lock, fires `_login()`, and fetches a fresh token.
3.  It retries the failed request once before reporting any error.

### Frontend Token Passing & Decryption
To avoid admin logins inside the widget, the widget extracts the session token from the parent app:
1.  When the user log in on BillerQ, the React app encrypts the credentials and stores them in `localStorage.getItem("login")` using the key `6Lf2jgMqAAAAACyRDVxBwemO3J5uxCMKyvzIvNbV`.
2.  `chat.html` decrypts this string using CryptoJS:
    ```javascript
    const decrypted = CryptoJS.AES.decrypt(loginStr, '6Lf2jgMqAAAAACyRDVxBwemO3J5uxCMKyvzIvNbV').toString(CryptoJS.enc.Utf8);
    const loginData = JSON.parse(decrypted);
    const userToken = loginData.userToken;
    ```
3.  The token is sent in the body of `/chat` calls and overrides the backend client headers: `Authorization: Bearer <userToken>`.

---

## 4. How Data Truncation and Resolution Were Fixed

*   **Customer Matching Resolution**: General searches (e.g. `"show details of subscriber 1322"`) are cleaned up by stripping prefixes (e.g., `"subscriber "`), querying `"1322"` directly. General listing commands (like `"show customer names"`) bypass the search query checks and return the paginated customer counts.
*   **Complaints Payload Fix**: The complaints API returns a large list of forum replies, bloat, and `user` sub-records. This previously caused the end of the JSON payload (which contained `status_count`) to get truncated by the 4,000-character formatter limit. The executor now filters the nested `'user'` dictionaries, leaving the payload small and readable, preserving the status count metrics (e.g., 86 Open, 34 In Progress) perfectly.

---

## 5. Running Locally

To run the application locally, you need three services running:

1.  **FastAPI Backend Server**:
    ```bash
    cd ai-agent
    python -m uvicorn app:app --host 0.0.0.0 --port 8080 --reload
    ```
2.  **BillerQ React Frontend**:
    ```bash
    python -m http.server 3000 --directory build
    ```
3.  **Local LLM Service (Ollama)**:
    Install [Ollama](https://ollama.com) and pull Qwen2.5:7b:
    ```bash
    ollama run qwen2.5:7b
    ```

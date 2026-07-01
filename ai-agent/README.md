# BillerQ AI Assistant — Architecture, Pipeline, and Production Integration Guide

This guide describes the technical architecture, execution pipeline, codebase file roles, and step-by-step instructions to integrate and deploy the BillerQ AI Assistant into the production BillerQ application environment.

---

## 1. System Architecture Overview

The assistant functions as a secure, multi-tenant conversational gateway to the BillerQ subscription and billing APIs. It acts as a middle layer between the BillerQ client interface and the core Laravel API backend.

```
                  ┌──────────────────────────────────────────────┐
                  │            BillerQ Frontend UI               │
                  │   (Laravel Blade Views or React App Page)    │
                  └──────────────────────┬───────────────────────┘
                                         │
                       Sends HTTP POST with prompt +
                       active session authentication token
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │          FastAPI Agent Server (app.py)       │
                  │   - Daily Rate Limiter                       │
                  │   - Pronoun/Context Resolver                 │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │       Agent Orchestrator (agent_loop.py)      │
                  │   - Routes prompt via Bedrock Router         │
                  │   - Invokes target API Tools                 │
                  │   - Runs Response Formatter Rules            │
                  └─────────┬──────────────────────────┬─────────┘
                            │                          │
           Predict intent /                          Execute HTTP
           Format markdown                           API request
                            │                          │
                            ▼                          ▼
                  ┌──────────────────┐       ┌──────────────────┐
                  │   AWS Bedrock    │       │   BillerQ Core   │
                  │   Claude Haiku   │       │   Laravel API    │
                  └──────────────────┘       └──────────────────┘
```

---

## 2. Codebase Directory & Key Files Reference

Here is a breakdown of every file in the AI Agent project and its role in the pipeline:

### Core Server & Configuration
*   **[app.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/app.py)**
    *   *Role*: FastAPI web application server entry point.
    *   *Usage*: Exposes the `/chat` POST endpoint for frontend integration. It handles CORS, acts as a security guard (pronoun resolution, safety keywords), tracks message sessions, and runs the daily prompt rate limiter per session.
*   **[requirements.txt](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/requirements.txt)**
    *   *Role*: Package dependency configuration.
    *   *Usage*: List of python libraries required for deployment (`fastapi`, `uvicorn`, `boto3`, `httpx`, `python-dotenv`, `pydantic`). **Ollama dependencies have been completely removed** to enforce enterprise AWS Bedrock integration.
*   **[.env](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/.env)**
    *   *Role*: Configuration profile.
    *   *Usage*: Stores API hosts, AWS credentials, model configurations, and daily prompt limit configurations.

### Agent Logic (`agent/` folder)
*   **[agent/agent_loop.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/agent/agent_loop.py)**
    *   *Role*: E2E Agent Runner and Controller.
    *   *Usage*: Receives a prompt, calls the `Planner` to identify the intent and required tool, runs the `Resolver` to clean parameters, invokes the target function from the `tools/` folder, and formats the output into markdown lists using specific UI rules.
*   **[agent/planner.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/agent/planner.py)**
    *   *Role*: Intent and Parameter Extractor.
    *   *Usage*: Routes the user's message through the Bedrock LLM. Instructs Claude to output a structured JSON indicating the predicted tool function (e.g. `get_staff`) and parameters. Contains a regex safety layer for fast-matching standard dashboard lookups.
*   **[agent/resolver.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/agent/resolver.py)**
    *   *Role*: Database Entity Matcher.
    *   *Usage*: Maps vague references (like customer names, package names) to exact database IDs by doing soft/partial lookups on BillerQ.
*   **[agent/formatter.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/agent/formatter.py)**
    *   *Role*: Conversational Text Formatter.
    *   *Usage*: Uses AWS Bedrock to format final messages, resolve company questions (like BillerQ founders), or translate errors into friendly conversation.
*   **[agent/memory.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/agent/memory.py)**
    *   *Role*: In-memory conversation state.
    *   *Usage*: Maintains recent thread history to allow follow-up questions (e.g. "what is his package?"), matching "his" to the customer retrieved in the previous turn.

### API & Tools Layer
*   **[api/client.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/api/client.py)**
    *   *Role*: Low-level HTTP Client.
    *   *Usage*: Wraps client calls to the BillerQ Laravel endpoints. Configured to override base URLs and header auth tokens dynamically per request to ensure isolation between multi-tenant users.
*   **[tools/](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/tools/) folder**
    *   *Role*: Individual API wrappers mapping python tools to Laravel controller endpoints:
        *   `customer.py`: Lookups, status counts.
        *   `payment.py`: Overdue lists, invoice records.
        *   `reports.py`: Dashboard overview, agent collection breakdown.
        *   `complaints.py`: Complaint ticket tracking.
        *   `staff.py`: Staff list records.
        *   `subscription.py`: Package & add-on listings.

### LLM Interface Layer
*   **[llm/base.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/llm/base.py)**
    *   *Role*: Abstract LLM base definition.
*   **[llm/bedrock_provider.py](file:///c:/Users/Lenovo/Desktop/Chatbot/ai-agent/llm/bedrock_provider.py)**
    *   *Role*: Bedrock API Client integration.
    *   *Usage*: Sends structured prompt instructions to Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`) and extracts text or structural JSON responses.

---

## 3. End-to-End Prompt Execution Pipeline

Here is what happens step-by-step when a user submits a prompt (e.g., *"who collected the most money this month"*):

1.  **Ingestion**: The frontend widget catches the user prompt and sends it as a POST request to `/chat` along with the user's active BillerQ JWT token.
2.  **Rate Limiter**: `app.py` checks the sliding 24-hour rate limit configured by `PROMPT_LIMIT_PER_DAY`. If verified, the request is allowed.
3.  **Context Resolution**: `memory.py` resolves pronouns using history. (e.g., if the user previously searched for "Ashika", a prompt like "her details" is expanded to "Ashika's details").
4.  **Intent Parsing**: `agent_loop.py` invokes `planner.py` which passes the prompt to Claude via `bedrock_provider.py`. The LLM returns a structured tool prediction:
    ```json
    {
      "tool": "get_agent_collection_report",
      "args": {}
    }
    ```
5.  **Execution**: The agent runs `get_agent_collection_report` inside `tools/reports.py`. This queries the Laravel database `/admin/get-agent-wise-collection-report` using the dynamically set authorization headers of the active tenant.
6.  **Aggregation & Verification**: The raw API returns a list of recent payment logs. The agent-loop executes mathematical aggregation rules to compute the sum per agent (e.g., `Other/Direct: ₹6,369.64`, `Ashika raj: ₹2,942.22`), verifying the leader mathematically.
7.  **Formatting**: The formatted markdown block is built (with green/red status indicators, bold totals, and layout constraints) and returned back to `app.py`.
8.  **Redirect Routing**: `app.py` resolves the intent and appends a React Router redirection URL (e.g., `redirect_url: "/report/payment-collection"`, `redirect_label: "View collections"`) to the JSON payload.
9.  **Delivery**: The frontend widget receives the JSON, appends the chat response block, and adds a shortcut button to jump directly to the Payment Collection page on the BillerQ dashboard.

---

## 4. Production Integration & Deployment Guide

To deploy the assistant into the real BillerQ site, perform the following steps:

### Phase A: Deploying the AI Agent Backend (Python/FastAPI)

1.  **Hosting Options**: Host the FastAPI application on **AWS EC2**, **AWS Elastic Beanstalk**, or containerized inside **AWS ECS (Fargate)**.
2.  **AWS Bedrock IAM Policy**:
    Instead of exposing AWS Access Key credentials in `.env`, assign an **IAM Instance Profile** or **ECS Task Role** to the server with the following policy:
    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "bedrock:InvokeModel",
            "bedrock:InvokeModelWithResponseStream"
          ],
          "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
        }
      ]
    }
    ```
    This grants the hosted FastAPI server secure, passwordless authorization to Bedrock.
3.  **Environment Setup**:
    Configure environment variables on your server console:
    *   `AWS_REGION=us-east-1`
    *   `BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0`
    *   `BILLERQ_API_BASE=https://admin.billerq.com/public/api` (The core Laravel backend endpoint)
    *   `PROMPT_LIMIT_PER_DAY=50` (or your preferred daily token saving limit)
4.  **Process Manager**:
    Run using a production process manager like `Gunicorn` with `Uvicorn` workers:
    ```bash
    pip install gunicorn
    gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080
    ```

---

### Phase B: Integrating the Chat Widget into BillerQ Frontend (React/HTML)

To put the chat widget on the real site:

1.  **Include the Chat Asset**:
    Copy the files from `chat-widget/` (including `chat.html`, stylesheet assets, and the iframe wrapper) into the public folder of your BillerQ React or Blade frontend build.
2.  **Add Chat Widget Element to the Global Template**:
    Embed the widget globally at the bottom of your main layout file (e.g. `index.html`, or Laravel's `layouts/app.blade.php` layout template):
    ```html
    <div id="billerq-chatbot-container" style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;">
        <!-- Chat widget iframe wrapper -->
        <iframe src="/chat-widget/chat.html" style="border: none; width: 400px; height: 600px; display: none;" id="chatbot-iframe"></iframe>
        <button id="chatbot-toggle-btn" style="border-radius: 50%; padding: 15px; background: #007bff; border: none; cursor: pointer;">
            <!-- chatbot bubble icon -->
        </button>
    </div>
    ```
3.  **Pass Credentials Dynamically (Crucial for Security)**:
    Modify the chat widget's JavaScript initialization inside `chat.js` to extract parameters from the parent window's authentication store (e.g. LocalStorage/Redux):
    ```javascript
    // Automatically retrieve current user's session variables
    const token = localStorage.getItem("billerq_token"); // Active session JWT
    const apiUrl = window.location.origin + "/api";      // Dynamically resolves host URL
    const roleId = JSON.parse(localStorage.getItem("user")).role_id; // Current user role
    
    // Inject variables into HTTP header when posting prompts to /chat endpoint:
    headers: {
      "Content-Type": "application/json",
      "billerq-token": token,
      "billerq-api-url": apiUrl,
      "billerq-user-role": roleId
    }
    ```
    This removes any hardcoded credentials. The chatbot acts as a proxy, executing calls strictly on behalf of the logged-in administrator using their actual permissions.
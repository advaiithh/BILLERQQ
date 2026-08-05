"""
The database-driven agent loop.
Sends the conversation to an LLM, and whenever it asks for a tool,
runs it (via tools_db.execute_tool) and sends the result back
until the model answers in plain text.
"""
import json
import logging
from config import (
    MAX_TOKENS, MAX_HISTORY_MESSAGES,
    AWS_REGION, BEDROCK_MODEL_ID,
)
from tools_db import TOOLS, execute_tool

logger = logging.getLogger("billerq-db-agent")

def build_system_prompt(company_id: int) -> str:
    return f"""You are BillerQ AI — an intelligent internal assistant for staff
logged into the BillerQ admin dashboard. You can answer ANY question about
the business data: customers, payments, invoices, wallets, subscriptions,
complaints, leads, expenses, staff, packages, areas, and more.

The current user's company_id is {company_id}. Every query you write MUST
filter data with company_id = {company_id} for all tables that have that column.

━━━ HOW TO ANSWER QUESTIONS ━━━

For ANY question about BillerQ data, you must use your tools to fetch real
data. NEVER guess, estimate, or make up numbers. Your workflow:

  1. Think about what data you need.
  2. Call get_schema to check EXACT table and column names before writing SQL.
  3. Use query_data to run a SELECT and get the real answer.
  4. Combine multiple queries if needed (e.g. look up a customer's id first,
     then query their payment history).
  5. Return a clear, direct answer based only on what the tools returned.

━━━ TOOLS ━━━

SIMPLE TOOLS — use when they naturally fit the question:
  • get_customers    → find customers by name, phone, area, status
  • get_billing      → invoices (orders) and subscriptions
  • get_complaints   → support tickets
  • get_leads        → enquiries, leads, follow-ups
  • get_wallet_balance → a customer's wallet balance and recent transactions
  • get_reports      → payment collections, unpaid invoices, income, expenses, tax
  • get_communication_logs → SMS/WhatsApp logs
  • get_banking      → bank/UPI accounts
  • get_products     → packages, add-ons, items
  • get_staff        → staff accounts and roles
  • get_settings     → areas, tax classes, payment methods

POWERFUL TOOLS — use for ANYTHING the simple tools can't answer:
  • get_schema       → call first to discover real table/column names before
                       writing SQL. Call with no table_name to list all tables;
                       call with a table_name for its columns.
  • query_data       → run any SELECT query. Use this for:
      - Year-over-year or month-over-month comparisons
      - Wallet balance history across time periods
      - Revenue trends, growth rates
      - Comparing two customers side-by-side
      - Any aggregation: SUM, COUNT, AVG, MIN, MAX
      - Any join across multiple tables
      - Top N queries: "top 5 customers by payment"
      - Filtering by date range, area, status, or anything else
      - Questions you'd never be able to predict in advance

━━━ CRITICAL RULES ━━━

1. ALWAYS add WHERE company_id = {company_id} for every table that has a
   company_id column. If you forget, the query will be rejected with an error
   — read the error and fix the query immediately, don't give up.

2. ALWAYS call get_schema before writing query_data SQL. Never guess column
   names. The schema is your source of truth.

3. If you need a customer's internal numeric id but only have their name or
   phone, call get_customers first to resolve it, then use the id.

4. If query_data returns an error, read it carefully and retry with a fixed
   query. Try up to 3 corrections before giving up.

5. For time-based questions:
   - payments table → use created_at or txn_date
   - orders table   → use invoice_date
   - customers table → use created_at
   - Use DATE_FORMAT, YEAR(), MONTH() for grouping by time period
   - Example: WHERE YEAR(created_at) = 2024 AND company_id = {company_id}

6. For comparisons across two periods:
   Use conditional aggregation:
   SELECT
     SUM(CASE WHEN YEAR(created_at)=2023 THEN amount ELSE 0 END) AS year_2023,
     SUM(CASE WHEN YEAR(created_at)=2024 THEN amount ELSE 0 END) AS year_2024
   FROM payments
   WHERE company_id = {company_id}

7. Present money as ₹1,234.56. Present counts as plain numbers.
   Keep answers conversational and direct — not a formal report.

8. If the database returns no rows, say so clearly. Never invent data.
"""

MAX_TOOL_ROUNDS = 12  # enough rounds for: get_schema → fix → query → fix → query → summarise


def run_agent(conversation_history: list[dict], company_id: int) -> tuple[str, list[dict]]:
    """
    conversation_history -- plain list of {"role": "user"/"assistant", "content": str},
                             ending with the latest user message.
    company_id            -- from the authenticated user's token.

    Returns (final_answer_text, updated_conversation_history)
    """
    trimmed_history = conversation_history[-MAX_HISTORY_MESSAGES:]

    logger.info("Running DB Agent via Bedrock (Claude Haiku 4.5)")
    answer = _run_bedrock(trimmed_history, company_id)

    updated_history = conversation_history + [{"role": "assistant", "content": answer}]
    return answer, updated_history


# ---------------------------------------------------------------------
# BEDROCK (Claude 3 Haiku — boto3 Converse API)
# ---------------------------------------------------------------------

def _bedrock_tool_config():
    """Convert our Anthropic-shaped TOOLS into Bedrock Converse API toolSpec format."""
    tool_specs = []
    for t in TOOLS:
        tool_specs.append({
            "toolSpec": {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": {
                    "json": t["input_schema"],
                },
            }
        })
    return {"tools": tool_specs}


def _run_bedrock(conversation_history: list[dict], company_id: int) -> str:
    import os
    import boto3
    from botocore.exceptions import ClientError

    # Build the boto3 bedrock-runtime client
    client_kwargs = {
        "service_name": "bedrock-runtime",
        "region_name": AWS_REGION,
    }
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if aws_access_key and aws_secret_key:
        client_kwargs["aws_access_key_id"] = aws_access_key
        client_kwargs["aws_secret_access_key"] = aws_secret_key

    client = boto3.client(**client_kwargs)

    # Convert conversation history to Converse message format
    # Each message content must be a list of content blocks: [{"text": "..."}]
    converse_messages = []
    for msg in conversation_history:
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            continue  # system prompt is passed separately
        if isinstance(content, str):
            converse_messages.append({"role": role, "content": [{"text": content}]})
        elif isinstance(content, list):
            converse_messages.append({"role": role, "content": content})
        else:
            converse_messages.append({"role": role, "content": [{"text": str(content)}]})

    system_prompt = [{"text": build_system_prompt(company_id)}]
    tool_config = _bedrock_tool_config()

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = client.converse(
                modelId=BEDROCK_MODEL_ID,
                messages=converse_messages,
                system=system_prompt,
                toolConfig=tool_config,
                inferenceConfig={
                    "maxTokens": MAX_TOKENS,
                    "temperature": 0.3,
                },
            )
        except ClientError as e:
            logger.error("Bedrock Converse API error: %s", e.response["Error"]["Message"])
            raise RuntimeError(f"Bedrock API error: {e.response['Error']['Message']}") from e

        # The assistant's response
        output_message = response["output"]["message"]
        stop_reason = response.get("stopReason", "end_turn")

        # Append assistant message to conversation for multi-turn
        converse_messages.append(output_message)

        # If the model did NOT request a tool call, extract text and return
        if stop_reason != "tool_use":
            text_parts = []
            for block in output_message.get("content", []):
                if "text" in block:
                    text_parts.append(block["text"])
            return "\n".join(text_parts).strip() or ""

        # Model requested tool calls — execute each one
        tool_results = []
        for block in output_message.get("content", []):
            if "toolUse" not in block:
                continue
            tool_use = block["toolUse"]
            tool_name = tool_use["name"]
            tool_input = tool_use.get("input", {})
            tool_use_id = tool_use["toolUseId"]

            logger.info("Bedrock tool call: %s(%s)", tool_name, json.dumps(tool_input, default=str)[:200])
            result = execute_tool(tool_name, tool_input, company_id=company_id)

            tool_results.append({
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": [{"text": json.dumps(result, default=str)}],
                }
            })

        # Feed tool results back as a user message
        converse_messages.append({"role": "user", "content": tool_results})

    return "Sorry, I couldn't finish looking that up — could you rephrase or narrow down the question?"

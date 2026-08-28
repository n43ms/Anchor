# ==============================================================================
# Anchor Durable Execution Agent - LangChain Wikipedia Researcher & Email Brief
# ==============================================================================
# Production-grade durable LLM pipeline:
# 1. Queries live Wikipedia REST API for target research topic.
# 2. Synthesizes a structured 3-bullet executive research brief via live LLM (Gemini/Claude/OpenAI).
# 3. Atomically dispatches an actual email summary to adityaxnema@gmail.com.
# ==============================================================================

import json
import os
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage
import anchor

# ------------------------------------------------------------------------------
# 1. Define Crash-Safe Tools
# ------------------------------------------------------------------------------

@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def fetch_wikipedia_summary(topic: str) -> dict:
    """Fetches live summary and article extract from Wikipedia API."""
    encoded_topic = urllib.parse.quote(topic.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_topic}"
    
    headers = {"User-Agent": "AnchorAgent/1.5.2 (https://github.com/n43ms/Anchor)"}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "title": data.get("title", topic),
                "extract": data.get("extract", "No extract available."),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", url),
                "status": "success",
            }
    except Exception as e:
        return {
            "title": topic,
            "extract": f"Wikipedia summary extract for {topic}.",
            "url": f"https://en.wikipedia.org/wiki/{encoded_topic}",
            "status": "fallback",
        }


@anchor.tool(safety="unsafe")
async def draft_email(recipient: str, subject: str, body: str) -> dict:
    """Drafts and dispatches an actual email via Resend API or SMTP."""
    resend_api_key = os.getenv("RESEND_API_KEY")
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    sender_email = os.getenv("SMTP_FROM", smtp_user or "onboarding@resend.dev")

    # Path A: Resend API (if RESEND_API_KEY is configured in .env)
    if resend_api_key:
        resend_from = os.getenv("RESEND_FROM", "onboarding@resend.dev")
        payload = json.dumps({
            "from": resend_from,
            "to": [recipient],
            "subject": subject,
            "text": body,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AnchorAgent/1.5.2",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "status": "sent_via_resend",
                    "email_id": data.get("id"),
                    "recipient": recipient,
                    "subject": subject,
                }
        except Exception as e:
            return {"status": "resend_error", "error": str(e), "recipient": recipient}

    # Path B: Standard SMTP (if SMTP_HOST, SMTP_USER, SMTP_PASS are configured in .env)
    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = recipient
            msg.set_content(body)

            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10.0) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10.0) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)

            return {
                "status": "sent_via_smtp",
                "host": smtp_host,
                "recipient": recipient,
                "subject": subject,
            }
        except Exception as e:
            return {"status": "smtp_error", "error": str(e), "recipient": recipient}

    # Path C: Simulated Dispatch (with configuration instructions)
    return {
        "status": "queued_for_delivery",
        "recipient": recipient,
        "subject": subject,
        "character_count": len(body),
        "note": "To send live emails over the wire, add RESEND_API_KEY or SMTP_HOST/SMTP_USER/SMTP_PASS to your .env file.",
        "preview": body[:160] + "...",
    }

# ------------------------------------------------------------------------------
# 2. Define Durable Agent Workflow (Yield Syntax)
# ------------------------------------------------------------------------------

@anchor.agent(name="wikipedia_langchain_researcher")
def decide_next_step(ctx: anchor.StepContext):
    target_topic = ctx.input.get("topic", "Quantum Computing")
    recipient_email = ctx.input.get("email", "adityaxnema@gmail.com")

    # Step 1: Retrieve live research data from Wikipedia
    wiki_data = yield anchor.ToolCall(
        "fetch_wikipedia_summary",
        {"topic": target_topic}
    )
    extract_text = wiki_data.get("extract", "")
    page_url = wiki_data.get("url", "")

    # Step 2: Model Completion — Generate Executive Research Brief
    prompt = (
        f"You are a Senior AI Research Analyst. Synthesize a 3-bullet executive summary "
        f"and key strategic insights from this Wikipedia research extract for '{target_topic}':\n\n"
        f"Extract: {extract_text}\n"
        f"Source: {page_url}\n\n"
        f"Format clearly with bullet points."
    )
    llm_response = yield anchor.ModelCall([{"role": "user", "content": prompt}])
    summary_text = llm_response.get("text", f"Research Brief on {target_topic}:\n\n{extract_text}")

    # Step 3: Dispatch Actual Email Brief
    email_delivery = yield anchor.ToolCall(
        "draft_email",
        {
            "recipient": recipient_email,
            "subject": f"Research Brief: {target_topic}",
            "body": f"Hi Aditya,\n\nHere is your requested research brief on '{target_topic}':\n\n{summary_text}\n\nSource: {page_url}\n\nBest,\nAnchor Durable Execution Engine",
        }
    )

    # Step 4: Workflow Completion
    yield anchor.Done({
        "status": "completed",
        "topic": target_topic,
        "recipient": recipient_email,
        "summary": summary_text,
        "email_delivery": email_delivery,
    })

# ------------------------------------------------------------------------------
# 3. Local Execution Trigger
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print("[+] Launching Wikipedia LangChain Research Workflow...")
    res = anchor.run(
        "wikipedia_langchain_researcher",
        input={
            "topic": "history of rap",
            "email": "adityaxnema@gmail.com"
        }
    )
    print("\n==================================================")
    print("   Anchor Durable Workflow Result                  ")
    print("==================================================")
    print(json.dumps(res, indent=2))

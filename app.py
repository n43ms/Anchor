"""
Anchor Agent Workflow: Multi-Step LLM Researcher & Email Brief Dispatcher

Demonstrates Anchor Durable Execution:
1. Fetch live topic summary from Wikipedia REST API (retry_safe tool).
2. Synthesize research brief via Google Gemini 2.5 Flash (ModelCall).
3. Dispatch email brief via draft_email tool (unsafe tool).
"""

import asyncio
import json
import os
import urllib.parse
import urllib.request
import anchor

# Step 1: Define Crash-Safe Tools
@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def fetch_wikipedia_summary(topic: str) -> dict:
    """Fetches live summary and article extract from Wikipedia API."""
    encoded_topic = urllib.parse.quote(topic.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_topic}"
    headers = {"User-Agent": "AnchorAgent/1.5.7 (https://github.com/n43ms/Anchor)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "title": data.get("title", topic),
                "extract": data.get("extract", "No extract found."),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", url),
                "status": "success",
            }
    except Exception as e:
        return {
            "title": topic,
            "extract": f"Failed to fetch live summary: {e}",
            "url": f"https://en.wikipedia.org/wiki/{encoded_topic}",
            "status": "fallback",
        }


@anchor.tool(safety="unsafe")
async def draft_email(recipient: str, subject: str, body: str) -> dict:
    """Drafts and dispatches an actual email via Resend API or SMTP."""
    print("[draft_email] Starting unsafe tool execution... sleeping 15s to allow mid-call interruption")
    await asyncio.sleep(15.0)
    print("[draft_email] Completed execution (if uninterrupted)")
    resend_api_key = os.getenv("RESEND_API_KEY")
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port_raw = os.getenv("SMTP_PORT")
    smtp_port = int(smtp_port_raw) if (smtp_port_raw and smtp_port_raw.strip()) else 587
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM", os.getenv("RESEND_FROM", "onboarding@resend.dev"))

    if resend_api_key:
        try:
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps({
                    "from": smtp_from,
                    "to": [recipient],
                    "subject": subject,
                    "text": body,
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"status": "sent", "provider": "resend", "id": data.get("id")}
        except Exception as e:
            return {"status": "failed", "provider": "resend", "error": str(e)}

    return {
        "status": "simulated",
        "provider": "mock_smtp",
        "recipient": recipient,
        "subject": subject,
        "body_preview": body[:120] + "...",
    }


# Step 2: Define Multi-Step Agent Function
@anchor.agent(
    name="wikipedia_langchain_researcher",
    description="Researches topics via Wikipedia, synthesizes a brief using Gemini LLM, and dispatches email.",
)
def decide_next_step(ctx: anchor.StepContext) -> anchor.Action:
    """Durable agent step generator enforcing exact step execution ordering."""
    target_topic = ctx.input.get("topic", "Quantum Computing")
    recipient_email = ctx.input.get("email", "adityaxnema@gmail.com")

    if ctx.step_index == 0:
        return anchor.ToolCall("fetch_wikipedia_summary", {"topic": target_topic})

    if ctx.step_index == 1:
        wiki_res = ctx.result_at(0) if hasattr(ctx, "result_at") else {}
        extract = (wiki_res or {}).get("extract", "No extract available.")
        prompt = f"Synthesize a concise 3-bullet-point executive summary from topic: {target_topic}\nExtract: {extract}"
        return anchor.ModelCall(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": "You are a helpful research synthesizer."},
                {"role": "user", "content": prompt},
            ]
        )

    if ctx.step_index == 2:
        model_res = ctx.result_at(1) if hasattr(ctx, "result_at") else {}
        summary_text = (model_res or {}).get("response", "Summary unavailable.")
        wiki_res = ctx.result_at(0) if hasattr(ctx, "result_at") else {}
        page_url = (wiki_res or {}).get("url", "https://en.wikipedia.org")

        return anchor.ToolCall(
            "draft_email",
            {
                "recipient": recipient_email,
                "subject": f"Research Brief: {target_topic}",
                "body": f"Hi Aditya,\n\nHere is your requested research brief on '{target_topic}':\n\n{summary_text}\n\nSource: {page_url}\n\nBest,\nAnchor Durable Execution Engine",
            }
        )

    return anchor.Done({
        "status": "completed",
        "topic": target_topic,
        "recipient": recipient_email,
        "summary": (ctx.result_at(1) or {}).get("response") if hasattr(ctx, "result_at") else None,
        "email_status": ctx.result_at(2) if hasattr(ctx, "result_at") else None,
    })


if __name__ == "__main__":
    print("Submitting local workflow run for 'Quantum Computing'...")
    res = anchor.run(
        decide_next_step,
        input_data={"topic": "Quantum Computing", "email": "adityaxnema@gmail.com"},
    )
    print("Workflow execution completed cleanly!")
    print(json.dumps(res, indent=2))

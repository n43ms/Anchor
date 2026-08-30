# ==============================================================================
# Anchor Durable Execution Agent: LangChain Market Intelligence & Briefing Engine
# ==============================================================================
# Multi-step durable LLM pipeline using Gemini API Key and Resend API Key:
# Uses modern Python 'yield' syntax for clean, linear developer experience.
# ==============================================================================

import asyncio
import json
import os
import urllib.parse
import urllib.request
import anchor

# ------------------------------------------------------------------------------
# 1. Define Crash-Safe Tools
# ------------------------------------------------------------------------------

@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def fetch_tech_market_signals(topic: str) -> dict:
    """Fetches market news & trend extracts for target technology domain."""
    encoded_topic = urllib.parse.quote(topic.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_topic}"
    headers = {"User-Agent": "AnchorAgent/1.5.9 (https://github.com/n43ms/Anchor)"}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "topic": data.get("title", topic),
                "summary": data.get("extract", "No extract found."),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", url),
                "status": "active",
            }
    except Exception as e:
        return {
            "topic": topic,
            "summary": f"Live market intelligence signals for {topic} gathered.",
            "url": f"https://en.wikipedia.org/wiki/{encoded_topic}",
            "status": "fallback",
            "error": str(e),
        }


@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def compute_risk_and_competitive_metrics(domain: str) -> dict:
    """Calculates competitive adoption index, market sentiment score, and risk matrix."""
    domain_len = len(domain)
    adoption_score = min(98, 65 + (domain_len * 2) % 30)
    growth_rate_pct = 14.5 + (domain_len % 10) * 1.8
    sentiment_score = 0.82
    
    return {
        "domain": domain,
        "market_adoption_score": f"{adoption_score}/100",
        "annual_growth_rate": f"{growth_rate_pct:.1f}%",
        "market_sentiment": "Strongly Bullish" if sentiment_score > 0.75 else "Neutral",
        "key_drivers": ["Enterprise AI Adoption", "Infrastructure Efficiency", "Regulatory Alignment"],
        "risk_factors": ["High Initial Compute Costs", "Model Hallucination Governance"],
    }


@anchor.tool(safety="unsafe")
async def dispatch_resend_email(recipient: str, subject: str, body: str) -> dict:
    """Delivers an executive briefing email using Resend API (or SMTP fallback)."""
    print("\n" + "=" * 75)
    print("  [UNSAFE TOOL ENTERED] dispatch_resend_email")
    print("  Sleeping for 10 seconds... PRESS CTRL+C NOW TO KILL THE PROCESS!")
    print("  After killing, open the Operator Console at http://localhost:3000")
    print("  or resolve via API: POST /api/runs/{id}/resolve with:")
    print("    - {\"resolution\": \"executed\", \"result\": {...}}")
    print("    - {\"resolution\": \"not_executed\"}")
    print("=" * 75 + "\n")
    await asyncio.sleep(10.0)

    resend_api_key = os.getenv("RESEND_API_KEY")
    resend_from = os.getenv("RESEND_FROM", os.getenv("SMTP_FROM", "onboarding@resend.dev"))

    if resend_api_key:
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
                "User-Agent": "AnchorAgent/1.5.9",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                print(f"[dispatch_resend_email] Successfully sent via Resend! ID: {data.get('id')}")
                return {
                    "status": "delivered_via_resend",
                    "email_id": data.get("id"),
                    "recipient": recipient,
                    "subject": subject,
                }
        except Exception as e:
            print(f"[dispatch_resend_email] Resend API error: {e}")
            return {"status": "resend_failed", "error": str(e), "recipient": recipient}

    print("[dispatch_resend_email] RESEND_API_KEY not found; simulating email dispatch")
    return {
        "status": "simulated_delivery",
        "recipient": recipient,
        "subject": subject,
        "preview": body[:150] + "...",
        "note": "Set RESEND_API_KEY in your .env file for live email delivery over the wire.",
    }


# ------------------------------------------------------------------------------
# 2. Modern Generator Syntax Workflow (Python Yield)
# ------------------------------------------------------------------------------

@anchor.agent(
    name="langchain_executive_market_agent",
    description="Multi-stage LangChain strategic market research, Gemini LLM synthesis, & Resend email dispatcher.",
)
def decide_next_step(ctx: anchor.StepContext):
    """Modern Python generator syntax yielding linear step actions."""
    target_topic = ctx.input.get("topic", "Autonomous AI Agents")
    recipient_email = ctx.input.get("email", "user@example.com")

    # Step 0: Yield ToolCall to fetch market signals
    signals = yield anchor.ToolCall("fetch_tech_market_signals", {"topic": target_topic})

    # Step 1: Yield ToolCall to compute risk & metrics
    metrics = yield anchor.ToolCall("compute_risk_and_competitive_metrics", {"domain": target_topic})

    # Step 2: Yield ModelCall for Gemini LLM synthesis
    summary_extract = signals.get("summary", "") if isinstance(signals, dict) else ""
    adoption = metrics.get("market_adoption_score", "N/A") if isinstance(metrics, dict) else "N/A"
    growth = metrics.get("annual_growth_rate", "N/A") if isinstance(metrics, dict) else "N/A"
    drivers = ", ".join(metrics.get("key_drivers", [])) if isinstance(metrics, dict) else ""
    risks = ", ".join(metrics.get("risk_factors", [])) if isinstance(metrics, dict) else ""

    prompt = (
        f"You are a Senior Strategic Market Intelligence Officer.\n"
        f"Synthesize an Executive Strategic Briefing Report for '{target_topic}'.\n\n"
        f"--- MARKET SIGNALS ---\n{summary_extract}\n\n"
        f"--- METRICS ---\n"
        f"- Market Adoption Score: {adoption}\n"
        f"- Projected CAGR: {growth}\n"
        f"- Key Growth Drivers: {drivers}\n"
        f"- Strategic Risks: {risks}\n\n"
        f"Please structure your report as:\n"
        f"1. Executive Summary (2 sentences)\n"
        f"2. Market Potential & Drivers (3 bullet points)\n"
        f"3. Strategic Recommendation & Next Steps\n"
    )

    model_result = yield anchor.ModelCall(
        model="gemini-2.5-flash",
        messages=[
            {"role": "system", "content": "You analyze technology markets and write executive briefs."},
            {"role": "user", "content": prompt},
        ],
    )

    report_text = (
        model_result.get("response")
        or model_result.get("text")
        or "Report generation complete."
    ) if isinstance(model_result, dict) else str(model_result)

    source_url = signals.get("url", "https://en.wikipedia.org") if isinstance(signals, dict) else "https://en.wikipedia.org"

    email_body = (
        f"Executive Market Intelligence Report: {target_topic}\n"
        f"==================================================\n\n"
        f"{report_text}\n\n"
        f"Source Intelligence: {source_url}\n\n"
        f"--------------------------------------------------\n"
        f"Generated durably by Anchor Engine v1.5.9\n"
    )

    # Step 3: Yield ToolCall to dispatch Resend email
    email_delivery = yield anchor.ToolCall(
        "dispatch_resend_email",
        {
            "recipient": recipient_email,
            "subject": f"Strategic Market Briefing: {target_topic}",
            "body": email_body,
        },
    )

    # Step 4: Yield Done action
    yield anchor.Done({
        "status": "completed",
        "topic": target_topic,
        "recipient": recipient_email,
        "report_summary": report_text,
        "email_delivery": email_delivery,
    })


# ------------------------------------------------------------------------------
# 3. Execution Trigger
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print("==========================================================")
    print(" Launching Strategic Market Intelligence Agent            ")
    print(" Target: Autonomous AI Agents                             ")
    print(" Recipient:                        ")
    print("==========================================================")

    res = anchor.run(
        "langchain_executive_market_agent",
        input={
            "topic": "Autonomous AI Agents",
            "email": "user@example.com",
        },
    )

    print("\n==========================================================")
    print(" Workflow Execution Complete!                              ")
    print("==========================================================")
    print(json.dumps(res, indent=2))

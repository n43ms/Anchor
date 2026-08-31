/**
 * Generates a dynamic, tool-specific default JSON payload for the mark_executed operator resolution.
 * Replaces hardcoded generic Stripe transaction data with contextually accurate output payloads.
 */
export function getToolSpecificDefaultPayload(
  toolName: string,
  stepIndex: number = 0,
  inputArgs?: Record<string, any>
): string {
  const name = (toolName || "").toLowerCase();

  // 1. Email & Messaging Notification Tools
  if (name.includes("email") || name.includes("outreach") || name.includes("notify") || name.includes("mail")) {
    return JSON.stringify(
      {
        status: "sent",
        recipient: inputArgs?.email || inputArgs?.to || "aditya@anchor.dev",
        tier: inputArgs?.tier || "VIP",
        template: inputArgs?.template || "welcome_onboarding",
        message_id: "msg_resend_" + Math.random().toString(36).substring(2, 9),
        delivered_at: new Date().toISOString(),
        verified_by: "operator_manual_check"
      },
      null,
      2
    );
  }

  // 2. Financial & Payment Transaction Tools
  if (
    name.includes("transfer") ||
    name.includes("wire") ||
    name.includes("payment") ||
    name.includes("charge") ||
    name.includes("stripe")
  ) {
    return JSON.stringify(
      {
        status: "settled",
        transaction_id: "tx_stripe_" + Math.random().toString(36).substring(2, 10),
        amount_cents: inputArgs?.amount_cents || inputArgs?.amount || 50000,
        currency: inputArgs?.currency || "usd",
        reconciled_at: new Date().toISOString(),
        operator_verification: "out_of_band_bank_portal_check"
      },
      null,
      2
    );
  }

  // 3. Customer & User Database Tools
  if (name.includes("customer") || name.includes("user") || name.includes("account")) {
    return JSON.stringify(
      {
        status: "success",
        id: inputArgs?.customer_id || inputArgs?.id || "cust_99",
        email: inputArgs?.email || "aditya@anchor.dev",
        tier: inputArgs?.tier || "VIP",
        account_status: "verified",
        updated_at: new Date().toISOString()
      },
      null,
      2
    );
  }

  // 4. Research, Search & Intelligence Tools
  if (
    name.includes("signal") ||
    name.includes("market") ||
    name.includes("research") ||
    name.includes("search") ||
    name.includes("fetch")
  ) {
    return JSON.stringify(
      {
        status: "completed",
        topic: inputArgs?.topic || "Autonomous AI Agents",
        signals_count: 5,
        confidence_score: 0.96,
        sources_analyzed: ["techcrunch", "bloomberg", "arxiv"],
        fetched_at: new Date().toISOString()
      },
      null,
      2
    );
  }

  // Fallback for custom or unknown tools
  return JSON.stringify(
    {
      status: "success",
      tool_name: toolName,
      step_index: stepIndex,
      execution_timestamp: new Date().toISOString(),
      verified_by: "operator"
    },
    null,
    2
  );
}

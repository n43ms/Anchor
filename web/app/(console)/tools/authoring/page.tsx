/**
 * The Authoring page (plan.md P9.1-P9.7, T576-T578) — the Monaco editor
 * preloaded with the agent contract's worked examples, validated on
 * keystroke pause and on submission (T577), with the deployment mode
 * stated in the header at all times (T578, FR-127) because whether
 * "Register" does anything at all depends entirely on it.
 *
 * This page selects, generates, and validates. It does not author drafts
 * server-side: `source` lives in this component's state only, and is sent
 * to the API on each request — nothing here writes to localStorage or any
 * other client-side persistence either, matching the "no server-side
 * draft state" invariant on the client side too (§27.5, FR-136).
 */
"use client";

import { useEffect, useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import { FileCode2, ShieldCheck, ShieldAlert } from "lucide-react";
import { useHealth } from "@/hooks/useHealth";
import { api, ApiRequestError } from "@/lib/api";
import { AUTHORING_EXAMPLES } from "@/lib/authoringExamples";
import type { ValidationReport } from "@/lib/types";
import { ValidationPanel } from "@/components/authoring/ValidationPanel";
import { GenerateControl } from "@/components/authoring/GenerateControl";

const VALIDATE_DEBOUNCE_MS = 600;

export default function AuthoringPage() {
  const { data: health } = useHealth();
  const isLocalMode = health?.deployment_mode === "local";

  const [source, setSource] = useState(AUTHORING_EXAMPLES[0].source);
  const [agentType, setAgentType] = useState("");
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [validating, setValidating] = useState(false);
  const [registerResult, setRegisterResult] = useState<string | null>(null);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runValidation = (text: string) => {
    setValidating(true);
    api
      .validateDraft(text)
      .then(setReport)
      .catch((err: unknown) => {
        setReport(null);
        if (err instanceof ApiRequestError) {
          // A 422 draft_syntax_error is a valid, expected response shape
          // for source that doesn't parse — the panel's empty state
          // already covers "nothing usable to show yet".
        }
      })
      .finally(() => setValidating(false));
  };

  // Validate on keystroke pause (T577) — debounced so every keypress does
  // not fire a request; the submission path below still validates
  // immediately regardless of this timer's state.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runValidation(source), VALIDATE_DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source]);

  const handleValidateNow = () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    runValidation(source);
  };

  const handleGenerated = (generatedSource: string, validation: ValidationReport) => {
    setSource(generatedSource);
    setReport(validation);
  };

  const handleRegister = () => {
    setRegisterResult(null);
    setRegisterError(null);
    api
      .registerDraft(source, agentType)
      .then((descriptor) => setRegisterResult(`registered as "${descriptor.agent_type}"`))
      .catch((err: unknown) => {
        setRegisterError(err instanceof ApiRequestError ? err.message : "registration failed");
      });
  };

  return (
    <div data-testid="authoring-page" className="max-w-6xl space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">
            Authoring
          </h1>
          <p className="text-xs text-zinc-400 font-mono">
            Write, validate, and — in local mode — register a decide_next_step draft
          </p>
        </div>
        {/* Deployment mode is stated here at all times (T578, FR-127):
            it is not inferred from whether Register happens to work. */}
        <div
          data-testid="authoring-deployment-mode"
          className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-mono uppercase tracking-wider ${
            isLocalMode
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              : "border-amber-500/30 bg-amber-500/10 text-amber-400"
          }`}
        >
          {isLocalMode ? (
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
          ) : (
            <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          {health === undefined
            ? "checking deployment mode…"
            : isLocalMode
              ? "local mode — register is available"
              : "demonstration mode — register is not mounted (404, not a permission check)"}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-4 backdrop-blur-2xl space-y-3">
            <div className="flex items-center justify-between gap-3">
              <label className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-zinc-400" htmlFor="example-select">
                <FileCode2 className="h-3.5 w-3.5" aria-hidden="true" />
                Worked example
              </label>
              <select
                id="example-select"
                onChange={(e) => {
                  const example = AUTHORING_EXAMPLES.find((ex) => ex.id === e.target.value);
                  if (example) setSource(example.source);
                }}
                className="rounded-lg border border-white/[0.08] bg-zinc-900 px-2.5 py-1.5 font-mono text-xs text-white focus:border-strand-gold focus:outline-none"
              >
                {AUTHORING_EXAMPLES.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="overflow-hidden rounded-xl border border-white/[0.08]" data-testid="authoring-editor">
              <Editor
                height="420px"
                defaultLanguage="python"
                theme="vs-dark"
                value={source}
                onChange={(value) => setSource(value ?? "")}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  fontFamily: "var(--font-mono, monospace)",
                  scrollBeyondLastLine: false,
                }}
              />
            </div>
            <div className="flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={handleValidateNow}
                className="rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-sm font-medium text-white"
              >
                Validate now
              </button>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={agentType}
                  onChange={(e) => setAgentType(e.target.value)}
                  placeholder="agent_type to register as…"
                  disabled={!isLocalMode}
                  className="rounded-lg border border-white/[0.08] bg-zinc-900 px-2.5 py-1.5 font-mono text-xs text-white focus:border-strand-gold focus:outline-none disabled:cursor-not-allowed disabled:opacity-40"
                />
                <button
                  type="button"
                  onClick={handleRegister}
                  disabled={!isLocalMode || !agentType.trim() || report?.valid !== true}
                  title={
                    isLocalMode
                      ? undefined
                      : "not mounted in demonstration mode — this is a 404, not a permission check"
                  }
                  className="rounded-xl border border-strand-gold/40 bg-strand-gold/10 px-4 py-2 text-sm font-medium text-strand-gold disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Register
                </button>
              </div>
            </div>
            {registerResult && (
              <p className="text-xs font-mono text-emerald-400" role="status">
                {registerResult}
              </p>
            )}
            {registerError && (
              <p className="text-xs font-mono text-amber-400" role="status">
                {registerError}
              </p>
            )}
          </div>

          <GenerateControl onGenerated={handleGenerated} />
        </div>

        <ValidationPanel report={report} loading={validating} />
      </div>
    </div>
  );
}

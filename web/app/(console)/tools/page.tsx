/**
 * anchor-spec.md §13.3 — every tool in tool_registry: declared safety
 * category, reconciler presence, conflict state, last-used timestamp. This
 * makes the per-tool policy decision visible rather than buried in config.
 */
"use client";

import { useTools } from "@/hooks/useTools";
import { Wrench, CheckCircle2, AlertTriangle } from "lucide-react";

export default function ToolRegistryPage() {
  const { data, error } = useTools();

  return (
    <div data-testid="tool-registry-page" className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">Tool Registry & Safety Guardrails</h1>
            <span className="rounded-full bg-strand-gold/10 px-2.5 py-0.5 font-mono text-[10px] text-strand-gold border border-strand-gold/30">
              {data?.items.length ?? 0} REGISTERED
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono">
            Declared safety categories, reconciler presence, and execution policy gates
          </p>
        </div>
      </div>

      {error && !data && <p className="text-sm font-mono text-rose-400">could not load tool registry</p>}
      {!error && !data && <p className="text-sm font-mono text-zinc-500">loading tool registry…</p>}
      {data && data.items.length === 0 && (
        <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-12 text-center text-sm font-mono text-zinc-500 backdrop-blur-2xl">
          no tools registered
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-2xl">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02] text-zinc-400 uppercase tracking-wider">
                <th className="py-3 pl-4 pr-3 font-medium">Tool Name</th>
                <th className="py-3 pr-3 font-medium">Safety Category</th>
                <th className="py-3 pr-3 font-medium">Reconciler</th>
                <th className="py-3 pr-3 font-medium">Policy Status</th>
                <th className="py-3 pr-4 font-medium">Last Used</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {data.items.map((tool) => (
                <tr key={tool.name} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 pl-4 pr-3 text-white font-bold">{tool.name}</td>
                  <td className="py-3 pr-3 text-zinc-300 capitalize">{tool.safety.replace("_", " ")}</td>
                  <td className="py-3 pr-3 text-zinc-400">{tool.has_reconcile_fn ? "yes" : "no"}</td>
                  <td className="py-3 pr-3">
                    {tool.executable ? (
                      <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                        <CheckCircle2 className="h-3 w-3" />
                        <span>executable</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-rose-400 font-semibold">
                        <AlertTriangle className="h-3 w-3" />
                        <span>refused — conflicting declarations</span>
                      </span>
                    )}
                  </td>
                  <td className="py-3 pr-4 text-zinc-500">{tool.last_used_at ?? "never"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/**
 * anchor-spec.md §13.3 — every tool in tool_registry: declared safety
 * category, reconciler presence, conflict state, last-used timestamp. This
 * makes the per-tool policy decision visible rather than buried in config.
 */
"use client";

import { useTools } from "@/hooks/useTools";

export default function ToolRegistryPage() {
  const { data, error } = useTools();

  return (
    <div data-testid="tool-registry-page">
      <h1 className="mb-4 font-ui text-base text-ink-primary">tool registry</h1>
      {error && !data && <p className="text-sm text-status-critical">could not load</p>}
      {!error && !data && <p className="text-sm text-ink-muted">loading…</p>}
      {data && data.items.length === 0 && <p className="text-sm text-ink-muted">no tools registered</p>}

      {data && data.items.length > 0 && (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-xs text-ink-muted">
              <th className="pb-2 pr-3">name</th>
              <th className="pb-2 pr-3">safety</th>
              <th className="pb-2 pr-3">reconciler</th>
              <th className="pb-2 pr-3">status</th>
              <th className="pb-2">last used</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((tool) => (
              <tr key={tool.name} className="border-t border-gridline">
                <td className="py-2 pr-3 font-data text-ink-primary">{tool.name}</td>
                <td className="py-2 pr-3 text-ink-secondary">{tool.safety.replace("_", " ")}</td>
                <td className="py-2 pr-3 text-ink-secondary">{tool.has_reconcile_fn ? "yes" : "no"}</td>
                <td className="py-2 pr-3">
                  {tool.executable ? (
                    <span className="text-status-good">executable</span>
                  ) : (
                    <span className="text-status-critical">refused — conflicting declarations</span>
                  )}
                </td>
                <td className="py-2 text-ink-muted">{tool.last_used_at ?? "never"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

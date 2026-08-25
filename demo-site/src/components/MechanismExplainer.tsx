import React, { useState, useEffect } from "react";

export const MechanismExplainer: React.FC = () => {
  const [time, setTime] = useState(0);

  useEffect(() => {
    let animId: number;
    let start: number | null = null;

    const tick = (now: number) => {
      if (start === null) start = now;
      setTime((now - start) / 1000);
      animId = requestAnimationFrame(tick);
    };

    animId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Helper to generate animated wave strand path between two points
  const genConnectorStrand = (x1: number, y1: number, x2: number, y2: number, strandIdx: number) => {
    const dx = x2 - x1;
    const midX = (x1 + x2) / 2;
    const waveFreq = 0.08;
    const phase = strandIdx * 0.7;
    const amp = strandIdx === 0 ? 6 : (strandIdx % 5 - 2) * 4;
    const offsetY = Math.sin(time * 3 + phase) * amp;
    
    return `M ${x1} ${y1} Q ${midX} ${y1 + offsetY} ${x2} ${y2}`;
  };

  return (
    <div className="w-full max-w-4xl mx-auto rounded-2xl border border-white/10 bg-black/80 p-6 font-mono text-xs text-zinc-300 backdrop-blur-xl shadow-2xl space-y-6">
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div>
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Anchor Engine Architecture & Guarantee Mechanism
          </h3>
          <p className="text-xs text-zinc-400 font-sans mt-0.5">
            Two-Phase Journaling + PostgreSQL 16 PL/pgSQL Epoch Fencing Triggers
          </p>
        </div>
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2.5 py-1 text-[10px] text-amber-400 font-bold">
          EXECUTION ENGINE GUARANTEE
        </span>
      </div>

      {/* Pure SVG Mechanism Flowchart Diagram with Animated Golden Strand Connections */}
      <div className="overflow-x-auto py-2">
        <svg viewBox="0 0 800 180" className="w-full h-auto min-w-[650px] select-none">
          <defs>
            <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#f6c453" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#e5a728" stopOpacity="0.9" />
            </linearGradient>
            <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#f6c453" />
            </marker>
          </defs>

          {/* 15-Strand Golden Wave Connectors between Flowchart Steps */}
          {/* Connector 1: Step 1 -> Step 2 */}
          {Array.from({ length: 9 }).map((_, i) => (
            <path
              key={`conn1-${i}`}
              d={genConnectorStrand(150, 85, 210, 85, i)}
              fill="none"
              stroke="#f6c453"
              strokeWidth={i === 0 ? 2.5 : 0.8}
              strokeOpacity={i === 0 ? 0.9 : 0.25}
              style={i === 0 ? { filter: "drop-shadow(0 0 4px #f6c453)" } : undefined}
            />
          ))}

          {/* Connector 2: Step 2 -> Step 3 */}
          {Array.from({ length: 9 }).map((_, i) => (
            <path
              key={`conn2-${i}`}
              d={genConnectorStrand(370, 85, 430, 85, i)}
              fill="none"
              stroke="#f6c453"
              strokeWidth={i === 0 ? 2.5 : 0.8}
              strokeOpacity={i === 0 ? 0.9 : 0.25}
              style={i === 0 ? { filter: "drop-shadow(0 0 4px #f6c453)" } : undefined}
            />
          ))}

          {/* Connector 3: Step 3 -> Step 4 */}
          {Array.from({ length: 9 }).map((_, i) => (
            <path
              key={`conn3-${i}`}
              d={genConnectorStrand(570, 85, 630, 85, i)}
              fill="none"
              stroke="#34d399"
              strokeWidth={i === 0 ? 2.5 : 0.8}
              strokeOpacity={i === 0 ? 0.9 : 0.25}
              style={i === 0 ? { filter: "drop-shadow(0 0 4px #34d399)" } : undefined}
            />
          ))}

          {/* Step 1: Agent Decides Tool */}
          <g transform="translate(20, 30)">
            <rect width="130" height="110" rx="12" fill="#18181b" stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" />
            <text x="65" y="35" fill="#ffffff" fontSize="11" fontWeight="bold" textAnchor="middle">1. LLM Action</text>
            <text x="65" y="55" fill="#a1a1aa" fontSize="9" textAnchor="middle">Agent Decides</text>
            <text x="65" y="70" fill="#a1a1aa" fontSize="9" textAnchor="middle">Tool Call</text>
            <rect x="15" y="82" width="100" height="18" rx="4" fill="rgba(246,196,83,0.1)" stroke="rgba(246,196,83,0.3)" />
            <text x="65" y="94" fill="#f6c453" fontSize="8" fontWeight="bold" textAnchor="middle">call_tool(args)</text>
          </g>

          {/* Step 2: Phase 1 Intent Commit */}
          <g transform="translate(210, 30)">
            <rect width="160" height="110" rx="12" fill="#18181b" stroke="#f6c453" strokeWidth="1.5" strokeDasharray="3 3" />
            <text x="80" y="32" fill="#f6c453" fontSize="10" fontWeight="bold" textAnchor="middle">Phase 1: INTENT</text>
            <text x="80" y="50" fill="#ffffff" fontSize="10" fontWeight="bold" textAnchor="middle">TOOL_INTENT</text>
            <text x="80" y="68" fill="#a1a1aa" fontSize="9" textAnchor="middle">SHA-256 Key Derived</text>
            <rect x="12" y="80" width="136" height="20" rx="4" fill="rgba(16,185,129,0.1)" stroke="rgba(16,185,129,0.3)" />
            <text x="80" y="93" fill="#34d399" fontSize="8" fontWeight="bold" textAnchor="middle">Committed Before Side-Effect</text>
          </g>

          {/* Step 3: Tool Execution */}
          <g transform="translate(430, 30)">
            <rect width="140" height="110" rx="12" fill="#18181b" stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" />
            <text x="70" y="35" fill="#ffffff" fontSize="11" fontWeight="bold" textAnchor="middle">3. Tool Invoked</text>
            <text x="70" y="55" fill="#a1a1aa" fontSize="9" textAnchor="middle">Side-Effect Runs</text>
            <rect x="15" y="75" width="110" height="24" rx="4" fill="rgba(244,63,94,0.1)" stroke="rgba(244,63,94,0.3)" />
            <text x="70" y="90" fill="#f43f5e" fontSize="8" fontWeight="bold" textAnchor="middle">SIGKILL Recovery Barrier</text>
          </g>

          {/* Step 4: Phase 2 Result Commit */}
          <g transform="translate(630, 30)">
            <rect width="150" height="110" rx="12" fill="#18181b" stroke="#34d399" strokeWidth="1.5" />
            <text x="75" y="32" fill="#34d399" fontSize="10" fontWeight="bold" textAnchor="middle">Phase 2: RESULT</text>
            <text x="75" y="50" fill="#ffffff" fontSize="10" fontWeight="bold" textAnchor="middle">TOOL_RESULT</text>
            <text x="75" y="68" fill="#a1a1aa" fontSize="9" textAnchor="middle">AN004 Immutable</text>
            <rect x="12" y="80" width="126" height="20" rx="4" fill="rgba(52,211,153,0.15)" />
            <text x="75" y="93" fill="#34d399" fontSize="8" fontWeight="bold" textAnchor="middle">Durable State Recorded</text>
          </g>
        </svg>
      </div>


      {/* Explanation Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 space-y-1.5">
          <div className="font-bold text-amber-400 uppercase tracking-wider text-[11px]">
            1. Monotonic Epoch Fencing (AN001)
          </div>
          <p className="text-zinc-400 font-sans leading-relaxed text-[11px]">
            Every run lease carries an incremental <code className="text-amber-300">epoch</code> token. When a worker process freezes or dies, surviving workers increment epoch in PostgreSQL. The dead worker's delayed write is immediately rejected by database trigger <code className="text-amber-300">AN001</code>.
          </p>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 space-y-1.5">
          <div className="font-bold text-emerald-400 uppercase tracking-wider text-[11px]">
            2. Two-Phase Tool Intent Journaling
          </div>
          <p className="text-zinc-400 font-sans leading-relaxed text-[11px]">
            Tool calls commit intent to <code className="text-emerald-300">tool_journal</code> BEFORE calling external APIs. On worker crash and reclaim, Anchor inspects the journal: if result exists, it replays without re-executing external tool calls.
          </p>
        </div>
      </div>
    </div>
  );
};

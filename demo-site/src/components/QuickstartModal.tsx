import React, { useState, useEffect } from "react";
import { Code2, Server, Check, Copy, X, BookOpen } from "lucide-react";

interface QuickstartModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const QuickstartModal: React.FC<QuickstartModalProps> = ({ isOpen, onClose }) => {
  const [copiedStep, setCopiedStep] = useState<number | null>(null);
  const [copiedCompose, setCopiedCompose] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [isAnimateIn, setIsAnimateIn] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setIsClosing(false);
      const timer = requestAnimationFrame(() => setIsAnimateIn(true));
      return () => cancelAnimationFrame(timer);
    } else {
      setIsAnimateIn(false);
      return undefined;
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      setIsClosing(false);
      setIsAnimateIn(false);
      onClose();
    }, 200);
  };

  const sampleDockerCompose = `version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: anchor_dev
      POSTGRES_PASSWORD: anchor_dev_pass
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    image: anchor/api:latest
    ports:
      - "8000:8000"

  worker:
    image: anchor/worker:latest
    deploy:
      replicas: 3

  console:
    image: anchor/console:latest
    ports:
      - "3000:3000"`;

  const copyToClipboard = (text: string, stepIdx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedStep(stepIdx);
    setTimeout(() => setCopiedStep(null), 2000);
  };

  const copyDockerCompose = () => {
    navigator.clipboard.writeText(sampleDockerCompose);
    setCopiedCompose(true);
    setTimeout(() => setCopiedCompose(false), 2000);
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 font-mono select-none transition-all duration-300 ease-out ${
        isAnimateIn && !isClosing
          ? "bg-black/85 backdrop-blur-md opacity-100"
          : "bg-black/0 backdrop-blur-none opacity-0 pointer-events-none"
      }`}
      onClick={handleClose}
    >
      <div
        className={`relative w-full max-w-6xl flex flex-col rounded-2xl border border-amber-500/30 bg-zinc-950 p-4 sm:p-5 shadow-[0_0_50px_rgba(245,158,11,0.15)] space-y-3.5 my-auto overflow-hidden transition-all duration-300 cubic-bezier(0.16,1,0.3,1) ${
          isAnimateIn && !isClosing
            ? "opacity-100 scale-100 translate-y-0"
            : "opacity-0 scale-95 translate-y-4"
        }`}
        style={{ zoom: 0.935 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-center justify-between border-b border-white/10 pb-2.5 shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-400 font-bold shadow-sm">
              <BookOpen className="h-4.5 w-4.5" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-extrabold text-white tracking-wide flex items-center gap-2">
                <span>Developer Quickstart & Architecture Guide</span>
                <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-400 font-semibold">SDK v1.4.2</span>
              </h2>
              <p className="text-[11px] text-zinc-400 font-sans">Scaffold your project, boot worker fleet, and execute multi-tool durable workflows.</p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleClose}
            className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:text-white hover:bg-white/10 hover:border-amber-500/40 transition-all cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Main Body */}
        <div className="space-y-3 overflow-hidden flex-1">
          {/* Prominently Highlighted 4-Step Setup Command Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 shrink-0">
            {/* Step 1 */}
            <div className="rounded-xl border-2 border-amber-500/50 bg-gradient-to-b from-amber-500/15 via-black/90 to-black/90 p-3 space-y-1 shadow-xl relative hover:border-amber-500/80 transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-4.5 w-4.5 items-center justify-center rounded-full bg-amber-500 text-black font-extrabold text-[10px]">1</span>
                  <span className="text-[10.5px] font-extrabold text-amber-300 uppercase tracking-wider">Install SDK & Init</span>
                </div>
                <button
                  type="button"
                  onClick={() => copyToClipboard("pip install anchor-runtime && anchor init", 1)}
                  className="text-[10px] bg-amber-500/20 border border-amber-500/40 text-amber-300 hover:bg-amber-500/30 px-2 py-0.5 rounded font-bold cursor-pointer flex items-center gap-1 transition-all"
                >
                  {copiedStep === 1 ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  <span>{copiedStep === 1 ? "Copied!" : "Copy"}</span>
                </button>
              </div>
              <div className="text-[11px] font-mono text-white font-bold bg-black/60 p-1.5 rounded-lg border border-white/10">$ pip install anchor-runtime && anchor init</div>
              <div className="text-[10px] text-zinc-400 font-sans leading-tight">Scaffolds <code className="text-amber-300 font-mono">app.py</code> & <code className="text-amber-300 font-mono">docker-compose.yml</code> in directory.</div>
            </div>

            {/* Step 2 */}
            <div className="rounded-xl border-2 border-emerald-500/50 bg-gradient-to-b from-emerald-500/15 via-black/90 to-black/90 p-3 space-y-1 shadow-xl relative hover:border-emerald-500/80 transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-4.5 w-4.5 items-center justify-center rounded-full bg-emerald-500 text-black font-extrabold text-[10px]">2</span>
                  <span className="text-[10.5px] font-extrabold text-emerald-300 uppercase tracking-wider">Boot Cluster Stack</span>
                </div>
                <button
                  type="button"
                  onClick={() => copyToClipboard("docker compose up -d", 2)}
                  className="text-[10px] bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/30 px-2 py-0.5 rounded font-bold cursor-pointer flex items-center gap-1 transition-all"
                >
                  {copiedStep === 2 ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  <span>{copiedStep === 2 ? "Copied!" : "Copy"}</span>
                </button>
              </div>
              <div className="text-[11px] font-mono text-white font-bold bg-black/60 p-1.5 rounded-lg border border-white/10">$ docker compose up -d</div>
              <div className="text-[10px] text-zinc-400 font-sans leading-tight">Boots Postgres 16 DB, Redis 7 & 3 Worker Replicas.</div>
            </div>

            {/* Step 3 */}
            <div className="rounded-xl border-2 border-blue-500/50 bg-gradient-to-b from-blue-500/15 via-black/90 to-black/90 p-3 space-y-1 shadow-xl relative hover:border-blue-500/80 transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-4.5 w-4.5 items-center justify-center rounded-full bg-blue-500 text-black font-extrabold text-[10px]">3</span>
                  <span className="text-[10.5px] font-extrabold text-blue-300 uppercase tracking-wider">Run Agent Workflow</span>
                </div>
                <button
                  type="button"
                  onClick={() => copyToClipboard("python app.py", 3)}
                  className="text-[10px] bg-blue-500/20 border border-blue-500/40 text-blue-300 hover:bg-blue-500/30 px-2 py-0.5 rounded font-bold cursor-pointer flex items-center gap-1 transition-all"
                >
                  {copiedStep === 3 ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  <span>{copiedStep === 3 ? "Copied!" : "Copy"}</span>
                </button>
              </div>
              <div className="text-[11px] font-mono text-white font-bold bg-black/60 p-1.5 rounded-lg border border-white/10">$ python app.py</div>
              <div className="text-[10px] text-zinc-400 font-sans leading-tight">Submits workflow AST & streams 2-phase durable steps.</div>
            </div>

            {/* Step 4: Cluster Endpoints & Console UI */}
            <div className="rounded-xl border-2 border-purple-500/50 bg-gradient-to-b from-purple-500/15 via-black/90 to-black/90 p-3 space-y-1 shadow-xl relative hover:border-purple-500/80 transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-4.5 w-4.5 items-center justify-center rounded-full bg-purple-500 text-black font-extrabold text-[10px]">4</span>
                  <span className="text-[10.5px] font-extrabold text-purple-300 uppercase tracking-wider">Access Cluster UI</span>
                </div>
                <span className="text-[9.5px] bg-purple-500/20 border border-purple-500/40 text-purple-300 px-1.5 py-0.5 rounded font-bold">
                  Live Ports
                </span>
              </div>
              <div className="text-[11px] font-mono text-white font-bold bg-black/60 p-1.5 rounded-lg border border-white/10 flex items-center justify-between">
                <span>Console: <span className="text-amber-300 font-extrabold">:3000</span></span>
                <span className="text-zinc-400 text-[10px]">API: <span className="text-purple-300 font-extrabold">:8000</span></span>
              </div>
              <div className="text-[10px] text-zinc-400 font-sans leading-tight">Open <code className="text-amber-300 font-mono">localhost:3000</code> to inspect live runs & workers.</div>
            </div>
          </div>

          {/* Side-by-Side Code Preview Panes */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 shrink-0">
            {/* Pane 1: How Your Agent Code Looks (app.py - ZERO SCROLLING, 100% VISIBLE) */}
            <div className="rounded-xl border border-white/10 bg-black shadow-xl overflow-hidden flex flex-col h-[390px] hover:border-white/20 transition-all">
              <div className="flex items-center justify-between border-b border-white/10 bg-zinc-950 px-3.5 py-2 text-xs shrink-0">
                <div className="flex items-center gap-2">
                  <Code2 className="h-3.5 w-3.5 text-amber-400" />
                  <span className="text-white font-extrabold text-[12px]">How Your Agent Code Looks</span>
                  <span className="text-zinc-500 text-[10px]">(app.py)</span>
                </div>
              </div>

              <div className="p-3 bg-black/95 text-[10px] leading-[1.35] font-mono flex-1 overflow-hidden">
                <pre className="text-zinc-200">
                  <code>
                    <span className="text-purple-400 font-bold">import</span> <span className="text-white">anchor</span>, <span className="text-white">json</span>{"\n\n"}
                    <span className="text-zinc-500 italic"># Tool 1: Fetch Customer Data (Retry-Safe)</span>{"\n"}
                    <span className="text-amber-400 font-bold">@anchor.tool</span><span className="text-zinc-300">(safety=</span><span className="text-emerald-400">"retry_safe"</span><span className="text-zinc-300">, naturally_idempotent=</span><span className="text-rose-400 font-bold">True</span><span className="text-zinc-300">)</span>{"\n"}
                    <span className="text-purple-400 font-bold">def</span> <span className="text-blue-400 font-bold">fetch_customer</span><span className="text-zinc-300">(customer_id: </span><span className="text-cyan-300">str</span><span className="text-zinc-300">) -&gt; </span><span className="text-cyan-300">dict</span><span className="text-zinc-300">:</span>{"\n"}
                    <span className="text-purple-400 font-bold">    return</span> <span className="text-zinc-300">&#123;</span><span className="text-emerald-400">"id"</span><span className="text-zinc-300">: customer_id, </span><span className="text-emerald-400">"email"</span><span className="text-zinc-300">: </span><span className="text-emerald-400">"aditya@anchor.dev"</span><span className="text-zinc-300">, </span><span className="text-emerald-400">"tier"</span><span className="text-zinc-300">: </span><span className="text-emerald-400">"VIP"</span><span className="text-zinc-300">&#125;</span>{"\n\n"}
                    <span className="text-zinc-500 italic"># Tool 2: Dispatch Email Notification (Unsafe Side-Effect)</span>{"\n"}
                    <span className="text-amber-400 font-bold">@anchor.tool</span><span className="text-zinc-300">(safety=</span><span className="text-emerald-400">"unsafe"</span><span className="text-zinc-300">)</span>{"\n"}
                    <span className="text-purple-400 font-bold">def</span> <span className="text-blue-400 font-bold">send_welcome_email</span><span className="text-zinc-300">(email: </span><span className="text-cyan-300">str</span><span className="text-zinc-300">, tier: </span><span className="text-cyan-300">str</span><span className="text-zinc-300">) -&gt; </span><span className="text-cyan-300">dict</span><span className="text-zinc-300">:</span>{"\n"}
                    <span className="text-purple-400 font-bold">    return</span> <span className="text-zinc-300">&#123;</span><span className="text-emerald-400">"status"</span><span className="text-zinc-300">: </span><span className="text-emerald-400">"sent"</span><span className="text-zinc-300">, </span><span className="text-emerald-400">"to"</span><span className="text-zinc-300">: email, </span><span className="text-emerald-400">"tier"</span><span className="text-zinc-300">: tier&#125;</span>{"\n\n"}
                    <span className="text-zinc-500 italic"># 3. Multi-Tool Durable Agent Workflow</span>{"\n"}
                    <span className="text-amber-400 font-bold">@anchor.agent</span><span className="text-zinc-300">(name=</span><span className="text-emerald-400">"onboarding_agent"</span><span className="text-zinc-300">)</span>{"\n"}
                    <span className="text-purple-400 font-bold">def</span> <span className="text-blue-400 font-bold">onboarding_agent</span><span className="text-zinc-300">(ctx: anchor.StepContext):</span>{"\n"}
                    <span className="text-zinc-300">    customer = </span><span className="text-purple-400 font-bold">yield</span><span className="text-white font-bold"> anchor.ToolCall</span><span className="text-zinc-300">(</span><span className="text-emerald-400">"fetch_customer"</span><span className="text-zinc-300">, &#123;</span><span className="text-emerald-400">"customer_id"</span><span className="text-zinc-300">: ctx.input[</span><span className="text-emerald-400">"customer_id"</span><span className="text-zinc-300 font-bold">]&#125;)</span>{"\n"}
                    <span className="text-zinc-300">    email_res = </span><span className="text-purple-400 font-bold">yield</span><span className="text-white font-bold"> anchor.ToolCall</span><span className="text-zinc-300">(</span><span className="text-emerald-400">"send_welcome_email"</span><span className="text-zinc-300">, &#123;</span><span className="text-emerald-400">"email"</span><span className="text-zinc-300">: customer[</span><span className="text-emerald-400">"email"</span><span className="text-zinc-300">], </span><span className="text-emerald-400">"tier"</span><span className="text-zinc-300">: customer[</span><span className="text-emerald-400 font-bold">"tier"</span><span className="text-zinc-300 font-bold">]&#125;)</span>{"\n"}
                    <span className="text-purple-400 font-bold">    yield</span><span className="text-white font-bold"> anchor.Done</span><span className="text-zinc-300">(&#123;</span><span className="text-emerald-400">"status"</span><span className="text-zinc-300">: </span><span className="text-emerald-400">"completed"</span><span className="text-zinc-300 font-bold">, </span><span className="text-emerald-400">"customer"</span><span className="text-zinc-300">: customer, </span><span className="text-emerald-400 font-bold">"email"</span><span className="text-zinc-300">: email_res&#125;)</span>{"\n\n"}
                    <span className="text-zinc-500 italic"># 4. Trigger & Submit to Cluster</span>{"\n"}
                    <span className="text-purple-400 font-bold">if</span> <span className="text-rose-400">__name__</span> == <span className="text-emerald-400">"__main__"</span><span className="text-zinc-300">:</span>{"\n"}
                    <span className="text-zinc-300">    result = anchor.run(</span><span className="text-emerald-400">"onboarding_agent"</span><span className="text-zinc-300">, input=&#123;</span><span className="text-emerald-400">"customer_id"</span><span className="text-zinc-300">: </span><span className="text-emerald-400">"cust_99"</span><span className="text-zinc-300">&#125;)</span>{"\n"}
                    <span className="text-blue-400">    print</span><span className="text-zinc-300">(json.dumps(result, indent=</span><span className="text-amber-400">2</span><span className="text-zinc-300">))</span>
                  </code>
                </pre>
              </div>

              <div className="flex items-center justify-between border-t border-white/10 bg-zinc-950 px-3.5 py-1 text-[10px] text-zinc-400 shrink-0">
                <span className="text-emerald-400 flex items-center gap-1.5 font-semibold">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  <span>Python 3.12 SDK</span>
                </span>
                <span className="text-zinc-500">Auto .env • Multi-Tool Replay</span>
              </div>
            </div>

            {/* Pane 2: How Your Cluster Is Configured (docker-compose.yml - SCROLLABLE) */}
            <div className="rounded-xl border border-white/10 bg-black shadow-xl overflow-hidden flex flex-col h-[390px] hover:border-white/20 transition-all">
              <div className="flex items-center justify-between border-b border-white/10 bg-zinc-950 px-3.5 py-2 text-xs shrink-0">
                <div className="flex items-center gap-2">
                  <Server className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-white font-extrabold text-[12px]">How Your Cluster Is Configured</span>
                  <span className="text-zinc-500 text-[10px]">(docker-compose.yml)</span>
                </div>

                <button
                  type="button"
                  onClick={copyDockerCompose}
                  className="text-[10px] text-emerald-300 hover:text-white font-bold cursor-pointer flex items-center gap-1 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded transition-all"
                >
                  {copiedCompose ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  <span>{copiedCompose ? "Copied YAML" : "Copy YAML"}</span>
                </button>
              </div>

              <div className="p-3 bg-black/95 text-[10.5px] leading-relaxed font-mono flex-1 overflow-y-auto custom-scrollbar">
                <pre className="text-zinc-300">
                  <code>{sampleDockerCompose}</code>
                </pre>
              </div>

              <div className="flex items-center justify-between border-t border-white/10 bg-zinc-950 px-3.5 py-1 text-[10px] text-zinc-400 shrink-0">
                <span className="text-zinc-400 flex items-center gap-1.5 font-semibold">
                  <span className="h-1.5 w-1.5 rounded-full bg-zinc-400" />
                  <span>Docker Compose Stack</span>
                </span>
                <span className="text-zinc-500">Postgres 16 • Redis 7 • 3 Workers</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Close Action */}
        <div className="flex items-center justify-end pt-2 border-t border-white/10 shrink-0">
          <button
            type="button"
            onClick={handleClose}
            className="rounded-xl border border-amber-500/40 bg-amber-500/20 px-5 py-1 text-xs font-bold text-amber-300 hover:bg-amber-500/35 transition-all cursor-pointer shadow-md"
          >
            Close Guide
          </button>
        </div>
      </div>
    </div>
  );
};

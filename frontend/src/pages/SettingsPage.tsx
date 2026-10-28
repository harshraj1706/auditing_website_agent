import React, { useEffect, useState } from 'react';
import { Sidebar } from '../components/Sidebar';
import { api } from '../services/api';
import type { HealthResponse } from '../types/audit';
import {
  Settings,
  Server,
  ShieldCheck,
  Database,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = () => {
    setLoading(true);
    api
      .checkHealth()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#0B0F17] text-slate-100">
      <Sidebar />

      <main className="flex-1 p-6 md:p-10 max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Settings className="w-4 h-4" />
              SYSTEM DIAGNOSTICS & ENGINE CONFIGURATION
            </div>
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">
              Engine Diagnostics & Info
            </h1>
          </div>

          <button
            type="button"
            onClick={fetchHealth}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
            Refresh Health
          </button>
        </div>

        {/* Backend & Engine Diagnostics Card */}
        <div className="p-6 rounded-2xl bg-[#111827] border border-slate-800 space-y-6 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-cyan-950/60 border border-cyan-800/60 flex items-center justify-center text-cyan-400">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-100">
                  FastAPI REST Engine Status
                </h2>
                <p className="text-xs text-slate-400">
                  Real-time status of backend orchestrator and filesystem integrity
                </p>
              </div>
            </div>

            {health?.engine_ready ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-950/60 text-emerald-400 text-xs font-mono font-semibold border border-emerald-800/60">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Operational
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-950/60 text-rose-400 text-xs font-mono font-semibold border border-rose-800/60">
                <AlertTriangle className="w-3.5 h-3.5" />
                Offline / Unreachable
              </span>
            )}
          </div>

          {health && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-[#0B0F17] border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400">API Version:</span>
                <span className="text-cyan-300 font-bold">{health.version}</span>
              </div>
              <div className="p-3 rounded-lg bg-[#0B0F17] border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400">Python Stdlib:</span>
                <span className="text-emerald-400 font-bold">Verified 3.10+</span>
              </div>
              <div className="p-3 rounded-lg bg-[#0B0F17] border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400">Marketplace Manifest:</span>
                <span className={health.details?.marketplace_json ? 'text-emerald-400' : 'text-rose-400'}>
                  {health.details?.marketplace_json ? 'Present' : 'Missing'}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-[#0B0F17] border border-slate-800 flex items-center justify-between">
                <span className="text-slate-400">Report Schema JSON:</span>
                <span className={health.details?.report_schema_json ? 'text-emerald-400' : 'text-rose-400'}>
                  {health.details?.report_schema_json ? 'Loaded' : 'Missing'}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Operating Safeguards & Architecture Card */}
        <div className="p-6 rounded-2xl bg-[#111827] border border-slate-800 space-y-4 shadow-xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-teal-950/60 border border-teal-800/60 flex items-center justify-center text-teal-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">
                Operating Safeguards & Crawl Boundaries
              </h2>
              <p className="text-xs text-slate-400">
                Hard constraints enforced across all crawl and inspection skills
              </p>
            </div>
          </div>

          <div className="space-y-3 text-xs text-slate-300">
            <div className="p-3.5 rounded-xl bg-[#0B0F17] border border-slate-800/80 space-y-1">
              <div className="font-semibold text-slate-200">1. Strict Robots.txt Compliance</div>
              <p className="text-slate-400">
                The engine evaluates robots.txt before crawling and honors disallow rules for AI fetchers.
              </p>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0B0F17] border border-slate-800/80 space-y-1">
              <div className="font-semibold text-slate-200">2. Bounded Budget (≤12 Pages, &lt;5 Minutes)</div>
              <p className="text-slate-400">
                Crawls are capped at 12 representative pages on origin, with a 12s per-request timeout.
              </p>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0B0F17] border border-slate-800/80 space-y-1">
              <div className="font-semibold text-slate-200">3. Safe Read-Only (Zero Live Writes)</div>
              <p className="text-slate-400">
                Recommend-only architecture. Never invokes live forms, cart flows, or mutations.
              </p>
            </div>
          </div>
        </div>

        {/* Phase 3 Roadmap Notice */}
        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2.5 text-slate-300 font-semibold text-sm">
            <Database className="w-4 h-4 text-cyan-400" />
            <span>Phase 3 Architecture Roadmap</span>
            <span className="ml-auto text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              Upcoming
            </span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Persistent PostgreSQL/Supabase storage, multi-user authentication, team workspaces,
            and scheduled recurring website monitoring are scoped for Phase 3. The current phase
            operates with a fast, zero-dependency in-process job store.
          </p>
        </div>
      </main>
    </div>
  );
};

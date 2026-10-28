import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { StatusBadge } from '../components/StatusBadge';
import { sessionStore } from '../services/sessionStore';
import type { AuditHistoryItem } from '../types/audit';
import {
  Clock,
  ArrowRight,
  PlusCircle,
  Trash2,
  Info,
} from 'lucide-react';

export const RecentAuditsPage: React.FC = () => {
  const [audits, setAudits] = useState<AuditHistoryItem[]>([]);

  useEffect(() => {
    setAudits(sessionStore.getAudits());
  }, []);

  const handleClear = () => {
    sessionStore.clear();
    setAudits([]);
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#0B0F17] text-slate-100">
      <Sidebar />

      <main className="flex-1 p-6 md:p-10 max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Clock className="w-4 h-4" />
              SESSION AUDIT LOG
            </div>
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">
              Recent Website Audits
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {audits.length > 0 && (
              <button
                type="button"
                onClick={handleClear}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                Clear Session
              </button>
            )}
            <Link
              to="/audit/new"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-400 hover:from-cyan-400 hover:to-teal-300 text-slate-950 font-bold text-xs shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all"
            >
              <PlusCircle className="w-4 h-4" />
              New Audit
            </Link>
          </div>
        </div>

        {/* Honest Session Scope Warning Banner */}
        <div className="flex items-start gap-3 p-4 rounded-xl bg-cyan-950/30 border border-cyan-800/40 text-cyan-300 text-xs leading-relaxed">
          <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-cyan-400" />
          <div>
            <strong className="text-cyan-200">Session-Only Storage:</strong> Audits listed here reflect executions submitted during your current browser session. In this development phase, jobs are held in the API's in-process store and browser memory. Persistent database history (Supabase/PostgreSQL) is scoped for subsequent production phases.
          </div>
        </div>

        {/* Audits Table */}
        {audits.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-[#111827] border border-slate-800 space-y-4">
            <Clock className="w-12 h-12 text-slate-600 mx-auto" />
            <h3 className="text-lg font-bold text-slate-200">No Audits in Current Session</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              You haven't run any audits yet in this session. Start a new audit to inspect website AI-readiness.
            </p>
            <Link
              to="/audit/new"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs transition-colors"
            >
              Start First Audit
            </Link>
          </div>
        ) : (
          <div className="rounded-xl bg-[#111827] border border-slate-800 overflow-hidden shadow-lg">
            <div className="divide-y divide-slate-800">
              {audits.map((item) => (
                <div
                  key={item.audit_id}
                  className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-800/40 transition-colors"
                >
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-sm font-bold text-slate-100">
                        {item.url}
                      </span>
                      <StatusBadge status={item.status} size="sm" />
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400">
                      <span>ID: {item.audit_id.slice(0, 16)}...</span>
                      <span>Submitted: {new Date(item.created_at).toLocaleTimeString()}</span>
                      {item.total_findings !== undefined && (
                        <span className="text-cyan-400 font-semibold">
                          {item.total_findings} findings ({item.critical || 0} critical)
                        </span>
                      )}
                    </div>
                  </div>

                  <Link
                    to={`/audit/${item.audit_id}`}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold self-start sm:self-center transition-colors"
                  >
                    View Report <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
